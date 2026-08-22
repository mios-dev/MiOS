<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A13 risk-tier dispatch-sandbox profile resolver. Pure-stdlib core that maps a verb's permission tier (read|write|interactive) to a SandboxProfile -- the confinement (mechanism + writable workspace + read-only/network posture) the dispatch chokepoint should run the verb under. read -> none (pure info), write -> a per-dispatch writable workspace with the rest read-only, interactive -> the strictest isolation (bwrap/podman, no net). FAIL-CLOSED (security-sensitive, NOT degrade-open): an unknown/missing tier resolves to the STRICTEST profile, never 'none'. mios-sandbox-exec owns the actual confinement (bwrap + the T-230 seccomp filter) and the workspace; this module owns the deterministic POLICY so it unit-tests in isolation. build_bwrap_argv is a reference shape, not the argv that runs -- see T-309.
AI-related: ./server.py, ./mios_pdp.py, /usr/share/mios/mios.toml, /var/lib/mios/ai/dispatch, ./test_mios_sandbox.py
AI-functions: resolve_profile, workspace_path, build_bwrap_argv, class SandboxProfile

<!-- mios-src:23ca3f2de679 from usr/lib/mios/agent-pipe/mios_pipe/access/sandbox.py:1-3 -->

