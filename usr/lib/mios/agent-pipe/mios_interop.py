# AI-hint: WS-11 layered-interop 3-projection core. Pure-stdlib projector that renders ONE MiOS capability (a verb, a recipe, or a promoted skill) into the A2A AgentCard "skill" shape -- the THIRD interop projection alongside the MCP tool + OpenAI function shapes server.py already emits -- plus project_all() returning the key fields of all three for parity-checking. Lets the A2A directory advertise the full capability surface (passport-gated by the caller) in the open A2A standard, not only via MCP/OpenAI. server.py owns wiring the A2A skills into the agent card; this module owns the pure projection so it unit-tests in isolation.
# AI-related: ./mios_manifest.py, ./server.py, /.well-known/agent-card.json, ./test_mios_interop.py
# AI-functions: to_a2a_skill, project_all, _tags
"""mios_interop -- 3-projection interop for the MiOS agent-pipe (WS-11).

Pure stdlib. A capability (verb/recipe/skill) is advertised three ways: the MCP
`tools/list` shape, the OpenAI function shape (both already projected in
server.py), and -- the missing third -- the A2A AgentCard `skills[]` shape so a
federated peer discovers MiOS capabilities over the open A2A standard. This
module renders that A2A shape + a parity view of all three, deterministically.

A2A skill entry (AgentCard.skills[], stable across A2A 0.3/1.0):
  {id, name, description, tags[]}  -- id is the canonical capability key.
"""

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
    # de-dup, stable order
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
