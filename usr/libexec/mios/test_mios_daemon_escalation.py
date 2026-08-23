#!/usr/bin/env python3
# AI-hint: Standalone unit test for the mios-daemon escalation governor (GUARD-01): loads the hyphenated CLI by path with its side-e...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_libexec_mios_test_mios_daemon_escalation_py.md
"""Assert the daemon's repeat-escalation gate honours its two SSOT knobs."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAILED = 0


def load():
    loader = importlib.machinery.SourceFileLoader("mios_daemon_under_test",
                                                  str(HERE / "mios-daemon"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    mod.__name__ = "mios_daemon_under_test"      # keeps any __main__ guard shut
    loader.exec_module(mod)
    return mod


def check(label, cond):
    global FAILED
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")
    if not cond:
        FAILED += 1


d = load()


def reset(cooldown, attempts):
    d.ESCALATION_COOLDOWN_S = cooldown
    d.ESCALATION_MAX_ATTEMPTS = attempts
    d._escalation_seen.clear()


# 1. First escalation of a concern always passes.
reset(1800.0, 3)
check("first escalation allowed", d._escalation_allowed("c1") is True)

# 2. An immediate repeat is inside the cooldown -> suppressed.
check("repeat inside cooldown suppressed", d._escalation_allowed("c1") is False)

# 3. A different concern is independent.
check("distinct concern unaffected", d._escalation_allowed("c2") is True)

# 4. Once the cooldown has elapsed the concern may escalate again...
reset(1800.0, 3)
d._escalation_allowed("c3")
d._escalation_seen["c3"]["last"] -= 4000          # pretend the cooldown passed
check("escalation allowed after cooldown", d._escalation_allowed("c3") is True)

# 5. ...until the attempt cap parks it, permanently.
reset(1800.0, 2)
d._escalation_allowed("c4")                        # attempt 1
d._escalation_seen["c4"]["last"] -= 4000
d._escalation_allowed("c4")                        # attempt 2 -> at the cap
d._escalation_seen["c4"]["last"] -= 4000
check("parked at the attempt cap", d._escalation_allowed("c4") is False)
check("park is recorded", d._escalation_seen["c4"]["parked"] is True)
d._escalation_seen["c4"]["last"] -= 99999
check("parked concern stays parked", d._escalation_allowed("c4") is False)

# 6. Degrade-open: a non-positive cooldown disables the gate.
reset(0.0, 3)
check("cooldown<=0 degrades open",
      all(d._escalation_allowed("c5") is True for _ in range(5)))

# 7. The table is bounded.
reset(1800.0, 3)
for i in range(d._ESCALATION_MAX_ENTRIES + 200):
    d._escalation_allowed(f"bulk-{i}")
check("entry table stays bounded",
      len(d._escalation_seen) <= d._ESCALATION_MAX_ENTRIES + 1)

print(f"\n{9 - FAILED}/9 checks pass")
sys.exit(1 if FAILED else 0)
