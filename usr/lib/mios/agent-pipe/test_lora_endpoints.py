#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for LoRA list/load endpoints (CONV-06).
# Pure python/stdlib/dependency test, no running server required.
# AI-related: ./server.py

import os
import sys
import types
import asyncio
from unittest import mock

# Point to repo's vendor mios.toml
here = os.path.dirname(os.path.abspath(__file__))
repo = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
toml = os.path.join(repo, "usr", "share", "mios", "mios.toml")
if "MIOS_TOML" not in os.environ and os.path.isfile(toml):
    os.environ["MIOS_TOML"] = toml

# Setup minimal FastAPI/HTTPX stubs
for name in ("websockets", "uvicorn"):
    sys.modules.setdefault(name, mock.MagicMock(name=name))

# Mock httpx such that HTTPError is a real Exception subclass to avoid MRO conflicts
MockHTTPError = type("MockHTTPError", (Exception,), {})
httpx_mock = mock.MagicMock(name="httpx")
httpx_mock.HTTPError = MockHTTPError
sys.modules["httpx"] = httpx_mock

fastapi = types.ModuleType("fastapi")
class _App:
    def __getattr__(self, _attr):
        def _decorator_factory(*_a, **_k):
            def _wrap(fn=None):
                return fn if fn is not None else (lambda f: f)
            return _wrap
        return _decorator_factory
    def include_router(self, *a, **k): pass

fastapi.FastAPI = lambda *a, **k: _App()
fastapi.APIRouter = lambda *a, **k: _App()
fastapi.Request = mock.MagicMock()
fastapi.WebSocket = object

responses = types.ModuleType("fastapi.responses")
class MockJSONResponse:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code
    def json(self):
        return self.content

class MockResponse:
    def __init__(self, content, status_code=200, media_type=None):
        self.content = content
        self.status_code = status_code
        self.headers = {"content-type": media_type}
    def json(self):
        import json
        return json.loads(self.content)

setattr(responses, "JSONResponse", MockJSONResponse)
setattr(responses, "Response", MockResponse)
setattr(responses, "HTMLResponse", object)
setattr(responses, "RedirectResponse", object)
setattr(responses, "StreamingResponse", object)

sys.modules["fastapi"] = fastapi
sys.modules["fastapi.responses"] = responses

# Now import server after stubs are installed
import server

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

class MockRequest:
    def __init__(self, body_dict):
        self.body_dict = body_dict
    async def json(self):
        return self.body_dict

class MockHttpxResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.content = bytes(str(json_data), "utf-8")
        self.headers = {"content-type": "application/json"}
    def json(self):
        return self.json_data

async def test_lora_list_dual_mode():
    os.environ["MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE"] = "dual"
    res = await server.lora_list()
    check("lora_list (dual): empty adapters returned", res.get("adapters") == [])
    check("lora_list (dual): disabled is False", res.get("enabled") is False)

async def test_lora_list_single_mode():
    os.environ["MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE"] = "single"
    
    mock_models = {
        "data": [
            {"id": "base-model", "object": "model"},
            {"id": "adapter-coding", "object": "model", "parent": "base-model"},
            {"id": "adapter-reasoning", "object": "model", "root": "base-model"}
        ]
    }
    
    mock_client = mock.AsyncMock()
    mock_client.get.return_value = MockHttpxResponse(mock_models)
    
    with mock.patch("server._get_client", mock.AsyncMock(return_value=mock_client)):
        res = await server.lora_list()
        check("lora_list (single): enabled is True", res.get("enabled") is True)
        adapters = res.get("adapters") or []
        check("lora_list (single): parsed 2 adapters", len(adapters) == 2)
        check("lora_list (single): coding adapter present", any(a["id"] == "adapter-coding" for a in adapters))

async def test_lora_load_dual_mode():
    os.environ["MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE"] = "dual"
    req = MockRequest({"lora_name": "coding", "lora_path": "/path"})
    res = await server.lora_load(req)
    check("lora_load (dual): status code is 400", res.status_code == 400)
    check("lora_load (dual): returns error message", "only supported" in res.content.get("error"))

async def test_lora_load_single_mode():
    os.environ["MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE"] = "single"
    req = MockRequest({"lora_name": "coding", "lora_path": "/path"})
    
    mock_client = mock.AsyncMock()
    mock_client.post.return_value = MockHttpxResponse({"status": "loaded"})
    
    with mock.patch("server._get_client", mock.AsyncMock(return_value=mock_client)):
        res = await server.lora_load(req)
        check("lora_load (single): status code is 200", res.status_code == 200)

async def main():
    await test_lora_list_dual_mode()
    await test_lora_list_single_mode()
    await test_lora_load_dual_mode()
    await test_lora_load_single_mode()
    
    if _fails > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
