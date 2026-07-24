# AI-hint: Shared environment helper for stripping empty MIOS_* environment variables.
# ============================================================================
# usr/lib/mios/mios_env.py
# ============================================================================

import os

def strip_empty_mios_env(env=None):
    """
    Remove empty MIOS_* environment variables so os.environ.get(KEY, DEFAULT)
    properly falls back to default values rather than trying to parse empty strings.
    """
    if env is None:
        env = os.environ
    for k in list(env.keys()):
        if k.startswith("MIOS_") and env[k] == "":
            env.pop(k, None)
    return env
