#!/usr/bin/env python3
# AI-hint: Drift check 156 check_doc_ratchet_monotone -- asserts ceiling values in mios.toml are <= recorded floor values.
# AI-doc: usr/share/doc/mios/manual/tools.md

import os
import sys

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))


def read_floor(path: str) -> dict[str, int]:
    out: dict[str, int] = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 2 and parts[1].strip().lstrip("-").isdigit():
                out[parts[0].strip()] = int(parts[1])
    return out


def main() -> int:
    ssot_path = os.path.join(ROOT, "usr", "share", "mios", "mios.toml")
    with open(ssot_path, "rb") as fh:
        ssot = tomllib.load(fh)

    docs = ssot.get("docs", {}) or {}
    ai_tag = ssot.get("ai_tag", {}) or {}
    ceilings = {
        "max_unmigrated_narrative": int(docs.get("max_unmigrated_narrative", 0)),
        "max_stale_refs": int(docs.get("max_stale_refs", 0)),
        "max_overlong_hints": int(ai_tag.get("max_overlong_hints", docs.get("max_overlong_hints", 0))),
        "max_undocumented_components": int(docs.get("max_undocumented_components", 0)),
    }

    floor_path = os.path.join(ROOT, "usr", "share", "mios", "reference", "doc-ratchet-floor.tsv")
    floors = read_floor(floor_path)

    violations = []
    for key, curr in ceilings.items():
        if key in floors:
            recorded = floors[key]
            if curr > recorded:
                violations.append(
                    f"ceiling for '{key}' in mios.toml ({curr}) exceeds recorded monotone floor in doc-ratchet-floor.tsv ({recorded})"
                )

    if violations:
        for v in violations:
            print(f"check_doc_ratchet_monotone: {v}", file=sys.stderr)
        return 1

    print("check_doc_ratchet_monotone OK: all ceilings <= monotone floor baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
