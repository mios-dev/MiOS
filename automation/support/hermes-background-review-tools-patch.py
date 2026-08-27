#!/usr/bin/env python3
# AI-hint: Patch script that modifies agent/background_review.py to union the full global tool surface into the review whitelist, preventing tool-denial errors during post-turn self-improvement passes.
# AI-functions: main
from __future__ import annotations

import sys

MARKER = "MIOS-PATCH: background-review-global-tools"

ANCHOR = "            set_thread_tool_whitelist(\n"
INJECT = (
    "            # " + MARKER + " (all global tools for\n"
    "            # Hermes): union the parent agent's FULL tool surface into the\n"
    "            # review whitelist so the post-turn pass is denied NOTHING.\n"
    "            review_whitelist = set(review_whitelist) | set(\n"
    "                getattr(agent, \"valid_tool_names\", None) or ())\n"
)

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
