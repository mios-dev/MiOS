#!/usr/bin/env python3
# AI-hint: Standalone unit test for mios_sample_tune sibling module.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_sample_tune."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from mios_sample_tune import SamplingScheduler

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def main():
    sched = SamplingScheduler()
    code_params = sched.estimate_hyperparameters("Write a python function to parse json")
    check("code temperature is 0.0", code_params["temperature"] == 0.0)
    check("code mode deterministic", code_params["mode"] == "deterministic")

    creative_params = sched.estimate_hyperparameters("Brainstorm creative ideas for a story")
    check("creative temperature is higher", creative_params["temperature"] > 0.5)

    if _fails > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
