<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_capreg -- unified, RBAC-filtered capability registry...

mios_capreg -- unified, RBAC-filtered capability registry projection (WS-2).

MiOS's capability surface is three-projected (verbs / MCP / A2A), and mios_manifest
projects the verb catalog -- but recipes (the [recipes.*] OS-command templates) and
their permission tiers were never unified into one RBAC-filtered manifest. This is
that projection: given the verb catalog + the recipe table + a caller's permission
CEILING, emit the single list of capabilities that caller may use, each tagged
kind (verb|recipe) + tier (+ platforms for recipes).

FAIL-CLOSED (security, mirrors mios_pdp.resolve_ceiling): a capability whose tier
is unknown is NEVER included, and an unknown ceiling admits NOTHING. Tiers are
ascending privilege (read < write < interactive); a capability is admitted iff
its tier-rank <= the ceiling's tier-rank AND the ceiling is itself a known tier.

server.py owns: reading the SSOT sections, resolving the caller's ceiling via
mios_pdp, choosing the host platform, and the generative-refusal (LLM) layer that
WS-2 also calls for. This module owns the deterministic, testable projection.

<!-- mios-src:5f9d3c8c60c1 from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/capreg.py:3-20 -->

### Project ONE RBAC-filtered capability manifest from the verb...

Project ONE RBAC-filtered capability manifest from the verb catalog +
    recipe table + skill set for a caller whose permission ceiling is `ceiling`.
    Each entry: {name, kind: "verb"|"recipe"|"skill", tier, description
    [, platforms][, uses]}.
    Verbs/recipes use `permission` (default "read"); a recipe is dropped when
    `platform` is given and it has no template for it. A SKILL's tier is the max
    over its component verbs (skill_effective_tier) and it is admitted only when
    BOTH that tier is allowed AND every component verb is itself admitted
    (reachability fail-closed -- a skill you cannot fully execute is not offered).
    Deterministic (sorted by kind then name); fail-closed via `allowed`.

<!-- mios-src:d1c8003f0eba from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/capreg.py:99-108 -->

### The structured capability DAG (WS-2): nodes...

The structured capability DAG (WS-2): nodes (verbs|recipes|skills) + edges
    (skill -> the verb/skill each step invokes). Recipes + verbs are leaves; only
    skills have out-edges. Returns {nodes, edges, cycles, dangling}: `cycles` are
    skill->skill reference cycles (a malformed skill set; the manifest fails such
    a skill closed via skill_effective_tier) and `dangling` are step targets that
    are neither a known verb nor a known skill. Pure + deterministic.

<!-- mios-src:fd397e9f3e92 from usr/lib/mios/agent-pipe/mios_pipe/lifecycle/capreg.py:204-209 -->
