<!-- AI-hint: Entry point for GitHub Copilot and AI agents working in the MiOS repo. Frames what MiOS is (an immutable bootc/OCI Fedora workstation that is also a local self-replicating agentic AI OS), points at the canonical agent contract, and lists the build/lint/manifest quick-action commands. The repo root IS the deployed system root.
     AI-related: usr/share/mios/ai/system.md, usr/share/mios/ai/INDEX.md, CLAUDE.md, AGENTS.md, automation/ai-bootstrap.sh, Justfile, mios-bootstrap -->
# 'MiOS' — GitHub Copilot / AI-agent entry point

> _This is the `.github/` redirector for GitHub Copilot and other AI agents
> arriving at the **MiOS** repo. It tells you what the project is, where the
> authoritative agent contract lives, and the few commands that matter for
> build/lint/manifest work. It does **not** redefine identity, posture, or the
> Architectural Laws — those live in the canonical docs below._

## What MiOS is (so this entry point makes sense)

MiOS is one system built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image — boot it,
`bootc upgrade` it like a `git pull`, `bootc rollback` it like a Ctrl-Z) that is
*also* a **local, self-replicating, agentic AI operating system**. The same image
that ships GNOME/Wayland, NVIDIA + AMD ROCm + Intel iGPU via CDI, KVM/libvirt
with VFIO passthrough, and a k3s + Ceph one-node-cluster path also ships a full
local agent stack behind one OpenAI-compatible endpoint.

The throughline of the AI half: **inference lanes → agent-pipe / Hermes
orchestration → PostgreSQL + pgvector memory → MCP/A2A**, all reached through the
single endpoint named by `MIOS_AI_ENDPOINT` (default `http://localhost:8080/v1`).
Local inference runs on the `mios-llm-light` lane (`:11450`, llama.cpp behind the
upstream `mios-llm-light` proxy image) — the everyday models, the `mios-opencode` coder model,
**and** embeddings (`nomic-embed-text`) — with gated heavy GPU lanes
(`mios-llm-heavy`/SGLang, `mios-llm-heavy-alt`/vLLM) for VRAM-permitting work.

That dual nature is why this repo is laid out the way it is: **the repo root IS
the deployed system root.** The `usr/`, `etc/`, `srv/`, `var/` directories here
mirror exactly where files land on a booted host; the `Containerfile` bakes them
in, the build pipeline assembles the image, and the bootc lifecycle carries it
forward. **When you edit a file here you are editing the OS.**

## Your job as an AI agent here

Help **build, lint, and extend the image and its code paths** — not to operate a
running machine. Respect the six **Architectural Laws** (USR-OVER-ETC,
NO-MKDIR-IN-VAR, BOUND-IMAGES, BOOTC-CONTAINER-LINT, UNIFIED-AI-REDIRECTS,
UNPRIVILEGED-QUADLETS); they are the contract that lets MiOS be immutable and
agentic at once. The full statements live in the canonical docs below.

## Where the authoritative contract lives

- **Canonical agent system prompt:** `usr/share/mios/ai/system.md`
  (deployed from `mios-bootstrap`).
- **Architectural Laws + OpenAI-compatible API surface (agent contract):**
  `usr/share/mios/ai/INDEX.md`.
- **Claude Code overlay** (build commands, repo conventions, session rules):
  `CLAUDE.md` at repo root; tool-neutral peer redirectors are `AGENTS.md` and
  `GEMINI.md`. All defer to `usr/share/mios/ai/system.md` once the OS is running.

## Quick actions

The deliverable of a build is the OCI image; `just lint` is the Architectural
Law 4 gate (`bootc container lint`) that image must pass.

- **Validate / build image:** `just build`
- **Re-run lint:** `just lint`
- **Refresh AI manifests:** `just artifact` (wraps `./automation/ai-bootstrap.sh`
  — regenerates directory manifests, syncs the Wiki, rebuilds the RAG knowledge
  base, refreshes env configs; idempotent)

`just --list` shows every target. Configuration SSOT is
`usr/share/mios/mios.toml` (packages, ports, AI lanes, services) — never
hard-code names, ports, or vendor URLs.
