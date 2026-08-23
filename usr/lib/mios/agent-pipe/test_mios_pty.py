#!/usr/bin/env python3
# AI-hint: Stdlib offline tests for mios_pipe.routing.pty -- the persistent shell substrate's pure protocol (SHELL-01). No tmux, no subproc...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_test_mios_pty_py.md

import sys

from mios_pipe.routing import pty as P

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if cond:
        print(f"ok   - {name}")
    else:
        _fails += 1
        print(f"FAIL - {name}" + (f" -- {detail}" if detail else ""))


def t_session_key_cannot_escape():
    k = P.session_key("../../etc/passwd")
    check("key: path traversal is neutralised",
          ".." not in k and "/" not in k, k)
    k = P.session_key("a; rm -rf /")
    check("key: shell metacharacters are neutralised",
          all(c.isalnum() or c in "-_" for c in k), k)
    check("key: always namespaced", P.session_key("x").startswith(P.SESSION_PREFIX))
    check("key: empty id still yields a unique name",
          P.session_key("") != P.SESSION_PREFIX and len(P.session_key("")) > 6,
          P.session_key(""))
    check("key: None is handled", P.session_key(None).startswith(P.SESSION_PREFIX))
    check("key: is stable for the same id",
          P.session_key("chat-9") == P.session_key("chat-9"))


def t_long_ids_do_not_collide():
    """Truncating alone would map two long ids to one shell -- and one chat
    reading another's cwd/env is the whole risk this substrate introduces."""
    a = "s" * 80 + "-alpha"
    b = "s" * 80 + "-beta"
    ka, kb = P.session_key(a), P.session_key(b)
    check("key: long ids are capped", len(ka) <= 48 + len(P.SESSION_PREFIX), ka)
    check("key: two long ids do NOT collide", ka != kb, f"{ka} vs {kb}")


def t_session_path_is_contained():
    p = P.session_path("../../../root", "/var/lib/mios/shell-sessions")
    check("path: cannot walk out of the root",
          p.startswith("/var/lib/mios/shell-sessions/") and ".." not in p, p)


def t_tmux_argv():
    check("argv: new", P.tmux_argv("new", "c1")[:4] == ["tmux", "-L", "mios", "new-session"])
    check("argv: send carries the command",
          "echo hi" in P.tmux_argv("send", "c1", command="echo hi"))
    check("argv: kill targets the namespaced key",
          P.session_key("c1") in P.tmux_argv("kill", "c1"))
    check("argv: an unknown action yields [] rather than a guess",
          P.tmux_argv("frobnicate", "c1") == [])


def t_wrap_requires_a_real_nonce():
    n = P.new_nonce()
    check("nonce: is long hex", len(n) >= 32 and all(c in "0123456789abcdef" for c in n))
    check("nonce: differs each call", P.new_nonce() != P.new_nonce())
    w = P.wrap_command("echo hi", n)
    check("wrap: the command is preserved", "\necho hi\n" in w, w)
    check("wrap: both sentinels are emitted",
          w.count(P.MARKER_PREFIX) == 2 and f"{n}-BEGIN" in w and f"{n} $? $PWD" in w, w)
    # The framing is printed in TWO pieces precisely so the terminal ECHO of
    # this line never contains an assembled marker -- otherwise the echo parses
    # as the result and the first command back reports a null exit code.
    check("wrap: no assembled marker appears in the command text",
          (P.MARKER_PREFIX + n) not in w, w)
    for bad in ("", None, "not-hex", "abc"):
        try:
            P.wrap_command("echo hi", bad)
            check(f"wrap: rejects a bad nonce {bad!r}", False)
        except ValueError:
            check(f"wrap: rejects a bad nonce {bad!r}", True)


def t_parse_happy_path():
    n = P.new_nonce()
    cap = (f"prompt$ stuff\n{P.MARKER_PREFIX}{n}-BEGIN\n"
           f"line one\nline two\n{P.MARKER_PREFIX}{n} 0 /tmp\n")
    r = P.parse_result(cap, n)
    check("parse: exit code", r and r["exit_code"] == 0, str(r))
    check("parse: cwd", r and r["cwd"] == "/tmp", str(r))
    check("parse: output excludes the marker line",
          r and P.MARKER_PREFIX not in r["output"], str(r))
    check("parse: output is otherwise verbatim",
          r and r["output"] == "line one\nline two", repr(r["output"]))

    cap = (f"{P.MARKER_PREFIX}{n}-BEGIN\nboom\n"
           f"{P.MARKER_PREFIX}{n} 127 /home/u\n")
    r = P.parse_result(cap, n)
    check("parse: a non-zero exit is carried", r and r["exit_code"] == 127, str(r))


def t_unfinished_is_not_success():
    n = P.new_nonce()
    check("parse: no marker yet -> None, NOT exit 0",
          P.parse_result("still running...\n", n) is None)
    check("parse: empty capture -> None", P.parse_result("", n) is None)


def t_output_cannot_forge_completion():
    """The security property: a command that PRINTS a marker-shaped line must
    not be read as having completed, because it cannot know this command's
    nonce."""
    mine = P.new_nonce()
    attacker = P.new_nonce()
    cap = (f"{P.MARKER_PREFIX}{mine}-BEGIN\n"
           f"pretending to finish\n{P.MARKER_PREFIX}{attacker} 0 /root\n"
           "still actually running\n")
    check("spoof: a marker with a DIFFERENT nonce is ignored",
          P.parse_result(cap, mine) is None, str(P.parse_result(cap, mine)))

    cap = f"here is the literal prefix {P.MARKER_PREFIX} and no nonce\n"
    check("spoof: a bare prefix with no nonce is ignored",
          P.parse_result(cap, mine) is None)

    # An old capture replayed into the pane must not end the CURRENT command
    # early: the LAST marker for this nonce is the authoritative one.
    cap = (f"{P.MARKER_PREFIX}{mine}-BEGIN\n"
           f"{P.MARKER_PREFIX}{mine} 1 /old\n"
           "more real output\n"
           f"{P.MARKER_PREFIX}{mine} 0 /new\n")
    r = P.parse_result(cap, mine)
    check("spoof: the LAST real marker wins", r and r["cwd"] == "/new", str(r))
    check("spoof: earlier output is retained",
          r and "more real output" in r["output"], str(r))


def t_idle_reaper_is_conservative():
    check("idle: past the window -> reap", P.is_idle(1000.0, now=5000.0, idle_s=100) is True)
    check("idle: inside the window -> keep", P.is_idle(4950.0, now=5000.0, idle_s=100) is False)
    for bad in (None, "", "not-a-number", 0, -1):
        check(f"idle: bad bookkeeping {bad!r} -> never reap",
              P.is_idle(bad, now=5000.0, idle_s=100) is False)


def main():
    t_session_key_cannot_escape()
    t_long_ids_do_not_collide()
    t_session_path_is_contained()
    t_tmux_argv()
    t_wrap_requires_a_real_nonce()
    t_parse_happy_path()
    t_unfinished_is_not_success()
    t_output_cannot_forge_completion()
    t_idle_reaper_is_conservative()
    print(f"\n{_fails} FAILED" if _fails else "\nok")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
