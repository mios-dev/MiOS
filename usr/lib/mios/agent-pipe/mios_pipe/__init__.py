# AI-hint: root of mios_pipe package. Sanitizes empty MIOS_* env vars on import so
# the SSOT resolver's var-closure emissions never break int()/float() config reads.

# The SSOT resolver (tools/lib/userenv.sh) emits EVERY referenced MIOS_* var so shell
# consumers stay `set -u`-safe and var-closure (Law 9) holds -- including vars with NO
# value, which it exports as an EMPTY string (`export VAR="${VAR:-}"`, userenv.sh:598).
# Python's os.environ.get(KEY, DEFAULT) only applies DEFAULT when KEY is ABSENT, so an
# empty MIOS_* silently overrides the default; int()/float() coercions then raise
# ValueError at IMPORT time (`float('')`), which crashes the agent plane on boot AND
# every unit test that imports the kernel. An empty MIOS_* is semantically UNSET (the
# resolver itself treats empty as "no value" -- userenv.sh:145 / mios_toml.py:52), so
# remove empties here, before any module reads the environment. This runs whenever any
# mios_pipe submodule is first imported -- ahead of mios_pipe.kernel.config and, via
# server.py's `from mios_config import ...` (line 188, before its first read), ahead of
# server.py too. Env vars a test sets AFTER import are untouched (this runs once).
def _strip_empty_mios_env() -> None:
    import os
    for _k in [k for k in list(os.environ) if k.startswith("MIOS_") and os.environ.get(k) == ""]:
        os.environ.pop(_k, None)


_strip_empty_mios_env()
