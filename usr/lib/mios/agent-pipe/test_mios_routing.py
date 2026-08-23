#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_routing (refactor R2 ROUTING-layer extraction). Pure stdlib, no server.py/DB/network/pytest.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_routing (refactor R2)."""

import sys
import os
sys.path.insert(0, "/usr/lib/mios")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import tempfile

import mios_routing as r

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


_TOML = """
[routing]
router_enable = true
launch_filler_phrases = ["for me", "on my desktop", "please"]
remember_trigger_phrases = ["Remember That", "note that"]
web_search_trigger_phrases = ["search for"]

[routing.domains.web]
desc = "web research"
verbs = ["web_search", "web_scrape", "crawl", "web_extract"]
"""


def _write_toml():
    fd, path = tempfile.mkstemp(suffix=".toml")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(_TOML)
    os.environ["MIOS_TOML"] = path
    return path


def t_load_phrases():
    fillers = r._load_routing_phrases("launch_filler_phrases")
    check("phrases longest-first", fillers[0] == "on my desktop", str(fillers))
    check("phrases complete", set(fillers) == {"on my desktop", "for me", "please"},
          str(fillers))
    remember = r._load_routing_phrases("remember_trigger_phrases")
    check("phrases lowercased", "remember that" in remember and "note that" in remember,
          str(remember))
    check("missing key -> []", r._load_routing_phrases("does_not_exist") == [])
    check("launch_fillers loader", r._load_launch_fillers() == fillers)


def t_load_domains():
    domains, enable = r._load_routing_domains()
    check("router_enable parsed", enable is True)
    check("domain desc parsed", domains.get("web", {}).get("desc") == "web research",
          str(domains))
    check("domain verbs parsed",
          domains.get("web", {}).get("verbs") == ["web_search", "web_scrape", "crawl", "web_extract"],
          str(domains))


def t_deterministic_route():
    r.configure(
        compound_action_alt="type|write",
        fastpath_verbs=frozenset({"open_app", "pc_type", "schedule", "remember"}),
        launch_triggers=frozenset({"open"}),
        launch_fillers=["on my desktop", "for me", "please"],
        launch_lead_words=frozenset({"the", "my"}),
        launch_trail_words=frozenset({"app", "application"}),
    )
    o = r._deterministic_action_route("open notepad")
    check("open -> open_app", o == {"intent": "dispatch", "tool": "open_app",
                                    "args": {"name": "notepad"}, "_deterministic": True},
          str(o))
    o2 = r._deterministic_action_route("open the calculator app")
    check("lead/trail stripped", o2 and o2["args"]["name"] == "calculator", str(o2))
    o3 = r._deterministic_action_route("open spotify for me")
    check("filler stripped", o3 and o3["args"]["name"] == "spotify", str(o3))
    p = r._deterministic_action_route("type 'hello world'")
    check("type -> pc_type", p == {"intent": "dispatch", "tool": "pc_type",
                                   "args": {"text": "hello world"}, "_deterministic": True},
          str(p))
    check("question -> None", r._deterministic_action_route("what is the weather?") is None)
    check("non-trigger -> None", r._deterministic_action_route("tell me a story") is None)
    check("compound -> None",
          r._deterministic_action_route("open notepad and type hello") is None)


def main():
    _write_toml()
    t_load_phrases()
    t_load_domains()
    t_deterministic_route()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
