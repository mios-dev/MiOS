# AI-hint: Standalone unit test for mios_kvfork to verify KV-cache fork primitives, ensuring filename sanitization, length capping, and fork validation logic match the server's expected contract.
# AI-related: mios_kvfork, mios-kv, mios-kv-abc, mios-kv-default, mios-kv-a_b_c, mios-kv-parent, mios-kv-child
# AI-functions: _check, _reference_kv_filename, t_filename_matches_server, t_validate, t_plan, t_outcome, t_parse_bool, t_clamp, main
"""Standalone unit test for mios_kvfork (WS-8 KV-cache fork primitives).

Pure stdlib + the sibling module only -- no server.py import, so it runs on any
Python 3.10+ without the agent-pipe runtime deps. Mirrors the mios_sched /
mios_evict standalone-test pattern: explicit asserts, PASS/FAIL summary, exit
code != 0 on any failure.

Run:  python test_mios_kvfork.py
"""

import re
import sys

from mios_kvfork import (
    kv_filename,
    conv_token,
    validate_fork,
    plan_fork,
    fork_outcome,
    parse_bool,
    clamp_branches,
)

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


# ── kv_filename: must stay byte-identical to server.py _kv_filename ──────────
def _reference_kv_filename(conv) -> str:
    """The server.py _kv_filename body, copied here so the test PINS the contract
    (a child file must be the file _kv_paging later restores)."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(conv or "default"))[:120]
    return f"mios-kv-{safe or 'default'}.bin"


def t_filename_matches_server() -> None:
    cases = ["abc", "chat/with slashes", "weird:chars*here", "", None,
             "x" * 300, "default", "a.b-c_d", "한국어unicode", "  spaces  "]
    bad = [c for c in cases if kv_filename(c) != _reference_kv_filename(c)]
    _check("filename: identical to server _kv_filename", not bad,
           f"diverged on={bad}")
    _check("filename: shape", kv_filename("abc") == "mios-kv-abc.bin",
           kv_filename("abc"))
    _check("filename: empty -> default", kv_filename("") == "mios-kv-default.bin",
           kv_filename(""))
    _check("filename: sanitised", kv_filename("a/b c") == "mios-kv-a_b_c.bin",
           kv_filename("a/b c"))
    _check("filename: capped <= 120 token", len(conv_token("z" * 400)) == 120,
           f"len={len(conv_token('z' * 400))}")


# ── validate_fork ────────────────────────────────────────────────────────────
def t_validate() -> None:
    ok, _ = validate_fork("parent", "child")
    _check("validate: distinct ok", ok)
    ok, reason = validate_fork("", "child")
    _check("validate: empty src rejected", not ok and "source" in reason, reason)
    ok, reason = validate_fork("parent", "")
    _check("validate: empty dst rejected", not ok and "destination" in reason, reason)
    ok, reason = validate_fork(None, "child")
    _check("validate: None src rejected", not ok, reason)
    ok, reason = validate_fork("same", "same")
    _check("validate: self-fork rejected", not ok and "same KV file" in reason, reason)
    # Two distinct-LOOKING convs that sanitise to the SAME file must be rejected.
    ok, reason = validate_fork("a/b", "a_b")
    _check("validate: collision after sanitise rejected", not ok, reason)
    # Whitespace-only is empty.
    ok, _ = validate_fork("   ", "child")
    _check("validate: whitespace src rejected", not ok)


# ── plan_fork ────────────────────────────────────────────────────────────────
def t_plan() -> None:
    plan = plan_fork("parent", "child")
    _check("plan: two steps", len(plan) == 2, f"len={len(plan)}")
    _check("plan: restore parent first",
           plan[0] == ("restore", "parent", "mios-kv-parent.bin"), str(plan[0]))
    _check("plan: save child second",
           plan[1] == ("save", "child", "mios-kv-child.bin"), str(plan[1]))
    # Order is load-bearing: restore (page IN) must precede save (page OUT).
    actions = [step[0] for step in plan]
    _check("plan: order restore->save", actions == ["restore", "save"], str(actions))
    # The filenames in the plan match kv_filename for the same convs.
    _check("plan: filenames consistent",
           plan[0][2] == kv_filename("parent") and plan[1][2] == kv_filename("child"))
    # Sanitised tokens in the plan.
    p2 = plan_fork("a/b", "c d")
    _check("plan: sanitised tokens",
           p2[0][1] == "a_b" and p2[1][1] == "c_d", str(p2))


# ── fork_outcome ─────────────────────────────────────────────────────────────
def t_outcome() -> None:
    forked, reason = fork_outcome(restore_ok=True, save_ok=True)
    _check("outcome: both ok -> forked", forked and "from parent prefix" in reason, reason)
    forked, reason = fork_outcome(restore_ok=False, save_ok=True)
    _check("outcome: restore-fail still forked (degraded)",
           forked and "WARNING" in reason, reason)
    forked, reason = fork_outcome(restore_ok=True, save_ok=False)
    _check("outcome: save-fail -> not forked", not forked and "could not save" in reason, reason)
    forked, reason = fork_outcome(restore_ok=False, save_ok=False)
    _check("outcome: both fail -> not forked + notes restore",
           not forked and "parent restore also failed" in reason, reason)


# ── parse_bool (default-off gating) ──────────────────────────────────────────
def t_parse_bool() -> None:
    _check("bool: default off", parse_bool(None) is False)
    _check("bool: default honoured", parse_bool(None, default=True) is True)
    truthy = all(parse_bool(v) for v in ("true", "1", "YES", "On", True))
    _check("bool: truthy set", truthy)
    falsy = not any(parse_bool(v) for v in ("false", "0", "no", "OFF", "", False))
    _check("bool: falsy set", falsy)
    _check("bool: garbage -> default", parse_bool("maybe", default=False) is False)


# ── clamp_branches (runaway guard) ───────────────────────────────────────────
def t_clamp() -> None:
    _check("clamp: within cap", clamp_branches(3, hard_cap=8) == 3)
    _check("clamp: over cap clamped", clamp_branches(50, hard_cap=8) == 8)
    _check("clamp: negative -> 0", clamp_branches(-5, hard_cap=8) == 0)
    _check("clamp: non-numeric -> default", clamp_branches("x", hard_cap=8, default=2) == 2)
    _check("clamp: None -> default", clamp_branches(None, hard_cap=8, default=1) == 1)
    _check("clamp: default also clamped", clamp_branches("x", hard_cap=3, default=99) == 3)
    _check("clamp: zero cap floors all", clamp_branches(5, hard_cap=0) == 0)


def main() -> int:
    for t in (t_filename_matches_server, t_validate, t_plan, t_outcome,
              t_parse_bool, t_clamp):
        t()
    passed = sum(1 for _, ok, _ in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
