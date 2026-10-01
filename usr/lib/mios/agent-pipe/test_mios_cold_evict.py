#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_cold_evict (CONV-09).
# AI-related: ./mios_cold_evict.py

import os
import sys
import asyncio
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import mios_cold_evict

TEST_DIR = None

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

class AsyncMock:
    def __init__(self, return_value=None):
        self.return_value = return_value
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.return_value

async def test_export_to_cold_success():
    pg = mock.Mock()
    rows = [{"row_to_json": {"id": 123, "q": "test query", "answer": "test answer"}}]
    pg.execute = AsyncMock(return_value=rows)

    with mock.patch("subprocess.run") as mock_run:
        res_path = await mios_cold_evict.export_to_cold(
            pg, row_ids=[123], table="knowledge", dest_dir=TEST_DIR, zstd_level=3
        )

        check("export: returns zst file path", res_path is not None)
        check("export: path suffix is .zst", str(res_path).endswith(".zst"))
        check("export: subprocess.run called once", mock_run.call_count == 1)

        args = mock_run.call_args[0][0]
        check("export: level flag correct", "-3" in args)
        check("export: resolved zstd command matches", args[0] == shutil.which("zstd"))

async def test_export_to_cold_error_cleanup():
    pg = mock.Mock()
    rows = [{"row_to_json": {"id": 123, "q": "error test"}}]
    pg.execute = AsyncMock(return_value=rows)

    with mock.patch("subprocess.run", side_effect=Exception("zstd error")):
        try:
            await mios_cold_evict.export_to_cold(
                pg, row_ids=[123], table="knowledge", dest_dir=TEST_DIR, zstd_level=3
            )
            check("cleanup: raised exception", False, "should have failed")
        except Exception:
            check("cleanup: no tmp files left", not list(Path(TEST_DIR).rglob("*.tmp")))

async def test_real_compression_and_invalid_level():
    pg = mock.Mock()
    payload = {"id": 123, "q": "round-trip"}
    pg.execute = AsyncMock(return_value=[{"row_to_json": payload}])
    archive = await mios_cold_evict.export_to_cold(pg, [123], "knowledge", TEST_DIR, 3)
    decoded = subprocess.run([shutil.which("zstd"), "-dc", str(archive)], check=True, capture_output=True, text=True).stdout
    check("export: real zstd preserves JSON payload", json.loads(decoded) == payload)
    for level in (0, 23, True, "3"):
        try:
            await mios_cold_evict.export_to_cold(pg, [123], "knowledge", TEST_DIR, level)
        except ValueError:
            check(f"export: invalid level {level!r} rejected", True)
        else:
            check(f"export: invalid level {level!r} rejected", False)

async def test_cold_sweep():
    pg = mock.Mock()
    select_results = [{"id": 1}, {"id": 2}]

    execute_calls = []
    async def mock_execute(sql, params=None, fetch=False):
        execute_calls.append((sql, params))
        if "SELECT id" in sql:
            return select_results
        elif "SELECT row_to_json" in sql:
            return [{"row_to_json": {"id": 1, "q": "q1"}}, {"row_to_json": {"id": 2, "q": "q2"}}]
        return None

    pg.execute = mock_execute

    with mock.patch("subprocess.run"):
        plan = {"ttl_delete": 2, "cap_delete": 0}
        report = await mios_cold_evict.cold_sweep(
            pg, plan, table="knowledge", dest_dir=TEST_DIR, zstd_level=3
        )

        check("sweep: correct number exported", report["exported"] == 2)
        check("sweep: returns non-empty dest path", report["dest"] != "")

        check("sweep: select was run", any("SELECT id" in call[0] for call in execute_calls))
        check("sweep: delete was run", any("DELETE FROM" in call[0] for call in execute_calls))

async def main():
    global TEST_DIR
    with tempfile.TemporaryDirectory(prefix="mios-cold-test-") as temp:
        TEST_DIR = temp
        await test_export_to_cold_success()
        await test_export_to_cold_error_cleanup()
        await test_cold_sweep()
        await test_real_compression_and_invalid_level()
    if _fails > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
