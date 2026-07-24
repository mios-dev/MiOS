# AI-hint: Unit test for mios_pipe.health module (AGY-113).
from __future__ import annotations

from mios_pipe.health import build_health_response


def test_build_health_response():
    res = build_health_response("ok", "0.3.0", "http://localhost:8642", 8640)
    assert res["status"] == "ok"
    assert res["version"] == "0.3.0"
    assert res["port"] == 8640
