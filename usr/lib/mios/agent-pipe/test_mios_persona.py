#!/usr/bin/env python3
# AI-hint: Standalone unit test for mios_persona sibling module.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_persona."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from mios_persona import DomainCategory, PersonaSynthesizer

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

def main():
    synth = PersonaSynthesizer()
    cat, conf, _scores = synth.classifier.classify(
        "How do I configure eBPF cgroups and memory limits in linux?")
    check("kernel domain detected", cat == DomainCategory.KERNEL_SYSTEMS)

    prompt = synth.synthesize("Base prompt", cat, confidence=conf)
    check("system prompt enriched", "Base prompt" in prompt and "Linux Kernel" in prompt)

    if _fails > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
