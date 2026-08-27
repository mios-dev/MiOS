#!/usr/bin/env python3
# AI-hint: Runtime route-parity gate for the agent-pipe strangler-fig refactor (WS R13 Step 2b) -- the LIVE-FastAPI complement to the...
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Live-app route-parity gate: the REAL FastAPI app server.py builds must serve
EXACTLY the MiOS routes the committed surface golden promises (refactor R13 Step 2b)."""

import json
import os
import sys
import types
import unittest

_FASTAPI_BUILTIN_PATHS = frozenset({
    "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc",
})

_WS_METHOD = "WS"
_GOLDEN_WS_TOKEN = "WEBSOCKET"   # how the AST projector spells a websocket route
_HEAD_METHOD = "HEAD"
_ROUTE_SEP = " -> "

def _is_repo_module(name: str) -> bool:
    """True when a missing module is one THIS repo ships, so its absence is a
    code defect rather than an uninstalled third-party dependency."""
    head = (name or "").split(".")[0]
    if not head:
        return False
    here = os.path.dirname(os.path.abspath(__file__))
    return (head.startswith("mios")
            and (os.path.isdir(os.path.join(here, head))
                 or os.path.isfile(os.path.join(here, head + ".py"))))

def _install_websockets_stub():
    """Insert a no-op stand-in for the ONE heavy dependency this gate does not require
    installed (``websockets``), leaving every OTHER runtime dep
    (fastapi/starlette/pydantic/uvicorn/httpx) as the REAL package so ``server.app`` is
    a genuine FastAPI instance. server.py imports a handful of websockets submodules at
    module load for its portal terminal proxy; an empty module satisfies the import
    without a live client (no route is exercised at import time -- daemons start in the
    FastAPI lifespan, not at import). ``setdefault`` leaves a real websockets in place
    when one IS installed."""
    ws = types.ModuleType("websockets")
    wse = types.ModuleType("websockets.exceptions")
    wse.ConnectionClosed = type("ConnectionClosed", (Exception,), {})
    ws.exceptions = wse
    sys.modules.setdefault("websockets", ws)
    sys.modules.setdefault("websockets.exceptions", wse)
    for sub in ("legacy", "legacy.client", "client", "sync", "sync.client",
                "asyncio", "asyncio.client"):
        sys.modules.setdefault("websockets." + sub, types.ModuleType("websockets." + sub))

def _repo_root():
    """Repo root = four levels up from this file (usr/lib/mios/agent-pipe/), the SAME
    anchor test_server_import._resolve_toml uses, so the golden and the vendor toml are
    found relative to the checkout on any host (no absolute path baked in)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", "..", ".."))

def _golden_path():
    """Canonical committed surface golden. Referencing the canonical golden path mirrors
    test_mios_surface.py's relative-to-__file__ convention -- the golden's location IS
    its single source of truth, so this resolves rather than restates it."""
    return os.path.join(_repo_root(), "usr", "share", "mios", "ai", "v1",
                        "surface.generated.json")

def _resolve_mios_toml():
    """Point MIOS_TOML at the real vendor mios.toml before importing server, reusing
    test_server_import._resolve_toml when that sibling import gate is present so the
    resolution stays single-sourced; degrade to the same relative resolution when it is
    not. server.py turns into a crashing None-logger if the toml is unresolved, so this
    must run before ``import server``."""
    try:
        from test_server_import import _resolve_toml
    except Exception:  # noqa: BLE001 -- sibling gate absent on a partial checkout
        toml = os.path.join(_repo_root(), "usr", "share", "mios", "mios.toml")
        if "MIOS_TOML" not in os.environ and os.path.isfile(toml):
            os.environ["MIOS_TOML"] = toml
        return
    _resolve_toml()

def _app_route_pairs(app, websocket_route_cls):
    """``(method, path)`` for every route the LIVE app serves, minus the FastAPI
    built-ins and minus HEAD. A websocket route carries no HTTP ``methods`` and is
    identified by the framework's own websocket route class, then recorded under the
    normalised _WS_METHOD token. Replaces flat iteration with recursive routing traversal
    to handle _IncludedRouter and Mount sub-routes introduced in newer FastAPI/Starlette versions."""
    pairs = set()

    def traverse(routes):
        for route in routes:
            cls_name = type(route).__name__
            if cls_name == "_IncludedRouter":
                traverse(route.original_router.routes)
            elif cls_name == "Mount" or hasattr(route, "routes"):
                traverse(route.routes)
            else:
                path = getattr(route, "path", None)
                if path is None or path in _FASTAPI_BUILTIN_PATHS:
                    continue
                if isinstance(route, websocket_route_cls):
                    pairs.add((_WS_METHOD, path))
                    continue
                methods = getattr(route, "methods", None)
                if not methods:
                    continue
                for method in methods:
                    if method == _HEAD_METHOD:
                        continue
                    pairs.add((method, path))

    traverse(app.routes)
    return pairs

def _golden_route_pairs(golden):
    """``(method, path)`` parsed from each ``"{METHOD} {path} -> {handler}"`` golden
    record, normalising the websocket token to _WS_METHOD so it matches the live app.
    The AST projector emits ONE record per method, so a multi-method / api_route route
    is already split into distinct records and needs no special handling here."""
    pairs = set()
    for record in golden.get("routes", []):
        method, _, after = record.partition(" ")
        path = after.split(_ROUTE_SEP, 1)[0]
        if method == _GOLDEN_WS_TOKEN:
            method = _WS_METHOD
        pairs.add((method, path))
    return pairs

class TestAppRouteParity(unittest.TestCase):
    """Runtime route-parity gate: the REAL FastAPI app server.py builds must serve
    EXACTLY the MiOS routes the committed surface golden promises (method + path) --
    the strong runtime complement to the AST-only mios_surface parity gate."""

    app = None
    fastapi = None
    websocket_route_cls = None

    @classmethod
    def setUpClass(cls):
        try:
            import fastapi
        except Exception as exc:  # noqa: BLE001 -- web stack absent on a bare checkout
            raise unittest.SkipTest(f"fastapi unavailable: {exc!r}")
        try:
            from starlette.routing import WebSocketRoute
        except Exception as exc:  # noqa: BLE001 -- starlette ships with fastapi; guard anyway
            raise unittest.SkipTest(f"starlette unavailable: {exc!r}")
        _resolve_mios_toml()
        _install_websockets_stub()
        try:
            import server
        except ModuleNotFoundError as exc:  # a third-party dep is absent -> environmental skip
            if _is_repo_module(getattr(exc, "name", "") or ""):
                raise AssertionError(
                    f"server.py imports a REPO module that does not exist: {exc!r}"
                ) from exc
            raise unittest.SkipTest(f"server import needs a dependency absent here: {exc!r}")
        except (ImportError, NameError, AttributeError) as exc:
            # NOT environmental. An ImportError naming a symbol, or a
            # module-scope NameError, means server.py references something the
            # repo does not define -- the service cannot start. Skipping that
            # made this gate vacuous while agent-pipe was unimportable.
            raise AssertionError(f"server.py is unimportable (repo defect): {exc!r}") from exc
        cls.fastapi = fastapi
        cls.websocket_route_cls = WebSocketRoute
        cls.app = server.app

    def test_app_is_real_fastapi(self):
        """The gate must not silently pass against a stubbed app: server.app is a
        genuine fastapi.FastAPI instance whose class lives in the real fastapi package,
        never a test double."""
        app = self.app
        self.assertIsInstance(app, self.fastapi.FastAPI)
        self.assertEqual(type(app).__module__.split(".")[0], self.fastapi.__name__)
        self.assertTrue(app.routes, "real app exposes a non-empty route table")

    def test_route_parity_with_golden(self):
        """The live app's served MiOS routes == the golden's routes (method + path).
        On drift the message lists missing_from_app and extra_in_app so a migration that
        drops or renames a served route fails LOUDLY."""
        golden_path = _golden_path()
        if not os.path.isfile(golden_path):
            self.skipTest(f"surface golden absent (partial checkout): {golden_path}")
        with open(golden_path, encoding="utf-8") as fh:
            golden = json.load(fh)

        app_pairs = _app_route_pairs(self.app, self.websocket_route_cls)
        golden_pairs = _golden_route_pairs(golden)

        missing_from_app = sorted(f"{m} {p}" for m, p in golden_pairs - app_pairs)
        extra_in_app = sorted(f"{m} {p}" for m, p in app_pairs - golden_pairs)
        self.assertEqual(
            app_pairs, golden_pairs,
            "served route surface drifted from the committed golden:\n"
            f"  missing_from_app (golden promises, app does NOT serve): {missing_from_app}\n"
            f"  extra_in_app (app serves, golden does NOT list): {extra_in_app}",
        )
        self.assertEqual(len(app_pairs), golden.get("counts", {}).get("routes"))
        print(f"[test_mios_approutes] MiOS route parity OK: app={len(app_pairs)} "
              f"golden={len(golden_pairs)} (method+path, real fastapi.FastAPI app)")

if __name__ == "__main__":
    unittest.main(verbosity=2)
