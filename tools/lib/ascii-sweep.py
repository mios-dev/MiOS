#!/usr/bin/env python3
# tools/lib/ascii-sweep.py — replace common smart-punctuation Unicode with the
# ASCII equivalent. Idempotent. Operates on file paths given on argv.
# Touches comments AND values — the goal is to make every byte ASCII so
# byte-naive parsers (WSL2 wsl.conf, naive INI, etc.) can't mis-track lines.

import sys
from pathlib import Path

SUBS = {
    "—": "--",   # em dash
    "–": "-",    # en dash
    "‘": "'",    # left single quote
    "’": "'",    # right single quote / smart apostrophe
    "“": '"',    # left double quote
    "”": '"',    # right double quote
    "…": "...",  # horizontal ellipsis
    " ": " ",    # no-break space
    "‐": "-",    # hyphen
    "−": "-",    # minus sign
    "«": '"',    # left guillemet
    "»": '"',    # right guillemet
    "‚": ",",    # single low-9 quotation mark
    "„": '"',    # double low-9 quotation mark
    "′": "'",    # prime
    "″": '"',    # double prime
    "‹": "<",    # single left angle quote
    "›": ">",    # single right angle quote
    "─": "-",    # box drawings light horizontal
    "━": "-",    # box drawings heavy horizontal
    "═": "=",    # box drawings double horizontal
    "│": "|",    # box drawings light vertical
    "┃": "|",    # box drawings heavy vertical
    "║": "|",    # box drawings double vertical
    "┌": "+", "┐": "+", "└": "+", "┘": "+",  # light corners
    "┏": "+", "┓": "+", "┗": "+", "┛": "+",  # heavy corners
    "╔": "+", "╗": "+", "╚": "+", "╝": "+",  # double corners
    "├": "+", "┤": "+", "┬": "+", "┴": "+", "┼": "+",  # light tees
    "▶": ">", "◀": "<", "▲": "^", "▼": "v",  # filled arrows
    "→": "->", "←": "<-", "↑": "^", "↓": "v",  # arrows
    "✓": "+", "✗": "x", "✔": "+", "✘": "x",  # check/cross
    "•": "*", "·": ".", "▪": "*", "▫": "*",  # bullets
    "⚠": "!", "⚡": "!", "ℹ": "i",  # symbols
    "§": "S",  # section sign (legal-doc references)
    "©": "(c)", "®": "(R)", "™": "(TM)",  # trademark/copyright
    "°": " deg",  # degree sign
    "±": "+/-", "×": "x", "÷": "/",  # math operators
    "€": "EUR", "£": "GBP", "¥": "JPY", "¢": "c",  # currency
    "﻿": "",     # BOM (drop)
    "​": "",     # zero-width space (drop)
    "‎": "",     # left-to-right mark (drop)
    "‏": "",     # right-to-left mark (drop)
}

def process(path: Path) -> bool:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        # Not valid UTF-8; leave alone (could be binary)
        return False
    new = text
    for old, repl in SUBS.items():
        new = new.replace(old, repl)
    # Final sanity: now must be pure ASCII
    if any(ord(c) > 127 for c in new):
        # File has non-ASCII chars we don't know how to map — flag and skip
        bad = sorted({c for c in new if ord(c) > 127})
        sys.stderr.write(f"WARN {path}: unmapped non-ASCII: {[hex(ord(c)) for c in bad]}\n")
        return False
    if new == text:
        return False
    path.write_bytes(new.encode("ascii"))
    return True

if __name__ == "__main__":
    changed = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.is_file():
            continue
        if process(p):
            print(f"changed: {arg}")
            changed += 1
    print(f"\n{changed} file(s) changed", file=sys.stderr)
