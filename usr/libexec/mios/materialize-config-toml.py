#!/usr/bin/env python3
import os
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="[materialize-config-toml] %(levelname)s: %(message)s")
log = logging.getLogger("materialize-config-toml")

def get_pg_config():
    e = os.environ
    return {
        "host": e.get("MIOS_PG_HOST", "localhost"),
        "port": int(e.get("MIOS_PORT_PGVECTOR", "8432") or 8432),
        "user": e.get("MIOS_PG_USER", "mios"),
        "password": e.get("MIOS_PG_PASS", "mios"),
        "dbname": e.get("MIOS_PG_DB", "mios"),
    }

def format_toml_value(val):
    if isinstance(val, bool):
        return "true" if val else "false"
    elif isinstance(val, int):
        return str(val)
    elif isinstance(val, str):
        escaped = val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    elif isinstance(val, list):
        items = [format_toml_value(x) for x in val]
        return "[" + ", ".join(items) + "]"
    elif isinstance(val, dict):
        items = [f"{k} = {format_toml_value(v)}" for k, v in sorted(val.items())]
        return "{" + ", ".join(items) + "}"
    else:
        return str(val)

def escape_toml_key(k):
    import re
    if re.match(r"^[A-Za-z0-9_-]+$", k):
        return k
    escaped = k.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'

def main():
    try:
        import psycopg
    except ImportError:
        log.error("psycopg not installed.")
        return 1
        
    cfg = get_pg_config()
    conn_str = (f"postgresql://{cfg['user']}:{cfg['password']}"
                f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}")
                
    try:
        with psycopg.connect(conn_str, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # 1. Read config_kv
                cur.execute(
                    """
                    SELECT scope, key, value FROM config_kv
                    WHERE layer = 0
                    ORDER BY scope, key;
                    """
                )
                rows = cur.fetchall()
                
                # Group by scope
                config_by_scope = {}
                for scope, key, value_json in rows:
                    if scope == 'verbs':
                        continue  # handled separately
                    if scope not in config_by_scope:
                        config_by_scope[scope] = {}
                    config_by_scope[scope][key] = value_json

                # We output standard sections in original order if they exist, else alphabetical
                sections_order = ["ports", "ai", "routing", "pgvector", "a2a", "mcp", "observability", "sandbox", "security", "agent_passport", "agent_pipe"]
                all_scopes = list(config_by_scope.keys())
                for s in sections_order:
                    if s not in all_scopes and s in config_by_scope:
                        all_scopes.append(s)
                # Sort all_scopes so that standard sections come first in the predefined order
                def scope_key(sc):
                    try:
                        return sections_order.index(sc)
                    except ValueError:
                        return len(sections_order)
                all_scopes.sort(key=scope_key)

                # Output each section
                first_printed = False
                for scope in all_scopes:
                    # Sort keys
                    keys = sorted(config_by_scope[scope].keys())
                    
                    # Print standard keys
                    printed_section_header = False
                    for k in keys:
                        v = config_by_scope[scope][k]
                        if isinstance(v, dict):
                            # If value is a dict, it represents a sub-table like [ai.vllm]
                            continue
                        if not printed_section_header:
                            if first_printed:
                                print("")
                            print(f"[{escape_toml_key(scope)}]")
                            printed_section_header = True
                            first_printed = True
                        print(f"{k} = {format_toml_value(v)}")
                    
                    # Print sub-tables (dicts)
                    for k in keys:
                        v = config_by_scope[scope][k]
                        if isinstance(v, dict):
                            if first_printed:
                                print("")
                            print(f"[{escape_toml_key(scope)}.{escape_toml_key(k)}]")
                            first_printed = True
                            for sub_k in sorted(v.keys()):
                                print(f"{sub_k} = {format_toml_value(v[sub_k])}")

                # 2. Output routing domains from domain_verb
                cur.execute(
                    """
                    SELECT domain, description, array_agg(verb_name ORDER BY verb_name)
                    FROM domain_verb
                    GROUP BY domain, description
                    ORDER BY domain;
                    """
                )
                domain_rows = cur.fetchall()
                for domain, desc, verbs_list in domain_rows:
                    if first_printed:
                        print("")
                    print(f"[routing.domains.{escape_toml_key(domain)}]")
                    first_printed = True
                    if desc:
                        print(f"desc = {format_toml_value(desc)}")
                    # Convert psycopg array wrapper to standard list
                    v_list = list(verbs_list)
                    print(f"verbs = {format_toml_value(v_list)}")

                # 3. Read verbs._defaults
                cur.execute(
                    """
                    SELECT value FROM config_kv
                    WHERE scope = 'verbs' AND key = '_defaults' AND layer = 0;
                    """
                )
                def_row = cur.fetchone()
                defaults = def_row[0] if def_row else {}

                # Print defaults
                if first_printed:
                    print("")
                print("[verbs._defaults]")
                first_printed = True
                for k in sorted(defaults.keys()):
                    print(f"{k} = {format_toml_value(defaults[k])}")

                # 4. Read verbs
                cur.execute(
                    """
                    SELECT name, sig, desc_default, tier, permission, cmd, params,
                           section, examples, model_name, hidden, aliases,
                           conflict_group, parallel_limit, max_result_chars
                    FROM verb
                    ORDER BY name;
                    """
                )
                verb_rows = cur.fetchall()
                for (vname, sig, desc, tier, perm, cmd, params,
                     section, examples, model_name, hidden, aliases,
                     conflict_group, parallel_limit, max_result_chars) in verb_rows:
                    
                    if first_printed:
                        print("")
                    print(f"[verbs.{escape_toml_key(vname)}]")
                    first_printed = True
                    # Collect keys to print if they differ from default
                    if sig:
                        print(f"sig = {format_toml_value(sig)}")
                    if desc:
                        print(f"desc = {format_toml_value(desc)}")
                    
                    # Optional fields with defaults
                    if section:
                        print(f"section = {format_toml_value(section)}")
                    if examples:
                        # examples is jsonb (list)
                        print(f"examples = {format_toml_value(examples)}")
                    
                    if tier != defaults.get("tier", "common"):
                        print(f"tier = {format_toml_value(tier)}")
                    if perm != defaults.get("permission", "read"):
                        print(f"permission = {format_toml_value(perm)}")
                    if cmd:
                        print(f"cmd = {format_toml_value(cmd)}")
                    if model_name:
                        print(f"model_name = {format_toml_value(model_name)}")
                    if hidden != defaults.get("hidden", False):
                        print(f"hidden = {format_toml_value(hidden)}")
                    if aliases:
                        print(f"hidden_aliases = {format_toml_value(aliases)}")
                    if conflict_group:
                        print(f"conflict_group = {format_toml_value(conflict_group)}")
                    if parallel_limit != defaults.get("parallel_limit", 0):
                        print(f"parallel_limit = {format_toml_value(parallel_limit)}")
                    if max_result_chars != defaults.get("max_result_chars", 0):
                        print(f"max_result_chars = {format_toml_value(max_result_chars)}")
                        
                    # Print parameters
                    if params:
                        for param_k in sorted(params.keys()):
                            param_v = params[param_k]
                            print(f"\n  [verbs.{escape_toml_key(vname)}.params.{escape_toml_key(param_k)}]")
                            for pk in sorted(param_v.keys()):
                                print(f"  {pk} = {format_toml_value(param_v[pk])}")

    except Exception as e:
        log.error("Materialization failed: %s", e)
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
