<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Pure config constants + SSOT mios.toml readers (extracted...

Pure config constants + SSOT mios.toml readers (extracted from server.py).

Moved verbatim from ``server.py`` (refactor R1); the module is pure (stdlib only
-- ``os`` / ``logging`` / lazily-imported ``tomllib``) and ``server.py`` re-imports
every name so its importable surface is unchanged. ``mios_config`` MUST NOT import
``server`` (the one-way boundary enforced by ``98-drift-checks.sh`` check 6).

<!-- mios-src:bad8df8dfd78 from usr/lib/mios/agent-pipe/mios_pipe/kernel/config.py:3-9 -->

### SAFETY-validate a posted mios.toml replacement. Args...

SAFETY-validate a posted mios.toml replacement.

    Args:
        toml_text: the raw replacement TOML text (already parse-checked by the
            caller, but re-parsed here so this helper is standalone/testable).
        live_config: the current live merged config dict (used ONLY to detect a
            DROPPED critical section). Omit / pass None to skip the drop check
            (degrade-open: if the live config can't be read we don't block).

    Returns:
        (ok: bool, errors: list[str]). ``ok`` is True with an empty ``errors``
        list when the config is safe to write.

<!-- mios-src:8cbd4a5336ce from usr/lib/mios/agent-pipe/mios_pipe/kernel/config.py:415-427 -->
