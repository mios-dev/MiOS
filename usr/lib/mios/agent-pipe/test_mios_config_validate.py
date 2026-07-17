# AI-hint: Hermetic unit tests for the WS-CONFIG server-side SAFETY validator
# (mios_pipe.kernel.config.validate_config) used by POST /portal/config AFTER the
# parse-check and BEFORE the atomic write. Pure/offline: no server, no DB, no FS.
# AI-related: ./mios_pipe/kernel/config.py, ./mios_pipe/routing/portal.py
"""Hermetic tests for validate_config (WS-CONFIG safety net).

Run standalone:  python test_mios_config_validate.py
Or via pytest:   pytest test_mios_config_validate.py
"""

import os
import sys

# Make the co-located mios_pipe package importable when run standalone.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mios_pipe.kernel.config import validate_config


VALID = """
[identity]
mios_user = "corey"

[ports]
agent_pipe = 8640
hermes = 8642
"""


def test_accepts_valid_config():
    ok, errors = validate_config(VALID, live_config={"identity": {"mios_user": "x"},
                                                     "ports": {"agent_pipe": 8640}})
    assert ok is True, errors
    assert errors == []


def test_rejects_dropped_identity_section():
    # Live config HAS [identity]; the replacement drops it -> reject, no write.
    posted = """
[ports]
agent_pipe = 8640
"""
    live = {"identity": {"mios_user": "corey"}, "ports": {"agent_pipe": 8640}}
    ok, errors = validate_config(posted, live_config=live)
    assert ok is False
    assert any("identity" in e for e in errors), errors


def test_rejects_dropped_ports_section():
    posted = """
[identity]
mios_user = "corey"
"""
    live = {"identity": {"mios_user": "corey"}, "ports": {"agent_pipe": 8640}}
    ok, errors = validate_config(posted, live_config=live)
    assert ok is False
    assert any("ports" in e for e in errors), errors


def test_rejects_bad_port_out_of_range():
    posted = """
[identity]
mios_user = "corey"

[ports]
agent_pipe = 70000
"""
    ok, errors = validate_config(posted, live_config={})
    assert ok is False
    assert any("agent_pipe" in e and "65535" in e for e in errors), errors


def test_rejects_non_integer_port():
    posted = """
[identity]
mios_user = "corey"

[ports]
agent_pipe = "8640"
"""
    ok, errors = validate_config(posted, live_config={})
    assert ok is False
    assert any("agent_pipe" in e for e in errors), errors


def test_rejects_blank_mios_user():
    posted = """
[identity]
mios_user = "   "

[ports]
agent_pipe = 8640
"""
    ok, errors = validate_config(posted, live_config={})
    assert ok is False
    assert any("mios_user" in e for e in errors), errors


def test_rejects_oversize_payload():
    # > 2 MB body -> rejected before any parse.
    big = "# pad\n" + ("x = 1\n" * 400000)
    assert len(big.encode("utf-8")) > 2 * 1024 * 1024
    ok, errors = validate_config(big, live_config={})
    assert ok is False
    assert any("too large" in e.lower() for e in errors), errors


def test_rejects_unparseable_toml():
    ok, errors = validate_config("this is = = not toml [[[", live_config={})
    assert ok is False
    assert errors


def test_drop_check_degrades_open_without_live():
    # No live_config -> the drop-check is skipped (degrade-open); a config with
    # no [identity]/[ports] is still accepted as far as the safety net cares.
    ok, errors = validate_config("[misc]\nfoo = 1\n", live_config=None)
    assert ok is True, errors


def _run_all():
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
