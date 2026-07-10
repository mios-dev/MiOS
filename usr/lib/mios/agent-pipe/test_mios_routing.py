#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_routing (refactor R2 ROUTING-layer extraction). Pure stdlib, no server.py/DB/network/pytest. Writes a synthetic mios.toml [routing] block + points MIOS_TOML at it to exercise the real config readers (_load_routing_phrases lowercases + sorts longest-first; _load_routing_domains parses [routing.domains.*] + the router_enable switch), then drives _deterministic_action_route through the configure() DI seam (synthetic fast-path verb sets + launch fillers + compound action vocab) to prove an unambiguous "open <app>" binds open_app, a quoted "type '<text>'" binds pc_type, and a question / compound / non-trigger message routes to None. Guards the extracted layer so a later move can't silently change the deterministic pre-router contract or the SSOT phrase parsing.
# AI-related: ./mios_routing.py
# AI-functions: check, t_load_phrases, t_load_domains, t_deterministic_route, main
"""Unit tests for mios_routing (refactor R2)."""

import os
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
verbs = ["web_search", "fetch_page"]
"""


def _write_toml():
    fd, path = tempfile.mkstemp(suffix=".toml")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(_TOML)
    os.environ["MIOS_TOML"] = path
    return path


def t_load_phrases():
    fillers = r._load_routing_phrases("launch_filler_phrases")
    # lowercased, de-duplicated, longest-first.
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
    # Inject synthetic fast-path verb sets + launch phrase frozensets (these
    # derive from _VERB_CATALOG in server.py and are normally injected there).
    r.configure(
        compound_action_alt="type|write",
        fastpath_verbs=frozenset({"open_app", "pc_type", "schedule", "remember"}),
        launch_triggers=frozenset({"open"}),
        launch_fillers=["on my desktop", "for me", "please"],
        launch_lead_words=frozenset({"the", "my"}),
        launch_trail_words=frozenset({"app", "application"}),
    )
    # Unambiguous launch -> open_app(name=...).
    o = r._deterministic_action_route("open notepad")
    check("open -> open_app", o == {"intent": "dispatch", "tool": "open_app",
                                    "args": {"name": "notepad"}, "_deterministic": True},
          str(o))
    # Lead determiner + trailing generic noun stripped.
    o2 = r._deterministic_action_route("open the calculator app")
    check("lead/trail stripped", o2 and o2["args"]["name"] == "calculator", str(o2))
    # Trailing courtesy filler stripped.
    o3 = r._deterministic_action_route("open spotify for me")
    check("filler stripped", o3 and o3["args"]["name"] == "spotify", str(o3))
    # Quoted standalone type -> pc_type(text=...).
    p = r._deterministic_action_route("type 'hello world'")
    check("type -> pc_type", p == {"intent": "dispatch", "tool": "pc_type",
                                   "args": {"text": "hello world"}, "_deterministic": True},
          str(p))
    # Neutral / question / compound / non-trigger -> None.
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
