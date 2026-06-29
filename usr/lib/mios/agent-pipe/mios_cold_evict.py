# AI-hint: Cold-export and zstd compression module for knowledge table eviction (CONV-09).
# usr/lib/mios/agent-pipe/mios_cold_evict.py

import os
import json
import uuid
import datetime
import subprocess
from pathlib import Path

import mios_evict

async def export_to_cold(pg, row_ids: list[int], table: str, dest_dir: str, zstd_level: int) -> Path:
    if not row_ids:
        return None

    now = datetime.datetime.now(datetime.timezone.utc)
    yyyy = now.strftime("%Y")
    mm_dd = now.strftime("%m-%d")
    
    target_dir = Path(dest_dir) / yyyy / mm_dd
    target_dir.mkdir(parents=True, exist_ok=True)
    
    file_id = uuid.uuid4().hex
    tmp_path = target_dir / f"{file_id}.jsonl.tmp"
    zst_path = target_dir / f"{file_id}.jsonl.zst"
    
    sql = f"SELECT row_to_json(t) FROM {table} t WHERE id = ANY(%(ids)s)"
    rows = await pg.execute(sql, {"ids": row_ids}, fetch=True)
    
    if not rows:
        return None
        
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            for r in rows:
                if isinstance(r, dict) and "row_to_json" in r:
                    f.write(json.dumps(r["row_to_json"]) + "\n")
                elif isinstance(r, dict):
                    f.write(json.dumps(r) + "\n")
                else:
                    f.write(str(r) + "\n")
                    
        # Compress using zstd
        subprocess.run(
            ["zstd", f"--level={zstd_level}", "-o", str(zst_path), str(tmp_path)],
            check=True,
            capture_output=True
        )
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
                
    return zst_path

async def cold_sweep(pg, plan: dict, table: str, dest_dir: str, zstd_level: int) -> dict:
    try:
        from mios_config import _toml_section
        kn_toml = _toml_section("knowledge") or {}
    except Exception:
        kn_toml = {}

    min_access = int(os.environ.get("MIOS_KNOWLEDGE_EVICT_MIN_ACCESS") or kn_toml.get("evict_min_access") or 1)
    ttl_days = int(os.environ.get("MIOS_KNOWLEDGE_EVICT_TTL_DAYS") or kn_toml.get("evict_ttl_days") or 90)

    row_ids = []

    # 1. Select TTL candidates
    ttl_delete = plan.get("ttl_delete", 0)
    if ttl_delete > 0:
        where = mios_evict.evict_where(with_ttl=True)
        order = mios_evict.order_by(cap=False)
        sql = mios_evict.select_ids_sql(table, where, order)
        params = mios_evict.evict_params(min_access, ttl_days, ttl_delete)
        rows = await pg.execute(sql, params, fetch=True)
        row_ids.extend(mios_evict.parse_ids(rows))

    # 2. Select Cap candidates
    cap_delete = plan.get("cap_delete", 0)
    if cap_delete > 0:
        where = mios_evict.evict_where(with_ttl=False)
        order = mios_evict.order_by(cap=True)
        sql = mios_evict.select_ids_sql(table, where, order)
        params = mios_evict.evict_params(min_access, ttl_days, cap_delete)
        rows = await pg.execute(sql, params, fetch=True)
        row_ids.extend(mios_evict.parse_ids(rows))

    if not row_ids:
        return {"exported": 0, "dest": ""}

    # 3. Export to zstd
    zst_path = await export_to_cold(pg, row_ids, table, dest_dir, zstd_level)

    # 4. Delete rows from PG
    if zst_path:
        delete_sql = mios_evict.delete_ids_sql(table)
        await pg.execute(delete_sql, {"ids": row_ids}, fetch=False)
        return {"exported": len(row_ids), "dest": str(zst_path)}

    return {"exported": 0, "dest": ""}
