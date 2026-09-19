#!/usr/bin/env python3
"""
Canned prompt rendering: a prompt is a reviewable FILE with declared variables, not a string
assembled inside a shell script.

Why this exists
---------------
The AGY manager prompt lived as a 131-line double-quoted shell assignment with three sibling
branches for the dispatch rule. That shape produced, in one week:

  * 25 shell variables reaching the model UNEXPANDED, because a raw-string backslash-dollar
    survived into a double-quoted assignment -- the manager was handed `$SKILL_DIR` literally;
  * a whole script broken at runtime (exit 127, `SEQUENCE,: not found`) because a pair of
    double quotes inside the prompt text closed the assignment early -- `sh -n` passes, since
    the result is still syntactically valid shell;
  * an instruction to pass `WaitMsBeforeAsync 1800000` that outlived its own refutation by two
    commits, because it sat in a branch nobody diffed.

None of those are model problems. They are all consequences of prompt text being shell source.
As files with declared variables they are diffable, testable, and the renderer refuses the
three failure shapes outright.

The contract
------------
A template is a Markdown file that opens with a declaration block:

    <!-- devloop-prompt
    name: manager
    requires: RUN_ROOT, SKILL_DIR, LANES, DISPATCH_RULE
    summary: one or more indented lines, free text
    -->

and a body that references variables as `{{NAME}}`. Rendering fails, loudly and before any
output is produced, when:

  1. the body uses a placeholder the header does not declare          (undeclared)
  2. a declared variable is not supplied                              (missing)
  3. a variable is supplied that the template does not declare        (unknown -- usually a
     rename that updated one side only)
  4. any `{{` survives substitution                                   (partial render)
  5. any `$UPPERCASE_NAME` survives into the output                   (a shell leak: text the
     model cannot act on, and the exact defect above)

Rule 5 has one deliberate exception: `$?`, `$0`-`$9` and `$$` are shell fragments the prompt
legitimately quotes inside example commands.

Usage
-----
    prompt.py render <template> --var K=V [--var K=V ...] [--out FILE]
    prompt.py declare <template>        # print name + required variables, machine-readable
    prompt.py lint [<dir>]              # check every template parses and self-declares

Exit: 0 ok, 1 usage, 2 template or render error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HEADER_RE = re.compile(r"\A<!--\s*devloop-prompt\s*\n(.*?)\n-->\n", re.DOTALL)
PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
# A shell-style variable that survived into rendered text. $? $0-$9 $$ are legitimate quoting.
SHELL_LEAK_RE = re.compile(r"\$(?!\?|\$|[0-9])\{?[A-Z_][A-Z0-9_]{2,}\}?")

DEFAULT_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates" / "prompts"


class PromptError(Exception):
    """A template or render fault. Always names the template and the offending symbol."""


class Template:
    def __init__(self, path: Path) -> None:
        self.path = path
        text = path.read_text("utf-8")
        m = HEADER_RE.match(text)
        if not m:
            raise PromptError(f"{path.name}: missing the `<!-- devloop-prompt ... -->` "
                              f"declaration block; a template that declares nothing cannot be "
                              f"checked against its body")
        self.body = text[m.end():]
        self.meta = self._parse_header(m.group(1), path)
        self.name = self.meta.get("name") or path.stem
        req = self.meta.get("requires", "")
        self.requires = [v.strip() for v in req.split(",") if v.strip()]
        self.used = sorted(set(PLACEHOLDER_RE.findall(self.body)))

        undeclared = [v for v in self.used if v not in self.requires]
        if undeclared:
            raise PromptError(f"{path.name}: body uses {undeclared} but `requires:` does not "
                              f"declare them (declared: {self.requires or 'none'})")
        unused = [v for v in self.requires if v not in self.used]
        if unused:
            raise PromptError(f"{path.name}: `requires:` declares {unused} that the body never "
                              f"uses -- a stale declaration hides a rename")

    @staticmethod
    def _parse_header(raw: str, path: Path) -> dict:
        meta: dict[str, str] = {}
        key = None
        for line in raw.split("\n"):
            if line[:1] in (" ", "\t") and key:          # continuation of the previous value
                meta[key] += " " + line.strip()
                continue
            if ":" not in line:
                if line.strip():
                    raise PromptError(f"{path.name}: header line is not `key: value`: {line!r}")
                continue
            key, _, val = line.partition(":")
            key = key.strip()
            meta[key] = val.strip()
        return meta

    def render(self, values: dict[str, str]) -> str:
        unknown = sorted(set(values) - set(self.requires))
        if unknown:
            raise PromptError(f"{self.path.name}: given {unknown}, which this template does not "
                              f"declare (declares: {self.requires})")
        missing = [v for v in self.requires if v not in values]
        if missing:
            raise PromptError(f"{self.path.name}: missing value(s) for {missing}")

        out = PLACEHOLDER_RE.sub(lambda m: values[m.group(1)], self.body)

        if "{{" in out:
            left = sorted(set(PLACEHOLDER_RE.findall(out))) or ["<malformed>"]
            raise PromptError(f"{self.path.name}: placeholders survived rendering: {left}")
        # Backslash-escaped quotes and dollars are shell ESCAPING, not prompt text. They are
        # meaningless to a model and arrive as visible noise -- and they are exactly what a
        # template lifted out of a double-quoted shell assignment brings with it. (Measured:
        # the manager prompt reached the model reading `grep \\"^!\\" .gitignore`.)
        escapes = sorted(set(re.findall(r'\\[\"$`]', out)))
        if escapes:
            raise PromptError(
                f"{self.path.name}: shell escape sequences {escapes} survived into the rendered "
                f"prompt. A template is not shell source; write the character itself.")
        leaks = sorted(set(SHELL_LEAK_RE.findall(out)))
        if leaks:
            raise PromptError(
                f"{self.path.name}: shell-style variables reached the rendered prompt: "
                f"{leaks}. The model is handed these literally and cannot act on them. If one "
                f"is meant as literal text, rewrite it; if it is a value, declare it.")
        if not out.strip():
            raise PromptError(f"{self.path.name}: rendered to nothing")
        return out


def load(name_or_path: str, root: Path = DEFAULT_DIR) -> Template:
    p = Path(name_or_path)
    if not p.is_file():
        p = root / name_or_path
        if not p.is_file() and not name_or_path.endswith(".md"):
            p = root / (name_or_path + ".md")
    if not p.is_file():
        raise PromptError(f"no such template: {name_or_path} (looked in {root})")
    return Template(p)


def _kv(pairs: list[str]) -> dict[str, str]:
    out = {}
    for p in pairs:
        if "=" not in p:
            raise PromptError(f"--var expects KEY=VALUE, got {p!r}")
        k, _, v = p.partition("=")
        out[k.strip()] = v
    return out


def cmd_render(a) -> int:
    t = load(a.template, Path(a.dir) if a.dir else DEFAULT_DIR)
    out = t.render(_kv(a.var))
    if a.out:
        Path(a.out).write_text(out, "utf-8")
        print(f"{t.name}: {len(out)} bytes -> {a.out}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


def cmd_declare(a) -> int:
    t = load(a.template, Path(a.dir) if a.dir else DEFAULT_DIR)
    print(json.dumps({"name": t.name, "requires": t.requires, "path": str(t.path),
                      "summary": t.meta.get("summary", "")}, indent=2))
    return 0


def cmd_lint(a) -> int:
    root = Path(a.dir) if a.dir else DEFAULT_DIR
    files = sorted(root.glob("*.md"))
    if not files:
        print(f"no templates in {root} -- an empty prompt directory is not a passing lint",
              file=sys.stderr)
        return 2
    bad = 0
    for f in files:
        try:
            t = Template(f)
            print(f"  ok   {f.name}: requires {t.requires or 'nothing'}")
        except PromptError as e:
            print(f"  FAIL {e}", file=sys.stderr)
            bad += 1
    print(f"{len(files)} template(s), {bad} bad")
    return 2 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--dir", help=f"template directory (default {DEFAULT_DIR})")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render"); r.add_argument("template")
    r.add_argument("--var", action="append", default=[], metavar="KEY=VALUE")
    r.add_argument("--out"); r.set_defaults(f=cmd_render)

    d = sub.add_parser("declare"); d.add_argument("template"); d.set_defaults(f=cmd_declare)

    l = sub.add_parser("lint"); l.set_defaults(f=cmd_lint)

    a = ap.parse_args()
    try:
        return a.f(a)
    except PromptError as e:
        print(f"prompt: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
