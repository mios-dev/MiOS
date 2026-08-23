# AI-hint: Puts the repository's agent-pipe on sys.path so a suite tests the tree it ships from, not whatever is installed on the host.
# AI-related: usr/lib/mios/agent-pipe/server.py, tools/ci-suites.py
"""Import this before importing `server`.

Nine suites each inserted the INSTALLED agent-pipe directory onto sys.path. A
CI runner has no such directory, so `import server` raised and every one of
those suites failed -- which is why none of them was ever wired into a
workflow. A developer machine that does have MiOS installed ran them against
the installed copy instead of the working tree, so the change under test was
not the code being tested.

Resolving from `__file__` fixes both: the repository copy comes first, and the
installed path stays as a fallback for a suite executed outside a checkout.
"""
import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1] / "usr" / "lib" / "mios" / "agent-pipe"
_INSTALLED = pathlib.Path("/usr/lib/mios/agent-pipe")

for _candidate in (_REPO, _INSTALLED):
    if _candidate.is_dir():
        _p = str(_candidate)
        if _p in sys.path:
            sys.path.remove(_p)
        sys.path.insert(0, _p)
        break
else:  # pragma: no cover -- neither a checkout nor an install
    raise ImportError(f"agent-pipe not found at {_REPO} or {_INSTALLED}")
