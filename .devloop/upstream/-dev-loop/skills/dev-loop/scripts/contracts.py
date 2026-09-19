#!/usr/bin/env python3
"""
scripts/contracts.py
Ephemeral cross-worktree interface exchange for concurrent Dev Loop workers.
"""
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

CONTRACTS_DIR = Path(".worktrees/.contracts")

def publish_contract(worker_id: str, interface_name: str, schema_payload: Dict[str, Any]) -> Path:
    """Publish an interface definition to the cross-worktree bus."""
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    contract_file = CONTRACTS_DIR / f"{interface_name}.json"
    temp_file = CONTRACTS_DIR / f"{interface_name}.tmp"
    
    envelope = {
        "producer": worker_id,
        "interface": interface_name,
        "timestamp": time.time(),
        "schema": schema_payload
    }
    
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(envelope, f, indent=2)
    temp_file.replace(contract_file)
    return contract_file

def consume_contract(interface_name: str, max_wait_sec: int = 10) -> Optional[Dict[str, Any]]:
    """Poll for an interface contract published by another concurrent worker."""
    contract_file = CONTRACTS_DIR / f"{interface_name}.json"
    start = time.time()
    while time.time() - start < max_wait_sec:
        if contract_file.exists():
            try:
                with open(contract_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        time.sleep(0.5)
    return None

if __name__ == "__main__":
    print("[dev-loop] Contracts bus ready.")
