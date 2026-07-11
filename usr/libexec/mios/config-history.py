#!/usr/bin/env python3
import os
import sys
import argparse
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="[config-history] %(levelname)s: %(message)s")
log = logging.getLogger("config-history")

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
    parser = argparse.ArgumentParser(description="Query the audit log of configuration changes.")
    parser.add_argument("key", nargs="?", help="Filter logs by a specific configuration key (e.g., ai.model).")
    parser.add_argument("--scope", "-s", help="Filter logs by scope/table name (e.g. config_kv, verb, domain_verb).")
    parser.add_argument("--limit", "-l", type=int, default=50, help="Limit the number of history entries displayed.")

    args = parser.parse_args()

    try:
        import psycopg
    except ImportError:
        log.error("psycopg is not installed. Cannot query configuration history.")
        return 1

    pg_cfg = get_pg_config()
    conn_str = (f"postgresql://{pg_cfg['user']}:{pg_cfg['password']}"
                f"@{pg_cfg['host']}:{pg_cfg['port']}/{pg_cfg['dbname']}")

    try:
        with psycopg.connect(conn_str, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = "SELECT ts, scope, key, old_value, new_value, actor, source FROM config_event"
                filters = []
                params = []

                if args.key:
                    filters.append("key = %s")
                    params.append(args.key)
                if args.scope:
                    filters.append("scope = %s")
                    params.append(args.scope)

                if filters:
                    query += " WHERE " + " AND ".join(filters)

                query += " ORDER BY ts ASC LIMIT %s"
                params.append(args.limit)

                cur.execute(query, params)
                rows = cur.fetchall()

                if not rows:
                    print("No configuration events found matching query.")
                    return 0

                print(f"{'TIMESTAMP':<25} | {'SCOPE':<12} | {'KEY':<30} | {'OLD VALUE':<15} -> {'NEW VALUE':<15} | {'ACTOR':<10} | {'SOURCE':<15}")
                print("-" * 135)
                for ts, scope, key, old_val, new_val, actor, source in rows:
                    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts, datetime) else str(ts)
                    old_str = str(old_val) if old_val is not None else "<none>"
                    new_str = str(new_val) if new_val is not None else "<none>"
                    actor_str = str(actor) if actor is not None else "<system>"
                    source_str = str(source) if source is not None else "<unknown>"

                    # Truncate values to fit formatting
                    if len(old_str) > 15:
                        old_str = old_str[:12] + "..."
                    if len(new_str) > 15:
                        new_str = new_str[:12] + "..."

                    print(f"{ts_str:<25} | {scope:<12} | {key:<30} | {old_str:<15} -> {new_str:<15} | {actor_str:<10} | {source_str:<15}")

    except Exception as e:
        log.error("Failed to query configuration history: %s", e)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
