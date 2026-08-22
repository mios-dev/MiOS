#!/usr/bin/env python3
# AI-hint: Drift check 155 check_comment_ratchet -- asserts measured comment metrics do not exceed ceiling values.
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_check_comment_ratchet_py.md

import os
import sys

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "usr", "libexec", "mios"))
sys.path.insert(0, os.path.join(ROOT, "usr", "lib", "mios"))
import mios_comments as mc


def main() -> int:
    ssot_path = os.path.join(ROOT, "usr", "share", "mios", "mios.toml")
    with open(ssot_path, "rb") as fh:
        ssot = tomllib.load(fh)

    docs = ssot.get("docs", {}) or {}
    ai_tag = ssot.get("ai_tag", {}) or {}

    max_unmigrated = int(os.environ.get("MIOS_MAX_UNMIGRATED_NARRATIVE", docs.get("max_unmigrated_narrative", 999999)))
    max_stale = int(os.environ.get("MIOS_MAX_STALE_REFS", docs.get("max_stale_refs", 999999)))
    max_hints = int(os.environ.get("MIOS_MAX_OVERLONG_HINTS", ai_tag.get("max_overlong_hints", docs.get("max_overlong_hints", 999999))))
    max_undoc = int(os.environ.get("MIOS_MAX_UNDOCUMENTED_COMPONENTS", docs.get("max_undocumented_components", 999999)))

    policy = mc.Policy.from_toml(ssot)

    narrative = 0
    stale = 0
    hints = 0
    undoc = 0

    refindex = mc.RefIndex.build(ROOT)
    for b, v in mc.iter_source_files(ROOT):
        try:
            blocks = mc.lex(v)
        except Exception:
            continue
        for block in blocks:
            block = mc.Block(**{**block.__dict__, "path": b})
            verdict = mc.classify(block, policy, refindex)
            if verdict.cls == "DROP":
                continue
            if verdict.cls == "MIGRATE":
                narrative += 1
            elif verdict.cls == "MIGRATE_HEADER" or (block.in_header_block and len(block.text) > policy.hint_max_chars):
                hints += 1
            if verdict.stale:
                stale += 1

    violations = []
    if narrative > max_unmigrated:
        violations.append(f"unmigrated_narrative ({narrative}) exceeds ceiling [docs].max_unmigrated_narrative ({max_unmigrated})")
    if stale > max_stale:
        violations.append(f"stale_refs ({stale}) exceeds ceiling [docs].max_stale_refs ({max_stale})")
    if hints > max_hints:
        violations.append(f"overlong_hints ({hints}) exceeds ceiling [ai_tag].max_overlong_hints ({max_hints})")
    if undoc > max_undoc:
        violations.append(f"undocumented_components ({undoc}) exceeds ceiling [docs].max_undocumented_components ({max_undoc})")

    if violations:
        for v in violations:
            print(f"check_comment_ratchet: {v}", file=sys.stderr)
        return 1

    print(f"check_comment_ratchet OK: narrative={narrative}/{max_unmigrated}, stale={stale}/{max_stale}, hints={hints}/{max_hints}, undoc={undoc}/{max_undoc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
