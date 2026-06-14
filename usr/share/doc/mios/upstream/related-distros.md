<!-- AI-hint: Provides a comparative analysis of MiOS against sibling Universal Blue images and other atomic/immutable distributions to define MiOS's specific positioning as a single immutable bootc/OCI Fedora image that is also a complete local, agentic AI operating system for the HCI workstation-server hybrid.
     AI-related: mios-dev -->
# Related Distros — Comparison Context

> **Purpose.** This doc situates MiOS within the immutable-OS landscape so a
> reader can answer one question: *given the existing atomic/bootc distros, why
> does MiOS exist and what is it for?* It is positioning context — not a build or
> deploy guide. For the base-image lineage see `upstream/ucore-hci.md`; for the
> bootc model see `upstream/fedora-bootc.md` and `upstream/bootc.md`.
>
> **Audience.** Anyone evaluating MiOS against a sibling distro, or deciding
> which atomic OS fits a workload.

## What MiOS is (the thing being compared)

MiOS is one product built two ways at once:

1. **An immutable, bootc/OCI-shaped Fedora workstation.** The entire OS is a
   single container image (`FROM ghcr.io/ublue-os/ucore-hci:stable-nvidia`). You
   boot it, `bootc upgrade` it like a `git pull`, and `bootc rollback` it like a
   Ctrl-Z. It ships GNOME/Wayland, NVIDIA + ROCm + iGPU acceleration via CDI,
   KVM/libvirt with VFIO passthrough (Looking Glass), and a k3s + Ceph
   one-node-cluster path — the HCI workstation-server hybrid posture.
2. **A local, self-replicating, agentic AI operating system.** The same image
   ships a full local agent stack behind one OpenAI-compatible endpoint: the
   **agent-pipe** orchestrator (`:8640`) fronting the **MiOS-Hermes** gateway
   (`:8642`), **PostgreSQL + pgvector** (`:5432`) as the unified agent memory,
   and three local **inference lanes** — `mios-llm-light` (the primary llama.cpp
   lane on `:11450`, which also serves embeddings) plus the gated heavy lanes
   `mios-llm-heavy` (SGLang, `:11441`) and `mios-llm-heavy-alt` (vLLM). MCP
   exposes the tool surface; A2A federates peer agents.

No mainstream atomic distro ships both halves in one image. That gap is the whole
reason for this comparison: the sibling images below each cover *part* of what
MiOS is, and the purpose of this doc is to make the boundary explicit.

## Sibling Universal Blue images

MiOS is `FROM` ucore-hci, so its closest relatives are the other Universal Blue
spins of the same Fedora/ucore foundation. They diverge by intended workload.

| Image | Spin | Use case | URL |
| --- | --- | --- | --- |
| Bluefin | GNOME developer workstation | conventional dev desktop, devcontainer focus | <https://github.com/ublue-os/bluefin> |
| Aurora | KDE | KDE-preferred workstation | <https://github.com/ublue-os/aurora> |
| Bazzite | Gaming/handheld | Steam Deck-class, HTPC | <https://github.com/ublue-os/bazzite> |
| ucore | Server/HCI base | self-hosted infra | <https://github.com/ublue-os/ucore> |
| **MiOS** | **HCI workstation+server hybrid + local agentic AI OS** | **immutable workstation with a built-in local agent stack** | <https://github.com/mios-dev/MiOS> |

MiOS sits closest to ucore / ucore-hci, then extends it: a GNOME desktop plus
KVM/VFIO passthrough, k3s, and Ceph (the workstation-server hybrid), *and* the
self-hosted local AI plane (agent-pipe + Hermes + pgvector + the inference lanes)
on top. The sibling spins stop at the OS; MiOS continues into the agent stack.

## Other immutable / atomic distros

Beyond the Universal Blue family, MiOS shares the broader "atomic OS" idea — an
indivisible, versioned, rollback-capable root — with these projects. The
distinction that matters for MiOS is whether the root is a true **OCI image**
(what bootc upgrades/rolls back, and what every Architectural Law is written to
keep deterministic).

| Distro | Backend | OCI image? | Notes |
| --- | --- | --- | --- |
| Fedora Silverblue | rpm-ostree | no (rpm-ostree refs) | GNOME, predecessor of bootc |
| Fedora Kinoite | rpm-ostree | no | KDE Silverblue |
| Fedora bootc | bootc | yes | The lineage MiOS is in |
| CentOS Stream bootc | bootc | yes | Where BIB is published from |
| RHEL image mode | bootc | yes | Red Hat enterprise sibling |
| CoreOS Layering | rpm-ostree | yes (via `coreos.inst.image_url`) | Pre-bootc |
| NixOS | Nix | no (declarative Nix) | Different model — declarative, not image-based |
| Talos | bespoke | yes (Kubernetes-only, API-driven) | No SSH, no shell |
| Flatcar | Container Linux | yes | CoreOS Linux successor |
| Vanilla OS | apx + abroot | yes | Ubuntu-based, dual-root atomic |
| openSUSE MicroOS | btrfs snapshots | no | Btrfs-snapshot-based atomic |

## Why MiOS vs each

Each alternative is excellent at its niche; MiOS is chosen when a single
immutable image must be *all* of: a GPU workstation, a virtualization/HCI host,
and a self-hosted local agentic AI OS. The reasons below trace back to that
dual nature.

| Alt | Why MiOS instead |
| --- | --- |
| Bluefin | Dev-desktop only — no KVM/VFIO passthrough, no Ceph, no built-in local AI/agent stack |
| Bazzite | Gaming-tuned; not provisioned for HCI or the always-on agent plane |
| Silverblue | Pre-bootc (rpm-ostree); harder to run as a pure container image and to carry the bound-image AI stack |
| RHEL image mode | Closed source, requires subscription |
| NixOS | Different mental model (declarative); the MiOS pipeline + bootc lifecycle assume an OCI image |
| Talos | Kubernetes-only; no desktop, no general-purpose workstation, no local user agent surface |
| Flatcar | Server-only; no desktop; smaller package set; no AI plane |

## How this positioning ties back to the system

The comparison is not cosmetic — it explains the design of the rest of MiOS:

- **Choosing OCI/bootc over rpm-ostree or btrfs snapshots** is what makes the
  build pipeline (`Containerfile` → numbered `automation/` phases → bootc
  lifecycle) reproducible, and it is what the Architectural Laws protect:
  USR-OVER-ETC, NO-MKDIR-IN-VAR, BOUND-IMAGES, BOOTC-CONTAINER-LINT keep the
  image deterministic and self-contained so `bootc upgrade`/`rollback` work.
- **Starting `FROM` ucore-hci** (not bare fedora-bootc) is why the NVIDIA,
  libvirt/KVM, and virtualization plumbing the HCI posture needs is already
  present — see `upstream/fedora-bootc.md` §Why-MiOS-doesn't-FROM-fedora-bootc.
- **Going beyond every sibling** is the local AI plane, governed by the two
  AI-facing laws: UNIFIED-AI-REDIRECTS (every agent/tool resolves
  `MIOS_AI_ENDPOINT`, no vendor-hardcoded URLs) and UNPRIVILEGED-QUADLETS (the
  whole agent stack runs least-privileged). That plane is what no other entry in
  these tables ships in-image.

## Cross-refs

- `usr/share/doc/mios/upstream/ucore-hci.md` — the base image MiOS builds `FROM`
- `usr/share/doc/mios/upstream/fedora-bootc.md` — the bootc/Fedora lineage upstream of ucore-hci
- `usr/share/doc/mios/upstream/bootc.md` — the bootc lifecycle model
- `usr/share/doc/mios/concepts/architecture.md` — full MiOS architecture and pillars
