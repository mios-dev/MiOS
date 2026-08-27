#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/check-daemon-governor.py: builds throwaway daemon/SSOT/chat trees in a temp dir and asserts the gate pass...
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Assert the governor-coverage gate fails for each defect class it guards."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "check-daemon-governor.py")
FAILED = 0

SSOT = """[daemon]
knob_a = 1
[budget]
autonomous_max_inflight = 1
"""
GOOD_DAEMON = '''#!/usr/bin/env python3
A = _cfg_num("ENV_A", "knob_a", 1.0)
def worker_loop():
    while True:
        if _pressure_should_skip("worker"):
            continue
'''
CHAT_OK = '_budget_num("MIOS_BUDGET_AUTO_MAX_INFLIGHT", "autonomous_max_inflight", 1)\n'

def build(tmp, daemon=GOOD_DAEMON, ssot=SSOT, chat=CHAT_OK, extra=None):
    os.makedirs(os.path.join(tmp, "usr/libexec/mios"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "usr/share/mios"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "usr/lib/mios/agent-pipe/mios_pipe/routing"), exist_ok=True)
    open(os.path.join(tmp, "usr/libexec/mios/mios-daemon"), "w").write(daemon)
    open(os.path.join(tmp, "usr/share/mios/mios.toml"), "w").write(ssot)
    open(os.path.join(tmp, "usr/lib/mios/agent-pipe/mios_pipe/routing/chat.py"), "w").write(chat)
    for name, body in (extra or {}).items():
        open(os.path.join(tmp, "usr/libexec/mios", name), "w").write(body)
    return tmp

def case(label, want_zero, **kw):
    global FAILED
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, MIOS_ROOT=build(tmp, **kw))
        rc = subprocess.run([sys.executable, GATE], env=env,
                            capture_output=True, text=True).returncode
    ok = (rc == 0) if want_zero else (rc != 0)
    print(f"[{'PASS' if ok else 'FAIL'}] {label} (exit {rc})")
    if not ok:
        FAILED += 1

case("complete governor passes", True)
case("ungated autonomous loop fails", False,
     daemon=GOOD_DAEMON + '\ndef rogue_loop():\n    while True:\n        pass\n')
case("declared-but-dead knob fails", False,
     daemon='def worker_loop():\n    if _pressure_should_skip("w"): pass\n')
case("knob only in a COMMENT is not a consumer", False,
     daemon='# mentions "knob_a" in prose only\ndef worker_loop():\n    if _pressure_should_skip("w"): pass\n')
case("knob only in a TEST file is not a consumer", False,
     daemon='def worker_loop():\n    if _pressure_should_skip("w"): pass\n',
     extra={"test_mios_thing.py": 'X = "knob_a"\n'})
case("drifted budget fallback fails", False,
     chat='_budget_num("MIOS_BUDGET_AUTO_MAX_INFLIGHT", "autonomous_max_inflight", 9)\n')
case("exempt server loop needs no gate", True,
     daemon=GOOD_DAEMON + '\ndef daemon_agent_server_loop():\n    while True:\n        pass\n')

print(f"\n{7 - FAILED}/7 checks pass")
sys.exit(1 if FAILED else 0)
