#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_router Stage-2 parity (AGY-127). Pure stdlib, no server.py/DB/pytest. Loads tests/router_corpus.json and verifies Router.route(plan).mode matches expected_mode and cascade_mode for every row.
# AI-related: ./mios_router.py, ./tests/router_corpus.json
# AI-functions: check, cascade_mode, main

import json
import os
import sys

from mios_pipe.routing import router as r

_fails = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def cascade_mode(refined: dict) -> str:
    """Inline intent cascade mirror from server.py / chat_completions."""
    if not isinstance(refined, dict):
        return "agent"
    intent = str(refined.get("intent") or "").strip().lower()
    if intent in ("chat", "dispatch", "multi_task", "dag", "agent"):
        return intent
    return "agent"


def main() -> int:
    global _fails
    base_dir = os.path.dirname(os.path.abspath(__file__))
    corpus_path = os.path.join(base_dir, "tests", "router_corpus.json")
    if not os.path.isfile(corpus_path):
        corpus_path = os.path.join(base_dir, "router_corpus.json")

    check("corpus file exists", os.path.isfile(corpus_path), corpus_path)
    if not os.path.isfile(corpus_path):
        return 1

    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    check("corpus is non-empty list", isinstance(corpus, list) and len(corpus) > 0, f"count={len(corpus)}")

    for idx, row in enumerate(corpus):
        desc = row.get("description", f"row {idx}")
        inp = row.get("input", {})
        expected = row.get("expected_mode")

        decision = r.route(inp)
        casc = cascade_mode(inp)

        check(f"router_parity[{idx}]: {desc} (route mode == expected)", decision.mode == expected, f"got={decision.mode!r}, expected={expected!r}")
        check(f"router_parity[{idx}]: {desc} (route mode == cascade)", decision.mode == casc, f"route={decision.mode!r}, cascade={casc!r}")

    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
