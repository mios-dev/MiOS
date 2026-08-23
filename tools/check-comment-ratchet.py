#!/usr/bin/env python3
# AI-hint: Developer report for the comment metrics -- narrative, stale refs, over-cap hints, undocumented components. NOT a registered drift check: enforcement lives in check_docs_ratchet, which the gate actually runs.
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

    missing = []

    def ceiling(env_var, *lookups):
        """A ratchet ceiling, or a hard failure if the SSOT has stopped carrying it.

        Defaulting an absent ceiling to 999999 makes the check unfailable the
        moment a key is renamed, and it keeps reporting PASS while doing so --
        the worst outcome, because it also stops anyone looking. An absent
        ceiling is a broken gate, not an unlimited one.
        """
        env_val = os.environ.get(env_var)
        if env_val is not None:
            return int(env_val)
        for table, key in lookups:
            if key in table:
                return int(table[key])
        missing.append(f"{lookups[0][1]} (env {env_var})")
        return 0

    max_unmigrated = ceiling("MIOS_MAX_UNMIGRATED_NARRATIVE",
                             (docs, "max_unmigrated_narrative"))
    max_stale = ceiling("MIOS_MAX_STALE_REFS", (docs, "max_stale_refs"))
    max_hints = ceiling("MIOS_MAX_OVERLONG_HINTS",
                        (ai_tag, "max_overlong_hints"), (docs, "max_overlong_hints"))
    max_undoc = ceiling("MIOS_MAX_UNDOCUMENTED_COMPONENTS",
                        (docs, "max_undocumented_components"))

    if missing:
        for m in missing:
            print(f"[comment-ratchet] ERROR: no ceiling in SSOT for {m}", file=sys.stderr)
        return 1

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
