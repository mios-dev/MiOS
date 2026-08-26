#!/usr/bin/env python3
# AI-hint: Standalone unit test for mios_deliberate sibling module.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_deliberate."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from mios_deliberate import DeliberationConfig, DeliberationEngine

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def main():
    cfg = DeliberationConfig(max_iterations=3, convergence_threshold=0.05)
    check("config max iterations", cfg.max_iterations == 3)
    check("config threshold", cfg.convergence_threshold == 0.05)

    engine = DeliberationEngine(cfg)
    check("engine instantiated", engine is not None)

    if _fails > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
