# AI-hint: Standalone unit test for the #49 read-tool-enrich domain-filter fix: a compound that spans domains must keep verbs refine EXPLICITLY hinted (and, for a local_state query, the deterministic core state verbs) even when the turn routed to one domain -- so "list windows AND system status" (apps_windows route) still grounds on system_status.
# AI-related: server.py
# AI-functions: _check, _enrich_keep, t_compound_cross_domain, t_local_state_core, t_no_overground, t_no_domain, main
"""Standalone unit test for the #49 enrich domain-filter contract.

server.py `_read_tool_enrich` restricts AUTO-added enrich verbs to the routed
domain, but must NOT drop (a) verbs refine explicitly hinted -- a compound can
span domains -- nor (b) the deterministic local_state core verbs when the turn is
a state query mis-routed to e.g. apps_windows. This pins that set-logic with a
reference impl (pure stdlib; mirrors the server.py keep computation), the same
pattern as test_mios_launch. Live behaviour is verified on MiOS-DEV.

Run:  python test_mios_compound.py
"""

import sys

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


# Reference impl of the server.py _read_tool_enrich domain-keep logic (#49).
def _enrich_keep(hints, explicit, dvset, core, local_state):
    keep = set(dvset) | set(explicit)
    if local_state:
        keep |= set(core)
    return [h for h in hints if h in keep]


APPS = {"list_windows", "focus_window", "close_window", "maximize_window"}
SYS = {"system_status", "sys_env", "process_list", "container_status"}
FILES = {"fs_search", "text_view", "directory_lookup"}
CORE = {"system_status", "mios_apps", "process_list", "container_status", "list_windows"}


def t_compound_cross_domain() -> None:
    # "list windows AND system status" -> routed apps_windows; both EXPLICITLY
    # hinted; local_state set. Both must survive (the live #49 repro).
    out = _enrich_keep(
        hints=["list_windows", "system_status"],
        explicit={"list_windows", "system_status"},
        dvset=APPS, core=CORE, local_state=True)
    _check("compound: explicit cross-domain verb kept", "system_status" in out, str(out))
    _check("compound: domain verb kept", "list_windows" in out, str(out))


def t_local_state_core() -> None:
    # local_state query routed apps_windows, refine hinted ONLY list_windows
    # (dropped system_status) -> the deterministic CORE still grounds system_status.
    out = _enrich_keep(
        hints=["list_windows", "system_status", "process_list", "container_status"],
        explicit={"list_windows"},
        dvset=APPS, core=CORE, local_state=True)
    _check("local_state: core system_status survives mis-route",
           "system_status" in out, str(out))
    _check("local_state: core process_list survives", "process_list" in out, str(out))


def t_no_overground() -> None:
    # A FILES query (not local_state) that carries an AUTO (non-explicit)
    # system_status must still be domain-scoped OUT -- no over-grounding.
    out = _enrich_keep(
        hints=["fs_search", "system_status"],
        explicit={"fs_search"},          # system_status was auto-added, NOT asked
        dvset=FILES, core=CORE, local_state=False)
    _check("no-overground: auto cross-domain verb dropped",
           "system_status" not in out, str(out))
    _check("no-overground: domain verb kept", "fs_search" in out, str(out))


def t_no_domain() -> None:
    # No routed domain -> the caller doesn't apply this filter at all; here we
    # confirm the keep-logic is a strict subset and never invents verbs.
    out = _enrich_keep(
        hints=["list_windows", "system_status"],
        explicit={"list_windows", "system_status"},
        dvset=set(), core=set(), local_state=False)
    _check("subset: only explicit kept when dvset empty",
           set(out) == {"list_windows", "system_status"}, str(out))


def main() -> int:
    for t in (t_compound_cross_domain, t_local_state_core, t_no_overground, t_no_domain):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
