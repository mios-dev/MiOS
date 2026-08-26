#!/usr/bin/env python3
# AI-hint: Standalone unit test for mios_rerank sibling module.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_rerank."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from mios_rerank import CrossEncoderReranker

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def main():
    reranker = CrossEncoderReranker(top_k=2)
    candidates = [
        {"id": 1, "text": "Fedora bootc container operating system", "vector_score": 0.8},
        {"id": 2, "text": "Baking apple pies in the kitchen", "vector_score": 0.6},
        {"id": 3, "text": "Linux bootc immutable architecture", "vector_score": 0.75}
    ]
    ranked = reranker.rerank("bootc linux", candidates)
    check("top-k limit applied", len(ranked) == 2)
    check("top candidate is relevant", "bootc" in ranked[0]["text"])

    if _fails > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
