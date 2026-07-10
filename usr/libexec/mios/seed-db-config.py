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
                        
                        cur.execute(
                            """
                            INSERT INTO verb (name, sig, desc_default, tier, permission, cmd, params)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (name) DO UPDATE SET
                                sig = EXCLUDED.sig,
                                desc_default = EXCLUDED.desc_default,
                                tier = EXCLUDED.tier,
                                permission = EXCLUDED.permission,
                                cmd = EXCLUDED.cmd,
                                params = EXCLUDED.params;
                            """,
                            (vname, sig, desc, tier, perm, cmd, json.dumps(params))
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
                        for vname in vlist:
                            cur.execute("SELECT 1 FROM verb WHERE name = %s;", (vname,))
                            if cur.fetchone():
                                cur.execute(
                                    """
                                    INSERT INTO domain_verb (domain, verb_name)
                                    VALUES (%s, %s)
                                    ON CONFLICT DO NOTHING;
                                    """,
                                    (dom, vname)
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
