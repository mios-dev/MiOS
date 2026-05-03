#!/usr/bin/env python3
# ascii-sweep.py -- one-shot typographic + emoji scrubber for MiOS-owned text.
#
# Substitutions are pure presentation-layer (no shell or markdown semantics
# change), so this is safe to run across docs, shell scripts, PowerShell,
# TOML, JSON, YAML, and Containerfiles.
#
# Run from repo root:
#   python3 tools/ascii-sweep.py [--apply] [--paths PATH ...]
# Default is dry-run: prints per-file change counts without writing.

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# Pure typographic Unicode -> ASCII. Pure-substitution: every entry is the
# same byte-count semantic mapping that Markdown/shell/TOML/JSON renderers
# treat identically once normalized.
TYPOGRAPHIC = {
    "—": "--",   # em-dash
    "–": "-",    # en-dash
    "−": "-",    # minus sign
    "‘": "'",    # left single quote
    "’": "'",    # right single quote
    "‚": "'",    # single low-9 quote
    "‛": "'",    # single high-reversed-9 quote
    "“": '"',    # left double quote
    "”": '"',    # right double quote
    "„": '"',    # double low-9 quote
    "‟": '"',    # double high-reversed-9 quote
    " ": " ",    # NBSP
    " ": " ",    # narrow NBSP
    "​": "",     # zero-width space
    "‌": "",     # zero-width non-joiner
    "‍": "",     # zero-width joiner
    "﻿": "",     # BOM (when mid-file)
    "…": "...",  # ellipsis
    "·": "*",    # middle dot
    "•": "*",    # bullet
    "‣": "*",    # triangular bullet
    "⁃": "-",    # hyphen bullet
    "«": '"',    # left guillemet
    "»": '"',    # right guillemet
}

# Status-indicator emoji -> ASCII tags so logs stay scannable.
STATUS_EMOJI = {
    "✅": "[ok]",      # green check
    "✓": "[ok]",      # check
    "✔": "[ok]",      # heavy check
    "✗": "[x]",       # ballot x
    "✘": "[x]",       # heavy ballot x
    "⚠": "[!]",       # warning sign
    "⚠️": "[!]",  # warning sign + variation selector
    "ℹ": "[i]",       # info source
    "ℹ️": "[i]",
    "⛔": "[!]",       # no entry
    "✨": "",          # sparkles
    "✳": "*",         # eight-spoked asterisk
    "✴": "*",         # eight-pointed star
    "❕": "[!]",       # white exclamation
    "❗": "[!]",       # heavy exclamation
}

# Decorative emoji ranges -- strip outright (not semantically load-bearing).
DECORATIVE_RE = re.compile(
    "[\U0001F300-\U0001FAFF"   # symbols & pictographs, transport, supplemental
    "\U0001F600-\U0001F64F"    # emoticons
    "\U0001F680-\U0001F6FF"    # transport
    "\U0001F900-\U0001F9FF"    # supplemental symbols
    "☀-➿"             # misc symbols + dingbats
    "⬀-⯿"             # arrows / shapes
    "️"                     # variation selectors stragglers
    "]"
)

# Files to scan: tracked-only via `git ls-files`. Binary detection: read
# first 8 KiB and bail on NUL.
TEXT_EXTS = {
    ".md", ".txt", ".sh", ".bash", ".zsh", ".ps1", ".psd1",
    ".toml", ".yaml", ".yml", ".json", ".jsonl",
    ".conf", ".cfg", ".ini", ".rules", ".preset", ".target",
    ".service", ".socket", ".timer", ".mount", ".path",
    ".container", ".image", ".network", ".volume",
    ".te", ".fc", ".if",   # SELinux
    ".kbd", ".env",
}
TEXT_BASENAMES = {"Containerfile", "Justfile", "Dockerfile", "Makefile",
                   "LICENSE", "VERSION"}

# Skip auto-generated AI training data and embeddings -- these are derived
# from KB source files; sanitizing them in place would diverge them from
# the regenerator output. Re-run the KB build to refresh them after the
# sweep instead.
SKIP_PATTERNS = (
    "var/lib/mios/embeddings/",
    "var/lib/mios/training/",
    "var\\lib\\mios\\embeddings\\",  # Windows path form from git ls-files
    "var\\lib\\mios\\training\\",
)


def is_text_file(path: Path) -> bool:
    if path.name in TEXT_BASENAMES:
        return True
    if path.suffix.lower() in TEXT_EXTS:
        return True
    return False


def list_tracked_files() -> list[Path]:
    out = subprocess.check_output(
        ["git", "ls-files", "-z"], text=False
    ).split(b"\x00")
    files: list[Path] = []
    for raw in out:
        if not raw:
            continue
        rel = raw.decode("utf-8", errors="replace")
        p = Path(rel)
        if not p.exists():
            continue
        if any(rel.startswith(s) for s in SKIP_PATTERNS):
            continue
        if not is_text_file(p):
            continue
        files.append(p)
    return files


def sweep_text(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}

    def bump(key: str, n: int = 1) -> None:
        counts[key] = counts.get(key, 0) + n

    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        pair = ch + nxt
        if pair in STATUS_EMOJI:
            repl = STATUS_EMOJI[pair]
            out.append(repl)
            bump("status_emoji_pair")
            i += 2
            continue
        if ch in STATUS_EMOJI:
            out.append(STATUS_EMOJI[ch])
            bump("status_emoji")
            i += 1
            continue
        if ch in TYPOGRAPHIC:
            out.append(TYPOGRAPHIC[ch])
            bump("typographic")
            i += 1
            continue
        out.append(ch)
        i += 1
    text = "".join(out)

    def repl_decorative(m: re.Match[str]) -> str:
        bump("decorative_emoji")
        return ""

    text = DECORATIVE_RE.sub(repl_decorative, text)
    return text, counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write changes to disk (default: dry-run)")
    ap.add_argument("--paths", nargs="*", default=None,
                    help="restrict to these tracked paths")
    args = ap.parse_args()

    if args.paths:
        paths = [Path(p) for p in args.paths if Path(p).exists()
                 and is_text_file(Path(p))]
    else:
        paths = list_tracked_files()

    grand: dict[str, int] = {}
    touched = 0
    for p in paths:
        try:
            raw = p.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw[:8192]:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        new, counts = sweep_text(text)
        if not counts:
            continue
        touched += 1
        for k, v in counts.items():
            grand[k] = grand.get(k, 0) + v
        delta = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        sys.stdout.write(f"{p}: {delta}\n")
        if args.apply and new != text:
            p.write_text(new, encoding="utf-8", newline="")
    sys.stdout.write(
        f"\n[{'apply' if args.apply else 'dry-run'}] touched {touched} files; "
        + ", ".join(f"{k}={v}" for k, v in sorted(grand.items()))
        + "\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
