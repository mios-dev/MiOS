<!-- AI-hint: Defines the CLI grammar and shell-widget behavior for the `mios` command and the `@` shortcut — the terminal front door to the MiOS local agent. Covers verb dispatch, the chat path to MiOS-Hermes (:8642/v1), the `@` bash/zsh widget + real binary, quoting/escaping, TTY vs non-TTY output, and exit codes. Grounds the user-facing entry point in MiOS's wider agentic-AI-OS stack (Hermes gateway -> agent-pipe -> inference lanes -> pgvector memory).
     AI-related: /usr/bin/mios, /usr/bin/@, /etc/profile.d/mios-agent.sh, /etc/profile.d/mios-verbs.sh, /usr/share/mios/ai/system.md, mios-agent -->
<!-- FHS: /usr/share/mios/docs/terminal/INVOCATIONS.md -->

# Terminal Invocation Grammar (`mios *` and `@*`)

## Purpose & place in the system

MiOS is one thing built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image you `bootc
upgrade` like a `git pull` and `bootc rollback` like a Ctrl-Z) that is *also* a
**local, self-hosted agentic AI operating system**. The same image that ships
the GNOME/Wayland desktop, NVIDIA+ROCm+iGPU via CDI, and KVM/libvirt passthrough
also ships a full agent stack behind one OpenAI-compatible endpoint.

This document specifies the **terminal front door** to that AI stack: the `mios`
CLI and the `@` shortcut. They are the shell-native way to (a) run MiOS system
verbs (build the image, open the dashboard, configure passthrough) and (b) talk
to the local agent — without leaving the prompt.

Where the request goes once you press Enter:

```
  mios <prompt> / @<prompt>
        │  (verb? → exec the wrapper directly)
        │  (deterministic "open <app>" → mios-launch)
        ▼  (everything else → chat)
  MIOS_AI_ENDPOINT  (default http://localhost:8642/v1)
        ▼
  MiOS-Hermes  — OpenAI-compatible agent gateway, tool-loop, sessions, skills
        ▼  (front-ends route through it; agent-pipe :8640 orchestrates fan-out)
  inference lanes (mios-llm-light :11450, gated heavy lanes)
        ▼
  pgvector memory (:5432)  ·  tools over MCP  ·  peers over A2A
```

The CLI is intentionally thin: it resolves the layered system prompt, loads the
tool schemas, streams tokens, and runs the function-calling roundtrip against
**MiOS-Hermes** — the one gateway every front-end (Open WebUI, the chat
gateways, this CLI) targets. Per **Architectural Law 5 (UNIFIED-AI-REDIRECTS)**,
it never hard-codes a vendor URL: it resolves the brain from `MIOS_AI_ENDPOINT`.

## `mios` — Canonical CLI

`mios` is a **verb dispatcher + locally-hosted OpenAI-compatible agent shell**
(`/usr/bin/mios`). If the first argument matches a known verb whose wrapper is
reachable, it `exec`s that wrapper directly; otherwise the arguments are treated
as a chat prompt for the agent.

```
mios <verb> [args...]        Run a MiOS system verb (table below).
mios <prompt...>             Chat + tool calls against MiOS-Hermes.
mios --no-tools <prompt...>  Chat with function-calling disabled.
mios --json <schema> <prompt...>
                             Structured output (schema = a file in
                             /usr/lib/mios/schemas/ without .schema.json); tools off.
mios help                    Show the verb + chat usage.
```

### System verbs

| Verb | Action |
|------|--------|
| `mios build` | Run the MiOS OCI build pipeline (`mios-build-driver`; unattended on a non-TTY). |
| `mios dash` / `mios mini` | Framed dashboard (services + endpoints + git tree); `mini` = compact. |
| `mios config` | Open the HTML configurator (the `mios.toml` editor) in your browser. |
| `mios code` | Open code-server (`http://localhost:8080/`) in your browser. |
| `mios ai` | Open Open WebUI (`http://localhost:3030/`) in your browser. |
| `mios ai clear` | DAY-0 clean slate: wipe chats/jobs/kanban/DBs/RAG. |
| `mios xbox` | Xbox VM Secure Boot / XML repair. |
| `mios virt` | Apply optimized VM config + CPU pinning. |
| `mios vfio` / `vfio-check` / `vfio-toggle` | Configure / report / interactively select GPU/USB passthrough. |
| `mios tune` | System-wide CPU isolation & latency tuning. |
| `mios summary` / `profile` / `assess` | Quick overview / interactive profiler / full capability report. |
| `mios iommu` / `iommu-groups` | Pretty-print / list raw IOMMU topology. |
| `mios env` / `sync-env` | Inspect the layered `MIOS_*` env / regenerate `install.env` from `mios.toml`. |
| `mios flatpaks` | Manage system-wide Flatpaks. |
| `mios theme` | Sync bibata/GTK/Qt themes. |
| `mios user` | Initialize user space (dotfiles/XDG). |

> The verb table is the same set the interactive `mios()` shell function in
> `/etc/profile.d/mios-verbs.sh` routes — kept in sync deliberately. That shell
> function only exists for interactive shells, so non-interactive callers (the
> agent's `terminal` tool, CI, the Forgejo runner, `bash -c 'mios build'`) land
> in `/usr/bin/mios`, which carries the same verb map. A verb missing from the
> CLI map would fall through to *chat* — e.g. a bare `build` would be sent to the
> gateway as a prompt rather than running the pipeline.

### Chat path

Anything that isn't a verb is a chat turn:

```sh
mios "why did my build fail at phase 32?"
mios --no-tools "draft a kargs.d snippet to add console=ttyS0"
mios --json kanban-card "make a card to migrate the embed lane"
```

The chat path:

1. Resolves the **system prompt** via the layered override chain (highest wins):
   `$MIOS_AI_SYSTEM_PROMPT` → `~/.config/mios/system-prompt.md` →
   `/etc/mios/ai/system-prompt.md` → `/usr/share/mios/ai/system.md` (canonical).
2. Loads the tool definitions from `/usr/lib/mios/tools/chat-completions-api/*.json`.
3. Opens a streaming chat against `MIOS_AI_ENDPOINT` and runs the function-calling
   roundtrip — for each `tool_call` the model emits, it dispatches the matching
   executable under `/usr/libexec/mios/tools/<name>`, appends the result, and
   re-calls until the model finishes.

The endpoint serves **one virtual model** — `hermes-agent`, the agent loop
itself. The actual generation model is selected *inside* Hermes (and ultimately
served by the inference lanes), not chosen per request; the request `model`
defaults to `hermes-agent` (`MIOS_AI_GATEWAY_MODEL`). `MIOS_AI_MODEL` remains the
raw model-tag SSOT for the image build and lane config, which is a separate knob.

### Deterministic launch pre-route

In tool-using chat mode, an unambiguous `open|launch|start|run <app>` is treated
as one concrete action and dispatched straight to `mios-launch`, bypassing the
small Hermes model's tool loop (which is unreliable for launches). Filler/lead/
trail phrases come from the SSOT `[routing].*` lists in `mios.toml` — the *same*
lists the agent-pipe deterministic route uses, so there are **no hardcoded
English app/topic deny-lists**. Falls through to ordinary chat if `mios-launch`
is missing or the prompt is ambiguous.

## `@` — Shell-Position-Free Invocation

`@` is the shorthand for the chat path — it delegates to `/usr/bin/mios` so
`@<prompt>` and `mios <prompt>` resolve to the same agent surface.

- **As widget**: at any prompt position, typing `@hello world<Enter>` invokes the
  agent with `hello world`. Bash uses a `READLINE_LINE` rewrite via `bind -x`;
  zsh uses a ZLE widget bound on `^M`. The widget rewrites the line into the real
  `@` binary call (`@ <quoted-arg>`) before accepting it. See
  `/etc/profile.d/mios-agent.sh`.

  > The bash binding terminates on `\C-j` (line-feed), **not** `\C-m` (carriage
  > return): `\C-m` is `\r`, so a `\r → …\C-m` binding recursively re-triggers
  > itself and readline aborts with "maximum macro execution nesting level
  > exceeded" on every Enter, breaking all shell input. `\C-j` submits cleanly.

- **As binary**: `/usr/bin/@` is a real executable. Pipes work — with no
  arguments and stdin attached, it reads the piped text as the prompt:

  ```sh
  cat error.log | @ "summarize this"
  cat error.log | @          # stdin becomes the whole prompt
  ```

- **Escape hatch**: `\@foo` (leading backslash) is passed to the shell literally.
  The widget honors quoting: `'@foo'` is literal.

## Examples

```sh
mios "why did my build fail at phase 32?"
@why did the build fail
@ "draft a kargs.d snippet to add console=ttyS0"
mios build
mios dash
mios env                              # inspect the layered MIOS_* surface
mios sync-env                         # regenerate install.env after editing mios.toml
```

## Quoting and special characters

| Input               | Effect                                        |
|---------------------|-----------------------------------------------|
| `@foo bar`          | Agent called with `foo bar`.                   |
| `@'foo $X bar'`     | Agent called with `foo $X bar` (literal).      |
| `@"foo $X bar"`     | Variable expansion happens, then the agent.    |
| `\@foo`             | Shell literal (no widget rewrite).            |
| `echo @foo`         | `echo` runs; `@foo` is its argument.          |
| `cmd \| @ "Q"`      | Pipes stdin into the agent as context.         |

## TTY vs non-TTY

- TTY → streaming SSE tokens, printed incrementally as they arrive; tool calls
  are echoed as `[tool] name({...})` so the operator sees the loop.
- Non-TTY (pipe / `>`) → the `@` binary also reads its prompt from stdin when no
  argument is given, so `cmd | @` feeds command output to the agent as context.

## Exit codes

| Code | Meaning                                                |
|------|--------------------------------------------------------|
| 0    | Success.                                               |
| 1    | Runtime error (chat call failed; endpoint/model shown on stderr). |
| 2    | Usage error (empty prompt, missing `--json` schema, bad args). |
| 127  | The `openai` SDK is missing (install hint on stderr).  |
| 130  | SIGINT during stream (Ctrl-C).                         |

## Related

- Endpoint resolution and the AI plane: see `MIOS_AI_ENDPOINT` (Law 5) and the
  inference lanes — **`mios-llm-light`** (`:11450`, primary llama.cpp lane behind
  the upstream `mios-llm-light` proxy image; serves everyday models, the
  `mios-opencode` coder model, **and** embeddings via `nomic-embed-text`) plus
  the gated heavy lanes **`mios-llm-heavy`** (SGLang, `:11441`) and
  **`mios-llm-heavy-alt`** (vLLM). The lanes speak the OpenAI/Ollama-compatible
  API (an upstream API-compat reference only — Ollama itself is not a MiOS
  backend).
- Orchestration: **agent-pipe** (`:8640`) fronting **MiOS-Hermes** (`:8642`),
  with the **prefilter** (`:8641`) and **opencode-gateway** (`:8633`).
- Memory: **PostgreSQL + pgvector** (`mios-pgvector`, `:5432`) — the unified
  agent datastore (agent_memory, event, tool_call, session, skill, scratch,
  knowledge, sys_env, kanban, …), accessed via `mios-pg-query` / `mios-db --pg`.
- Repo context switching from the shell: `mios-repo {main|bootstrap}` (the
  `mios_repo_use` helper in `/etc/profile.d/mios-agent.sh`; it must alias, since a
  binary can't mutate the parent shell's env).
