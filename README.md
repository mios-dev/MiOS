<!-- AI-hint: Project overview and high-level architecture for MiOS, an immutable container-image-based Linux workstation that is also a local self-hosted agentic AI OS; use this to understand the system's core identity, what it does end-to-end (build pipeline -> OCI image -> bootc lifecycle; local inference lanes -> agent orchestration -> pgvector memory), its licensing, and primary value proposition.
     AI-related: /usr/libexec/mios/mios-build-driver, /usr/share/mios/configurator/, /usr/share/mios/mios.toml, /usr/share/mios/ai/, /usr/share/mios/ai/system.md, /usr/share/mios/llamacpp/mios-llm-light.yaml, mios-build-driver, mios-dev, mios-bootstrap, mios-build-local, mios-llm-light, mios-pgvector, mios-ceph -->
# 'MiOS'

> **Core Thesis:** Read the [MiOS Architectural Thesis & Scope Statement](usr/share/doc/mios/manual/thesis.md) defining the 4 pillars of MiOS, its nature as a research vehicle/proof-of-concept, and the distinction between designed deployment scope vs. observed runtime environments (dev VM & WSL2).

> **Pronounced "MyOS"** -- short for *My OS* / *My Operating System*. The
> name is a stylistic capitalization of the same shorthand; it carries no
> other meaning and refers to no person or organization.
>
> **Project nature.** 'MiOS' is a **research project**, not a commercial
> product. It is *generative*: synthesized from a small set of seed
> scripts and manually-curated documentation, then iteratively expanded
> by automated tooling and human review. Treat every script, lint, and
> default as an artifact under ongoing review.
>
> **Runtime agreements.** By invoking any entry point in this repo
> (`just <target>`, `install.sh`, `install.ps1`, `bootstrap.{sh,ps1}`,
> the deployed `mios` CLIs, `bootc upgrade` against a 'MiOS' image, ...),
> you acknowledge [`AGREEMENTS.md`](./AGREEMENTS.md) -- Apache-2.0 main
> license, bundled-component licenses ([`usr/share/doc/mios/reference/licenses.md`](usr/share/doc/mios/reference/licenses.md)),
> and attribution ([`usr/share/doc/mios/reference/credits.md`](usr/share/doc/mios/reference/credits.md)). All upstream projects
> and standards referenced here are the property of their respective
> owners; 'MiOS' integrates with them but claims no affiliation with
> them.

An immutable, container-image-shaped Linux workstation that boots like an OS,
upgrades like a `git pull`, and rolls back like a Ctrl-Z. It's Fedora
underneath, with a curated stack on top for people who actually use their
machines for AI, virtualization, and clusters -- not just spreadsheets.

And it's more than a desktop: 'MiOS' is also a **local, self-hosted agentic AI
operating system**. The same image that ships your GNOME session ships a full
inference + agent stack -- local LLM lanes, an OpenAI-compatible front door, a
multi-agent orchestration pipeline, and a PostgreSQL+pgvector memory -- all
running on *your* hardware, offline-capable, with no vendor account in the loop.
The OS can reason about itself, drive its own tools, and (because the whole
thing is one rebuildable OCI image) effectively re-create itself.

The default ref:

```
ghcr.io/mios-dev/mios:latest
```

If you've got a Fedora-bootc-compatible host (or a Hyper-V VHDX, ISO, qcow2,
or WSL2 distro you can run), you can be on 'MiOS' in the time it takes the
network to pull the image.

---

## Why bother

A normal distro evolves like a Jenga tower: every package update is a small
prayer, every clean reinstall is a weekend. 'MiOS' is the opposite -- the
whole OS is one OCI image. You upgrade it the way you'd upgrade a container.
If something breaks, `bootc rollback` and you're back where you started, with
no "I sure hope `dnf` finishes" in the middle.

That single-image discipline is also what makes the AI side trustworthy: the
agent stack isn't a pile of pip-installed daemons you have to babysit -- it's
baked into the same immutable image, version-locked to the OS, and reproduced
exactly on every box that pulls the ref.

What you actually get out of the box:

- **GNOME 50 on Wayland** (the desktop), plus Phosh as a tablet-style
  fallback for portrait / RDP scenarios.
- **NVIDIA + AMD ROCm + Intel iGPU**, all wired up via CDI so containers can
  see the hardware without you fighting `--device` flags.
- **KVM/QEMU + libvirt + Looking Glass B7** baked into the image, with
  VFIO-PCI passthrough kargs already staged. Hand a discrete GPU to a
  Windows VM and game on it.
- **k3s + Ceph** for when you want to grow the box into a one-node cluster
  without re-imaging.
- **A complete local AI surface**, OpenAI-compatible behind
  `MIOS_AI_ENDPOINT`. Local inference lanes (`mios-llm-light` for the
  everyday models + embeddings, plus gated heavy GPU lanes) feed a multi-agent
  pipeline with PostgreSQL+pgvector memory. Every agent and tool on the system
  targets that one endpoint via `MIOS_AI_ENDPOINT`, so any OpenAI-API-compatible
  editor/CLI client (no vendor lock-in) talks to the same brain.
- **Real security defaults**: SELinux enforcing, fapolicyd deny-by-default,
  USBGuard, CrowdSec sovereign-mode IPS, kernel-lockdown integrity, MOK-
  signed kernel modules. Not the security-theater kind.
- **Global Schemas & TypeScript Safe Routing**: Strict OpenAI JSON Schemas
  (`usr/lib/mios/schemas/`) and TypeScript type-safe discriminated unions
  (`usr/lib/mios/ts/`) ensuring zero-parameter-injection across agent pipelines.
- **Native AI Metadata System**: File-level `AI-hint`, `AI-related`, and
  `AI-functions` are first-class OS metadata, indexed by `usr/libexec/mios/mios-ai-metadata.py`
  into `usr/share/mios/ai/v1/metadata.json` for deterministic tool discovery.
- **Mobile Terminal & Blink Shell Optimization**: Native support for iOS Blink
  Shell with `Shift + Tab` (backtab) pass-through, extended terminal keys (`extkeys`),
  and touchscreen shortcuts (`usr/share/mios/tmux/blink-mobile-keys.tmux.conf`).
- **Rust Static Binary Safety Net**: Security boundaries enforced by static
  Rust binaries (`tools/native/`), capturing secrets via native Linux Keyrings
  and executing system mutations strictly via tokenized `execve` boundaries.

These aren't four separate products bolted together -- they're one system. The
GPU wiring (CDI) is what lets the inference lanes and the passthrough VMs each
claim hardware; the immutable image is what lets the cluster grow a node
in-place; the local AI surface is what turns the workstation into something that
can operate *itself*.

---

## The 30-second elevator pitch for engineers

It's [Universal Blue's `ucore-hci`](https://github.com/ublue-os/ucore) (which
is itself Fedora CoreOS + uCore + HCI tooling) plus a deliberate workstation
layer on top. The whole image is `bootc`-managed -- meaning `/usr` is a
read-only composefs mount, `/etc` gets a 3-way merge across upgrades, and
`/var` survives everything. New release? `bootc upgrade`. Bad release?
`bootc rollback`. No more "the package manager left my system in a state."

Think of it as a workstation flavor of CoreOS / Silverblue with the
hyperconverged bits of Talos / openSUSE MicroOS -- except it's still a
day-to-day desktop you can ship code from, *and* it carries its own local agent
runtime so the OS can drive tools, search the web, manage VMs, and answer
questions without phoning home.

---

## Try it

### Already on a Fedora-bootc-compatible host

```bash
bootc switch ghcr.io/mios-dev/mios:latest
sudo systemctl reboot
```

### From scratch, on Windows

**Canonical entry — `WinKey+R` → paste → Enter → accept UAC:**

```text
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1 | iex"
```

That `irm | iex` shape is the entry contract -- runnable from the
Windows Run dialog, cmd.exe, or any PowerShell session, with no
pre-existing pwsh, ExecutionPolicy override, or manual elevation.
`Get-MiOS.ps1` self-cache-busts on entry (Fastly's 5-min TTL is
invisible to you), self-elevates two-pass (user profile + admin
provisioning), shrinks `C:\` and creates `M:\` at exactly 256 GB
NTFS, installs Podman Desktop, provisions the `MiOS-DEV` podman
machine, clones `mios.git` + `mios-bootstrap` onto `M:\`, then
auto-chains into `/usr/libexec/mios/mios-build-driver` inside
`MiOS-DEV` for the OCI build.

The Windows installer drops the result as a WSL2 distro, a Hyper-V VHDX,
an Anaconda installer ISO, and a qcow2 -- pick whichever fits.

`mios.bat` (in [mios-bootstrap](https://github.com/mios-dev/mios-bootstrap))
is an equivalent shortcut: `WinKey+R` → `mios.bat` (or double-click)
invokes the same `irm | iex` one-liner above. The `irm | iex` shape is
the contract; the `.bat` is one wrapper.

mios.git (this repo) is the system FHS overlay baked into the deployed
image; user definitions in mios-bootstrap.git overlay these factory
defaults at build/install time, with user-set fields taking precedence.
Each prompt auto-accepts the resolved-from-`mios.toml` default after
**90 seconds** idle (set `$env:MIOS_PROMPT_TIMEOUT=0` to disable,
`=1` for fastest unattended).

### From scratch, on Linux

```bash
git clone https://github.com/mios-dev/MiOS.git && cd MiOS
just preflight
just build
just iso       # or: just raw / just qcow2 / just vhdx / just wsl2
```

`just --list` shows every target. `Justfile` is the source of truth for the
Linux side; `mios-build-local.ps1` is the Windows equivalent.

### In a hosted cloud session (Claude Code cloud environment)

A hosted cloud session runs on a fixed Ubuntu VM that cannot be replaced; this repo's devcontainer image (`.devcontainer/Containerfile`, packages from `mios.toml [packages.devcontainer]`) runs inside it, so the session is the same MiOS dev environment as the devcontainer, Codespaces and Cloud Shell. Create the environment once (claude.ai/code, the cloud icon above the message box, **Add cloud environment**), paste the script below into **Setup script**, add the variables, and tick it as the default. The platform runs the script, snapshots the disk, and every later session starts from that snapshot.

**Setup script.** It clones the dev-loop plugin to `/opt/dev-loop` and hands off to its `cloud-fedora-setup.sh`. All the logic lives in that clone, so this text never needs editing, and it always exits 0 because a failing setup script fails every session:

```bash
#!/bin/bash
# MiOS Fedora dev environment + the dev-loop plugin (/dev-loop:*) in every session.
export FEDORA_DEVCONTAINER_REPO=https://github.com/mios-dev/MiOS
export FEDORA_DEVCONTAINER_FILE=.devcontainer/Containerfile
# dev-loop plugin checkout; loaded by CLAUDE_CODE_PLUGIN_DIRS=/opt/dev-loop
if [ -d /opt/dev-loop/.git ]; then
  git -C /opt/dev-loop pull -q --ff-only || true
else
  git clone -q --depth 1 https://github.com/mios-dev/-dev-loop /opt/dev-loop || true
fi
[ -f /opt/dev-loop/skills/dev-loop/scripts/env/cloud-fedora-setup.sh ] &&
  bash /opt/dev-loop/skills/dev-loop/scripts/env/cloud-fedora-setup.sh
exit 0
```

**Environment variables**, set in the same dialog:

| Variable | Value | What it does |
|---|---|---|
| `FEDORA_DEVCONTAINER_REPO` | `https://github.com/mios-dev/MiOS` | Projection mode: the session's Fedora userspace is this repo's devcontainer, built unedited, so it is the one MiOS dev image. Unset, the script builds a generic Fedora image instead. |
| `FEDORA_DEVCONTAINER_FILE` | `.devcontainer/Containerfile` | The Containerfile inside that repo. This is the default; setting it keeps the environment a complete record. |
| `CLAUDE_CODE_PLUGIN_DIRS` | `/opt/dev-loop` | Loads the dev-loop plugin in every session, whatever repo it opens: the `/dev-loop:*` commands, hooks and agents. A cloud session loads plugins no other way. |

Optional, same place:

| Variable | Default | What it does |
|---|---|---|
| `FEDORA_RUNTIME` | `auto` | `auto`, `podman` or `docker`. MiOS is Podman-native: `auto` takes podman when it is installed and Docker only where it is the sole runtime, which is this cloud VM. An explicit runtime that is missing logs an error and builds nothing. |
| `FEDORA_SETUP_BUDGET_S` | `0` (never) | Defers the devcontainer lifecycle prebuild (`miosd`, the root overlay, `/opt/mios/bin`) once this many seconds of the setup have elapsed, so a slow run stays inside the platform's roughly 5-minute snapshot budget. A deferred prebuild is applied later, inside a session, with `bash /opt/dev-loop-fedora/cloud-fedora-setup.sh --lifecycle`. A full run measured 452 s; start with `240` if the environment cache stops building. |
| `FEDORA_DEVCONTAINER_REF` | the repo's default branch | Branch or tag of the repo to clone. |
| `FEDORA_EXEC_USER` | `root` | The user container commands run as. `mios-dev` matches the devcontainer's `remoteUser`. |
| `FEDORA_PROVISION_HOST` | `1` | `0` skips provisioning the VM itself (`agy`, keyring, headless grants, dev-loop skill), which otherwise runs first. |
| `FEDORA_REBUILD` | `0` | `1` forces an image rebuild even when one is cached. |

What every session then has: `mios-dev <cmd>` and `fedora <cmd>` run inside the Fedora image at the same path as on the host; `agy`, `claude`, `gemini` and `copilot` on the host and in the image; the `/dev-loop:*` commands. Sign in to `agy` once per container: `bash /opt/dev-loop/skills/dev-loop/scripts/env/agy-login.sh` prints the URL, then the same command with `--code '<code>'` finishes. The script and every variable are owned by [-dev-loop](https://github.com/mios-dev/-dev-loop) (`skills/dev-loop/references/environment.md`, with the measurements behind each default); this copy is for the operator creating the environment.

---

## How it's actually structured

Most distros hide their layout behind a package manager. 'MiOS' doesn't -- the
**repo root is the deployed system root**. Browse `usr/`, `etc/`, `srv/`,
`var/` here in GitHub and you're looking at exactly where those files land
on a booted system. There's no `system_files/` indirection, no Ansible
playbook materializing things into place. What you see is what gets baked.

The build pipeline is just a `Containerfile` that runs every script in
`automation/[NN]-*.sh` in numeric order. Each script does one thing
(install packages, configure SELinux, render the UKI, generate CDI specs,
etc.) and the numeric prefix encodes execution order. Add a new step? Drop
a new `45-myfeature.sh` next to its peers.

That pipeline is the first half of the system's lifecycle: **build pipeline →
OCI image → `bootc` lifecycle on the host.** The scripts that wire up the AI
plane (the inference lanes, the agent units, the pgvector schema) are just more
numbered steps -- the same mechanism that installs packages also stands up the
brain.

If you want to know what makes a package show up in the image, check
[`usr/share/mios/mios.toml`](usr/share/mios/mios.toml) under
`[packages.<section>].pkgs` -- that's the runtime source of truth,
parsed by `automation/lib/packages.sh` and edited via the configurator
HTML at `/usr/share/mios/configurator/`. Human-readable companion
documentation lives at
[`usr/share/doc/mios/reference/PACKAGES.md`](usr/share/doc/mios/reference/PACKAGES.md).
Want to know what kernel arguments ship? They're in
[`usr/lib/bootc/kargs.d/`](usr/lib/bootc/kargs.d/).

---

## The local AI stack (the "self-hosted agent OS" half)

The AI surface is one of the things 'MiOS' is *for*, so here's the end-to-end
shape. Everything below ships in the image, runs on your hardware, and is
reachable through the single OpenAI-compatible endpoint named by
`MIOS_AI_ENDPOINT`.

- **Inference lanes** -- named by *function*, not by upstream tool:
  - `mios-llm-light` (port key `llm_light`) is the **primary** lane: a `llama.cpp`
    multi-model server fronted by the upstream
    [mios-llm-light](https://github.com/mostlygeek/llama-swap) proxy image
    (`ghcr.io/mostlygeek/llama-swap:cuda`). It auto-swaps the everyday chat /
    reasoning models behind one endpoint, KV-pages each conversation to disk,
    **and** serves embeddings (`nomic-embed-text`, OpenAI-compatible
    `/v1/embeddings`) plus the `mios-opencode` coder model. Its model map is
    [`usr/share/mios/llamacpp/mios-llm-light.yaml`](usr/share/mios/llamacpp/mios-llm-light.yaml).
  - `mios-llm-heavy` (port key `vllm`, served-name `mios-heavy`) is the heavy GPU lane
    (vLLM), gated off by default on VRAM grounds.
  - `mios-llm-heavy-alt` (port key `sglang`) is the alternate heavy lane (SGLang), likewise gated.
  - `mios-llm-worker@` are single-model swarm workers for fan-out.
  These speak the OpenAI/Ollama-compatible API, so any OpenAI-API client talks
  to them unchanged -- but the *inference engine* is `llama.cpp`/SGLang/vLLM, not
  a hosted service.
- **Orchestration** -- the **agent-pipe** (port key `agent_pipe`) is the router/dispatch
  gateway every front-end (Open WebUI, the Discord/chat gateways) talks to; it
  decomposes requests, fans out to agents, and calls tools. Behind it,
  **MiOS-Hermes** (port key `hermes`) is the OpenAI-compatible agent gateway that owns
  sessions, the tool-loop, skills, and browser control; a **prefilter**
  (port key `prefilter`) injects fan-out hints on decomposable prompts.
- **Memory** -- the unified agent datastore is **PostgreSQL + pgvector** (the
  `mios-pgvector` container, port key `pgvector`), holding agent memory, events, tool
  calls, sessions, skills, scratch, and a `knowledge` table of finished Q+A with
  vector recall. `nomic-embed-text` (served by `mios-llm-light`) provides the
  embeddings for that recall.
- **Tools & federation** -- agents call tools over **MCP** and reach other
  agents over **A2A**, and `web_search` is backed by a local **SearXNG**
  (port key `searxng`). The coder peer is served through the **opencode-gateway**
  (port key `opencode_gateway`) as a real `/v1` council member.

The throughline: **inference lanes → agent-pipe/Hermes orchestration → pgvector
memory → MCP/A2A**, all behind `MIOS_AI_ENDPOINT`. Full request/response
contract is in [`usr/share/doc/mios/reference/api.md`](usr/share/doc/mios/reference/api.md);
the agent-facing contract is under [`usr/share/mios/ai/`](usr/share/mios/ai/).

---

## The user-facing knobs

The whole user side is one file:

```
~/.config/mios/mios.toml
```

That's where you set your preferred username, hostname, base image, AI
model, Flatpaks to install at first boot, and any free-form environment
variables you want exported on login. Everything else inherits from the
vendor TOML at `/usr/share/mios/mios.toml` (the canonical SSOT).

```toml
[user]
name     = "you"
hostname = "you-laptop"

[ai]
model = "granite4.1:8b"

[flatpaks]
install = [
  "com.spotify.Client",
  "org.mozilla.firefox",
]

[env]
EDITOR = "nvim"
```

Run `just init-user-space` to seed it from the vendor template; `just edit`
to open it in `$EDITOR`; `just show-env` to see the resolved values.

---

## The architectural laws (the boring but load-bearing bits)

These are the rules every contribution has to obey. They're enforced by
build-time lint and by `automation/99-postcheck.sh`:

1. **USR-OVER-ETC** -- static config lives in `/usr/lib/<component>.d/`.
   `/etc/` is for admin overrides only.
2. **NO-MKDIR-IN-VAR** -- every `/var/` path is declared via
   `usr/lib/tmpfiles.d/*.conf`. Never written at build time.
3. **BOUND-IMAGES** -- every Quadlet image is symlinked into
   `/usr/lib/bootc/bound-images.d/` so it ships *with* the host.
4. **BOOTC-CONTAINER-LINT** -- every build ends with `bootc container lint`.
   Fail the lint, fail the build.
5. **UNIFIED-AI-REDIRECTS** -- every agent and tool targets `MIOS_AI_ENDPOINT`.
   No vendor-hardcoded URLs.
6. **UNPRIVILEGED-QUADLETS** -- every Quadlet declares `User=`, `Group=`,
   `Delegate=yes`. Documented exceptions: `mios-ceph` and `mios-k3s`
   (rationale in their headers).

These laws are what keep the whole-system promise honest: Law 3 is why the AI
containers ship *inside* the image, Law 5 is why every agent and editor resolves
to the one local endpoint, and Law 6 is why the agent plane runs unprivileged.

If you want the deeper dive: [`usr/share/mios/ai/INDEX.md`](usr/share/mios/ai/INDEX.md)
is the architectural contract (agent-facing),
[`usr/share/doc/mios/concepts/architecture.md`](usr/share/doc/mios/concepts/architecture.md)
is the layout, and
[`usr/share/doc/mios/guides/engineering.md`](usr/share/doc/mios/guides/engineering.md)
is the build-pipeline rules.

---

## Where things live

Documentation follows the FHS doc layout (`/usr/share/doc/<pkg>/`) with an
OpenAI-style topical split: `concepts/`, `guides/`, `reference/`, `audits/`.
The agent-facing contract lives under `/usr/share/mios/ai/`.

| Document | What's in it |
|---|---|
| [`usr/share/mios/ai/INDEX.md`](usr/share/mios/ai/INDEX.md) | Architectural laws + OpenAI-compatible API surface (agent contract). |
| [`usr/share/mios/ai/system.md`](usr/share/mios/ai/system.md) | Canonical agent system prompt. |
| [`usr/share/mios/ai/audit-prompt.md`](usr/share/mios/ai/audit-prompt.md) | Read-only audit-mode prompt for any OpenAI-API-compatible agent. |
| [`usr/share/mios/ai/v1/`](usr/share/mios/ai/v1/) | `models.json`, `mcp.json`, `metadata.json` -- per-OpenAI-v1-surface manifests. |
| [`usr/lib/mios/schemas/`](usr/lib/mios/schemas/) | Strict OpenAI-compatible JSON Schemas (`strict: true`, `additionalProperties: false`). |
| [`usr/lib/mios/ts/`](usr/lib/mios/ts/) | TypeScript global schemas, discriminated union action routing, and structural types. |
| [`usr/share/mios/tmux/`](usr/share/mios/tmux/) | Tmux configurations and mobile iOS Blink Shell shortcut presets. |
| [`docs/research/safe-schemas-and-rust-safety-net.md`](docs/research/safe-schemas-and-rust-safety-net.md) | Whole-system type safety, OpenAI wire formats, and Rust keyring safety net. |
| [`usr/share/doc/mios/guides/blink-tmux-mobile-keys.md`](usr/share/doc/mios/guides/blink-tmux-mobile-keys.md) | iOS Blink Shell x tmux Shift+Tab and mobile gesture guide. |
| [`usr/share/doc/mios/concepts/architecture.md`](usr/share/doc/mios/concepts/architecture.md) | Filesystem and hardware layout. |
| [`usr/share/doc/mios/guides/engineering.md`](usr/share/doc/mios/guides/engineering.md) | Build pipeline + shell conventions. |
| [`usr/share/doc/mios/guides/security.md`](usr/share/doc/mios/guides/security.md) | Hardening kargs and posture. |
| [`usr/share/doc/mios/guides/self-build.md`](usr/share/doc/mios/guides/self-build.md) | Build modes (CI, Linux, Windows, self-build). |
| [`usr/share/doc/mios/guides/deploy.md`](usr/share/doc/mios/guides/deploy.md) | bootc + Day-2 lifecycle. |
| [`usr/share/doc/mios/guides/install.md`](usr/share/doc/mios/guides/install.md) | KB ingest recipes (OpenAI-shaped). |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution conventions (root by GitHub convention). |
| [`usr/share/doc/mios/reference/api.md`](usr/share/doc/mios/reference/api.md) | OpenAI-compatible AI surface (full spec). |
| [`usr/share/doc/mios/reference/sources.md`](usr/share/doc/mios/reference/sources.md) | Every external reference, every upstream link. |
| [`usr/share/doc/mios/reference/credits.md`](usr/share/doc/mios/reference/credits.md) | Attribution registry. |
| [`usr/share/doc/mios/reference/licenses.md`](usr/share/doc/mios/reference/licenses.md) | Component licenses. |
| [`usr/share/doc/mios/reference/tree.md`](usr/share/doc/mios/reference/tree.md) | Annotated FHS tree. |
| [`usr/share/doc/mios/audits/`](usr/share/doc/mios/audits/) | Audit reports. |

For LLMs and AI agents arriving at the repo:
[`llms.txt`](llms.txt) and [`llms-full.txt`](llms-full.txt) are the
machine-readable index. [`AGENTS.md`](AGENTS.md), [`CLAUDE.md`](CLAUDE.md),
and [`GEMINI.md`](GEMINI.md) are the per-tool entry-point redirectors at
repo root for tool discovery -- they all defer to
`/usr/share/mios/ai/system.md` (canonical) once the OS is running.

---

## Status

'MiOS' is in active development at `v0.3.0`. The build pipeline is stable,
the image lints clean against `bootc container lint`, and the WSL2 + ISO
paths boot to a working desktop on the developer's daily-driver. The
bare-metal install path works but expects you to know what `bootc switch`
does before you run it.

On the AI side, the migration off the early Ollama/legacy-datastore/Qdrant stack is
complete: inference + embeddings now run on the `mios-llm-light` lane (port key `llm_light`)
with gated heavy GPU lanes, and the unified agent datastore is
PostgreSQL+pgvector. Ollama survives only as an upstream *API-compat reference*
(the lanes speak the OpenAI/Ollama-compatible API) and in historical migration
notes.

Open issues + roadmap live on the GitHub side. PRs welcome -- read
[`CONTRIBUTING.md`](CONTRIBUTING.md) before you push.

---

## License

Apache-2.0. Component licenses for every shipped piece are catalogued in
[`usr/share/doc/mios/reference/licenses.md`](usr/share/doc/mios/reference/licenses.md).

The `'MiOS'` name (capitalized) is a project mark; lowercase `mios` (used in
file paths, package names, env-var prefixes, etc.) is the technical
identifier and free of that constraint.
