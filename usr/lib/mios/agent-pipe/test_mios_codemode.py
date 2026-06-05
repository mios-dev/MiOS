"""Standalone unit test for mios_codemode (WS-2 Code Mode pure helpers).

Pure stdlib + the sibling module only -- no server.py / podman / DB import, so it
runs on any Python 3.10+ without the agent-pipe runtime deps. Mirrors the
test_mios_sched / test_mios_evict pattern: explicit asserts + a PASS/FAIL summary;
exit code != 0 on any failure.

Run:  python test_mios_codemode.py
"""

import sys

import mios_codemode as cm

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_normalize_lang() -> None:
    _check("lang: python passthrough", cm.normalize_lang("python") == "python")
    _check("lang: py alias", cm.normalize_lang("py") == "python")
    _check("lang: python3 alias", cm.normalize_lang("python3") == "python")
    _check("lang: bash passthrough", cm.normalize_lang("bash") == "bash")
    _check("lang: sh distinct from bash", cm.normalize_lang("sh") == "sh")
    _check("lang: unknown -> default", cm.normalize_lang("ruby") == cm.DEFAULT_LANG)
    _check("lang: empty -> default", cm.normalize_lang("") == cm.DEFAULT_LANG)
    _check("lang: None -> default", cm.normalize_lang(None) == cm.DEFAULT_LANG)


def t_clamp_timeout() -> None:
    _check("timeout: in-range kept", cm.clamp_timeout(30) == 30)
    _check("timeout: below min clamps", cm.clamp_timeout(0) == cm.MIN_TIMEOUT_S)
    _check("timeout: negative clamps", cm.clamp_timeout(-5) == cm.MIN_TIMEOUT_S)
    _check("timeout: above max clamps", cm.clamp_timeout(99999) == cm.MAX_TIMEOUT_S)
    _check("timeout: junk -> default", cm.clamp_timeout("abc", default=42) == 42)
    _check("timeout: None -> default", cm.clamp_timeout(None, default=60) == 60)
    _check("timeout: never zero", cm.clamp_timeout(0) >= cm.MIN_TIMEOUT_S)


def t_session_id() -> None:
    a = cm.session_id("chat-123")
    b = cm.session_id("chat-123")
    c = cm.session_id("chat-999")
    _check("session: deterministic", a == b, f"{a} vs {b}")
    _check("session: distinct per chat", a != c, f"{a} vs {c}")
    _check("session: prefixed", a.startswith("cm-"), a)
    _check("session: safe charset",
           all(ch.islower() or ch.isdigit() or ch == "-" for ch in a), a)
    # arbitrary nasty ids never break the token
    nasty = cm.session_id("../../etc/passwd  \n unicode-é")
    _check("session: nasty id sanitised",
           all(ch.islower() or ch.isdigit() or ch == "-" for ch in nasty), nasty)
    _check("session: empty -> fallback token",
           cm.session_id("") == cm.session_id("", "default"))


def t_extract_code() -> None:
    _check("extract: code key", cm.extract_code({"code": "x=1"}) == "x=1")
    _check("extract: source alias", cm.extract_code({"source": "y=2"}) == "y=2")
    _check("extract: script alias", cm.extract_code({"script": "z=3"}) == "z=3")
    _check("extract: snippet alias", cm.extract_code({"snippet": "q=4"}) == "q=4")
    _check("extract: strips ws", cm.extract_code({"code": "  a=1  "}) == "a=1")
    _check("extract: missing -> empty", cm.extract_code({}) == "")
    _check("extract: non-dict -> empty", cm.extract_code(None) == "")
    _check("extract: empty string -> empty", cm.extract_code({"code": "   "}) == "")


def t_validate_request() -> None:
    ok, p = cm.validate_request({"code": "print(1)", "lang": "py", "timeout": 5})
    _check("validate: ok flag", ok is True)
    _check("validate: code kept", p.get("code") == "print(1)")
    _check("validate: lang normalised", p.get("lang") == "python")
    _check("validate: timeout clamped-in", p.get("timeout") == 5)
    _check("validate: net default off", p.get("net") is False)

    ok2, p2 = cm.validate_request({})
    _check("validate: no code fails", ok2 is False and "error" in p2, str(p2))

    ok3, p3 = cm.validate_request({"code": "x" * (cm.MAX_CODE_CHARS + 1)})
    _check("validate: oversize fails", ok3 is False and "error" in p3, str(p3))

    ok4, p4 = cm.validate_request({"code": "ls", "net": "yes"})
    _check("validate: net truthy parsed", ok4 and p4.get("net") is True)


def t_gating() -> None:
    _check("enable: missing -> off", cm.is_enabled({}) is False)
    _check("enable: None -> off", cm.is_enabled(None) is False)
    _check("enable: false -> off", cm.is_enabled({"enable": False}) is False)
    _check("enable: 'false' str -> off", cm.is_enabled({"enable": "false"}) is False)
    _check("enable: true -> on", cm.is_enabled({"enable": True}) is True)
    _check("enable: 'true' str -> on", cm.is_enabled({"enable": "true"}) is True)
    _check("enable: 1 -> on", cm.is_enabled({"enable": 1}) is True)


def t_net_allowed() -> None:
    _check("net: agent yes + deploy no -> no",
           cm.net_allowed({"allow_net": False}, True) is False)
    _check("net: agent no + deploy yes -> no",
           cm.net_allowed({"allow_net": True}, False) is False)
    _check("net: agent yes + deploy yes -> yes",
           cm.net_allowed({"allow_net": True}, True) is True)
    _check("net: missing cfg -> no", cm.net_allowed({}, True) is False)


def t_podman_argv() -> None:
    argv = cm.podman_exec_argv("mios-coderun-sandbox-cm-abc", "python",
                               "/work/snippet.py")
    _check("argv: starts podman exec -i",
           argv[:3] == ["podman", "exec", "-i"], str(argv))
    _check("argv: container present",
           "mios-coderun-sandbox-cm-abc" in argv, str(argv))
    _check("argv: python interp", "python3" in argv, str(argv))
    _check("argv: src path present", "/work/snippet.py" in argv, str(argv))

    argv_b = cm.podman_exec_argv("c", "bash", "/work/s.sh")
    _check("argv: bash interp", "bash" in argv_b, str(argv_b))

    argv_i = cm.podman_exec_argv("c", "python", "/work/s.py",
                                 init="/usr/local/bin/exec-init")
    _check("argv: init wraps interp",
           argv_i.index("/usr/local/bin/exec-init") < argv_i.index("python3"),
           str(argv_i))


def t_parse_result() -> None:
    r = cm.parse_result("hello\n", "", 0)
    _check("parse: ok on rc0", r["ok"] is True and r["exit_code"] == 0)
    _check("parse: sandboxed flag", r["sandboxed"] is True)
    _check("parse: stdout kept", r["stdout"] == "hello\n")

    r2 = cm.parse_result("boom", "trace", 1)
    _check("parse: not-ok on rc1", r2["ok"] is False and r2["stderr"] == "trace")

    r3 = cm.parse_result('log line\n{"answer": 42}', "", 0)
    _check("parse: trailing JSON surfaced",
           r3.get("result") == {"answer": 42}, str(r3.get("result")))

    r4 = cm.parse_result("just text, no json", "", 0)
    _check("parse: no JSON -> no result key", "result" not in r4)

    big = "x" * 20000
    r5 = cm.parse_result(big, "", 0, max_chars=100)
    _check("parse: stdout bounded", len(r5["stdout"]) == 100, str(len(r5["stdout"])))


def t_build_cli_argv() -> None:
    payload = {"code": "print(1)", "lang": "python", "timeout": 5, "net": True}
    argv = cm.build_cli_argv("/usr/libexec/mios/mios-coderun-codemode",
                             payload, "chat-1", cfg={"allow_net": False})
    _check("cli: program first",
           argv[0].endswith("mios-coderun-codemode"), str(argv))
    _check("cli: lang flag", "--lang" in argv and "python" in argv, str(argv))
    _check("cli: timeout flag", "--timeout" in argv, str(argv))
    _check("cli: session flag", "--session" in argv, str(argv))
    _check("cli: net withheld when deploy off", "--net" not in argv, str(argv))

    argv2 = cm.build_cli_argv("/x/mios-coderun-codemode", payload, "chat-1",
                              cfg={"allow_net": True})
    _check("cli: net included when both on", "--net" in argv2, str(argv2))


def t_safe_token() -> None:
    _check("safe: strips slashes", "/" not in cm.safe_session_token("a/b"))
    _check("safe: empty -> default", cm.safe_session_token("") == "default")
    _check("safe: lowers", cm.safe_session_token("ABC") == "abc")


def main() -> int:
    for t in (t_normalize_lang, t_clamp_timeout, t_session_id, t_extract_code,
              t_validate_request, t_gating, t_net_allowed, t_podman_argv,
              t_parse_result, t_build_cli_argv, t_safe_token):
        t()
    passed = sum(1 for _, ok, _ in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
