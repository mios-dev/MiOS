#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_slo (WS-SCHED-SLO deadline/SLO scheduling core). Pure stdlib, no server.py/pytest. Verifies classify (autonomous/clamped -> best_effort, foreground -> interactive), per-class deadline budgets, the EDF least-deadline-first sort key (earliest deadline first, interactive tie-break), and the FAIL-CLOSED shed decision (interactive never shed; best_effort shed under over-ceiling OR unknown-health, the inversion of the degrade-open hole).
# AI-related: ./mios_slo.py
# AI-functions: check, main
"""Unit tests for mios_slo (WS-SCHED-SLO)."""
import sys

import mios_slo as slo

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_classify():
    check("classify: foreground high-prio -> interactive",
          slo.classify(foreground=True, autonomous=False, priority=9.0) == slo.INTERACTIVE)
    check("classify: autonomous -> best_effort",
          slo.classify(foreground=True, autonomous=True, priority=9.0) == slo.BEST_EFFORT)
    check("classify: background (not foreground) -> best_effort",
          slo.classify(foreground=False) == slo.BEST_EFFORT)
    check("classify: clamped foreground priority -> best_effort",
          slo.classify(foreground=True, priority=3.0, interactive_priority=7.0) == slo.BEST_EFFORT)
    check("classify: default -> interactive (protect human)", slo.classify() == slo.INTERACTIVE)


def t_deadline_edf():
    check("deadline: interactive budget 8s", slo.deadline(slo.INTERACTIVE, 100.0) == 108.0)
    check("deadline: best_effort budget 120s", slo.deadline(slo.BEST_EFFORT, 100.0) == 220.0)
    check("deadline: unknown class -> best_effort budget",
          slo.deadline("weird", 100.0) == 220.0)
    # EDF: interactive enqueued later still sorts BEFORE a best_effort enqueued earlier
    # (8s deadline < 120s deadline), i.e. least-deadline-first beats arrival order.
    k_be = slo.edf_key(slo.BEST_EFFORT, enqueue_t=0.0, now=0.0)     # deadline 120
    k_int = slo.edf_key(slo.INTERACTIVE, enqueue_t=10.0, now=10.0)  # deadline 18
    check("edf: interactive (later arrival) sorts before best_effort", k_int < k_be,
          f"{k_int} vs {k_be}")
    # tie on deadline -> interactive wins (smaller -rank)
    a = slo.edf_key(slo.INTERACTIVE, 0.0, 0.0, budgets={slo.INTERACTIVE: 5.0, slo.BEST_EFFORT: 5.0})
    b = slo.edf_key(slo.BEST_EFFORT, 0.0, 0.0, budgets={slo.INTERACTIVE: 5.0, slo.BEST_EFFORT: 5.0})
    check("edf: deadline tie -> interactive first", a < b, f"{a} vs {b}")


def t_shed():
    # interactive NEVER shed, even over-ceiling + unhealthy
    check("shed: interactive never shed (over+unhealthy)",
          slo.should_shed(slo.INTERACTIVE, over_ceiling=True, healthy=False) is False)
    # best_effort shed when over ceiling
    check("shed: best_effort shed over-ceiling",
          slo.should_shed(slo.BEST_EFFORT, over_ceiling=True, healthy=True) is True)
    # best_effort NOT shed with headroom + healthy
    check("shed: best_effort kept with headroom",
          slo.should_shed(slo.BEST_EFFORT, over_ceiling=False, healthy=True) is False)
    # FAIL-CLOSED: probe failed (unknown health) -> shed best_effort even if ceiling unknown
    check("shed: best_effort FAIL-CLOSED on unknown health",
          slo.should_shed(slo.BEST_EFFORT, over_ceiling=False, healthy=False) is True)


def t_ssot_configure():
    # The per-class budgets + the interactive-priority floor are NOT baked: they
    # read from the configure()-injected SSOT ([slo] in mios.toml). Prove behaviour
    # FOLLOWS a non-default config, then restore the documented defaults.
    # Baseline (documented defaults): floor 7.0 -> priority 5.0 = best_effort.
    check("ssot: default floor 7.0 clamps priority 5.0 -> best_effort",
          slo.classify(priority=5.0) == slo.BEST_EFFORT)
    check("ssot: default interactive budget 8s", slo.deadline(slo.INTERACTIVE, 0.0) == 8.0)

    # Inject a NON-DEFAULT SSOT: tighter floor (4.0) + different budgets.
    slo.configure(
        budgets={slo.INTERACTIVE: 3.0, slo.BEST_EFFORT: 60.0},
        default_priority=5.0,
        interactive_priority=4.0,
    )
    check("ssot: injected floor 4.0 now admits priority 5.0 -> interactive",
          slo.classify(priority=5.0) == slo.INTERACTIVE)
    check("ssot: bare classify() follows injected default_priority 5.0 vs floor 4.0",
          slo.classify() == slo.INTERACTIVE)
    check("ssot: injected interactive budget 3s drives deadline",
          slo.deadline(slo.INTERACTIVE, 0.0) == 3.0)
    check("ssot: injected best_effort budget 60s drives deadline",
          slo.deadline(slo.BEST_EFFORT, 0.0) == 60.0)
    check("ssot: unknown class falls back to injected best_effort budget",
          slo.deadline("weird", 0.0) == 60.0)

    # Restore the documented defaults so the rest of the suite is unaffected.
    slo.configure(
        budgets={slo.INTERACTIVE: 8.0, slo.BEST_EFFORT: 120.0},
        default_priority=7.0,
        interactive_priority=7.0,
    )
    check("ssot: defaults restored (floor 7.0 clamps priority 5.0)",
          slo.classify(priority=5.0) == slo.BEST_EFFORT)


def main():
    t_classify()
    t_deadline_edf()
    t_shed()
    t_ssot_configure()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
