# AI-hint: WS-A11/WS-3 server.py decomposition -- Stage 1c: the pure Dispatcher.
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_routing_dispatcher_py.md

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


class Dispatcher:
    """Routes RouteDecision.mode -> the injected handler for that mode."""

    def __init__(self, handlers: Optional[Dict[str, Callable]] = None, *,
                 default_mode: str = "agent") -> None:
        self._handlers: Dict[str, Callable] = dict(handlers or {})
        self._default = str(default_mode)

    @staticmethod
    def _mode_of(decision: Any) -> str:
        m = getattr(decision, "mode", None)
        if m is None and isinstance(decision, dict):
            m = decision.get("mode")
        return str(m or "")

    async def run(self, decision: Any, **ctx) -> Any:
        """Run the decision via its mode handler. Falls back to the default-mode
        handler for an unknown/missing mode; raises KeyError if neither exists
        (a fail-loud wiring error, not a runtime degrade)."""
        mode = self._mode_of(decision)
        handler = self._handlers.get(mode) or self._handlers.get(self._default)
        if handler is None:
            raise KeyError(
                f"mios_dispatcher: no handler for mode {mode!r} and no "
                f"'{self._default}' fallback (handlers wired: {self.modes()})")
        return await handler(decision, **ctx)

    def modes(self) -> list:
        return sorted(self._handlers)

    def can_handle(self, mode: str) -> bool:
        return str(mode) in self._handlers or self._default in self._handlers


class MockResponse:
    def __init__(self, data: dict, status_code: int = 200, text: str = ""):
        self._data = data
        self.status_code = status_code
        self._text = text or str(data)

    def json(self) -> dict:
        return self._data

    @property
    def text(self) -> str:
        return self._text


async def dispatch_via_http(payload: dict, endpoint: str, headers: dict = None) -> MockResponse:
    import httpx
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            r = await client.post(
                f"{endpoint}/chat/completions",
                json=payload,
                headers=headers
            )
            try:
                return MockResponse(r.json(), status_code=r.status_code, text=r.text)
            except Exception:
                return MockResponse({"error": {"message": r.text, "type": "backend_non_json"}}, status_code=r.status_code, text=r.text)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.NetworkError) as e:
            return MockResponse({"error": {"message": f"blade unreachable: {e}", "type": "blade_unreachable_error", "code": "blade_unreachable"}}, status_code=502)
        except Exception as e:
            return MockResponse({"error": {"message": str(e), "type": "backend_error"}}, status_code=502)


async def dispatch_via_queue(payload: dict, queue: Any) -> dict:
    if queue is None:
        raise ValueError("dispatch_via_queue: GatewayQueue is not initialized")
    import asyncio
    from mios_gateway_queue import GatewayRequest
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    req = GatewayRequest(payload=payload, fut=fut)
    await queue.put(req)
    return await fut

