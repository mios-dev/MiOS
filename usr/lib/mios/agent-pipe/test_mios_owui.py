#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_owui (OWUI RAG/task-template scaffold stripper). Pure stdlib, no server.py/DB/pytest. Verifies strip_owui_scaffold recovers the genuine user question from each OWUI scaffold shape (trailing-after-</context>, explicit <user_query>/<query>/<question>/<prompt> tag, head-before-### Task:, marker-sentence detection) and passes plain/non-OWUI text through unchanged, plus empty/whitespace and the recognised-but-uis olable fallback.
# AI-related: ./mios_owui.py
# AI-functions: check, main
"""Unit tests for mios_owui (OWUI scaffold stripping)."""

import sys

import mios_owui as owui

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_passthrough_plain():
    # A plain question with no OWUI scaffold markers must round-trip unchanged.
    q = "What is the capital of France?"
    check("plain: unchanged", owui.strip_owui_scaffold(q) == q)
    # Mentioning the bare word 'task' must NOT trigger stripping.
    q2 = "Please add this task to my list and remind me tomorrow."
    check("plain: bare 'task' word not a trigger", owui.strip_owui_scaffold(q2) == q2)
    # Containing a '<' (e.g. a comparison) must NOT trigger stripping.
    q3 = "Is 3 < 5 and is x<y in math?"
    check("plain: bare '<' not a trigger", owui.strip_owui_scaffold(q3) == q3)
    # A normal message that contains '### Task:' but NO </context> is NOT OWUI.
    q4 = "### Task: write a haiku about the sea"
    check("plain: '### Task:' alone (no </context>) unchanged",
          owui.strip_owui_scaffold(q4) == q4)
    # A normal message that contains '</context>' but no marker and no '### task:'
    # is NOT recognised as OWUI -> unchanged.
    q5 = "Explain the </context> XML tag to me."
    check("plain: stray '</context>' alone unchanged",
          owui.strip_owui_scaffold(q5) == q5)


def t_empty_and_whitespace():
    # Falsy input returned as-is (same object/value).
    check("empty: '' -> ''", owui.strip_owui_scaffold("") == "")
    check("empty: None -> None", owui.strip_owui_scaffold(None) is None)
    # Whitespace-only is truthy but has no markers -> returned unchanged (NOT trimmed).
    ws = "   \n\t  "
    check("whitespace: non-empty whitespace unchanged (not trimmed)",
          owui.strip_owui_scaffold(ws) == ws)


def t_trailing_after_context():
    # The CURRENT OWUI DEFAULT_RAG_TEMPLATE: real query APPENDED after </context>.
    scaffold = (
        "### Task:\n"
        "Respond to the user query using the provided context.\n"
        "### Guidelines:\n"
        "- be concise\n"
        "<context>\n"
        "Paris is the capital of France. Some retrieved source text here.\n"
        "</context>\n"
        "How tall is the Eiffel Tower?"
    )
    out = owui.strip_owui_scaffold(scaffold)
    check("trailing: recovers genuine question",
          out == "How tall is the Eiffel Tower?", repr(out))
    # The recovered text must NOT contain any scaffold leakage.
    check("trailing: no '### task:' leak", "### task:" not in out.lower())
    check("trailing: no context-block leak",
          "<context>" not in out.lower() and "</context>" not in out.lower())
    check("trailing: no marker sentence leak",
          "respond to the user query" not in out.lower())


def t_trailing_multiline_question():
    # The trailing question itself can be multi-line; DOTALL must keep all of it.
    scaffold = (
        "### Task:\nRespond to the user query using the provided context.\n"
        "<context>retrieved stuff</context>\n"
        "First line of my real question.\n"
        "Second line continues it."
    )
    out = owui.strip_owui_scaffold(scaffold)
    check("trailing: multi-line trailing query preserved whole",
          out == "First line of my real question.\nSecond line continues it.",
          repr(out))


def t_explicit_user_query_tag():
    # Older OWUI / other templates use an explicit <user_query> tag.
    scaffold = (
        "### Task:\nRespond to the user query using the provided context.\n"
        "<context>some sources</context>\n"
        "<user_query>What is photosynthesis?</user_query>"
    )
    out = owui.strip_owui_scaffold(scaffold)
    check("tag: <user_query> extracted", out == "What is photosynthesis?", repr(out))
    # Tag extraction is the FIRST branch -> wins even though a </context> trailing
    # branch could also match. The <user_query> content here is at the END after
    # </context>; verify the tag branch (not raw trailing incl. the tag) wins.
    check("tag: angle brackets stripped from result", "<" not in out and ">" not in out)


def t_alternate_payload_tags():
    # <query>, <question>, <prompt> are also recognised payload tags. Detection
    # still requires an OWUI signal: include the marker sentence to be recognised.
    for tag in ("query", "question", "prompt"):
        scaffold = (
            "### Task:\nRespond to the user query using the provided context.\n"
            "<context>ctx</context>\n"
            f"<{tag}>Genuine {tag} text here</{tag}>"
        )
        out = owui.strip_owui_scaffold(scaffold)
        check(f"tag: <{tag}> extracted", out == f"Genuine {tag} text here", repr(out))


def t_user_query_tag_alone_triggers():
    # '<user_query>' alone is an OWUI signal even without a marker / </context>.
    scaffold = "<user_query>Just the question</user_query>"
    out = owui.strip_owui_scaffold(scaffold)
    check("tag-trigger: <user_query> alone recognised + extracted",
          out == "Just the question", repr(out))


def t_empty_tag_falls_through():
    # An EMPTY <user_query></user_query> must not return an empty string; the tag
    # branch requires non-empty content, so detection still fires but the empty
    # tag is skipped and we fall through to later branches / fallback.
    scaffold = (
        "Real question precedes it.\n"
        "### Task:\nRespond to the user query using the provided context.\n"
        "<context>ctx</context>\n"
        "<user_query>   </user_query>"
    )
    out = owui.strip_owui_scaffold(scaffold)
    # Trailing-after-</context> branch sees only the empty <user_query> tag as the
    # candidate. That candidate has no '### task:' / '<context>' so it IS returned.
    # Document the ACTUAL contract: trailing branch wins with the (stripped) tag text.
    check("empty-tag: does not return empty string", out != "", repr(out))


def t_head_before_task():
    # Query may PRECEDE the template (some OWUI flows). Branch 3: take text before
    # the first '### Task:'. There is NO trailing text after </context> here.
    scaffold = (
        "Summarize the attached document for me.\n\n"
        "### Task:\nRespond to the user query using the provided context.\n"
        "### Guidelines:\n- cite sources\n"
        "<context>doc body text</context>"
    )
    out = owui.strip_owui_scaffold(scaffold)
    check("head: recovers leading question before '### Task:'",
          out == "Summarize the attached document for me.", repr(out))
    check("head: no scaffold leak", "### task:" not in out.lower()
          and "<context>" not in out.lower())


def t_marker_only_title_task():
    # OWUI title-generation task: 'generate a concise' marker, no </context>, no
    # explicit tag, query NOT cleanly isolable -> fallback returns text unchanged
    # (branch 4: recognised but not isolable -> leave as-is, don't drop content).
    scaffold = (
        "Generate a concise, 3-5 word title summarizing the chat history.\n"
        "Chat:\nUser: hello\nAssistant: hi"
    )
    out = owui.strip_owui_scaffold(scaffold)
    # No </context>, no '### task:' head split that strips anything (no '### task:'
    # present), no payload tag -> the whole thing comes back. Document it.
    check("marker-only: recognised but not isolable -> unchanged (no drop)",
          out == scaffold, repr(out))


def t_each_marker_detected():
    # Every OWUI_TEMPLATE_MARKERS entry must flip detection on. Pair each with a
    # </context> + trailing question so we can confirm detection by a CHANGED result.
    for marker in owui.OWUI_TEMPLATE_MARKERS:
        scaffold = (
            f"Some boilerplate that {marker} blah blah.\n"
            "<context>ctx</context>\n"
            "RECOVERED_QUESTION"
        )
        out = owui.strip_owui_scaffold(scaffold)
        check(f"marker: '{marker[:24]}...' triggers strip",
              out == "RECOVERED_QUESTION", repr(out))


def t_marker_case_insensitive():
    # Detection lower-cases the text: an UPPERCASE marker must still trigger.
    scaffold = (
        "RESPOND TO THE USER QUERY USING THE PROVIDED CONTEXT.\n"
        "<CONTEXT>ctx</CONTEXT>\n"
        "The actual question."
    )
    out = owui.strip_owui_scaffold(scaffold)
    check("case: uppercase marker + tag detected and stripped",
          out == "The actual question.", repr(out))


def t_task_plus_context_combo_trigger():
    # The '### task:' + '</context>' combination triggers even with NO marker
    # sentence and NO explicit payload tag.
    scaffold = (
        "### Task:\nDo the thing.\n"
        "<context>ctx</context>\n"
        "Genuine combo question?"
    )
    out = owui.strip_owui_scaffold(scaffold)
    check("combo: '### task:' + '</context>' triggers + recovers trailing",
          out == "Genuine combo question?", repr(out))


def t_trailing_boilerplate_rejected():
    # If the text after </context> is ITSELF more boilerplate (another '### Task:'
    # or '<context>'), the trailing branch must reject it and fall through.
    scaffold = (
        "Leading real question.\n"
        "### Task:\nRespond to the user query using the provided context.\n"
        "<context>first ctx</context>\n"
        "### Task: more nested boilerplate"
    )
    out = owui.strip_owui_scaffold(scaffold)
    # Trailing candidate contains '### task:' -> rejected. Falls to head branch,
    # which returns text before the FIRST '### task:'.
    check("reject-trailing: falls through to head when trailing is boilerplate",
          out == "Leading real question.", repr(out))


def t_idempotent_on_clean_output():
    # Stripping a scaffold then stripping the RESULT again must be a no-op
    # (the recovered clean question has no markers).
    scaffold = (
        "### Task:\nRespond to the user query using the provided context.\n"
        "<context>ctx</context>\n"
        "How do plants make energy?"
    )
    once = owui.strip_owui_scaffold(scaffold)
    twice = owui.strip_owui_scaffold(once)
    check("idempotent: second strip is a no-op", once == twice == "How do plants make energy?",
          f"{once!r} / {twice!r}")


def t_markers_constant_shape():
    # Guard the protocol-constant contract: markers are a non-empty tuple of
    # lower-case strings (detection lower-cases the text before matching).
    m = owui.OWUI_TEMPLATE_MARKERS
    check("markers: is a tuple", isinstance(m, tuple))
    check("markers: non-empty", len(m) >= 1)
    check("markers: all lower-case strings",
          all(isinstance(x, str) and x == x.lower() and x for x in m))
    check("markers: includes the core RAG sentence",
          "respond to the user query using the provided context" in m)


def main():
    t_passthrough_plain()
    t_empty_and_whitespace()
    t_trailing_after_context()
    t_trailing_multiline_question()
    t_explicit_user_query_tag()
    t_alternate_payload_tags()
    t_user_query_tag_alone_triggers()
    t_empty_tag_falls_through()
    t_head_before_task()
    t_marker_only_title_task()
    t_each_marker_detected()
    t_marker_case_insensitive()
    t_task_plus_context_combo_trigger()
    t_trailing_boilerplate_rejected()
    t_idempotent_on_clean_output()
    t_markers_constant_shape()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
