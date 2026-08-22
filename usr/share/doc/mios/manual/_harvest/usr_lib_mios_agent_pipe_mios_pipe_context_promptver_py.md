<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-LIFECYCLE-VER prompt-version registry (the PURE half). The ~12 agent-pipe hop prompts (router/refine/synthesis/polish/swarm/native-loop system templates) were UNVERSIONED -- no content-hash, no version, no rollback -- so there is no substrate for the self-improve ACT half (WS-11) to safely roll an auto-edited prompt forward/back. PromptRegistry.register(name, content) stamps a stable sha256 content-hash + a version that increments ONLY when the content changes; keeps a bounded history so rollback() restores the prior content as a new version; snapshot() (content-free) feeds /v1/prompts observability + drift detection. Pure stdlib + deterministic so it unit-tests in isolation; server.py registers the live hop-prompt constants at import + exposes the surface. Sibling of mios_registry/mios_capreg.
AI-related: ./server.py, ./mios_registry.py, ./mios_selfimprove.py, /usr/share/mios/mios.toml, ./test_mios_promptver.py
AI-functions: content_hash, register, current, history, rollback, snapshot, class PromptRegistry

<!-- mios-src:f84f5bfa4ac5 from usr/lib/mios/agent-pipe/mios_pipe/context/promptver.py:1-3 -->

