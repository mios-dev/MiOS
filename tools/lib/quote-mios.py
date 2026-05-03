#!/usr/bin/env python3
# tools/lib/quote-mios.py -- wrap the proper-noun spelling of the project
# name in single quotes for legal-attribution reasons. Lowercase variant
# (used in code, file names, env vars, paths, package names) is left alone.
#
# Match conditions:
#   * The 4-character proper-noun spelling, case-sensitive
#   * NOT preceded by "'"            (already quoted)
#   * NOT followed by "-", ".", "/", word char, or "'"
#       -> skips hyphenated names, .git URLs, /path/, IDENT_FOO, already-quoted
#
# Idempotent. Operates on the file paths given on argv.
#
# Important: the literal we match is built by string concatenation so this
# file does NOT contain its own match target -- otherwise running this
# script on its own source would mangle the regex.

import re, sys
from pathlib import Path

# Build the literal as 'M' + 'iOS' so the source code of this file never
# contains the raw 4-char form the regex looks for. Without this trick, the
# regex literal in this file would match itself on the first run and become
# a non-matching no-op for any future run.
_LIT = "M" + "iOS"
# Lookbehind / lookahead exclusions:
#   ['\w"/\\]       before -- single-quote (already wrapped), word char
#                              (identifier mid-token), double-quote (bare
#                              string literal: "MiOS" is a name/identifier,
#                              quoting it changes the value), forward slash
#                              (URL path component: /MiOS), backslash
#                              (Windows path: \MiOS)
#   [-./\\\w'"]     after  -- hyphen (MiOS-DEV), dot (MiOS.git), slash
#                              (URL paths), backslash (\MiOS\foo Windows
#                              path), word char, single-quote (already
#                              wrapped), double-quote (bare string)
PATTERN = re.compile(rf"(?<!['\w\"/\\]){_LIT}(?![-./\\\w'\"])")
REPLACE = f"'{_LIT}'"

# File extensions / names we'll happily touch. Anything else is skipped.
ALLOW_EXT = {
    ".md", ".sh", ".ps1", ".py", ".toml", ".conf", ".service",
    ".target", ".container", ".preset", ".txt", ".rules", ".cfg",
}
ALLOW_NAMES = {"Containerfile", "Justfile"}

def is_allowed(path: Path) -> bool:
    if path.name in ALLOW_NAMES:
        return True
    if path.suffix in ALLOW_EXT:
        return True
    return False

def process(path: Path) -> int:
    """Return number of replacements made."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, IsADirectoryError, PermissionError):
        return 0
    new, n = PATTERN.subn(REPLACE, text)
    if n:
        path.write_text(new, encoding="utf-8")
    return n

if __name__ == "__main__":
    total_files = 0
    total_subs = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.is_file():
            continue
        if not is_allowed(p):
            continue
        n = process(p)
        if n:
            print(f"{n:4d}  {arg}")
            total_files += 1
            total_subs += n
    print(f"\n{total_subs} replacements across {total_files} files", file=sys.stderr)
