<!-- AI-hint: Standard operating procedure for MiOS R14 maturity review — verifying the sibling unit suites, producing the OCI image + disk artifacts via the Justfile, and the operator-gated signing (cosign/Secure Boot) and release (tag + publish) workflows that ship a bootc-upgradeable image.
     AI-related: /usr/lib/mios/agent-pipe/server.py, mios-build-local, mios-dev, mios-ai, mios-agent-pipe, mios-agent-pipe.service -->
# MiOS maturity + release runbook (R14)

## Purpose and scope

MiOS is one system built two ways at once: an **immutable, bootc/OCI Fedora
workstation** (the whole OS is a single container image — boot it, `bootc upgrade`
it like a `git pull`, `bootc rollback` it like a Ctrl-Z) that is *also* a **local,
self-replicating, agentic AI operating system**. The same image that ships
GNOME/Wayland, GPU acceleration via CDI, KVM/libvirt with VFIO passthrough, and a
k3s+Ceph one-node-cluster path also ships a full local agent stack behind one
OpenAI-compatible endpoint.

This runbook is the **release-engineering view of that whole**: how a verified
working tree becomes a signed, upgradeable image. It closes the **docs** slice of
the R14 maturity-review gaps and documents the operator-gated steps that close the
**signing** and **release** slices. It sits at the end of the lifecycle the repo
encodes — *build pipeline → OCI image → bootc deploy/upgrade/rollback* — and tells
an operator (or Claude Code, which builds the image but does not operate the running
machine) exactly which steps are automatable and which require the operator's keys.

Sourced from the repo (`Justfile`, `CLAUDE.md`, the T26 naming-refactor plan) —
anything an operator must confirm for their environment is marked
**(operator-confirm)**. Precise build targets, ports, and paths are grounded in the
live files; do not substitute invented values.

## 1. Current maturity state (verified 2026-06-13)

| Gap | Status |
|---|---|
| **tests** | Sibling unit suites under `usr/lib/mios/agent-pipe/test_mios_*.py` — **9 suites green** (`sched`, `evict`, `hitl`, `aci`, `pg`, `kvfork`, `codemode`, `stress`, `launch`). The `pg` suite covers the PostgreSQL + pgvector agent datastore. Run: `for t in test_mios_*.py; do python3 "$t"; done`. |
| **docs** | This runbook + `usr/share/doc/mios/` (concepts/reference/guides) + the AIOS/standards plan docs. |
| **headless/server posture** | Supported via the layered config SSOT — `usr/share/mios/profile.toml` `[desktop]` plus `mios.toml` quadlet gating and the systemd service-gating conventions (`ConditionVirtualization`, optional `enable … || true`). A bare-server deployment turns off GNOME/remote-desktop while leaving the inference + agent stack on. There is no separate profile file; the same `mios.toml` overlays drive it. |
| **signing** | **OPEN — operator-gated** (§3). |
| **release (tag + artifacts)** | **OPEN — operator-gated** (§2/§4). |

## 2. Build artifacts (Linux, inside the dev VM `podman-MiOS-DEV`)

The deliverable of every build is the **OCI image** — the entire booted OS — and,
optionally, disk artifacts cut from it. The final step of `just build` is
`bootc container lint` (Architectural Law 4); a lint failure fails the build, which
is what keeps the image deterministic enough for `bootc upgrade`/`rollback`.

```bash
just preflight        # system prereq check
just build            # OCI image (ends with `bootc container lint` — Law 4)
just verify-images    # smoke-test output/ artifacts
just sbom             # CycloneDX SBOM via syft (artifacts/sbom/mios-sbom.json)
# Disk/installer artifacts (need MIOS_USER_PASSWORD_HASH + MIOS_SSH_PUBKEY for qcow2/vhdx):
just iso              # Anaconda installer ISO
just raw / qcow2 / vhdx / wsl2 / all
```

> ⚠️ **Disk hazard (lived 2026-06-07):** a `--no-cache` full image build filled the
> 256 GB **M:** drive and corrupted the dev VM. Do **not** run a no-cache full build
> on the size-capped M: drive; prune (`podman system prune` + `buildah rm --all` +
> `fstrim`) before large builds. Windows host: `.\mios-build-local.ps1` (full OCI
> build + rechunk + disk images + GHCR push).

## 3. Signing — **(operator-gated; keys are the operator's)**

Signing is what makes the bootc lifecycle trustworthy: a signed image lets
`bootc upgrade` verify provenance, and Secure Boot enrollment lets the signed
kernel/modules load on the booted host.

1. **OCI image signing** (supply-chain): sign the pushed image with the project's
   cosign key — `cosign sign ghcr.io/mios-dev/mios@<digest>` **(operator-confirm
   key/registry creds)**. bootc can then verify the signature on `bootc upgrade`.
2. **Secure Boot / MOK** (kernel + modules): enroll the project MOK so signed kernel
   modules load under Secure Boot — `mokutil --import <MOK.der>` then reboot to
   confirm enrollment **(operator-confirm: MOK key material + physical/enrollment step)**.

Both require key material only the operator holds; the assistant cannot and must not
fabricate or self-execute them.

## 4. Release (tag + publish) — **(operator-gated)**

```bash
git -C /path/to/mios tag -a vX.Y.Z -m "MiOS vX.Y.Z"
git -C /path/to/mios push origin vX.Y.Z
# then publish the verified, SIGNED image + artifacts to the registry/release
```

Push/publish are outward-facing + use operator credentials → operator executes. Once
the signed image is published, a deployed host moves to it with `bootc switch` /
`bootc upgrade`, and any regression is reverted with `bootc rollback` — the whole
point of shipping the OS as one image.

## 5. T26 Phase-3 — global-names migration **(operator-gated)**

The code-side naming refactor (Phases 1–2) is complete (verified: zero rename
targets remain). This is the same convention that retired the old **CloudWS** project
name (every `cloudws-*` artifact is now `mios-<component>`) and renamed the inference
units to function-based identities (`mios-llm-light`, `mios-llm-heavy`,
`mios-llm-heavy-alt`); upstream tool/image names (e.g. `llama-swap`) and the
OpenAI/Ollama-compatible API are kept as legitimate external references.

Phase-3 reconciles the `[services.*]` user/UID SSOT vs reality (e.g.
hermes/agent-pipe → `mios-ai`/850) and is **deferred by design** — its own plan
mandates **additive aliasing first** (keep both, flip canonical later), never in-place
renames of the frozen contract. Closing it needs an **image rebuild + offline
`chown -R` migration** of baked `/var` ownership → operator-gated. See
`usr/share/doc/mios/concepts/naming-refactor-plan.md`.

## 6. Per-change validation gate (every artifact/source edit)

This gate is the inner loop that keeps the working tree always-releasable, so any
verified commit can flow straight into §2–§4:

`py_compile` `server.py` + siblings · run the sibling unit suites · `tomllib`
`mios.toml` + kargs · `bash -n` touched scripts · deploy agent-pipe via
`wsl cp .../server.py /usr/lib/mios/agent-pipe/server.py` + `systemctl restart
mios-agent-pipe.service` (import-check before restart). Live changes are reversible
(`.bak` + git).

## Appendix — where this fits in the system

The release pipeline ships the **whole MiOS image**, including the local AI plane
this runbook's tests exercise. For reference, the agent stack the `pg`/`kvfork`/etc.
suites validate runs behind one OpenAI-compatible endpoint (`MIOS_AI_ENDPOINT`,
Architectural Law 5):

- **agent-pipe** (`:8640`) — orchestrator: router + refine + council/swarm fan-out +
  critic/polish; fronts MiOS-Hermes for every gateway.
- **MiOS-Hermes** (`:8642`) — OpenAI-compat agent gateway + tool loop; **MiOS-Prefilter**
  (`:8641`) injects delegation on fan-outable prompts.
- **MiOS-LLM-Light** (`:11450`) — primary local inference (llama.cpp behind the
  `llama-swap` proxy image), multi-model auto-swap + KV-cache paging; also serves
  embeddings (`nomic-embed-text`, OpenAI-compat `/v1/embeddings`) and the
  `mios-opencode` coder model. **MiOS-LLM-Heavy** (SGLang, `:11441`) and
  **MiOS-LLM-Heavy-Alt** (vLLM) are gated/off-by-default (VRAM).
- **MiOS-PGVector** (`:5432`) — PostgreSQL + pgvector, the unified agent datastore
  (agent_memory, event, tool_call, session, skill, scratch, knowledge, sys_env,
  kanban, …); accessed via `mios-pg-query` / `mios-db --pg`. **MiOS-Search** (SearXNG,
  `:8888`) backs `web_search`; **MiOS-OWUI** (`:3030`) is the browser front-end.
- MCP exposes the tool surface and A2A federates peer agents.

The six **Architectural Laws** the image must satisfy — **1 USR-OVER-ETC ·
2 NO-MKDIR-IN-VAR · 3 BOUND-IMAGES · 4 BOOTC-CONTAINER-LINT · 5 UNIFIED-AI-REDIRECTS ·
6 UNPRIVILEGED-QUADLETS** — are documented in full in `CLAUDE.md`; this runbook
enforces Law 4 at build time (§2) and Law 5 across the inference lanes above.
