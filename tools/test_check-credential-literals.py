# AI-hint: !/usr/bin/env python3 Sibling unit test for tools/check-credential-literals.py: builds throwaway unit trees and asserts the gate passes a grandfathered...
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_test_check_credential_literals_py.md
"""Assert the unit-credential gate is precise in both directions."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "check-credential-literals.py")
FAILED = 0


def build(tmp, unit_body, grandfathered):
    os.makedirs(os.path.join(tmp, "usr/share/containers/systemd"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "usr/lib/systemd/system"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "usr/share/mios"), exist_ok=True)
    open(os.path.join(tmp, "usr/share/containers/systemd/x.container"), "w").write(unit_body)
    entries = "".join(f'  "{g}",\n' for g in grandfathered)
    open(os.path.join(tmp, "usr/share/mios/mios.toml"), "w").write(
        f"[security.credential_literals]\ngrandfathered = [\n{entries}]\n")
    return tmp


def case(label, unit_body, grandfathered, want_zero):
    global FAILED
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, MIOS_ROOT=build(tmp, unit_body, grandfathered))
        rc = subprocess.run([sys.executable, GATE], env=env,
                            capture_output=True, text=True).returncode
    ok = (rc == 0) if want_zero else (rc != 0)
    print(f"[{'PASS' if ok else 'FAIL'}] {label} (exit {rc})")
    if not ok:
        FAILED += 1


KNOWN = "usr/share/containers/systemd/x.container:DB_PASSWORD"

case("grandfathered literal passes",
     "Environment=DB_PASSWORD=hunter2\n", [KNOWN], True)
case("new literal fails",
     "Environment=DB_PASSWORD=hunter2\nEnvironment=API_KEY=sk-live\n", [KNOWN], False)
case("stale grandfathered entry fails (shrink-only)",
     "Environment=NOTHING=1\n", [KNOWN], False)
case("token COUNT is not a credential",
     "Environment=HERMES_MAX_TOKENS=8192\n", [], True)
case("boolean feature flag is not a credential",
     "Environment=ENABLE_API_KEYS=True\n", [], True)
case("${VAR} indirection is not a literal",
     "Environment=DB_PASSWORD=${MIOS_DB_PASSWORD}\n", [], True)
case("empty value is not a literal",
     "Environment=DB_PASSWORD=\n", [], True)
case("numeric limit is not a credential",
     "Environment=TOKEN_LIMIT=42\n", [], True)

print(f"\n{8 - FAILED}/8 checks pass")
sys.exit(1 if FAILED else 0)
