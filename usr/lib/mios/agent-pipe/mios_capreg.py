# AI-hint: WS-2 unified capability registry projection -- the PURE half: merge the [verbs.*] catalog and the [recipes.*] OS-command templates into ONE RBAC-filtered, platform-aware capability manifest (each capability tagged kind=verb|recipe + its permission tier; included only if the caller's ceiling permits it). FAIL-CLOSED on unknown tier/ceiling (a security control, mirrors mios_pdp). Deterministic, stdlib-only so it unit-tests in isolation; server.py owns wiring this to the live surface + the generative-refusal (LLM) half. Complements mios_manifest (verb-only projection) + mios_registry (packages).
# AI-related: ./mios_manifest.py, ./mios_pdp.py, ./mios_registry.py, /usr/share/mios/mios.toml, ./server.py, ./test_mios_capreg.py
# AI-functions: tier_rank, allowed, recipe_platforms, build_capability_manifest, manifest_summary, load_recipes_from_toml, project_from_toml, diff_capabilities
"""mios_capreg -- unified, RBAC-filtered capability registry projection (WS-2).

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
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

_DEFAULT_TIERS = ("read", "write", "interactive")   # ascending privilege


def tier_rank(tier: str, tiers: "Sequence[str]" = _DEFAULT_TIERS) -> int:
    """Privilege rank of a tier (lower = safer). An unknown/blank tier ranks
    BEYOND the highest known tier (fail-closed -> never admitted under any
    real ceiling)."""
    t = str(tier or "").strip().lower()
    norm = [str(x).strip().lower() for x in tiers]
    return norm.index(t) if t in norm else len(norm)


def allowed(cap_tier: str, ceiling: str, tiers: "Sequence[str]" = _DEFAULT_TIERS) -> bool:
    """True iff a capability of `cap_tier` is permitted under `ceiling`. Fail-closed:
    an unknown cap tier (rank == len) exceeds every real ceiling; an unknown
    ceiling (rank == len) admits nothing."""
    n = len([str(x).strip().lower() for x in tiers])
    cr = tier_rank(ceiling, tiers)
    if cr >= n:                      # unknown/blank ceiling -> admit nothing
        return False
    return tier_rank(cap_tier, tiers) <= cr


def recipe_platforms(spec: dict) -> "List[str]":
    """Which platforms a recipe supports (it has a non-empty command template)."""
    return sorted(p for p in ("linux", "windows") if (spec or {}).get(p))


def build_capability_manifest(verbs: "Optional[Dict[str, dict]]",
                              recipes: "Optional[Dict[str, dict]]", *,
                              ceiling: str,
                              tiers: "Sequence[str]" = _DEFAULT_TIERS,
                              platform: "Optional[str]" = None) -> "List[dict]":
    """Project ONE RBAC-filtered capability manifest from the verb catalog +
    recipe table for a caller whose permission ceiling is `ceiling`. Each entry:
      {name, kind: "verb"|"recipe", tier, description[, platforms]}.
    Verbs use their `tier` (default "read"); recipes use `permission` (default
    "read") and are additionally dropped when `platform` is given and the recipe
    has no command template for it. Deterministic (sorted by kind then name);
    fail-closed via `allowed`."""
    out: "List[dict]" = []
    for name, spec in sorted((verbs or {}).items()):
        spec = spec or {}
        # The RBAC tier is `permission` (read|write|interactive); `tier` on a verb
        # is COMMONNESS (common/rare/core) -- a different axis. Default read (safest).
        tier = spec.get("permission", "read")
        if allowed(tier, ceiling, tiers):
            out.append({"name": str(name), "kind": "verb", "tier": str(tier),
                        "description": str(spec.get("description")
                                           or spec.get("desc", ""))[:200]})
    for name, spec in sorted((recipes or {}).items()):
        spec = spec or {}
        tier = spec.get("permission", "read")
        if not allowed(tier, ceiling, tiers):
            continue
        plats = recipe_platforms(spec)
        if platform and platform not in plats:
            continue                 # recipe not available on this host platform
        out.append({"name": str(name), "kind": "recipe", "tier": str(tier),
                    "platforms": plats,
                    "description": str(spec.get("description", ""))[:200]})
    out.sort(key=lambda c: (c["kind"], c["name"]))
    return out


def manifest_summary(manifest: "Sequence[dict]") -> dict:
    """Counts for observability: total + by kind + by tier."""
    by_kind: Dict[str, int] = {}
    by_tier: Dict[str, int] = {}
    for c in manifest or []:
        by_kind[c.get("kind", "?")] = by_kind.get(c.get("kind", "?"), 0) + 1
        by_tier[c.get("tier", "?")] = by_tier.get(c.get("tier", "?"), 0) + 1
    return {"total": len(manifest or []), "by_kind": by_kind, "by_tier": by_tier}


# ── SSOT load + manifest projection + drift diff (for the generator + gate) ──
def load_recipes_from_toml(path: str) -> "Dict[str, dict]":
    """Read the [recipes.*] table from mios.toml (file I/O, mirrors
    mios_manifest.load_verbs_from_toml). Returns {} if absent/unparseable."""
    try:
        import tomllib as _toml
    except ImportError:  # pragma: no cover -- py<3.11 fallback
        try:
            import tomli as _toml  # type: ignore
        except ImportError:
            return {}
    try:
        with open(path, "rb") as fh:
            data = _toml.load(fh)
    except (OSError, ValueError):
        return {}
    recs = data.get("recipes", {}) or {}
    return {str(k): (v or {}) for k, v in recs.items() if isinstance(v, dict)}


def project_from_toml(toml_path: str, *, ceiling: str = "interactive",
                      verbs: "Optional[Dict[str, dict]]" = None) -> "List[dict]":
    """Load [verbs.*] (via mios_manifest) + [recipes.*] and project the unified
    capability manifest at `ceiling` (default interactive = the full known-tier
    surface, the committed-artifact view). Platform-agnostic (lists every
    recipe's platforms)."""
    if verbs is None:
        try:
            import mios_manifest as _man   # sibling; loads [verbs.*]
            verbs = _man.load_verbs_from_toml(toml_path)
        except Exception:  # noqa: BLE001
            verbs = {}
    return build_capability_manifest(verbs, load_recipes_from_toml(toml_path),
                                     ceiling=ceiling)


def diff_capabilities(generated: "Sequence[dict]",
                      committed: "Sequence[dict]") -> "List[str]":
    """Human-readable drift between a freshly-projected manifest and the committed
    one, keyed by (kind, name). [] == in sync (used by the regen-diff gate)."""
    def _key(c):
        return (str(c.get("kind", "")), str(c.get("name", "")))
    gen = {_key(c): c for c in (generated or [])}
    com = {_key(c): c for c in (committed or [])}
    diffs: "List[str]" = []
    for k in sorted(set(gen) - set(com)):
        diffs.append(f"+ {k[0]}:{k[1]} (in SSOT, missing from committed)")
    for k in sorted(set(com) - set(gen)):
        diffs.append(f"- {k[0]}:{k[1]} (committed, no longer in SSOT)")
    for k in sorted(set(gen) & set(com)):
        g, c = gen[k], com[k]
        if g.get("tier") != c.get("tier"):
            diffs.append(f"~ {k[0]}:{k[1]} tier {c.get('tier')!r} -> {g.get('tier')!r}")
        if sorted(g.get("platforms") or []) != sorted(c.get("platforms") or []):
            diffs.append(f"~ {k[0]}:{k[1]} platforms {c.get('platforms')} -> {g.get('platforms')}")
    return diffs
