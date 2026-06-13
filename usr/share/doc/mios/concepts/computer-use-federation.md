<!-- AI-hint: Conceptual documentation of the Computer-Use Federation, defining the unified MCP/A2A architecture for Linux/Wayland desktop control via the `cu_*` verb catalog, `mios-computer-use` executor, and `mios-pc-vision` grounding.
     AI-related: /usr/libexec/mios/mios-computer-use, /usr/libexec/mios/mios-pc-vision, /usr/libexec/mios/mios-computer-use-server, /etc/mios/ai/v1/mcp.json, /etc/mios/ai/v1/a2a-peers.json, mios-computer-use, mios-pc-vision, mios-computer-use-server, mios-pc-control, mios-llm-light, mios-llm-heavy-alt -->
# Computer-Use Federation (MCP + A2A)

**Status:** shipped 2026-06-04. Linux/Wayland desktop computer-use delivered
as a full MCP + A2A capability -- local verbs and federated remote desktops.

## Where this fits in MiOS

MiOS is one thing built two ways at once: an **immutable bootc/OCI Fedora
workstation** (the whole OS is a single container image you `bootc upgrade` like
a `git pull` and `bootc rollback` like a Ctrl-Z) that is *also* a **local,
self-replicating agentic AI operating system**. The same image that ships
GNOME/Wayland and the virtualisation/cluster stack also ships a full local agent
stack behind one OpenAI-compatible endpoint: the **agent-pipe** orchestrator
(`:8640`) refines and fans a request across a council/swarm; **MiOS-Hermes**
(`:8642`) is the tool-loop gateway; **pgvector** (`:5432`) is the unified agent
memory; the **inference lanes** (`mios-llm-light` `:11450` primary, the gated
`mios-llm-heavy`/`mios-llm-heavy-alt` GPU lanes) do generation and embeddings;
**MCP** exposes the tool surface and **A2A** federates peer agents.

Computer-use is the part of that whole that lets the agent **act on a graphical
desktop** -- not just answer, but click, type, and verify on a real Wayland
session. Its design goal is to deliver that as a first-class capability through
the **open standards the agent-pipe already consumes** (MCP tools + A2A skills)
rather than bespoke plumbing. One capability surface; three deployment shapes;
zero new orchestrator. Because MiOS is *one* image for any hardware, the same
`cu_*` verb surface drives bare-metal GNOME, WSLg, and a federated remote
desktop -- the executor adapts by environment, never the caller.

## The pieces

| Component | Path | Role |
|---|---|---|
| **Executor** | `/usr/libexec/mios/mios-computer-use` | Environment-adaptive Linux/Wayland desktop driver. Backends: RemoteDesktop portal (libei) + Screenshot portal + AT-SPI grounding; self-written uinput fallback (no ydotool/AGPL). On WSLg it delegates to `mios-pc-control`; with a configured `executor_endpoint` it routes to a remote desktop. |
| **Verbs** | `mios.toml [verbs.cu_*]` | `cu_screenshot`, `cu_ground`, `cu_atspi_query`, `cu_window_list`, `cu_click`, `cu_type`, `cu_key`, `cu_key_combo`. Each enters `_VERB_CATALOG` and auto-projects to **MCP** (`/v1/verbs`), **OpenAI tools** (the agent loop), and **A2A skills** (the agent card) -- one SSOT, three projections, no per-protocol code. |
| **Grounding** | `/usr/libexec/mios/mios-pc-vision` | AT-SPI-first; vision fallback on `qwen3-vl:4b` (served by `mios-llm-light` on `:11450`, JSON coords) or the gated vLLM `mios-grounding` lane (`mios-llm-heavy-alt`, UI-TARS-1.5-7B, Action-DSL). Auto-selects parser by model name. |
| **Node server** | `/usr/libexec/mios/mios-computer-use-server` | Dual **MCP + A2A + REST-executor** server (FastAPI/uvicorn) that a desktop runs so the central pipe CONSUMES it. `systemd --user` service gated to `graphical-session.target`. |
| **Skill** | `usr/share/mios/hermes/skills/linux-control/SKILL.md` | The agent-facing decision tree (AT-SPI first, vision fallback, cu_* vs pc_*). |

## Three shapes, one surface

### 1. Local desktop (no network hop)

On any MiOS host with a Wayland session, the `cu_*` verbs dispatch straight to
`mios-computer-use`. Because the verbs are in `_VERB_CATALOG`, the local desktop
is **already** an MCP tool surface (`/v1/verbs`) and A2A skill set (agent card)
to anything that consumes this host's pipe. No server needed for the local case.

### 2. This desktop AS a federated producer

A desktop that should be drivable *by another* MiOS host runs
`mios-computer-use-server` -- one FastAPI/uvicorn process exposing the same
capability three ways on one port (default `:11438`):

* **MCP** (Streamable HTTP, spec 2025-06-18) at `POST/GET /mcp` --
  `initialize` / `tools/list` / `tools/call` for the nine `cu.*` tools.
* **A2A** (0.3.0) at `GET /.well-known/agent-card.json` (a `desktop-control`
  skill) + `POST /a2a` (`message/send` and SSE `message/stream`) +
  `GET /a2a/contexts/{id}` (shared inter-agent context).
* **REST executor** (`GET /screenshot|/windows`, `POST /input/*|/window/*`)
  -- the same contract the Windows `mios-oscontrol-server.ps1` speaks.

It is hand-rolled on FastAPI/uvicorn (the agent-pipe's own stack, from the
shared venv) rather than the `mcp` / `a2a-sdk` packages: those are pip-only
with churny APIs (`a2a-sdk >=1.0` dropped `A2AStarletteApplication`) that an
immutable air-gapped bootc image must not depend on. The surface is tiny and
the agent-pipe's own MCP/A2A client consumes these exact shapes, so interop is
guaranteed and the dependency closure stays at `fastapi`+`uvicorn` (dnf-clean).

### 3. The central pipe CONSUMING a remote desktop

The agent-pipe already wired MCP + A2A **consume** into the agent loop and DAG
(see `_mcp_tool_to_openai_tool`, `_a2a_send_message_to_peer`). To make a remote
desktop drivable, register its node-server URL in the operator overlays the pipe
already reads -- nothing else changes.

**As an MCP server** -- `/etc/mios/ai/v1/mcp.json`:

```json
{
  "servers": [
    {
      "id": "workstation",
      "url": "http://172.20.0.5:11438/mcp",
      "transport": "streamable-http",
      "enabled": true
    }
  ]
}
```

Its `cu.*` tools then surface in the agent loop as `mcp.workstation.cu.*`.

**As an A2A peer** -- `/etc/mios/ai/v1/a2a-peers.json`:

```json
{
  "peers": [
    {
      "id": "workstation",
      "url": "http://172.20.0.5:11438",
      "enabled": true,
      "label": "Workstation desktop"
    }
  ]
}
```

(Use LAN / local addresses -- the `172.x` WSL gateway or `192.168.x` -- not
tailnet `100.x`: Tailscale is OFF by MiOS policy, see `[a2a]` in `mios.toml`.)

On startup the pipe GETs `<url>/.well-known/agent-card.json`, parses the
`desktop-control` skill, and exposes it at `/v1/a2a/skills`. A DAG node tagged
with `a2a_peer_id=workstation` delegates a whole desktop task to that machine
with a shared `contextId`.

**MCP vs A2A, when:** MCP for fine-grained tool calls the central planner
sequences (`cu.screenshot` -> `cu.ground` -> `cu.click`); A2A to hand an entire
desktop sub-task ("log into X and download the latest invoice") to that
desktop's agent. Both are consumed by machinery that already exists.

This is the report's "one GUI agent per controlled desktop, one shared
orchestrator/model layer" -- realised over the consumed standards, not a second
Goose/OpenHands stack. Add a desktop = add two overlay entries.

## Security

The MiOS Architectural Laws keep the AI plane unified and least-privileged (Law
5 UNIFIED-AI-REDIRECTS, Law 6 UNPRIVILEGED-QUADLETS); the computer-use surface
extends that posture to the highest-trust capability MiOS has -- driving a real
desktop.

* **Bind loopback by default** (`[computer_use].bind_address`). Expose to a
  trusted segment by setting the LAN IP + firewalling the port to that segment;
  never bind a public interface. (`bind_address = ""` disables the server.)
* **DNS-rebinding guard** -- the MCP endpoint validates the `Origin` header
  (per spec); server-to-server callers (the pipe) send none and pass.
* **Optional bearer token** (`[computer_use].auth_token`) gates the write
  surfaces (`cu.click`/`type`/`key` + `/input/*` + A2A `message/*`). For
  cross-host delegation, require **A2A Ed25519 passport signing** at the pipe
  (the passport infra already exists at `/var/lib/mios/passports`).
* **DoD / approval gate** -- every write-class op runs through
  `mios-computer-use`, which honours the Definition-of-Done / approval gate
  (`[computer_use].require_approval = true`: write-class click/type/key go
  through the gate, read-class screenshot/window-list/ground auto). AT-SPI and
  the ScreenCast portal are *session-wide* grants -- gate them, and never
  auto-enable the node server on a host where the real desktop is the Windows
  side (WSLg defers to the existing broker lane).
* **No ydotool** -- input is the RemoteDesktop portal (libei, sandboxable,
  user-consented) or our own uinput device; the AGPL seat-wide ydotool daemon
  is never used.

## Grounding model

Grounding resolves through the same unified inference plane as the rest of MiOS,
so there is no separate vision backend to provision. Baseline `qwen3-vl:4b` runs
on the **always-on `mios-llm-light` lane** (`:11450`, llama.cpp behind the
`llama-swap` proxy image) -- the same engine that serves the everyday chat
models and embeddings, auto-swapping the vision model on demand. It is INERT
until the GGUFs are baked under `/models` (the operator downloads the weights;
the security classifier blocks the fetch for the assistant), then `cu_ground`'s
vision fallback activates with no endpoint change.

The accuracy upgrade is **UI-TARS-1.5-7B** (Apache-2.0) served as
`mios-grounding` on the gated vLLM lane `mios-llm-heavy-alt` (`:11440`); it
stays disabled until the dGPU has free VRAM (the shared 4090 is held by the
Windows host). `mios-pc-vision` auto-switches its coordinate parser by model
name, so enabling the heavy lane needs no code change -- just bake the weights +
flip the served name. All model/endpoint choices are SSOT (`mios.toml`
`[computer_use].grounding_model`), never hardcoded.

## See also

* `usr/share/mios/hermes/skills/linux-control/SKILL.md` -- agent decision tree.
* `usr/share/mios/hermes/skills/pc-control/SKILL.md` -- the Windows-host peer.
* `usr/share/mios/docs/agents/PC-CONTROL-LOCAL.md` -- the original local-only
  proposal this realises (now shipped, cross-platform + federated).
