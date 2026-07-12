<!-- AI-hint: Roadmap and research synthesis for MiOS infrastructure updates — hardware-verified overrides for WSL2 iGPU compute, gated heavy-lane (SGLang/vLLM) memory management, GUI/remote-display GPU recovery, dual-personality bootc/wsl-import portability, and agent-standards (MCP/A2A/AGNTCY) alignment. Situates each upgrade within MiOS as a whole: build pipeline -> OCI image -> bootc lifecycle, and inference lanes -> agent-pipe/Hermes -> pgvector memory -> MCP/A2A.
     AI-related: mios-podman-ps, mios-ai, mios-llm-light, mios-llm-heavy, mios-llm-heavy-alt, mios-igpu-server.ps1, mios-computer-use, mios-daemon-agent, mios-agent-pipe, mios-pgvector, podman.socket, console-getty.service -->
# MiOS Upstream-Gap Research + Implementation Plan — 2026-06-07

> **Status (re-baselined 2026-06-13):** This is a living research/roadmap doc. The inference and
> datastore facts below are current as of the migration off the early Ollama/legacy datastore/Qdrant stack:
> local inference and embeddings now run on the **`mios-llm-light`** lane (`:11450`), the heavy GPU
> lanes are **`mios-llm-heavy`** (SGLang, `:11441`) and **`mios-llm-heavy-alt`** (vLLM, `:11440`),
> and the unified agent datastore is **PostgreSQL + pgvector** (`mios-pgvector`, `:5432`). Ollama
> survives only as an *upstream API-compat reference* (the lanes speak the OpenAI/Ollama-compatible
> API). Where a task below still names a retired component in its rationale, that is historical
> record — the *action* is described against the current lane/service identities.

## What this doc is, and where it sits in MiOS

MiOS is one thing built two ways at once: an **immutable, bootc/OCI-shaped Fedora workstation** (the
whole OS is a single container image — boot it, `bootc upgrade` it like a `git pull`, `bootc rollback`
it like a Ctrl-Z) that is *also* a **local, self-replicating, agentic AI operating system**. The same
image that ships GNOME/Wayland, NVIDIA+ROCm+iGPU via CDI, KVM/libvirt with VFIO passthrough, and a
k3s+Ceph one-node-cluster path also ships a full local agent stack behind one OpenAI-compatible
endpoint (`MIOS_AI_ENDPOINT`).

This document is the **forward-looking infrastructure roadmap** for that whole system. It asks, across
five surfaces, where MiOS's *current* design has drifted from what upstream now makes possible, and it
sequences the moves that close the gap — while protecting the parts that already work. Each surface
maps onto one stage of the MiOS lifecycle or one plane of the agent stack:

- **Compute topology** (Waves 0, 2) — the **inference lanes** that feed the brain: `mios-llm-light`
  (primary, `:11450`), the gated heavy lanes `mios-llm-heavy`/`mios-llm-heavy-alt`, and the native iGPU
  lane. *Purpose: more local FLOPs per watt, fewer cross-host hops, a heavy/VLM lane that unblocks
  computer-use.*
- **Image & lifecycle** (Waves 1, 4) — the **build pipeline → OCI image → bootc lifecycle** itself:
  Podman/Quadlet hardening, `.wslconfig`/image hygiene, dual-personality (bootc + `wsl --import`)
  portability, offline atomic upgrades, supply-chain signing. *Purpose: keep the "one image, anywhere,
  offline, atomic, rollback-able" promise honest.*
- **GUI / remote display** (Wave 3) — how the immutable desktop is *seen* across the WSLg-over-RDP wall.
  *Purpose: recover the GPU the current software-rendered desktop leaves idle.*
- **Agent standards** (Wave 5) — the wire protocols underneath the agent plane: MCP for tools, A2A for
  agents, AGNTCY for federation/identity, durability for crash-resume. *Purpose: replace bespoke
  plumbing (the source of the recurring narrate-instead-of-call failures) with open standards.*

The connective tissue is unchanged: a user request flows from a front-end into the **agent-pipe**
orchestrator (`:8640`), which refines and fans it out; **MiOS-Hermes** (`:8642`) is the
OpenAI-compatible gateway and tool-loop agent; **pgvector** is the unified memory; the **inference
lanes** do the generation and embeddings; **MCP/A2A** expose tools and federate peers. Every task below
is justified by how it serves that throughline, and every retirement is gated so we never rip out a
load-bearing piece on an unverified assumption.

---

Synthesis of a 5-stream deep research pass (WSL2/g+GPU, bootc/image-mode, Podman/Quadlets,
AIOS/agent-standards, GUI/offline-serving) against the live MiOS architecture. Every claim is
versioned/dated in the source streams. Tasks are ordered by **impact × (1/effort) × confidence**,
with **verification gates** because several findings *overturn standing MiOS assumptions* and must be
hardware-confirmed before we rip anything out.

Legend: **[VERIFY]** gated on a probe · **conf:H/M/L** confidence · **eff:S/M/L** effort.

---

## 0. Headline findings — three of these overturn core MiOS assumptions

| # | Finding | Status vs MiOS memory |
|---|---------|----------------------|
| A | **AMD/Intel iGPU compute now works *inside* WSL2.** AMD shipped **ROCDXG** (`librocdxg`, ROCm 7.2.1 + Adrenalin 26.2.2, production Mar 2026, **incl. Strix/Strix Halo APUs**); Intel ships **Level Zero/OpenCL/OpenVINO** — both route GPGPU through the same `/dev/dxg`/DXGKRNL paravirt path NVIDIA uses. | **OVERTURNS** `gpu_igpu_compute_topology` ("AMD/Intel iGPU CANNOT compute in WSL"). Hardware-dependent → **[VERIFY]**. |
| B | **The gated heavy lane is NOT VRAM-blocked.** `--gpu-memory-utilization ~0.15–0.3` + **KV-cache CPU offload** (vLLM 0.22.1 native; SGLang 0.5.12 HiSparse) runs a quantized heavy/VLM lane in the ~4 GB the Windows host leaves on the 4090. | **OVERTURNS** the "heavy-lane VRAM-blocked" note in `gemma4_planner_deploy` / AIOS memories. **[VERIFY]** cheap. *(MiOS already serves `mios-llm-heavy` (SGLang, `:11441`) live; the alternate `mios-llm-heavy-alt` (vLLM, `:11440`) stays gated.)* |
| C | **WSLg-over-RDP cross-session rendering is STILL unfixed** (wslg#471/#1456 open; #1440 new regression). KasmVNC stands — but **Selkies (WebRTC+NVENC)** is a GPU-accelerated upgrade over KasmVNC/llvmpipe. | **CONFIRMS** `mios_gui_remote_display`; adds a better bypass. |
| D | **bootc-in-WSL is architecturally blocked** (no upstream fix; Build 2026 `wslc` is a Docker-Desktop replacement, *not* OS-image import). `bootc upgrade/switch` refuse to run in WSL ("requires a booted host system"). | New constraint → formalize **dual-personality image**. |
| E | **Podman rootful-socket drop-in + CDI auto-refresh** obsolete two MiOS hacks (the `mios-podman-ps` snapshot timer and manual GPU-CDI regen). | New, clean upstream wins. |
| F | **Standards drift**: MCP `2026-07-28` (stateless Streamable-HTTP, structured tool output, elicitation, sampling, MCP Apps), A2A **v1.0** + signed cards, **AGNTCY** OASF/Directory/Identity, durable-execution gap. | MiOS AHEAD on integration, BEHIND on wire-protocol + identity + durability. |

Also re-baseline: live WSL ceiling is **2.7.8 / kernel 6.18** (memory still assumes ~1.0.73.2 / 6.6).
**Memory correction:** `microsoft/WSL#40618` is the `/mnt/shared_memory` COPY-MODE init race, **not** the
VAIL cross-session limit (that's wslg#471/#1456). Fix the cross-reference in `mios_gui_remote_display`.

---

## Wave 0 — VERIFY the overturning claims (gates Waves 2-3) · eff:S

Cheap probes before committing engineering. Nothing is retired until these pass. *(These guard the
compute-topology plane: an unverified iGPU/heavy-lane claim must not be allowed to delete a working
lane the agent-pipe depends on.)*

- **T0.1 [VERIFY] iGPU-in-WSL compute.** Identify the actual iGPU SKU. If AMD Strix/Strix Halo →
  install Adrenalin 26.2.2 + ROCm 7.2.1 + ROCDXG in the WSL distro, run `torch.cuda.is_available()`
  / a HIP smoke test. If Intel Arc/11–14th-gen → Level Zero + a `clinfo`/OpenVINO probe. **Gate:** a
  real matmul executes on the iGPU *inside* the VM. **Watch:** the `.wslconfig memory=` VRAM cap on UMA
  APUs (ROCm#6022) — pool is capped by VM memory, not full UMA; needs kernel ≥6.18 (WSL 2.7.5+). conf:M
- **T0.2 [VERIFY] heavy lane in ~4 GB.** Launch vLLM 0.22.1 (or SGLang 0.5.12 HiSparse) with
  `--gpu-memory-utilization 0.2` + KV-CPU-offload on a small quantized model against the partially-occupied
  4090. **Gate:** serves an OpenAI-compatible completion without OOM while the Windows host holds ~20 GB.
  *(SGLang already validated live as `mios-llm-heavy` :11441; this gate covers the `mios-llm-heavy-alt`
  vLLM path before un-gating it.)* conf:H
- **T0.3 Re-baseline WSL.** Record live `wsl --version`/kernel; confirm ≥2.7.5 (6.18) so T0.1/coopmat2
  prerequisites hold. Set the stage for `sparseVhd`/`autoMemoryReclaim` (T1.3). conf:H

---

## Wave 1 — Low-risk, high-value wins (no hardware dependency) · eff:S–M

These harden the **image & lifecycle plane** — the Quadlets and host wiring that make the agent stack
ship *inside* the immutable image (Laws 3, 6) and start deterministically.

- **T1.1 Retire the `mios-podman-ps` snapshot hack with the rootful-socket pattern.** Add a
  `podman.socket` drop-in (`SocketMode=0660`/`SocketUser=root`/`SocketGroup=podman`) + a
  `/etc/tmpfiles.d/podman-rootful.conf` (`d /run/podman 0750 root podman`), add the agent-pipe service
  user to the `podman` group, point agent-pipe at `unix:///run/podman/podman.sock`. Kills the
  15-min-stale JSON snapshot + name-matching; gives live inspect data regardless of host-net.
  **Security caveat:** rootful socket = root-equivalent. Podman has **no scoped/read-only socket mode**
  (upstream gap). Decision: grant **read/inspect via group only** and keep writes off the agent user, OR
  keep a thin root read-proxy for least-privilege. Make this an explicit operator call, route through
  `mios.toml` (honors Law 6 UNPRIVILEGED-QUADLETS posture). conf:H eff:S
- **T1.2 CDI + `nvidia-cdi-refresh` → rootless GPU quadlets.** Install nvidia-container-toolkit **≥1.18.0**
  in the image (gets the `nvidia-cdi-refresh` service that auto-regens `/var/run/cdi/nvidia.yaml` on
  driver/reboot — obsoletes any manual regen). The inference-lane quadlets (`mios-llm-light`,
  `mios-llm-heavy`, `mios-llm-heavy-alt`) already pass the dGPU in via CDI
  (`AddDevice=nvidia.com/gpu=all`); finish the hardening by moving any remaining privileged/
  `NVIDIA_VISIBLE_DEVICES=all` shapes to CDI with `no-cgroups=true` + `--group-add keep-groups`, running
  **rootless** under their pinned service UIDs. Hardens the highest-attack-surface services. conf:H eff:M
- **T1.3 `.wslconfig` + image hygiene.** Set `sparseVhd=true` + tune `autoMemoryReclaim` (coordinate
  `memory=` with the T0.1 ROCm pool sizing). Add a **`/mnt/shared_memory` tmpfs pre-mount** systemd/tmpfiles
  boot hook (insurance vs the #40618 COPY-MODE invisible-window class). Adopt upstream's
  **`console-getty.service` mask** (multi-distro getty fix). All via SSOT, not literals (Law-adjacent:
  `mios.toml` is the single source of truth). conf:H eff:S
- **T1.4 `Notify=healthy` + HealthCmd across AI quadlets.** Replace hand-managed `After=` ordering for
  agent-pipe / `mios-llm-light` / `mios-llm-heavy` / OWUI with real systemd readiness gating +
  rollback-on-failed-health. Pairs with the existing `health_gate` convention that keeps the gated heavy
  lanes inert until reachable. conf:H eff:M

---

## Wave 2 — Compute topology modernization (gated on Wave 0) · eff:M–L

This wave reshapes the **inference-lane plane** that feeds agent-pipe/Hermes. Every retirement here is
gated on a Wave-0 probe so a working lane is never removed on an assumption.

- **T2.1 [VERIFY-gated on T0.1] Collapse the native-Windows iGPU server into an in-VM lane.** If T0.1
  passes, stand up an in-VM ROCm/Level-Zero iGPU lane and plan retirement of `mios-igpu-server.ps1` (:11436)
  + its Tailscale hop + the consolidated CPU/iGPU reasoner overlay node — removes a cross-host dependency.
  Keep the Windows-native server as fallback until the in-VM lane is proven under load. (The iGPU node ships
  with an EMPTY endpoint in vendor `mios.toml` for privacy; the tailnet IP is set in `/etc/mios`.) conf:M eff:M
- **T2.2 [gated on T0.2] Activate the alternate heavy + VLM lane.** Run a quantized heavy lane in the
  partial 4090 (low gpu-mem-util + KV-CPU-offload). MiOS already serves `mios-llm-heavy` (SGLang, `:11441`,
  HiCache CPU KV-offload) — this task un-gates the `mios-llm-heavy-alt` vLLM path (`:11440`,
  PagedAttention+APC) and, on either lane, **unblocks computer-use:** serve **Qwen3-VL** or **UI-TARS** for
  the `mios-computer-use`/`verify_launch` visual probe (validate grounding accuracy — Qwen3-VL
  pixel-grounding is reportedly weak; UI-TARS may ground better). The vision-grounding GGUF can also be
  served on `mios-llm-light` (`:11450`) once provisioned (see `mios-llm-light.yaml`'s `qwen3-vl:4b` entry).
  Re-enable the gemma4 planner heavy path this frees. conf:H eff:M
- **T2.3 llama.cpp RPC fabric + coopmat2.** Run an `rpc-server` per lane/node (phone/iGPU/dGPU/cluster);
  agent-pipe targets one logical RPC endpoint for models too big for any single lane — maps directly onto
  the existing `[agents.*.nodes.*]`/`[nodes.*]` binding, no Ray/K8s. Verify **coopmat2** is active on the
  Vulkan lane (~4.4× prefill on a 4090). Heed the upstream caveat: only worth RPC when a model doesn't fit
  one lane. conf:M eff:M
- **T2.4 Track WSL 3 (NPU passthrough).** Build-2026 preview = near-native GPU+NPU passthrough but
  Copilot+/NPU-only (Snapdragon X, Meteor/Lunar Lake; AMD dGPU deferred). Research-only watch item; opens an
  NPU-resident small-model lane MiOS has no story for. conf:M eff:S(watch)

---

## Wave 3 — GUI / remote-display upgrade (GPU recovery) · eff:M

This wave addresses how the immutable desktop is *seen* — the WSLg-over-RDP wall confirmed in
`mios_gui_remote_display`. None of these touch the WSLg problem itself; they bypass it and recover the GPU
the current software-rendered (llvmpipe) desktop leaves idle.

- **T3.1 Selkies (WebRTC + NVENC) desktop lane.** Replace/augment KasmVNC/llvmpipe with **Selkies** (→v2.0,
  PixelFlux Wayland mode): browser-native over Tailscale, NVENC hardware encode on the in-WSL 4090, audio,
  low-latency. Recovers the GPU the current llvmpipe desktop leaves idle — *without* touching the WSLg
  problem. **Neko** is the lighter single-app/browser option. conf:H eff:M
- **T3.2 Session-owning Wayland endpoint.** For the "what WSLg-over-RDP can't do" case, run
  **gnome-remote-desktop v50 headless** (owns its own session, sidesteps cross-session compositing) OR a
  per-app **gamescope/cage → Selkies** pipe. Spike **waypipe-over-vsock** to forward individual flatpak GUIs
  out of the WSL VM, bypassing WSLg's RDP path entirely. conf:M eff:M
- **T3.3 Flatpak OCI sideloading into the bootc image.** Flatpak 1.17 `--sideload-repo=oci-archive:` /
  `install --image oci-archive:` is the clean offline fit for MiOS's all-OCI worldview — bake flatpaks as
  oci-archives into the image, register a local sideload repo at firstboot (replaces flathub-at-build / baked
  ostree repo). Add a firstboot check reconciling the in-image `GL.nvidia` extension version vs the host WSL
  driver (version-pin hazard). conf:M eff:M

---

## Wave 4 — Portability: dual-personality image + offline upgrades · eff:L

This is the **image & lifecycle plane** at its hardest edge. The "one bootc image runs anywhere including
WSL" goal collides with a hard upstream wall (Finding D). Formalize the split so the system keeps its
atomic/rollback promise on bare metal *and* still runs in WSL.

- **T4.1 Dual-personality image.** (a) True **bootc** image for bare-metal/VM; (b) the *same* OCI layers
  exported as a **flat rootfs imported via `wsl --import`** where bootc is dormant and **MiOS owns the update
  mechanism** (re-import / overlay swap), since `bootc upgrade` is inoperable in WSL. Build a `rootfs-export →
  wsl --import` pipeline with `/etc/wsl-distribution.conf` + `wsl.conf` (`systemd=true`, default user). Keep
  the agent-plane services as Quadlets so they're byte-identical across both personalities (Law 3
  BOUND-IMAGES guarantees the AI containers ship inside both). conf:H eff:L
- **T4.2 bootc bare-metal profile + offline atomic upgrades.** Produce qcow2/raw/iso/vmdk/ami via
  **bootc-image-builder** (note: **no WSL/tar.gz output** — osbuild/bootc-image-builder#172 open; that's the
  rootfs-export gap T4.1 fills). Wire the **air-gapped upgrade flow**: local registry mirror (MiOS already runs
  a Forge/`mios-forge` registry) or `skopeo copy … oci:/usb` → `bootc switch --transport oci` →
  `bootc upgrade --apply`. Exploit **soft-reboot** for non-kernel updates (seconds of agent-plane downtime);
  split kernel vs userspace deltas. Watch zstd:chunked bugs (#509). conf:H eff:L
- **T4.3 Logically Bound Images for the agent stack.** Bind the agent stack — `mios-agent-pipe`, the
  inference lanes (`mios-llm-light`/`mios-llm-heavy`/`mios-llm-heavy-alt`), `mios-searxng`, `mios-pgvector`,
  `mios-adguard` — as LBI (`/usr/lib/bootc/bound-images.d` + `additionalimagestore=/usr/lib/bootc/storage`)
  so they version + pre-stage atomically with the OS image instead of runtime pulls — directly advances
  "fully offline" and is the natural evolution of Law 3 (BOUND-IMAGES). Mind the storage.conf GC footgun +
  b-i-b LBI disk-gen bug (#691). conf:M eff:M
- **T4.4 Supply chain + hardening, scoped by target.** cosign-sign MiOS images + ship `policy.json`
  (`sigstoreSigned`, attachments-in-image = no lookaside, fits offline); self-verify-on-pull in the WSL update
  path (bootc won't). Add `UserNS=auto` to rootful quadlets (per-container UID isolation). Bake **NVIDIA akmods
  at build time** per kernel (the `ostree-booted`-skipped driver problem) for bare-metal. Treat **composefs-sealed
  UKI + Secure Boot** as bare-metal-only future (experimental, UEFI-only — **not** a WSL dependency). conf:M eff:L

---

## Wave 5 — Agent-standards alignment (MiOS AHEAD on integration, BEHIND on wire/identity/durability) · eff:M–L

This wave hardens the **agent plane's wire protocols** — MCP for tools, A2A for agents, AGNTCY for
federation/identity, durability for crash-resume. The throughline goal: replace bespoke plumbing with open
standards to kill the recurring narrate-instead-of-call / fabrication failures, and let the agent-pipe/Hermes
loop discover and federate instead of reading hardcoded overlays.

- **T5.1 MCP `2026-07-28` adoption in the three-projection verb SSOT.** Stateless Streamable-HTTP
  (`_meta`-carried capabilities, no session handshake) + mandatory `Mcp-Method`/`Mcp-Name` routing headers
  (fits MiOS's Tailscale-serve fronts); **structured tool OUTPUT schemas (JSON Schema 2020-12)** — project
  output shapes, not just inputs, to attack the recurring narrate-instead-of-call / fabrication failures;
  **elicitation** (server→client ask-mid-call, the missing HITL primitive); **sampling** (verbs delegate
  sub-reasoning to the council); **MCP Apps** sandboxed-iframe UIs (natural fit for Portal/OWUI thinking-blocks);
  a **local/private MCP Registry + `.well-known` Server Cards** so agents discover internal servers via standard
  discovery instead of the hardcoded `mcp.json` overlay. conf:H eff:M
- **T5.2 A2A v1.0 + signed cards.** Upgrade the published card from 0.3.0 to **v1.0.0 / `a2a.proto`** shape;
  add **AgentCardSignature** (JWS over JCS-canonicalized card); map swarm/DAG node status onto the standard task
  states (SUBMITTED/WORKING/INPUT_REQUIRED/AUTH_REQUIRED); add standard **push notifications**
  (`TaskStatusUpdateEvent` webhooks). MiOS keeps its **AHEAD** edge: live inter-agent reasoning streaming via
  `GET /a2a/contexts/{id}`. conf:M eff:M
- **T5.3 AGNTCY OASF + self-hosted Agent Directory + Agent Identity (highest-leverage federation move).**
  Replace the hand-maintained `mcp.json`/`a2a-peers.json` overlays with a **local, syncable OASF-described Agent
  Directory** (OASF natively models both A2A agents and MCP servers) — advances the P1→P3 federation roadmap and
  honors the no-hardcode SSOT rule. Adopt **DID-based Agent Identity** (closes the open agent-identity gap;
  prerequisite to safely consuming external peers; pairs with T5.2 signed cards). conf:M eff:L
- **T5.4 Durability + replay + sleep-time memory (biggest robustness gap).** Event-source the swarm/DAG
  (Temporal-style local event history → crash-resume) — fixes the in-memory-progress-loss exposed by past
  runaway-AI / wedged-deploy incidents. Add a **sleep-time memory-consolidation agent** (drop-in for the idle
  CPU-pinned `mios-daemon-agent`) that rewrites memory blocks during downtime (Letta sleep-time compute), backed
  by the pgvector `agent_memory`/`knowledge` tables. Adopt an explicit **Memory-Block** abstraction over raw
  pgvector rows/embeddings. Formalize `_admit` against the ArXiv "Agent Control Protocol" (static risk score +
  stateful trace signals + ledger). conf:M eff:L
- **T5.5 Standardized HITL.** Implement the open "P3 HITL queue" via standards — **MCP elicitation (SEP-2322)**
  + **A2A `INPUT_REQUIRED`/`AUTH_REQUIRED`** task states — not bespoke plumbing. conf:M eff:M
- **T5.6 Confirm ACP is dead.** ACP merged into A2A under the Linux Foundation (Aug 2025); IBM winding it down.
  No action beyond confirming the existing memory note — do **not** build an ACP client. conf:H eff:S

---

## Confidence & caveats

- **Source quality:** WSL/bootc/standards facts are primary-sourced (GitHub releases, Microsoft/Red Hat docs,
  spec SEPs). Some Podman 2026-dated items lean on secondary blogs corroborated against primary release tags;
  AMD-iGPU-CDI and podman-bootc-on-Windows specifics were thin → flagged low-confidence.
- **Biggest reality-gap vs the MiOS pitch:** "one bootc image runs anywhere *including WSL*" is upstream-blocked.
  The honest architecture is the **dual-personality** model (T4.1). Don't market WSL bootc atomicity it can't deliver.
- **Hardware-gated:** Wave 2's iGPU collapse (T2.1) is the single most impactful simplification but depends
  entirely on the actual iGPU SKU passing T0.1. Verify before retiring `mios-igpu-server.ps1`.

## Suggested sequencing

Wave 0 (probe) → Wave 1 (bank the no-risk wins in parallel) → Wave 2 (compute, gated) → then choose:
Wave 3 (GUI/GPU recovery) and Wave 5 (standards) are independent and can interleave; Wave 4 (portability) is
the largest and can run as a background track. Each wave maps to existing MiOS principles: offline-first,
no-hardcode `mios.toml` SSOT, and the six Architectural Laws (USR-OVER-ETC · NO-MKDIR-IN-VAR · BOUND-IMAGES ·
BOOTC-CONTAINER-LINT · UNIFIED-AI-REDIRECTS · UNPRIVILEGED-QUADLETS) that keep the image both immutable and
agentic at once.
