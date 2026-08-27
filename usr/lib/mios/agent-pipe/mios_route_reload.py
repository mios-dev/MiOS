# AI-hint: Hot-reload of model routing tables without dropping active streams.
# AI-related: usr/lib/mios/agent-pipe/server.py, tests/test-route-reload.py
"""
MiOS Agent-Pipe Model Routing Table Hot-Reloader.
Allows updating model endpoint definitions in-memory with zero downtime for active client sessions.
"""

from __future__ import annotations

import copy
import threading
from typing import Any, Dict, Optional

class RouteTableManager:
    """Thread-safe hot-reloading model routing table manager."""

    def __init__(self, initial_routes: Optional[Dict[str, Any]] = None) -> None:
        self._routes: Dict[str, Any] = initial_routes or {}
        self._lock = threading.RLock()
        self._version = 1

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    def get_route(self, model_name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._routes.get(model_name)

    def reload_routes(self, new_routes: Dict[str, Any]) -> int:
        """Atomically replaces the routing table and increments the version."""
        with self._lock:
            self._routes = copy.deepcopy(new_routes)
            self._version += 1
            return self._version

    def list_models(self) -> list[str]:
        with self._lock:
            return list(self._routes.keys())
