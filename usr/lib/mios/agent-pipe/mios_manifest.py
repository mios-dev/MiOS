# AI-hint: WS-A1 anti-drift manifest projection -- the PURE core that projects the live verb catalog (mios.toml [verbs.*]) into a deterministic ai/v1 manifest object (registry_kind="verb-catalog"), so the model-facing verb surface has a committed, diffable SSOT projection separate from the file-backed Hermes build-tools registry (tools.json, registry_kind="hermes-build-tools" -- a DISJOINT namespace). load_verbs_from_toml parses the catalog the same way the agent-pipe loader does (section-gated); project_verb_catalog renders the stable manifest; diff_manifest compares a freshly-generated manifest against the committed one for the --check drift gate. The mios-ai-manifest-gen CLI + 38-drift-checks own the I/O; this module is pure (tomllib+json) so it unit-tests in isolation.
# AI-related: /usr/libexec/mios/mios-ai-manifest-gen, ./server.py, /usr/share/mios/mios.toml, /usr/share/mios/ai/v1/tools.json, ./test_mios_ai_manifest.py, ./automation/38-drift-checks.sh
# AI-functions: load_verbs_from_toml, project_verb_catalog, diff_manifest
"""mios_manifest -- verb-catalog -> ai/v1 manifest projection (WS-A1, the AIOS
SSOT anti-drift layer).

Pure stdlib (tomllib + json). The agent-pipe's _VERB_CATALOG is the live SSOT
for the model-facing verb surface, but there was no COMMITTED, diffable
projection of it -- so the surface could drift from the SSOT silently. This
module projects the catalog into a deterministic manifest object; a CLI writes
it to ai/v1/tools.generated.json and a drift gate runs `--check` (regenerate +
diff) to FAIL when the committed projection no longer matches the SSOT.

registry_kind
=============
The existing ai/v1/tools.json is the file-backed HERMES build-tools registry
(9 tool descriptors pointing at chat-completions-api/responses-api/dispatcher
JSON). It is a DISJOINT namespace from the 100+ mios.toml [verbs.*] (which
project live via MCP /v1/verbs, not a static file). To stop the two being
conflated, manifests carry an explicit registry_kind: "hermes-build-tools" for
tools.json, "verb-catalog" for the generated verb projection.
"""

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
        # WS-A7 serialization metadata is part of the SSOT surface -> project it
        # so a drift in conflict_group/parallel_limit is caught too.
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
