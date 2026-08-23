# AI-hint: Makes a suite import the agent pipe from the repository it ships in rather than whatever is installed on the host.
# AI-related: usr/lib/mios/agent-pipe/server.py
"""Import this before importing `server`.

Nine suites each pointed the import search at the INSTALLED directory. A CI
runner has no such directory, so importing the server raised and every one of
those suites failed -- which is why none was ever wired into a workflow. A
developer machine that does have MiOS installed ran them against the installed
copy instead of the working tree, so the change under test was not the code
being tested.

Resolving from this file's own location fixes both: the repository copy comes
first, and the installed directory stays as a fallback for a suite executed
outside a checkout.
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
