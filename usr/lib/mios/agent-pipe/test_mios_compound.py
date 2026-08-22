# AI-hint: Standalone unit test for the #49 read-tool-enrich domain-filter fix: a compound that spans domains must keep verbs refine EXPLICITLY hinted (and,...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_test_mios_compound_py.md
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
    out = _enrich_keep(
        hints=["list_windows", "system_status"],
        explicit={"list_windows", "system_status"},
        dvset=APPS, core=CORE, local_state=True)
    _check("compound: explicit cross-domain verb kept", "system_status" in out, str(out))
    _check("compound: domain verb kept", "list_windows" in out, str(out))


def t_local_state_core() -> None:
    out = _enrich_keep(
        hints=["list_windows", "system_status", "process_list", "container_status"],
        explicit={"list_windows"},
        dvset=APPS, core=CORE, local_state=True)
    _check("local_state: core system_status survives mis-route",
           "system_status" in out, str(out))
    _check("local_state: core process_list survives", "process_list" in out, str(out))


def t_no_overground() -> None:
    out = _enrich_keep(
        hints=["fs_search", "system_status"],
        explicit={"fs_search"},          # system_status was auto-added, NOT asked
        dvset=FILES, core=CORE, local_state=False)
    _check("no-overground: auto cross-domain verb dropped",
           "system_status" not in out, str(out))
    _check("no-overground: domain verb kept", "fs_search" in out, str(out))


def t_no_domain() -> None:
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
