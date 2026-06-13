#!/usr/bin/env python3
# AI-hint: Patch script that modifies agent/background_review.py to union the full global tool surface into the review whitelist, preventing tool-denial errors during post-turn self-improvement passes.
# AI-functions: main
"""Idempotent patch: give Hermes' BACKGROUND REVIEW the full global tool
surface (operator 2026-06-04: "make sure MiOS-Hermes can use all global
tools!! ... and all Global MiOS tools for Hermes too").

Upstream `agent/background_review.py` runs the post-turn self-improvement
pass under a thread-local tool whitelist built from ONLY the ["memory",
"skills"] toolsets -- everything else is denied at runtime. That made the
review agent's `patch` call fail ("Background review denied non-whitelisted
tool: patch. Only memory/skill tools are allowed."), so when its skill_manage
edit missed it had no working file-edit fallback, looped on a malformed
recreate, and burned the tool-turn budget ("agent may appear stuck").

This patch UNIONS the parent agent's full tool surface (`agent.valid_tool_names`
-- the same global tools the main loop has, MiOS verbs included) into the
review whitelist, so the background pass is no longer denied any tool. It also
softens the now-false "other tools will be denied" instruction. Memory/skill
tools remain first-class via the existing prompt; this only REMOVES the cap.

Idempotent: re-runs are no-ops once the marker is present (survives image
rebuilds; re-applied by automation/38-hermes-agent.sh over each site-packages).
Run: python3 hermes-background-review-tools-patch.py <path/to/background_review.py>
"""
from __future__ import annotations

import sys

MARKER = "MIOS-PATCH: background-review-global-tools"

# Anchor: the whitelist-enforcement call. We inject a union line just before it.
ANCHOR = "            set_thread_tool_whitelist(\n"
INJECT = (
    "            # " + MARKER + " (operator 2026-06-04 \"all global tools for\n"
    "            # Hermes\"): union the parent agent's FULL tool surface into the\n"
    "            # review whitelist so the post-turn pass is denied NOTHING.\n"
    "            review_whitelist = set(review_whitelist) | set(\n"
    "                getattr(agent, \"valid_tool_names\", None) or ())\n"
)

# Best-effort: drop the now-false "other tools will be denied" instruction so
# the review agent knows it MAY reach for any tool (e.g. patch) when a skill
# update needs it. Skipped silently if the upstream wording drifts.
OLD_PROMPT = (
    "                        + \"\\n\\nYou can only call memory and skill \"\n"
    "                        \"management tools. Other tools will be denied \"\n"
    "                        \"at runtime — do not attempt them.\"\n"
)
NEW_PROMPT = (
    "                        + \"\\n\\nFocus on memory and skill updates, but \"\n"
    "                        \"you MAY use any other available tool (e.g. patch, \"\n"
    "                        \"file edits) when a skill/memory update needs it.\"\n"
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: hermes-background-review-tools-patch.py <background_review.py>")
        return 2
    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print(f"[bg-review-tools-patch] cannot read {path}: {e}")
        return 1

    if MARKER in src:
        print(f"[bg-review-tools-patch] already patched: {path}")
        return 0

    if ANCHOR not in src:
        print(f"[bg-review-tools-patch] anchor not found (upstream drift?) -- "
              f"SKIPPED, no change: {path}")
        return 0

    # Inject the whitelist union before the FIRST enforcement call only.
    src = src.replace(ANCHOR, INJECT + ANCHOR, 1)

    if OLD_PROMPT in src:
        src = src.replace(OLD_PROMPT, NEW_PROMPT, 1)
    else:
        print("[bg-review-tools-patch] note: prompt-restriction text not found "
              "(wording drift) -- left as-is; whitelist union still applied")

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
    except OSError as e:
        print(f"[bg-review-tools-patch] cannot write {path}: {e}")
        return 1

    print(f"[bg-review-tools-patch] patched (full global tool surface): {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
