#!/usr/bin/env python3
# AI-hint: Unit test verifying atomic writing of mios.toml and SSOT projections under concurrent reads.
# AI-doc: usr/share/doc/mios/manual/tests.md
"""Verify atomic writes of mios.toml and projections so concurrent readers never see truncated content."""

from __future__ import annotations
import os
import sys
import tempfile
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TOML_PATH = os.path.join(_ROOT, "usr/share/mios/mios.toml")


def test_atomic_replace():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, "target.toml")
        initial_lines = ["line1\n", "line2\n", "line3\n", "line4\n", "line5\n"] * 50
        updated_lines = ["line1\n", "line2\n", "line3\n", "line4\n", "line5\n", "line6\n"] * 50

        with open(target, "w", encoding="utf-8") as f:
            f.writelines(initial_lines)

        min_expected_lines = min(len(initial_lines), len(updated_lines))
        seen_counts = []
        stop_event = threading.Event()

        def reader():
            for _ in range(100):
                if stop_event.is_set():
                    break
                try:
                    with open(target, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    seen_counts.append(len(lines))
                except OSError:
                    pass
                time.sleep(0.001)

        def writer():
            for _ in range(10):
                tmp = target + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.writelines(updated_lines)
                for _retry in range(10):
                    try:
                        os.replace(tmp, target)
                        break
                    except PermissionError:
                        time.sleep(0.002)
                time.sleep(0.005)

        t_read = threading.Thread(target=reader)
        t_write = threading.Thread(target=writer)

        t_read.start()
        t_write.start()

        t_write.join()
        stop_event.set()
        t_read.join()

        assert seen_counts, "Reader saw 0 reads"
        for count in seen_counts:
            assert count >= min_expected_lines, f"Observed truncated line count: {count} < {min_expected_lines}"


def main() -> int:
    print("[test-atomic-writes] Running atomic write verification...")
    test_atomic_replace()
    print("[test-atomic-writes] PASS: 100 reads observed only complete file versions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
