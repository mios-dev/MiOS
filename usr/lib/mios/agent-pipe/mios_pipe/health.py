# AI-hint: Health and status endpoint response builder module for MiOS agent-pipe.
from __future__ import annotations

from typing import Any, Dict


def build_health_response(
    status: str = "ok",
    version: str = "0.3.0",
    backend: str = "http://localhost:8642",
    port: int = 8640,
) -> Dict[str, Any]:
    return {
        "status": status,
        "version": version,
        "backend": backend,
        "port": port,
    }
