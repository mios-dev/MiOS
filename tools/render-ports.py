#!/usr/bin/env python3
# AI-hint: Renders the flat [ports] projection from the [ports.categories] numbering SSOT -- every port is derived as base + index*stride, so an operator reta...
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_render_ports_py.md
"""render-ports.py -- project [ports.categories] onto the flat [ports] table.

The categories table is the numbering SSOT: each category owns a `base`, a
`stride` and an ORDERED `members` list, and a member's port is

    base + index_in_members * stride

`pinned` entries (DNS/53) are protocol contracts and are emitted verbatim.

Usage:
    tools/render-ports.py            # rewrite the flat [ports] table in place
    tools/render-ports.py --check    # exit 1 if the flat table has drifted
    tools/render-ports.py --print    # print the derived name=port map
"""
from __future__ import annotations

import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # py<3.11
    import tomli as tomllib  # type: ignore

ROOT = os.environ.get("MIOS_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
TOML = os.environ.get("MIOS_TOML") or os.path.join(ROOT, "usr/share/mios/mios.toml")


def _categories(data: dict) -> dict:
    return (data.get("ports") or {}).get("categories") or {}


def derive_ports(data: dict) -> dict:
    """Return {port_name: value} derived from [ports.categories].

    Pinned ports are emitted at their literal value; derived ports are
    base + index*stride. stack_id is applied later by the resolver's
    process_val(), not here, so this stays the pre-offset SSOT.
    """
    out: dict[str, int] = {}
    for cat, cfg in sorted(_categories(data).items()):
        if not isinstance(cfg, dict):
            continue
        base = int(cfg.get("base", 0))
        stride = int(cfg.get("stride", 1))
        for idx, member in enumerate(cfg.get("members") or []):
            # An empty member is a RESERVED slot: it burns its index so a
            # retired service cannot renumber every service after it.
            if not member:
                continue
            out[member] = base + idx * stride
        for name, value in (cfg.get("pinned") or {}).items():
            out[name] = int(value)
    return out


def category_band(cfg: dict) -> tuple[int, int]:
    """Inclusive [lo, hi] the category's DERIVED members occupy."""
    base = int(cfg.get("base", 0))
    stride = int(cfg.get("stride", 1))
    n = len(cfg.get("members") or [])
    if n == 0:
        return (base, base)
    return (base, base + (n - 1) * stride)


def find_violations(data: dict) -> list[str]:
    """Schema integrity: single membership, no collisions, no band overlap,
    and flat-table agreement."""
    problems: list[str] = []
    cats = _categories(data)
    flat = {k: v for k, v in (data.get("ports") or {}).items()
            if isinstance(v, int) and k != "stack_id"}

    # 1. every port declared in exactly one category
    seen: dict[str, str] = {}
    for cat, cfg in sorted(cats.items()):
        if not isinstance(cfg, dict):
            continue
        names = list(cfg.get("members") or []) + list((cfg.get("pinned") or {}).keys())
        for name in names:
            if not name:      # reserved slot -- holds an index, names no port
                continue
            if name in seen:
                problems.append(
                    f"port '{name}' is claimed by both [ports.categories.{seen[name]}] "
                    f"and [ports.categories.{cat}]")
            seen[name] = cat

    for name in sorted(flat):
        if name not in seen:
            problems.append(
                f"port '{name}' is in the flat [ports] table but belongs to no category")
    for name in sorted(seen):
        if name not in flat:
            problems.append(
                f"port '{name}' is declared in [ports.categories.{seen[name]}] "
                f"but missing from the flat [ports] table")

    # 2. no two ports share a value
    derived = derive_ports(data)
    by_value: dict[int, list[str]] = {}
    for name, value in sorted(derived.items()):
        by_value.setdefault(value, []).append(name)
    for value, names in sorted(by_value.items()):
        if len(names) > 1:
            problems.append(f"port collision at {value}: {', '.join(names)}")

    # 3. category bands must not overlap
    bands = []
    for cat, cfg in sorted(cats.items()):
        if isinstance(cfg, dict) and (cfg.get("members") or []):
            lo, hi = category_band(cfg)
            bands.append((lo, hi, cat))
    bands.sort()
    for (lo1, hi1, c1), (lo2, hi2, c2) in zip(bands, bands[1:]):
        if lo2 <= hi1:
            problems.append(
                f"category band overlap: {c1} [{lo1}-{hi1}] overlaps {c2} [{lo2}-{hi2}]")

    # 4. the rendered projection must equal the flat table
    for name in sorted(set(derived) & set(flat)):
        if derived[name] != flat[name]:
            problems.append(
                f"[ports].{name} = {flat[name]} but [ports.categories.{seen[name]}] "
                f"derives {derived[name]} -- run tools/render-ports.py")

    return problems


_PORT_LINE = re.compile(r"^(\s*)([a-z0-9_]+)(\s*)=(\s*)(\d+)(\s*)(#.*)?$")


def render_table(text: str, derived: dict) -> str:
    """Rewrite the scalar values inside the flat [ports] table, preserving
    key order, alignment and trailing comments."""
    lines = text.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "[ports]":
            start = i
            break
    if start is None:
        raise SystemExit("render-ports: no [ports] table found")

    for i in range(start + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("["):
            break
        m = _PORT_LINE.match(lines[i].rstrip("\r"))
        if not m:
            continue
        indent, key, sp1, sp2, old, sp3, comment = m.groups()
        if key == "stack_id" or key not in derived:
            continue
        new = str(derived[key])
        # keep the '=' column stable: absorb the width delta into the gap
        pad = sp2 + " " * max(0, len(old) - len(new))
        if len(new) > len(old):
            pad = sp2[: max(1, len(sp2) - (len(new) - len(old)))]
        rebuilt = f"{indent}{key}{sp1}={pad}{new}"
        if comment:
            rebuilt += f"{sp3}{comment}"
        lines[i] = rebuilt + ("\r" if lines[i].endswith("\r") else "")
    return "\n".join(lines)


_FALLBACK_RE = re.compile(r"\$\{MIOS_PORT_([A-Z0-9_]+):-(\d+)\}")

# Consumers use the canonical alias remap for guacamole.
_ALIAS = {"GUACAMOLE": "GUACAMOLE_WEB"}

_SWEEP_PATHS = ("automation", "usr", "etc", "tools")
# A test fixture that deliberately carries a STALE literal is the only way to
# prove this sweeper works -- rewriting it turns the proof green over nothing.
_SWEEP_SKIP = ("manifest.json", ".tsv", "/reference/", "/knowledge/",
               "/target/", "/.git/", "node_modules",
               "/tools/test_", "/tests/")


def _sweep_files(root: str):
    for top in _SWEEP_PATHS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(root, top)):
            dirnames[:] = [d for d in dirnames
                           if d not in (".git", "target", "node_modules", "__pycache__")]
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                rel = path.replace("\\", "/")
                if any(s in rel for s in _SWEEP_SKIP):
                    continue
                yield path


def sync_fallbacks(root: str, derived: dict, apply: bool) -> list:
    """`${MIOS_PORT_X:-1234}` literals are degrade-open defaults, but a
    hand-typed one silently goes stale the moment a category base moves. Treat
    them as GENERATED: rewrite every one to its SSOT value."""
    upper = {k.upper(): v for k, v in derived.items()}
    problems = []
    for path in _sweep_files(root):
        try:
            with open(path, "r", encoding="utf-8", newline="") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        if "MIOS_PORT_" not in text:
            continue

        changed = []

        def _repl(m):
            key, lit = m.group(1), m.group(2)
            name = _ALIAS.get(key, key)
            want = upper.get(name)
            if want is None or str(want) == lit:
                return m.group(0)
            changed.append((key, lit, want))
            return "${MIOS_PORT_%s:-%d}" % (key, want)

        new_text = _FALLBACK_RE.sub(_repl, text)
        if changed:
            rel = os.path.relpath(path, root).replace("\\", "/")
            for key, lit, want in changed:
                problems.append(f"{rel}: MIOS_PORT_{key} fallback :-{lit} != SSOT {want}")
            if apply:
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(new_text)
    return problems


def main() -> int:
    check = "--check" in sys.argv
    show = "--print" in sys.argv

    with open(TOML, "rb") as fh:
        data = tomllib.load(fh)

    derived = derive_ports(data)
    if show:
        for name, value in sorted(derived.items(), key=lambda kv: (kv[1], kv[0])):
            print(f"{value:>6}  {name}")
        return 0

    problems = find_violations(data)
    # In apply mode these are REPAIRED in place, so they are progress output,
    # not blockers -- only --check treats them as drift.
    fallback_problems = sync_fallbacks(ROOT, derived, apply=not check)
    if check:
        problems += fallback_problems
    elif fallback_problems:
        print(f"[render-ports] re-synced {len(fallback_problems)} stale "
              f"${{MIOS_PORT_*:-N}} fallback(s) from SSOT")

    if check:
        if problems:
            sys.stderr.write("[render-ports] port schema drift:\n")
            for p in problems:
                sys.stderr.write(f"    {p}\n")
            return 1
        print(f"[render-ports] {len(derived)} ports derive cleanly from "
              f"{len(_categories(data))} categories")
        return 0

    # membership/collision problems are NOT fixable by re-rendering
    fatal = [p for p in problems if "run tools/render-ports.py" not in p]
    if fatal:
        sys.stderr.write("[render-ports] cannot render, fix the schema first:\n")
        for p in fatal:
            sys.stderr.write(f"    {p}\n")
        return 1

    with open(TOML, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    with open(TOML, "w", encoding="utf-8", newline="") as fh:
        fh.write(render_table(text, derived))
    print(f"[render-ports] rendered {len(derived)} ports into the flat [ports] table")
    return 0


if __name__ == "__main__":
    sys.exit(main())
