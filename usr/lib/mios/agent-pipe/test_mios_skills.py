#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_skills (refactor R7 SKILLS-cluster extraction). Pure stdlib, no server.py/DB/network/pytest. Pins the projector invariants (_make_schema_strict makes every property required + additionalProperties:False + null-unions optional props; _skill_to_openai_tool emits a strict mios_skill__<name> function-tool spec with required==params) and drives execute_skill through the DI seam with async stubs (configure(dispatch_verb=..., db_read=..., ...)) to prove a 1-step promoted skill runs the verb and returns the success envelope. Guards the extracted cluster so a later move/refactor can't silently change skill tool shapes or the step-engine contract.
# AI-related: ./mios_skills.py
# AI-functions: check, t_make_schema_strict, t_skill_to_openai_tool, t_execute_skill, t_skill_render_args, t_skill_invocation_lifecycle, t_skill_attribute_tool_call, t_slug_for_skill, t_render_skill_md, t_write_skill_md_fire, main
"""Unit tests for mios_skills (refactor R7)."""

import asyncio
import sys

import mios_skills as s

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_make_schema_strict():
    strict = s._make_schema_strict({
        "type": "object",
        "properties": {
            "a": {"type": "string"},
            "b": {"type": "integer"},
        },
        "required": ["a"],
    })
    check("strict additionalProperties False",
          strict.get("additionalProperties") is False)
    # OpenAI strict: every property must be in required.
    check("strict all props required",
          set(strict.get("required") or []) == {"a", "b"},
          str(strict.get("required")))
    # The optional prop 'b' gets a nullable type-union so it can be omitted.
    check("strict optional prop nullable",
          strict["properties"]["b"]["type"] == ["integer", "null"],
          str(strict["properties"]["b"]))
    # Non-dict input degrades to an empty strict object schema.
    deg = s._make_schema_strict("nope")
    check("strict non-dict degrade",
          deg == {"type": "object", "properties": {},
                  "required": [], "additionalProperties": False})


def t_skill_to_openai_tool():
    tool = s._skill_to_openai_tool({
        "name": "my skill!",
        "description": "does a thing",
        "body": {"params": ["url", "title"]},
    })
    check("tool type function", tool.get("type") == "function")
    fn = tool.get("function") or {}
    check("tool name sanitized + prefixed",
          fn.get("name") == "mios_skill__my_skill_", fn.get("name"))
    check("tool strict True", fn.get("strict") is True)
    params = fn.get("parameters") or {}
    check("tool required == params",
          params.get("required") == ["url", "title"])
    check("tool additionalProperties False",
          params.get("additionalProperties") is False)
    # Rich typed params test case
    tool_rich = s._skill_to_openai_tool({
        "name": "rich skill",
        "description": "does a rich thing",
        "body": {
            "params": {
                "url": {
                    "type": "string",
                    "description": "URL to open"
                },
                "disposition": {
                    "type": "string",
                    "enum": ["tab", "window"],
                    "description": "where to open"
                }
            }
        }
    })
    check("rich: tool type function", tool_rich.get("type") == "function")
    fn_rich = tool_rich.get("function") or {}
    check("rich: tool name", fn_rich.get("name") == "mios_skill__rich_skill")
    check("rich: tool strict True", fn_rich.get("strict") is True)
    params_rich = fn_rich.get("parameters") or {}
    check("rich: tool required matches keys", params_rich.get("required") == ["url", "disposition"])
    check("rich: tool additionalProperties False", params_rich.get("additionalProperties") is False)
    props_rich = params_rich.get("properties") or {}
    check("rich: url type", props_rich.get("url", {}).get("type") == "string")
    check("rich: url desc", props_rich.get("url", {}).get("description") == "URL to open")
    check("rich: disposition type", props_rich.get("disposition", {}).get("type") == "string")
    check("rich: disposition enum", props_rich.get("disposition", {}).get("enum") == ["tab", "window"])


def t_execute_skill():
    ROW = {"id": "skill:abc123", "name": "demo", "status": "promoted",
           "body": {"steps": [{"verb": "noop", "args": {}}]}}
    calls = {"dispatched": []}

    async def stub_db_read(*a, **k):
        return [{"result": [ROW]}]

    async def stub_dispatch(verb, args, *, session_id=None):
        calls["dispatched"].append((verb, args))
        return {"success": True, "exit_code": 0, "output": "ok", "stderr": ""}

    async def stub_db_post(*a, **k):
        return []

    async def stub_db_update(*a, **k):
        return None

    def stub_db_write(*a, **k):
        return None

    def stub_pg_mirror(*a, **k):
        return None

    # The invocation/attribution lifecycle + arg renderer now LIVE in mios_skills
    # (no longer injected); execute_skill drives the REAL helpers, which only need
    # the DB-event helpers + pg mirror stubbed (_passport_sign degrades to None
    # without a key, so open synthesizes a pg-id and proceeds).
    s.configure(
        db_read=stub_db_read,
        db_post=stub_db_post,
        db_update=stub_db_update,
        db_write=stub_db_write,
        pg_mirror=stub_pg_mirror,
        dispatch_verb=stub_dispatch,
        skills_enabled=True,
    )

    out = asyncio.run(s.execute_skill("demo", {}, session_id=None))
    check("execute_skill success", out.get("success") is True, str(out))
    check("execute_skill ran the verb",
          calls["dispatched"] == [("noop", {})], str(calls["dispatched"]))
    check("execute_skill one step recorded",
          len(out.get("steps") or []) == 1, str(out.get("steps")))


def t_skill_render_args():
    # $-token substitution from the params map; non-str values pass through.
    out = s._skill_render_args(
        {"url": "$site/page", "n": 5, "who": "$user"},
        {"site": "http://x", "user": "alice"})
    check("render substitutes tokens", out["url"] == "http://x/page", str(out))
    check("render leaves non-str untouched", out["n"] == 5, str(out))
    check("render second token", out["who"] == "alice", str(out))
    # A missing param leaves the $-token literal so the dispatch errors visibly.
    miss = s._skill_render_args({"a": "$gone"}, {})
    check("render missing param literal", miss["a"] == "$gone", str(miss))


def t_skill_invocation_lifecycle():
    posts = []
    mirrors = []

    async def stub_db_post(sql, *a, **k):
        posts.append(sql)
        return []  # pg-primary short-circuit shape -> open synthesizes an id

    def stub_pg_mirror(table, fields):
        mirrors.append((table, fields))

    s.configure(db_post=stub_db_post, pg_mirror=stub_pg_mirror)
    inv = asyncio.run(s._skill_invocation_open("skill:abc", {"x": 1}, None))
    check("open synthesizes inv id",
          isinstance(inv, str) and inv.startswith("skill_invocation:pg-"), str(inv))
    check("open records carry meta",
          s._SKILL_INV_META.get(inv) == {"skill": "skill:abc", "session": None},
          str(s._SKILL_INV_META.get(inv)))
    check("open issued a CREATE",
          any("CREATE skill_invocation" in p for p in posts), str(posts))
    asyncio.run(s._skill_invocation_close(inv, True))
    check("close mirrors outcome to pg",
          bool(mirrors) and mirrors[-1][0] == "skill_invocation"
          and mirrors[-1][1].get("success") is True, str(mirrors))
    check("close pops carry meta", inv not in s._SKILL_INV_META,
          str(s._SKILL_INV_META))
    check("close issued an UPDATE",
          any(p.startswith(f"UPDATE {inv}") for p in posts), str(posts))


def t_skill_attribute_tool_call():
    posts = []

    async def stub_db_post(sql, *a, **k):
        posts.append(sql)
        return []

    s.configure(db_post=stub_db_post)
    # Missing inv_id or tool_call_id -> no-op (no SQL emitted).
    asyncio.run(s._skill_attribute_tool_call(None, "tc:1", 0))
    asyncio.run(s._skill_attribute_tool_call("inv:1", None, 0))
    check("attribute no-op on missing ids", posts == [], str(posts))
    # Both present -> RELATE emitted carrying the step index.
    asyncio.run(s._skill_attribute_tool_call("inv:1", "tc:1", 3))
    check("attribute emits RELATE",
          any("RELATE inv:1->emitted->tc:1" in p and "step_index = 3" in p
              for p in posts), str(posts))


def t_slug_for_skill():
    # Synthetic non-dictionary tokens (no baked English example words); the slug
    # lowercases + collapses non-[a-z0-9] runs to single hyphens and trims edges.
    check("slug lowercases + hyphenates",
          s._slug_for_skill("  Zxq!! Vwk__Mtp  ") == "zxq-vwk-mtp",
          s._slug_for_skill("  Zxq!! Vwk__Mtp  "))
    # Length cap at 60 chars.
    long = "q" * 200
    check("slug length-capped to 60", len(s._slug_for_skill(long)) == 60)
    # Empty / all-stripped input degrades to the literal fallback.
    check("slug empty -> fallback", s._slug_for_skill("") == "skill")
    check("slug all-symbols -> fallback", s._slug_for_skill("@#$%") == "skill")


def t_render_skill_md():
    md = s._render_skill_md(
        "qwzx vptm", "mtpq result body",
        [{"tool": "verb_zz", "args": {"k": "v"}}], "sess:9")
    check("render frontmatter fence", md.startswith("---\n"))
    check("render carries goal", "qwzx vptm" in md)
    check("render carries outcome", "mtpq result body" in md)
    check("render lists the verb in frontmatter", "verb_zz" in md)
    check("render stamps the session", "session: sess:9" in md)
    # No tool history -> the explicit no-tools workflow note.
    md2 = s._render_skill_md("qwzx", "ans", None, None)
    check("render no-tools note",
          "answer produced without explicit tool calls" in md2)


def t_write_skill_md_fire(tmp_subdir):
    import os
    # Disabled flag -> hard no-op (no dir/file created).
    s.configure(skills_episodic_dir=os.path.join(tmp_subdir, "off"),
                skills_episodic_enabled=False)
    s._write_skill_md_fire(query="qwzx", answer="mtpq")
    check("write disabled -> no dir created",
          not os.path.isdir(os.path.join(tmp_subdir, "off")))
    # Enabled but empty q/a -> no-op (degrade-open, never raises).
    on_dir = os.path.join(tmp_subdir, "on")
    s.configure(skills_episodic_dir=on_dir, skills_episodic_enabled=True)
    s._write_skill_md_fire(query="", answer="mtpq")
    check("write empty-query -> skip",
          not os.path.isdir(on_dir) or not os.listdir(on_dir))
    # Enabled + real q/a -> a single .md file lands carrying the goal.
    s._write_skill_md_fire(query="qwzx vptm", answer="mtpq result",
                           tool_history=[{"tool": "verb_zz", "args": {}}],
                           session_id="sess:1")
    files = [f for f in os.listdir(on_dir) if f.endswith(".md")]
    check("write produced one .md", len(files) == 1, str(files))
    body = open(os.path.join(on_dir, files[0]), encoding="utf-8").read()
    check("written md carries goal + verb",
          "qwzx vptm" in body and "verb_zz" in body)


def main():
    import tempfile
    t_make_schema_strict()
    t_skill_to_openai_tool()
    t_execute_skill()
    t_skill_render_args()
    t_skill_invocation_lifecycle()
    t_skill_attribute_tool_call()
    t_slug_for_skill()
    t_render_skill_md()
    with tempfile.TemporaryDirectory() as td:
        t_write_skill_md_fire(td)
    print(f"\n{'OK' if _fails == 0 else 'FAIL'}: {_fails} failure(s)")
    sys.exit(1 if _fails else 0)


if __name__ == "__main__":
    main()
