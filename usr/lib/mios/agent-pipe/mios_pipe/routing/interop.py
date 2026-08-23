# AI-hint: WS-11 layered-interop 3-projection core. Pure-stdlib projector that renders ONE MiOS capability (a verb, a recipe, or a promoted skill) in...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_routing_interop_py.md

from __future__ import annotations

from typing import List


def _tags(kind: str, spec: dict) -> List[str]:
    tags = [str(kind)]
    sect = str((spec or {}).get("section") or "").strip()
    if sect:
        tags.append(sect.lower().replace(" ", "_").replace("/", "_"))
    perm = str((spec or {}).get("permission") or "").strip()
    if perm:
        tags.append(f"perm:{perm}")
    tier = str((spec or {}).get("tier") or "").strip()
    if tier:
        tags.append(f"tier:{tier}")
    seen, out = set(), []
    for t in tags:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def to_a2a_skill(name: str, spec: dict, kind: str = "verb") -> dict:
    """Project one capability into an A2A AgentCard skill entry. `kind` is
    verb|recipe|skill; the id namespaces non-verbs (mios_recipe__/mios_skill__)
    to match server.py's relay routing."""
    s = spec if isinstance(spec, dict) else {}
    prefix = {"recipe": "mios_recipe__", "skill": "mios_skill__"}.get(str(kind), "")
    cap_id = f"{prefix}{name}"
    desc = str(s.get("desc") or s.get("description") or "").strip()
    display = str(s.get("model_name") or "").strip() or str(name)
    return {
        "id": cap_id,
        "name": display,
        "description": desc[:500],
        "tags": _tags(kind, s),
    }


def project_all(name: str, spec: dict, kind: str = "verb") -> dict:
    """The key fields of all THREE projections for parity-checking: the bare
    name (MCP/OpenAI function name), the A2A skill id, and the shared
    description. A drift between them is a directory-vs-surface divergence."""
    a2a = to_a2a_skill(name, spec, kind)
    return {
        "function_name": str(name),       # MCP tool + OpenAI function name
        "a2a_id": a2a["id"],              # A2A skill id (prefixed for non-verbs)
        "description": a2a["description"],
        "kind": str(kind),
    }
