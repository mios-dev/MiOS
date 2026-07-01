#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_scratchpad (CONV-08).
# Pure python/stdlib/dependency test, no DB connection required.
# AI-related: ./mios_scratchpad.py

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

def test_scratchpad_enabled():
    os.environ["MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE"] = "true"
    
    # Reload module or verify functions directly
    import importlib
    try:
        import mios_scratchpad
        importlib.reload(mios_scratchpad)
    except ModuleNotFoundError as e:
        if "sqlite_vec" in str(e):
            print("[SKIP] enabled: sqlite_vec not installed")
            return
        raise
    
    check("enabled: flag is True", mios_scratchpad.SQLITE_VEC_ENABLE is True)
    
    conn, path = mios_scratchpad.create_scratchpad("test-sess", "/tmp")
    check("enabled: conn is created", conn is not None)
    check("enabled: path exists", path is not None and path.exists())
    
    # Insert vectors of size 768
    v1 = [0.1] * 768
    mios_scratchpad.vec_insert(conn, "observation 1", v1)
    
    v2 = [0.5] * 768
    mios_scratchpad.vec_insert(conn, "observation 2", v2)
    
    # Search closest to [0.1] * 768
    res = mios_scratchpad.vec_search(conn, [0.12] * 768, k=1)
    check("enabled: returned 1 search result", len(res) == 1)
    print("DEBUG res:", res)
    check("enabled: correct item returned", res[0]["content"] == "observation 1")
    check("enabled: distance is small", res[0]["distance"] < 1.0)
    
    # Destroy
    mios_scratchpad.destroy_scratchpad(conn, path)
    check("enabled: file is deleted", not path.exists())

def test_scratchpad_disabled():
    os.environ["MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE"] = "false"
    
    import importlib
    import mios_scratchpad
    importlib.reload(mios_scratchpad)
    
    check("disabled: flag is False", mios_scratchpad.SQLITE_VEC_ENABLE is False)
    
    conn, path = mios_scratchpad.create_scratchpad("test-sess-off", "/tmp")
    check("disabled: conn is None", conn is None)
    check("disabled: path is None", path is None)
    
    # Insert should no-op
    mios_scratchpad.vec_insert(conn, "nothing", [0.1] * 768)
    
    # Search should return empty list
    res = mios_scratchpad.vec_search(conn, [0.1] * 768)
    check("disabled: search returns empty list", res == [])
    
    # Destroy should no-op
    mios_scratchpad.destroy_scratchpad(conn, path)

def main():
    test_scratchpad_enabled()
    test_scratchpad_disabled()
    if _fails > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
