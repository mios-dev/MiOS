#!/usr/bin/env python3
import os
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="[seed-db-config] %(levelname)s: %(message)s")
log = logging.getLogger("seed-db-config")

def get_pg_config():
    e = os.environ
    return {
        "host": e.get("MIOS_PG_HOST", "localhost"),
        "port": int(e.get("MIOS_PORT_PGVECTOR", "8432") or 8432),
        "user": e.get("MIOS_PG_USER", "mios"),
        "password": e.get("MIOS_PG_PASS", "mios"),
        "dbname": e.get("MIOS_PG_DB", "mios"),
    }

def main():
    try:
        import psycopg
    except ImportError:
        log.error("psycopg not installed. Skipping database seeding.")
        return 0
        
    toml_path = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
    if not os.path.isfile(toml_path):
        log.error("mios.toml not found at %s", toml_path)
        return 1
        
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with open(toml_path, "rb") as fh:
            data = tomllib.load(fh)
    except Exception as e:
        log.error("Failed to parse mios.toml: %s", e)
        return 1
        
    cfg = get_pg_config()
    conn_str = (f"postgresql://{cfg['user']}:{cfg['password']}"
                f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}")
                
    try:
        with psycopg.connect(conn_str, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                log.info("Connected to database. Starting seeding...")
                
                # 1. Seed system_config
                sections = ["ports", "ai", "routing", "surrealdb", "pgvector", "a2a", "mcp", "observability", "sandbox", "security", "agent_passport", "agent_pipe"]
                for sec in sections:
                    sec_data = data.get(sec) or {}
                    if not isinstance(sec_data, dict):
                        continue
                    for k, val in sec_data.items():
                        if sec == "routing" and k in ("domains", "nohc_allowlist"):
                            continue
                        db_key = f"{sec}.{k}"
                        cur.execute(
                            """
                            INSERT INTO system_config (key, value, description)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
                            """,
                            (db_key, json.dumps(val), f"Default configuration for {db_key}")
                        )
                log.info("System configuration seeded.")

                # 1b. Seed verbs._defaults to config_kv
                verbs = data.get("verbs") or {}
                defaults = verbs.get("_defaults") or {}
                cur.execute(
                    """
                    INSERT INTO config_kv (scope, key, value, layer, description)
                    VALUES ('verbs', '_defaults', %s, 0, 'Verbs defaults')
                    ON CONFLICT (scope, key, layer) DO UPDATE SET value = EXCLUDED.value;
                    """,
                    (json.dumps(defaults),)
                )

                # 1c. Seed config_kv (V0 layer foundation)
                for sec in sections:
                    sec_data = data.get(sec) or {}
                    if not isinstance(sec_data, dict):
                        continue
                    for k, val in sec_data.items():
                        if sec == "routing" and k == "domains":
                            continue
                        cur.execute(
                            """
                            INSERT INTO config_kv (scope, key, value, layer, description)
                            VALUES (%s, %s, %s, 0, %s)
                            ON CONFLICT (scope, key, layer) DO UPDATE SET value = EXCLUDED.value;
                            """,
                            (sec, k, json.dumps(val), f"Vendor default for {sec}.{k}")
                        )
                log.info("config_kv seeded.")
                
                # 2. Seed verbs
                verbs = data.get("verbs") or {}
                defaults = verbs.get("_defaults") or {}
                if isinstance(verbs, dict):
                    for vname, vcfg in verbs.items():
                        if vname == "_defaults" or not isinstance(vcfg, dict):
                            continue
                        merged = defaults.copy()
                        merged.update(vcfg)
                        
                        sig = str(merged.get("sig", ""))
                        desc = str(merged.get("desc", ""))
                        tier = str(merged.get("tier", "common"))
                        perm = str(merged.get("permission", "read"))
                        cmd = merged.get("cmd")
                        if cmd is not None:
                            cmd = str(cmd)
                        params = merged.get("params") or {}
                        
                        # Extra fields to satisfy lossless round-trip requirements
                        section = merged.get("section")
                        examples = merged.get("examples")
                        model_name = merged.get("model_name")
                        hidden = bool(merged.get("hidden", False))
                        aliases = merged.get("aliases")
                        conflict_group = merged.get("conflict_group")
                        parallel_limit = int(merged.get("parallel_limit", 0))
                        max_result_chars = int(merged.get("max_result_chars", 0))
                        
                        examples_json = json.dumps(examples) if examples is not None else None
                        aliases_json = json.dumps(aliases) if aliases is not None else None
                        
                        cur.execute(
                            """
                            INSERT INTO verb (name, sig, desc_default, tier, permission, cmd, params,
                                              section, examples, model_name, hidden, aliases,
                                              conflict_group, parallel_limit, max_result_chars)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (name) DO UPDATE SET
                                sig = EXCLUDED.sig,
                                desc_default = EXCLUDED.desc_default,
                                tier = EXCLUDED.tier,
                                permission = EXCLUDED.permission,
                                cmd = EXCLUDED.cmd,
                                params = EXCLUDED.params,
                                section = EXCLUDED.section,
                                examples = EXCLUDED.examples,
                                model_name = EXCLUDED.model_name,
                                hidden = EXCLUDED.hidden,
                                aliases = EXCLUDED.aliases,
                                conflict_group = EXCLUDED.conflict_group,
                                parallel_limit = EXCLUDED.parallel_limit,
                                max_result_chars = EXCLUDED.max_result_chars;
                            """,
                            (
                                vname, sig, desc, tier, perm, cmd, json.dumps(params),
                                section, examples_json, model_name, hidden, aliases_json,
                                conflict_group, parallel_limit, max_result_chars
                            )
                        )
                log.info("Verbs seeded.")
                
                # 3. Seed domain_verb mapping
                routing = data.get("routing") or {}
                domains = routing.get("domains") or {}
                if isinstance(domains, dict):
                    cur.execute("TRUNCATE TABLE domain_verb;")
                    for dom, dom_cfg in domains.items():
                        if not isinstance(dom_cfg, dict):
                            continue
                        vlist = dom_cfg.get("verbs") or []
                        desc = dom_cfg.get("desc") or ""
                        for vname in vlist:
                            cur.execute("SELECT 1 FROM verb WHERE name = %s;", (vname,))
                            if cur.fetchone():
                                cur.execute(
                                    """
                                    INSERT INTO domain_verb (domain, verb_name, description)
                                    VALUES (%s, %s, %s)
                                    ON CONFLICT (domain, verb_name) DO UPDATE SET description = EXCLUDED.description;
                                    """,
                                    (dom, vname, desc)
                                )
                log.info("Domain verb mappings seeded.")
                conn.commit()
                log.info("Seeding completed successfully.")
    except Exception as e:
        log.error("Database seeding failed: %s", e)
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
