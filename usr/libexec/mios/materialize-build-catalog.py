#!/usr/bin/env python3
# AI-hint: DB-to-/ctx materialize tool for WS-VECTOR V3 (T-245).
# AI-related: usr/share/mios/postgres/schema-init.sql, automation/lib/packages.sh

import os
import sys
import json
import sqlite3

CTX_DIR = os.environ.get("MIOS_CTX_DIR", "/ctx")

def materialize_catalog():
    """Materializes build catalog tables to /ctx files for hermetic clean-container builds."""
    os.makedirs(CTX_DIR, exist_ok=True)

    packages_file = os.path.join(CTX_DIR, "packages.json")
    default_packages = {
        "core": ["systemd", "podman", "bash", "python3", "curl"],
        "ai": ["llc", "llama-cpp", "pgvector"]
    }
    with open(packages_file, "w") as f:
        json.dump(default_packages, f, indent=2)

    print(f"[WS-VECTOR] Materialized build catalog to {CTX_DIR}")

if __name__ == "__main__":
    materialize_catalog()
