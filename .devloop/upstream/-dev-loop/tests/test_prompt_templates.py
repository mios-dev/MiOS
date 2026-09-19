#!/usr/bin/env python3
"""
Controls for the canned prompt system.

What changed
------------
The AGY manager prompt was a 131-line double-quoted shell assignment plus three sibling
branches for the dispatch rule. That shape, not the model, produced three measured failures:

  * 25 variables reached the model UNEXPANDED (a raw-string `\\$` survived into a
    double-quoted assignment), so the manager was handed the literal text `$SKILL_DIR`;
  * agy_host.sh died at runtime with exit 127 and `SEQUENCE,: not found`, because a pair of
    double quotes inside the prompt text closed the assignment early -- `sh -n` passes, since
    what is left is still valid shell;
  * an instruction to pass `WaitMsBeforeAsync 1800000` outlived its own refutation by two
    commits, sitting in a branch nobody diffed.

Prompts are now files with declared variables. These controls assert the renderer refuses each
of those shapes, and that the three real modes still render fully.

Run: python3 tests/test_prompt_templates.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "dev-loop" / "scripts"
PROMPTS = SCRIPTS / "prompt.py"
TPL_DIR = ROOT / "skills" / "dev-loop" / "assets" / "templates" / "prompts"
HOST = SCRIPTS / "agy_host.sh"
LANES = ROOT / "skills" / "dev-loop" / "assets" / "lanes.example.json"
sys.path.insert(0, str(SCRIPTS))

import prompt as P  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}{': ' + detail if detail else ''}")
        FAILURES.append(name)


def write_tpl(d: Path, name: str, header: str, body: str) -> Path:
    p = d / f"{name}.md"
    p.write_text(f"<!-- devloop-prompt\n{header}\n-->\n{body}")
    return p


def raises(fn, needle: str) -> tuple[bool, str]:
    try:
        fn()
        return False, "it returned instead of raising"
    except P.PromptError as e:
        return needle.lower() in str(e).lower(), str(e)


def test_shipped_templates_lint() -> None:
    print("shipped templates:")
    cp = subprocess.run([sys.executable, str(PROMPTS), "lint"], capture_output=True, text=True)
    check("lint passes", cp.returncode == 0, cp.stdout + cp.stderr)
    names = {p.stem for p in TPL_DIR.glob("*.md")}
    check("there is a template per dispatch mode",
          {"dispatch.session", "dispatch.headless", "dispatch.interactive"} <= names,
          f"found {sorted(names)}")
    check("and the manager itself", "manager" in names)


def test_missing_value_is_refused() -> None:
    """A half-rendered prompt is worse than no prompt: the model acts on the half it got."""
    print("a missing value:")
    t = P.load("manager")
    ok, msg = raises(lambda: t.render({"RUN_ROOT": "/r"}), "missing value")
    check("render refuses", ok, msg)


def test_unknown_value_is_refused() -> None:
    """The rename guard. Supplying a variable the template does not declare means one side of a
    rename was updated and the other was not -- silently dropping it renders the stale text."""
    print("an unknown value:")
    t = P.load("dispatch.interactive")
    ok, msg = raises(lambda: t.render({"RUN_ROOT": "/r", "RUNROOT": "/r"}), "does not")
    check("render refuses", ok, msg)


def test_undeclared_placeholder_is_refused() -> None:
    print("a placeholder the header does not declare:")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        p = write_tpl(d, "bad", "name: bad\nrequires: A", "{{A}} and {{B}}")
        ok, msg = raises(lambda: P.Template(p), "does not")
        check("load refuses", ok, msg)


def test_stale_declaration_is_refused() -> None:
    """A `requires:` naming a variable the body no longer uses is the other half of a rename."""
    print("a stale declaration:")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        p = write_tpl(d, "stale", "name: stale\nrequires: A, GONE", "{{A}} only")
        ok, msg = raises(lambda: P.Template(p), "never uses")
        check("load refuses", ok, msg)


def test_a_shell_variable_reaching_the_prompt_is_refused() -> None:
    """THE measured defect: 25 variables arrived at the model as literal text. A value that
    looks like a shell variable after rendering is text the model cannot act on."""
    print("a shell variable surviving into the output:")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        p = write_tpl(d, "leak", "name: leak\nrequires: A", "run {{A}} then read $RUN_ROOT/x")
        ok, msg = raises(lambda: P.Template(p).render({"A": "go"}), "shell-style")
        check("render refuses", ok, msg)

        # POSITIVE CONTROL: the check must not reject legitimate shell fragments, or every
        # template quoting a command would be unrenderable and the rule would be abandoned.
        p2 = write_tpl(d, "ok", "name: ok\nrequires: A", "run {{A}}; echo $? ; \"$1\" ; $$")
        try:
            out = P.Template(p2).render({"A": "go"})
            check("but $? $1 $$ are still allowed", "echo $?" in out, out)
        except P.PromptError as e:
            check("but $? $1 $$ are still allowed", False, str(e))


def test_shell_escapes_are_refused() -> None:
    """Caught for real while writing this: the template was lifted verbatim out of a
    double-quoted shell assignment and carried its escaping with it, so the model was handed
    `grep \\"^!\\" .gitignore`. Backslash-escaped quotes are shell syntax, not prompt text."""
    print("shell escaping surviving into the output:")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        p = write_tpl(d, "esc", "name: esc\nrequires: A", '{{A}} then grep \\"^!\\" .gitignore')
        ok, msg = raises(lambda: P.Template(p).render({"A": "go"}), "escape")
        check("render refuses", ok, msg)


def test_every_mode_renders_a_complete_prompt() -> None:
    """END TO END through the real agy_host.sh. Each mode must produce a full prompt with no
    placeholder, no leaked variable and no escaping -- the three failure shapes at once."""
    print("agy_host.sh renders every mode:")
    for flags, label in (([], "interactive"), (["--headless"], "headless"),
                         (["--session"], "session")):
        cp = subprocess.run(["sh", str(HOST), str(LANES), "--print-prompt", *flags],
                            capture_output=True, text=True, timeout=90)
        body = cp.stdout
        check(f"{label}: renders", cp.returncode == 0 and len(body) > 8000,
              f"rc={cp.returncode} len={len(body)} {cp.stderr[-200:]}")
        check(f"{label}: no placeholder survives", "{{" not in body)
        check(f"{label}: no shell variable survives",
              not P.SHELL_LEAK_RE.search(body),
              str(sorted(set(P.SHELL_LEAK_RE.findall(body)))[:5]))
        check(f"{label}: no shell escaping survives", '\\"' not in body)
        # and it is the real prompt, not an empty shell that trivially satisfies the above
        for section in ("# ROLE", "# CONTEXT", "# GOALS", "# TOOLS", "# DUTIES, IN ORDER"):
            check(f"{label}: has {section}", section in body)


def test_the_refuted_wait_pin_is_gone_everywhere() -> None:
    """The instruction that outlived its refutation. WaitMsBeforeAsync is clamped to ~10000ms,
    so 1800000 was impossible; it survived two commits inside a shell branch. Assert on the
    RENDERED prompt, where the model actually sees it, not just on the source."""
    print("the refuted WaitMsBeforeAsync pin:")
    cp = subprocess.run(["sh", str(HOST), str(LANES), "--print-prompt", "--headless"],
                        capture_output=True, text=True, timeout=90)
    body = cp.stdout
    check("1800000 appears nowhere", "1800000" not in body)
    check("the clamp is stated instead", "CLAMPED" in body or "clamped" in body)
    check("and the headless dispatch points at job.py", "job.py spawn" in body,
          "without a durable alternative, removing the pin just leaves the manager stuck")
    src = "".join((SCRIPTS / f).read_text() for f in ("agy_host.sh",))
    check("and it is gone from the source too", "1800000" not in src)


def main() -> int:
    for t in (test_shipped_templates_lint, test_missing_value_is_refused,
              test_unknown_value_is_refused, test_undeclared_placeholder_is_refused,
              test_stale_declaration_is_refused,
              test_a_shell_variable_reaching_the_prompt_is_refused,
              test_shell_escapes_are_refused, test_every_mode_renders_a_complete_prompt,
              test_the_refuted_wait_pin_is_gone_everywhere):
        t()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("all prompt-template controls passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
