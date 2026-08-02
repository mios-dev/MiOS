# AI-hint: root of mios_pipe package. Sanitizes empty MIOS_* env vars on import so

def _strip_empty_mios_env() -> None:
    try:
        import sys, os
        usr_lib = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        if usr_lib not in sys.path:
            sys.path.insert(0, usr_lib)
        from mios_env import strip_empty_mios_env
        strip_empty_mios_env(os.environ)
    except ImportError:
        import os
        for _k in [k for k in list(os.environ) if k.startswith("MIOS_") and os.environ.get(k) == ""]:
            os.environ.pop(_k, None)


_strip_empty_mios_env()
