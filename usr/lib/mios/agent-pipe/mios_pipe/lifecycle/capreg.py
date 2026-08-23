# AI-hint: WS-2 unified capability registry projection -- the PURE half: merge the [verbs.*] catalog, the [recipes.*] OS-command templates, AND the ...
# AI-doc: usr/share/doc/mios/manual/lifecycle.md

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


def skill_steps(spec: dict) -> "List[str]":
    """The ordered capability names a skill invokes -- the DAG edges out of a
    skill. Reads body.steps[].verb (a step may name a verb OR another skill)."""
    body = (spec or {}).get("body") or spec or {}
    out: "List[str]" = []
    for s in (body.get("steps") or []):
        if isinstance(s, dict) and s.get("verb"):
            out.append(str(s["verb"]))
    return out


def skill_effective_tier(name: str, skills: "Dict[str, dict]",
                         verbs: "Optional[Dict[str, dict]]",
                         tiers: "Sequence[str]" = _DEFAULT_TIERS,
                         _seen: "Optional[frozenset]" = None) -> str:
    """A skill is no safer than the MOST-privileged capability it invokes, so its
    effective RBAC tier = the MAX tier over its transitive verb closure. Fail-
    closed: a component that is neither a known verb nor a known skill -> an
    unknown tier (never admitted); a skill->skill CYCLE -> the strictest known
    tier. A leaf-less skill is 'read'."""
    seen = _seen or frozenset()
    if name in seen:
        return tiers[-1]                     # cycle -> strictest known (fail-closed)
    seen = seen | {name}
    verbs = verbs or {}
    best, best_rank = "read", -1
    for comp in skill_steps(skills.get(name) or {}):
        if comp in verbs:
            t = str((verbs[comp] or {}).get("permission", "read"))
        elif comp in skills:
            t = skill_effective_tier(comp, skills, verbs, tiers, seen)
        else:
            return "(unknown)"               # dangling edge -> fail-closed
        r = tier_rank(t, tiers)
        if r > best_rank:
            best_rank, best = r, t
    return best


def build_capability_manifest(verbs: "Optional[Dict[str, dict]]",
                              recipes: "Optional[Dict[str, dict]]", *,
                              ceiling: str,
                              skills: "Optional[Dict[str, dict]]" = None,
                              tiers: "Sequence[str]" = _DEFAULT_TIERS,
                              platform: "Optional[str]" = None) -> "List[dict]":
    out: "List[dict]" = []
    verbs = verbs or {}
    for name, spec in sorted(verbs.items()):
        spec = spec or {}
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
    for name, spec in sorted((skills or {}).items()):
        spec = spec or {}
        uses = skill_steps(spec)
        tier = skill_effective_tier(name, skills, verbs, tiers)
        if not allowed(tier, ceiling, tiers):
            continue
        if not all(allowed(str((verbs.get(u) or {}).get("permission", "read")),
                           ceiling, tiers)
                   for u in uses if u in verbs):
            continue
        out.append({"name": str(name), "kind": "skill", "tier": str(tier),
                    "uses": uses,
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


def load_skills_from_dir(skills_dir: str) -> "Dict[str, dict]":
    """Read the structured JSON skills (usr/share/mios/skills/*.json) -- each has
    body.steps[].verb, the DAG edges. Returns {name: spec}; {} if the dir is
    absent/unreadable. Hermes prose SKILL.md skills are NOT structured capabilities
    (free text, no machine-readable steps) so they are intentionally not loaded."""
    import glob
    import json
    import os
    out: "Dict[str, dict]" = {}
    try:
        paths = sorted(glob.glob(os.path.join(skills_dir, "*.json")))
    except (OSError, ValueError):
        return {}
    for p in paths:
        try:
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        name = str(d.get("name") or os.path.splitext(os.path.basename(p))[0])
        out[name] = d
    return out


def build_capability_dag(verbs: "Optional[Dict[str, dict]]",
                         recipes: "Optional[Dict[str, dict]]",
                         skills: "Optional[Dict[str, dict]]") -> dict:
    verbs = verbs or {}
    recipes = recipes or {}
    skills = skills or {}
    known_verb, known_skill = set(verbs), set(skills)
    nodes = ([{"name": n, "kind": "verb"} for n in sorted(verbs)]
             + [{"name": n, "kind": "recipe"} for n in sorted(recipes)]
             + [{"name": n, "kind": "skill"} for n in sorted(skills)])
    edges: "List[dict]" = []
    dangling: set = set()
    for s in sorted(skills):
        for comp in skill_steps(skills[s]):
            kind = ("skill" if comp in known_skill
                    else "verb" if comp in known_verb else "unknown")
            edges.append({"from": s, "to": comp, "to_kind": kind})
            if kind == "unknown":
                dangling.add(comp)

    adj = {s: [c for c in skill_steps(skills[s]) if c in known_skill]
           for s in skills}
    WHITE, GREY, BLACK = 0, 1, 2
    color = {s: WHITE for s in skills}
    cycles: "List[str]" = []

    def _visit(u: str, stack: "List[str]") -> None:
        color[u] = GREY
        stack.append(u)
        for v in adj.get(u, []):
            if color.get(v) == GREY:
                i = stack.index(v) if v in stack else 0
                cycles.append(" -> ".join(stack[i:] + [v]))
            elif color.get(v) == WHITE:
                _visit(v, stack)
        stack.pop()
        color[u] = BLACK

    for s in sorted(skills):
        if color[s] == WHITE:
            _visit(s, [])
    return {"nodes": nodes, "edges": edges,
            "cycles": sorted(set(cycles)), "dangling": sorted(dangling)}


def _default_skills_dir(toml_path: str) -> str:
    """skills/ sits beside mios.toml (usr/share/mios/{mios.toml,skills/})."""
    import os
    return os.path.join(os.path.dirname(os.path.abspath(toml_path)), "skills")


def project_from_toml(toml_path: str, *, ceiling: str = "interactive",
                      verbs: "Optional[Dict[str, dict]]" = None,
                      skills_dir: "Optional[str]" = None) -> "List[dict]":
    """Load [verbs.*] (via mios_manifest) + [recipes.*] + the structured JSON
    skills and project the unified capability manifest at `ceiling` (default
    interactive = the full known-tier surface, the committed-artifact view).
    Platform-agnostic (lists every recipe's platforms). `skills_dir` defaults to
    the skills/ directory beside mios.toml."""
    if verbs is None:
        try:
            import mios_manifest as _man   # sibling; loads [verbs.*]
            verbs = _man.load_verbs_from_toml(toml_path)
        except Exception:  # noqa: BLE001
            verbs = {}
    skills = load_skills_from_dir(skills_dir or _default_skills_dir(toml_path))
    return build_capability_manifest(verbs, load_recipes_from_toml(toml_path),
                                     ceiling=ceiling, skills=skills)


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
