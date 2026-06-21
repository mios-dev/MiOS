# AI-hint: WS-A17 versioned agent/tool package format + local registry projection. Pure core that wraps each capability (a verb/tool, an agent, a recipe) into a VERSIONED package descriptor (author/name/version/kind + manifest) and projects a registry INDEX over them -- the SSOT-derived, flag-gated local "package registry" (an AIOS agent/tool distribution unit), built from the same live catalogs WS-A1 projects. build_package/build_registry are deterministic; verify_registry diffs a regenerated index vs the committed one for a drift gate. The mios-registry CLI + automation/lib/generate-packages.sh own the I/O + build-time materialization; this module is pure (stdlib) so it unit-tests in isolation.
# AI-related: ./mios_manifest.py, /usr/libexec/mios/mios-registry, /automation/lib/generate-packages.sh, /usr/lib/mios/schemas/mios-pkg.schema.json, /usr/lib/mios/schemas/mios-registry.schema.json, ./test_mios_registry.py
# AI-functions: build_package, build_registry, registry_path, verify_registry
"""mios_registry -- versioned package + local registry projection (WS-A17, the
AIOS agent/tool packaging layer).

Pure stdlib. A "package" is a versioned, self-describing wrapper around ONE
capability the live SSOT already defines -- a verb/tool, an agent, or a recipe.
The registry INDEX is a flat catalogue of those packages keyed by
author/name/version. Both are deterministic projections of the live catalogs
(the same ones WS-A1 projects), so the whole thing is a materialized SSOT
mirror, gated behind [ai].package_registry (ships inert -> nothing emitted, the
drift gate is a trivial pass).

Path layout (when materialized):
    ai/v1/packages/<author>/<name>/<version>/mios-pkg.toml   (per-package manifest)
    ai/v1/packages/registry.json                              (the index)
"""

from __future__ import annotations

from typing import Dict, List, Tuple

PKG_SCHEMA = "mios-pkg/v1"
REGISTRY_SCHEMA = "mios-registry/v1"


def registry_path(author: str, name: str, version: str) -> str:
    """Repo-relative path of a package manifest (forward slashes, layout above)."""
    return f"ai/v1/packages/{author}/{name}/{version}/mios-pkg.toml"


def build_package(name: str, kind: str, spec: dict, *,
                  author: str, version: str) -> dict:
    """Wrap one capability spec into a versioned package descriptor. `kind` is
    one of verb/agent/recipe; `spec` is the capability's SSOT entry (a stable
    subset is embedded so the package is self-describing)."""
    s = spec if isinstance(spec, dict) else {}
    manifest = {
        "description": str(s.get("desc") or s.get("description") or ""),
        "section": str(s.get("section", "")),
        "tier": str(s.get("tier", "")),
        "permission": str(s.get("permission", "")),
    }
    return {
        "object": "mios.package",
        "schema": PKG_SCHEMA,
        "author": str(author),
        "name": str(name),
        "version": str(version),
        "kind": str(kind),
        "manifest": {k: v for k, v in manifest.items() if v != ""},
    }


def build_registry(items: List[Tuple[str, str, dict]], *,
                   author: str, version: str) -> Dict:
    """Project a registry from (name, kind, spec) tuples. Returns
    {"index": <registry.json obj>, "packages": [<mios-pkg obj>, ...]}.
    Deterministic: packages sorted by (kind, name)."""
    ordered = sorted(((str(n), str(k), s) for n, k, s in (items or [])),
                     key=lambda t: (t[1], t[0]))
    packages = [build_package(n, k, s, author=author, version=version)
                for n, k, s in ordered]
    index = {
        "object": "mios.registry",
        "schema": REGISTRY_SCHEMA,
        "author": str(author),
        "version": str(version),
        "count": len(packages),
        "packages": [
            {
                "author": str(author),
                "name": p["name"],
                "version": str(version),
                "kind": p["kind"],
                "path": registry_path(author, p["name"], version),
            }
            for p in packages
        ],
    }
    return {"index": index, "packages": packages}


def verify_registry(regenerated_index: dict, committed_index: dict) -> List[str]:
    """Diff a freshly-regenerated registry index vs the committed one (empty ==
    in sync). Compares the package set by (kind, name, version)."""
    if not isinstance(committed_index, dict):
        return ["committed registry index missing or unparseable"]

    def keyset(idx):
        return {(str(e.get("kind")), str(e.get("name")), str(e.get("version")))
                for e in (idx.get("packages") or []) if isinstance(e, dict)}

    g, c = keyset(regenerated_index), keyset(committed_index)
    diffs = []
    for k in sorted(g - c):
        diffs.append(f"+ package {k} in SSOT but not in committed registry")
    for k in sorted(c - g):
        diffs.append(f"- package {k} in committed registry but not in SSOT")
    if committed_index.get("schema") != REGISTRY_SCHEMA:
        diffs.append(f"committed registry schema != {REGISTRY_SCHEMA}")
    return diffs
