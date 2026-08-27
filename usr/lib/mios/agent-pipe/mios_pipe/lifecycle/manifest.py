# AI-hint: WS-A1 anti-drift manifest projection -- the PURE core that projects the live verb catalog (mios.toml [verbs.*]) into a deterministic ai...
# AI-doc: usr/share/doc/mios/manual/lifecycle.md

from __future__ import annotations

import json
from typing import Dict, List

def load_verbs_from_toml(toml_path: str) -> Dict[str, dict]:
    """Parse mios.toml [verbs.*] into {name: spec}, section-gated exactly like
    the agent-pipe _load_verb_catalog (entries lacking `section` are the
    configurator's UI buttons, not agent verbs -- skipped)."""
    try:
        import tomllib as _toml
    except ImportError:  # pragma: no cover
        import tomli as _toml  # type: ignore
    with open(toml_path, "rb") as fh:
        data = _toml.load(fh)
    out: Dict[str, dict] = {}
    verbs = data.get("verbs") or {}
    if isinstance(verbs, dict):
        for name, cfg in verbs.items():
            if isinstance(cfg, dict) and "section" in cfg:
                out[str(name)] = cfg
    return out

def project_verb_catalog(catalog: Dict[str, dict], *, version: str = "v1") -> dict:
    """Render the verb catalog into a deterministic manifest object. Stable:
    verbs sorted by name, a fixed field subset, so re-running yields identical
    bytes unless the SSOT actually changed (the property the drift gate needs).
    Hidden verbs are still projected (they remain dispatchable) but flagged."""
    data: List[dict] = []
    for name in sorted(catalog or {}):
        spec = catalog.get(name) or {}
        if not isinstance(spec, dict):
            continue
        entry = {
            "name": str(name),
            "model_name": str(spec.get("model_name") or "").strip(),
            "section": str(spec.get("section", "Misc")),
            "sig": str(spec.get("sig", "")),
            "description": str(spec.get("desc", "")),
            "tier": str(spec.get("tier", "common")),
            "permission": str(spec.get("permission", "read")),
            "hidden": bool(spec.get("hidden", False)),
        }
        cg = str(spec.get("conflict_group") or "").strip()
        if cg:
            entry["conflict_group"] = cg
        try:
            pl = int(spec.get("parallel_limit") or 0)
        except (TypeError, ValueError):
            pl = 0
        if pl >= 1:
            entry["parallel_limit"] = pl
        data.append(entry)
    return {
        "object": "mios.verb.catalog",
        "version": version,
        "registry_kind": "verb-catalog",   # NOT the hermes-build-tools registry
        "generated": True,                  # machine-projected from mios.toml [verbs.*]
        "source": "/usr/share/mios/mios.toml#[verbs.*]",
        "count": len(data),
        "data": data,
    }

def diff_manifest(generated: dict, committed: dict) -> List[str]:
    """Return a list of human-readable differences between a freshly-generated
    manifest and the committed one (empty == in sync). Compares the `data`
    entries by name + the count; ignores volatile top-level fields. Used by the
    --check drift gate."""
    diffs: List[str] = []
    if not isinstance(committed, dict):
        return ["committed manifest missing or unparseable"]
    g = {e["name"]: e for e in (generated.get("data") or []) if isinstance(e, dict) and e.get("name")}
    c = {e["name"]: e for e in (committed.get("data") or []) if isinstance(e, dict) and e.get("name")}
    for name in sorted(set(g) - set(c)):
        diffs.append(f"+ verb '{name}' in SSOT but not in committed manifest")
    for name in sorted(set(c) - set(g)):
        diffs.append(f"- verb '{name}' in committed manifest but not in SSOT")
    for name in sorted(set(g) & set(c)):
        if g[name] != c[name]:
            diffs.append(f"~ verb '{name}' changed (regenerate the manifest)")
    if committed.get("registry_kind") != "verb-catalog":
        diffs.append("committed manifest registry_kind != 'verb-catalog'")
    return diffs
