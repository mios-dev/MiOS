import os
import json
import logging
import time

log = logging.getLogger("mios-agent-pipe")

# In-memory config overrides cache, populated from database
_DB_CONFIG_CACHE: dict = {}
_LAST_DB_SYNC = 0.0
_SYNC_INTERVAL_S = 60.0  # Sync with DB every 60 seconds
_DB_DOWN_UNTIL = 0.0
_BACKOFF_S = 30.0

def _get_pg_config():
    e = os.environ
    return {
        "host": e.get("MIOS_PG_HOST", "localhost"),
        "port": int(e.get("MIOS_PORT_PGVECTOR", "8432") or 8432),
        "user": e.get("MIOS_PG_USER", "mios"),
        "password": e.get("MIOS_PG_PASS", "mios"),
        "dbname": e.get("MIOS_PG_DB", "mios"),
    }

def _sync_config_from_db():
    global _LAST_DB_SYNC, _DB_CONFIG_CACHE, _DB_DOWN_UNTIL
    now = time.monotonic()
    if now < _DB_DOWN_UNTIL:
        return
    if now - _LAST_DB_SYNC < _SYNC_INTERVAL_S and _DB_CONFIG_CACHE:
        return
    
    try:
        import psycopg
        from psycopg.rows import dict_row
        cfg = _get_pg_config()
        conn_str = (f"postgresql://{cfg['user']}:{cfg['password']}"
                    f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}")
        with psycopg.connect(conn_str, connect_timeout=2) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT key, value FROM system_config;")
                rows = cur.fetchall()
                new_cache = {}
                for row in rows:
                    new_cache[row["key"]] = row["value"]
                _DB_CONFIG_CACHE = new_cache
                _LAST_DB_SYNC = now
    except Exception as e:
        _DB_DOWN_UNTIL = now + _BACKOFF_S
        log.debug("Database config sync failed (degrading to TOML/Env): %s", e)

def get_config(key: str, default=None):
    """Retrieve config value. Hierarchy:
    1. Process environment variable (MIOS_<key_upper>)
    2. Dynamic DB config override (system_config table)
    3. Layered mios.toml (via _toml_section)
    """
    env_key = "MIOS_" + key.upper().replace(".", "_")
    if env_key in os.environ:
        return os.environ[env_key]
    
    _sync_config_from_db()
    if key in _DB_CONFIG_CACHE:
        return _DB_CONFIG_CACHE[key]
    
    if "." in key:
        sec, k = key.split(".", 1)
        from mios_config import _toml_section
        sect = _toml_section(sec)
        parts = k.split(".")
        val = sect
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                val = None
                break
        if val is not None:
            return val
            
    return default
