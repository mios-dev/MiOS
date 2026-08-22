# AI-hint: !/usr/bin/env python3 Isolation tests for mios_pipe.routing.dispatch_cmd -- the verb->bash command BUILDER extracted from the dispatch chokepoint (T-273).
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_test_mios_dispatch_cmd_py.md

import sys

from mios_pipe.routing import dispatch_cmd as C

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if cond:
        print(f"ok   - {name}")
    else:
        _fails += 1
        print(f"FAIL - {name}" + (f" -- {detail}" if detail else ""))


_CATALOG = {
    "web_search":  {"cmd": "mios-web-search -n {limit=5} {query!}", "permission": "read"},
    "open_url":    {"cmd": "mios-open-url {url!}", "permission": "write"},
    # Opts IN to confinement via an explicit profile -- the only shape that may
    # ever be sandbox-wrapped.
    "confined":    {"cmd": "mios-run {x!}", "permission": "write",
                    "sandbox_profile": "strict"},
    # A write verb WITHOUT the explicit opt-in: tier alone must not wrap it.
    "unconfined":  {"cmd": "mios-run {x!}", "permission": "write"},
}


def _wire(*, enforce=False):
    C.configure(verb_catalog=_CATALOG, sandbox_enforce=enforce,
                sandbox_self_confined=("already-confined",))


def t_standalone_configuration():
    """The module is driven by configure() alone -- no mios_dispatch, no server."""
    _wire()
    check("configure: catalog is injected", "web_search" in C._VERB_CATALOG)
    check("configure: enforce flag is injected", C.SANDBOX_ENFORCE is False)
    _wire(enforce=True)
    check("configure: enforce flag updates", C.SANDBOX_ENFORCE is True)


def t_build_dispatch_cmd():
    _wire()
    cmd = C._build_dispatch_cmd("web_search", {"query": "hello world"})
    check("build: renders the SSOT template", cmd and "mios-web-search" in cmd, str(cmd))
    check("build: substitutes the required arg", cmd and "hello world" in cmd, str(cmd))
    check("build: applies the {arg=default} form", cmd and "-n 5" in cmd, str(cmd))

    check("build: an unknown verb yields None",
          C._build_dispatch_cmd("no_such_verb", {}) is None)


def t_sandbox_profile_resolution():
    _wire()
    prof = C._dispatch_sandbox_profile("confined")
    check("profile: an explicit override resolves", prof is not None)
    check("profile: a read verb resolves too",
          C._dispatch_sandbox_profile("web_search") is not None)
    check("profile: an unknown verb still resolves (fail-closed in mios_sandbox)",
          C._dispatch_sandbox_profile("no_such_verb") is not None)


def t_sandbox_wrap_is_opt_in():
    """The OPT-IN gate is the safety property: an explicit [verbs.*].sandbox_profile,
    NOT the permission tier, is what admits a verb to bwrap. Wrapping a launch or
    OS-control verb on tier alone would break it."""
    _wire(enforce=False)
    prof = C._dispatch_sandbox_profile("confined")
    cmd, ws = C._sandbox_wrap_cmd("confined", "echo hi", prof)
    check("wrap: enforce OFF -> never wrapped", cmd == "echo hi" and ws is None,
          f"{cmd!r} {ws!r}")

    _wire(enforce=True)
    cmd, ws = C._sandbox_wrap_cmd("unconfined", "echo hi",
                                  C._dispatch_sandbox_profile("unconfined"))
    check("wrap: a write verb WITHOUT the explicit opt-in is never wrapped",
          cmd == "echo hi" and ws is None, f"{cmd!r} {ws!r}")

    cmd, ws = C._sandbox_wrap_cmd("confined", "already-confined echo hi",
                                  C._dispatch_sandbox_profile("confined"))
    check("wrap: a self-confining cmd is left alone",
          cmd == "already-confined echo hi" and ws is None, f"{cmd!r}")


def t_normalize_container_exec():
    check("normalize: docker -> podman",
          C.normalize_container_exec("docker exec -i c bash").startswith("podman"))
    check("normalize: code-server -> mios-agents",
          "mios-agents" in C.normalize_container_exec("podman exec -i code-server bash"))
    check("normalize: a tty flag is dropped",
          "--tty" not in C.normalize_container_exec("podman exec --tty c bash"))
    check("normalize: -i is preserved",
          "-i" in C.normalize_container_exec("podman exec -it c true"))
    check("normalize: a bare interactive shell becomes `true`",
          C.normalize_container_exec("podman exec -i c /bin/bash").endswith("true"))


def main():
    t_standalone_configuration()
    t_build_dispatch_cmd()
    t_sandbox_profile_resolution()
    t_sandbox_wrap_is_opt_in()
    t_normalize_container_exec()
    print(f"\n{_fails} FAILED" if _fails else "\nok")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
