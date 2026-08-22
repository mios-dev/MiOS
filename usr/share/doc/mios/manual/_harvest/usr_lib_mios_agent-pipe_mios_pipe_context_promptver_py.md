<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_promptver -- versioned registry for the agent-pipe hop...

mios_promptver -- versioned registry for the agent-pipe hop prompts (WS-LIFECYCLE-VER).

The completeness critic flagged it: MiOS versions skill/recipe PACKAGES (WS-A17)
but the LIVE refine/synthesis/polish/swarm/council/native-loop system prompts
carry no version stamp, no A/B, no rollback. That is the missing PREREQUISITE for
the self-improve ACT half (WS-11): you cannot safely auto-edit a prompt without a
way to identify the live version + roll it back.

This module is the PURE substrate:
  * content_hash() -- stable sha256[:12] of a prompt's text.
  * PromptRegistry.register(name, content) -- stamp a version that bumps ONLY on
    a content change (idempotent for an unchanged prompt); bounded history.
  * rollback(name) -- restore the previous content as a NEW (forward) version.
  * snapshot() -- content-free {name -> version/hash/len/history} for /v1/prompts.

server.py registers the live prompt constants at import + exposes the surface;
this owns the deterministic versioning logic.

<!-- mios-src:784582ea411c from usr/lib/mios/agent-pipe/mios_pipe/context/promptver.py:3-20 -->
