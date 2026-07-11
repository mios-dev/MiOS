#!/usr/bin/env python3
import os
import sys
import json
import logging
import shutil

logging.basicConfig(level=logging.INFO, format="[materialize-user-config] %(levelname)s: %(message)s")
log = logging.getLogger("materialize-user-config")

def get_pg_config():
    e = os.environ
    return {
        "host": e.get("MIOS_PG_HOST", "localhost"),
        "port": int(e.get("MIOS_PORT_PGVECTOR", "8432") or 8432),
        "user": e.get("MIOS_PG_USER", "mios"),
        "password": e.get("MIOS_PG_PASS", "mios"),
        "dbname": e.get("MIOS_PG_DB", "mios"),
    }

def dict_to_toml(d):
    lines = []
    # Write top-level key-values first
    for k, v in sorted(d.items()):
        if not isinstance(v, dict):
            lines.append(f"{k} = {json.dumps(v)}")
    # Write sections
    for section, content in sorted(d.items()):
        if isinstance(content, dict):
            if lines:
                lines.append("")
            lines.append(f"[{section}]")
            for k, v in sorted(content.items()):
                lines.append(f"{k} = {json.dumps(v)}")
    return "\n".join(lines) + "\n"

def parse_simple_toml(filepath):
    # A basic parser for mios.toml fallback files
    res = {}
    current_section = None
    if not os.path.isfile(filepath):
        return res
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    current_section = line[1:-1].strip()
                    if current_section not in res:
                        res[current_section] = {}
                elif "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    try:
                        parsed_val = json.loads(v)
                    except Exception:
                        # Strip outer quotes if json parsing failed
                        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                            parsed_val = v[1:-1]
                        else:
                            parsed_val = v
                    if current_section:
                        res[current_section][k] = parsed_val
                    else:
                        res[k] = parsed_val
    except Exception as e:
        log.warning("Failed to parse fallback TOML %s: %s", filepath, e)
    return res

def main():
    toml_path = os.environ.get("MIOS_TOML", "/etc/mios/mios.toml")
    if not os.path.isfile(toml_path):
        toml_path = "/usr/share/mios/mios.toml"
        
    db_render_prefs = False
    if os.path.isfile(toml_path):
        # Quick parse to check db_render_prefs setting
        try:
            cfg = parse_simple_toml(toml_path)
            db_render_prefs = cfg.get("accounts", {}).get("db_render_prefs", False)
        except Exception as e:
            log.warning("Error parsing system mios.toml: %s", e)

    if not db_render_prefs:
        log.info("Database-backed user preference rendering is disabled.")
        return 0

    try:
        import psycopg
    except ImportError:
        log.warning("psycopg is not installed. Skipping user config materialization.")
        return 0

    pg_cfg = get_pg_config()
    conn_str = (f"postgresql://{pg_cfg['user']}:{pg_cfg['password']}"
                f"@{pg_cfg['host']}:{pg_cfg['port']}/{pg_cfg['dbname']}")

    try:
        with psycopg.connect(conn_str, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Resolve active accounts and their layered preferences
                cur.execute(
                    """
                    SELECT a.id, a.name, a.home_dir, a.uid, a.gid, ap.key, ap.value
                    FROM account a
                    LEFT JOIN account_preference ap ON a.id = ap.account_id
                    WHERE a.enabled = true
                    ORDER BY a.name, ap.layer ASC;
                    """
                )
                rows = cur.fetchall()
                if not rows:
                    log.info("No active accounts found in database.")
                    return 0

                # Group by account name
                accounts = {}
                for r_id, r_name, r_home_dir, r_uid, r_gid, p_key, p_value in rows:
                    if r_name not in accounts:
                        accounts[r_name] = {
                            "home_dir": r_home_dir or f"/home/{r_name}",
                            "uid": r_uid,
                            "gid": r_gid,
                            "prefs": {}
                        }
                    if p_key is not None:
                        accounts[r_name]["prefs"][p_key] = p_value

                for name, info in accounts.items():
                    home_dir = info["home_dir"]
                    uid = info["uid"]
                    gid = info["gid"]
                    prefs = info["prefs"]

                    log.info("Processing account: %s (home: %s)", name, home_dir)

                    # Initialize default user config from skel
                    user_toml = {}
                    skel_path = "/etc/skel/.config/mios/mios.toml"
                    if os.path.isfile(skel_path):
                        user_toml = parse_simple_toml(skel_path)
                    else:
                        # Fallback to general mios.toml template
                        general_path = "/usr/share/mios/mios.toml"
                        if os.path.isfile(general_path):
                            user_toml = parse_simple_toml(general_path)

                    user_files = {}

                    # Apply preferences
                    for key, val in prefs.items():
                        if key.startswith("file:"):
                            rel_path = key[5:]
                            user_files[rel_path] = val
                        else:
                            if "." in key:
                                sec, k = key.split(".", 1)
                                if sec not in user_toml:
                                    user_toml[sec] = {}
                                user_toml[sec][k] = val
                            else:
                                user_toml[key] = val

                    # Render default mios.toml if not explicitly overridden by file: key
                    default_toml_rel = ".config/mios/mios.toml"
                    if default_toml_rel not in user_files:
                        user_files[default_toml_rel] = dict_to_toml(user_toml)

                    # Materialize files idempotently
                    for rel_path, content in user_files.items():
                        target_file = os.path.abspath(os.path.join(home_dir, rel_path))
                        # Prevent writing outside user home
                        if not target_file.startswith(os.path.abspath(home_dir)):
                            log.warning("Security: skipping path %s outside home directory %s", rel_path, home_dir)
                            continue

                        # Ensure parent directories exist
                        parent_dir = os.path.dirname(target_file)
                        if not os.path.isdir(parent_dir):
                            os.makedirs(parent_dir, exist_ok=True)
                            if uid is not None and gid is not None:
                                try:
                                    os.chown(parent_dir, uid, gid)
                                except Exception as err:
                                    log.warning("Failed to chown directory %s: %s", parent_dir, err)

                        # Write file only if content has changed
                        existing_content = None
                        if os.path.isfile(target_file):
                            try:
                                with open(target_file, "r", encoding="utf-8") as f:
                                    existing_content = f.read()
                            except Exception:
                                pass

                        # Convert non-string content to raw content if needed
                        if not isinstance(content, str):
                            content = json.dumps(content, indent=2)

                        if existing_content != content:
                            with open(target_file, "w", encoding="utf-8") as f:
                                f.write(content)
                            log.info("Materialized file: %s", target_file)

                        # Adjust permissions and ownership
                        if uid is not None and gid is not None:
                            try:
                                os.chown(target_file, uid, gid)
                            except Exception as err:
                                log.warning("Failed to chown file %s: %s", target_file, err)

    except Exception as e:
        log.error("Failed to materialize user configs: %s", e)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
