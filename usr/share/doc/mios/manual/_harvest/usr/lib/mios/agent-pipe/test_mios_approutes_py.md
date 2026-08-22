<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Insert a no-op stand-in for the ONE heavy dependency this...

Insert a no-op stand-in for the ONE heavy dependency this gate does not require
    installed (``websockets``), leaving every OTHER runtime dep
    (fastapi/starlette/pydantic/uvicorn/httpx) as the REAL package so ``server.app`` is
    a genuine FastAPI instance. server.py imports a handful of websockets submodules at
    module load for its portal terminal proxy; an empty module satisfies the import
    without a live client (no route is exercised at import time -- daemons start in the
    FastAPI lifespan, not at import). ``setdefault`` leaves a real websockets in place
    when one IS installed.

<!-- mios-src:fd58fad5ea1e from usr/lib/mios/agent-pipe/test_mios_approutes.py:35-42 -->

### Point MIOS_TOML at the real vendor mios.toml before...

Point MIOS_TOML at the real vendor mios.toml before importing server, reusing
    test_server_import._resolve_toml when that sibling import gate is present so the
    resolution stays single-sourced; degrade to the same relative resolution when it is
    not. server.py turns into a crashing None-logger if the toml is unresolved, so this
    must run before ``import server``.

<!-- mios-src:20338cfdaa48 from usr/lib/mios/agent-pipe/test_mios_approutes.py:71-75 -->
