# AI-hint: !/usr/bin/env python3 Standalone assert-script unit test for mios_pipe.access.seccomp (T-230).
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_test_mios_seccomp_py.md

"""Unit tests for the dispatch sandbox's seccomp filter (T-230)."""

import glob
import re
import struct
import sys

from mios_pipe.access import seccomp as S

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _insns(blob):
    return [struct.unpack("<HBBI", blob[i:i + 8]) for i in range(0, len(blob), 8)]


def t_table_matches_kernel_abi():
    """A wrong number denies the wrong syscall, so the table is checked against
    the kernel's own header rather than trusted."""
    hdrs = glob.glob("/usr/include/**/asm/unistd_64.h", recursive=True)
    if not hdrs:
        print("[SKIP] ABI cross-check: no asm/unistd_64.h on this host")
        return
    text = open(hdrs[0], encoding="utf-8", errors="replace").read()
    kernel = {m.group(1): int(m.group(2))
              for m in re.finditer(r"^#define __NR_(\w+)\s+(\d+)", text, re.M)}
    check("ABI: the header parsed", len(kernel) > 200, str(len(kernel)))
    bad = [(n, v, kernel.get(n)) for n, v in S.SYSCALLS["x86_64"].items()
           if n in kernel and kernel[n] != v]
    check("ABI: every committed x86_64 number matches the kernel header",
          not bad, str(bad))
    missing = [n for n in S.SYSCALLS["x86_64"] if n not in kernel]
    check("ABI: no committed name is unknown to the kernel header",
          not missing, str(missing))


def t_denylist():
    base = S.resolve_denylist("x86_64")
    check("deny: the baseline floor resolves", len(base) >= 15, str(len(base)))
    ext = S.resolve_denylist("x86_64", ["swapon", "reboot"])
    check("deny: an SSOT list EXTENDS the floor", len(ext) > len(base))
    check("deny: the floor survives the extension", set(base) <= set(ext))
    check("deny: an unknown name is dropped, never guessed",
          S.resolve_denylist("x86_64", ["not_a_syscall"]) == base)
    check("deny: the result is sorted and unique",
          ext == sorted(set(ext)))
    tbl = S.syscall_numbers("x86_64")
    check("deny: ptrace is on the floor", tbl["ptrace"] in base)
    check("deny: mount is on the floor", tbl["mount"] in base)


def t_program_shape():
    nrs = S.resolve_denylist("x86_64")
    blob = S.build_filter("x86_64", nrs)
    ins = _insns(blob)
    check("prog: length is a whole number of sock_filters", len(blob) % 8 == 0)
    check("prog: it loads the ARCH first", ins[0] == (0x20, 0, 0, 4), str(ins[0]))
    check("prog: the arch compare names x86_64",
          ins[1][0] == 0x15 and ins[1][3] == S.AUDIT_ARCH["x86_64"], str(ins[1]))

    # The classic bypass: an arch mismatch that ALLOWS. It must land on DENY.
    n = len(nrs)
    check("prog: an arch MISMATCH falls through to the deny tail, not allow",
          ins[1][2] == n + 1, f"jf={ins[1][2]} n={n}")
    check("prog: then it loads the syscall number", ins[2] == (0x20, 0, 0, 0))
    check("prog: one compare per denied syscall",
          len(ins) == 3 + n + 2, f"{len(ins)} vs {3 + n + 2}")
    check("prog: the allow return is second to last", ins[-2] == (0x06, 0, 0, S.RET_ALLOW))
    check("prog: the tail returns EPERM by default",
          ins[-1] == (0x06, 0, 0, 0x00050000 | 1), str(ins[-1]))
    check("prog: every compare jumps to the deny tail",
          all(ins[3 + i][1] == n - i for i in range(n)))

    killed = _insns(S.build_filter("x86_64", nrs, action="kill"))
    check("prog: action=kill returns KILL_PROCESS",
          killed[-1] == (0x06, 0, 0, S.RET_KILL_PROCESS), str(killed[-1]))
    check("prog: an unknown action falls back to errno, never to allow",
          _insns(S.build_filter("x86_64", nrs, action="bogus"))[-1][3] != S.RET_ALLOW)


def t_refusals():
    for name, fn in (
        ("an unsupported architecture", lambda: S.build_filter("riscv64", [1])),
        ("a filter that denies nothing", lambda: S.build_filter("x86_64", [])),
        ("more denied syscalls than the jump range", lambda: S.build_filter(
            "x86_64", list(range(300)))),
        ("a denylist for an unknown arch", lambda: S.resolve_denylist("riscv64")),
        ("audit_arch for an unknown arch", lambda: S.audit_arch("riscv64")),
    ):
        try:
            fn()
            check(f"refuse: {name}", False, "did not raise")
        except S.SeccompUnsupported:
            check(f"refuse: {name}", True)


def main():
    t_table_matches_kernel_abi()
    t_denylist()
    t_program_shape()
    t_refusals()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
