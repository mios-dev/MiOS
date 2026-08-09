<!-- AI-hint: Minimal/Immutable Container-Host + AI-OS Peer Landscape for MiOS.
     AI-related: usr/share/mios/mios.toml, docs/adr/, AGY-TASKS.md -->
# Minimal/Immutable Container-Host + AI-OS Peer Landscape for MiOS

## 1. Direct answer on PodmanOS

**"PodmanOS" is not a real product.** There is no standalone Linux distribution or operating system named "PodmanOS." Podman is a container engine, not an OS ([podman.io](https://podman.io/)). The real OS-shaped artifact in the Podman/containers-team orbit is **`podman-machine-os`** — the customized Fedora CoreOS-based VM image (`quay.io/podman/machine-os`) that `podman machine` boots to provide a Linux kernel for containers on macOS/Windows/Linux, built by [containers/podman-machine-os](https://github.com/containers/podman-machine-os) (Apache-2.0, active, v6.0.1 on 2026-07-08). Any roadmap reference to a distinct "PodmanOS" is a naming artifact and should be closed out. The genuine peers in this family are **podman-machine-os** (the VM image), **[containers/bootc](https://github.com/containers/bootc)** (the substrate tool), and **[Fedora CoreOS](https://fedoraproject.org/coreos/)** (the base) — not a product called PodmanOS.

Note on layer confusion: `podman-machine-os` uses `bootc switch` for in-place OS swaps, so it is structurally the closest cousin to MiOS's rebase mechanic — but it is a throwaway dev-laptop container backend, not a hypervisor-router or AI-OS.

## 2. Landscape matrix

### Podman / containers-team OS efforts

| OS / Project | Substrate | Niche | License | vs MiOS |
|---|---|---|---|---|
| **podman-machine-os** ([repo](https://github.com/containers/podman-machine-os)) | FCOS base; rpm-ostree/ostree compose; in-place via `bootc switch` | The VM image `podman machine` boots for container backend on mac/Win/Linux | Apache-2.0 | Same FCOS+bootc-switch substrate mechanic, but a single throwaway dev VM — no VM orchestration, no /v1 AI plane, no SSOT. MiOS inverts it: host IS the product. **Reference.** |
| **containers/bootc** ([repo](https://github.com/containers/bootc)) | OCI image as transport + ostree-backed atomic deploy; CNCF Sandbox | "The container is the OS" — transactional in-place OS updates | Apache-2.0 / MIT | Not a competitor — MiOS's foundation (built FROM ublue-os/ucore-hci, bootc underneath). Gives nothing on VM routing or AI; MiOS differentiates above it. **Adopt-now.** |
| **bootc-image-builder** → [osbuild/image-builder](https://github.com/osbuild/bootc-image-builder) | osbuild pipeline over bootc/OCI inputs → qcow2/raw/ISO/AMI etc. | Turns a bootc image into installable/bootable media | Apache-2.0 | The standard path to make MiOS-Cat's Ventoy ISO/raw and fill the broken bare-metal leg via `bootc install --transport oci`. **Repo archived 2026-06-18 → point at osbuild/image-builder.** **Adopt-now.** |
| **Podman Desktop bootc extension** ([repo](https://github.com/podman-desktop/extension-bootc)) | Delegates to bootc-image-builder; no OS of its own | GUI to build/test/deploy a bootc disk image | Apache-2.0 | Build/test convenience, not an OS. UX reference for locally validating a MiOS image before writing USB. **Reference.** |

### Fedora-immutable / Universal Blue family + Hummingbird

| OS / Project | Substrate | Niche | License | vs MiOS |
|---|---|---|---|---|
| **uCore-hci** ([ublue-os/ucore](https://github.com/ublue-os/ucore)) | bootc + ostree on FCOS; Ignition first-boot; OCI-native updates | HCI server image: Cockpit/Podman/libvirt + virtualization batteries | Apache-2.0 | **MiOS's literal substrate**, not a competitor. Already delivers minimal-host + Podman/Quadlet + libvirt. MiOS adds SSOT-from-mios.toml, /v1 AI plane, MiOS-Cat/Ventoy. Hypervisor-router thesis inherited here. **Reference.** |
| **Fedora Hummingbird** ([Fedora Magazine](https://fedoramagazine.org/fedora-hummingbird-linux-taking-the-hummingbird-model-to-the-full-os/)) | bootc image mode; read-only root, state in /var+/etc; distroless, no pkg mgr/shell | Near-zero-CVE hermetic full host OS from pinned package lists | FOSS (MIT/Apache mix) | **Most strategically important peer.** Validates the minimal-immutable thesis but its no-shell/no-pkg-mgr distroless model conflicts with MiOS's rich SSOT toolchain + co-resident AI plane. A hardening TARGET/base to track, not drop-in. **Watch.** |
| **Fedora CoreOS** ([site](https://fedoraproject.org/coreos/)) | rpm-ostree/ostree + Ignition; migrating to bootc/dnf-image | Minimal auto-updating container host; ancestor of the lineage | FOSS (MIT/Apache mix) | Genealogical root MiOS descends from (via uCore). Ignition/cloud-fleet oriented; no hypervisor batteries, no AI, no operator SSOT — the "blank skeleton" end. **Reference.** |
| **Bluefin (+DX)** ([site](https://projectbluefin.io/)) | bootc on Fedora Atomic (Silverblue) | Cloud-native GNOME developer workstation; leans into local-AI/ramalama | Apache-2.0 | UBlue sibling aimed at desktop/dev, not headless AI host-router. Loosely ships local-AI tooling but no /v1-as-product, no hypervisor-router, no SSOT. **Reference.** |
| **Bazzite** ([site](https://bazzite.gg/)) | bootc on Fedora Atomic | Gaming desktops/handhelds (Steam Deck, ROG Ally) | Apache-2.0 | Orthogonal (gaming). Proof the UBlue signed-OCI pipeline scales to a polished consumer product — a delivery-polish template for MiOS-Cat. **Reference.** |
| **Aurora** ([site](https://getaurora.dev/)) | bootc on Fedora Atomic (Kinoite) | Zero-maintenance KDE Plasma desktop | Apache-2.0 | KDE sibling; no host/hypervisor/AI overlap. Confirms MiOS occupies the server/hci corner of a well-populated ecosystem. **Reference.** |
| **Fedora Silverblue / Kinoite** ([Atomic Desktops](https://fedoraproject.org/atomic-desktops/silverblue/)) | rpm-ostree/ostree → bootc (Unified Core) | Official immutable desktop editions; upstream of UBlue desktops | FOSS (MIT/Apache mix) | Desktop upstream, not a host/AI competitor. Canonical proof of the immutable-Fedora model MiOS relies on. **Reference.** |

### Flatcar / MicroOS-Aeon / Bottlerocket (alternate immutable substrates)

| OS / Project | Substrate | Niche | License | vs MiOS |
|---|---|---|---|---|
| **Flatcar Container Linux** ([site](https://www.flatcar.org/)) | Ignition + read-only /usr + ChromeOS-style A/B (update_engine, Omaha/Nebraska); sysext; **not** ostree/bootc | Fleet-scale minimal K8s node host (CoreOS Container Linux successor) | Apache-2.0; CNCF Incubating | Closest philosophical peer on "minimal immutable host" but Ignition/Omaha substrate vs MiOS's bootc/OCI lineage. Bare container/K8s node — no AI, no Windows guests. Reference for pkg-manager-free fleet updates + sysext layering. **Reference.** |
| **openSUSE MicroOS** ([site](https://microos.opensuse.org/)) | transactional-update over Btrfs snapshots on RPM; Combustion/Ignition; TPM2 FDE (2026); **not** ostree/bootc/A-B | Immutable rolling micro-service/edge/K8s host (SLE Micro/kubic lineage) | Mixed FOSS (openSUSE/SUSE) | Direct architectural alternative via the RPM+Btrfs-snapshot path — the key substrate divergence from MiOS's OCI/bootc thesis. Adopting it would mean abandoning bootc. No AI plane, no hypervisor-router. **Reference.** |
| **openSUSE Aeon** ([site](https://aeondesktop.github.io/)) | MicroOS substrate + Flatpak + Distrobox | Zero-maintenance immutable GNOME desktop | Mixed FOSS | Overlaps only on immutable-desktop layering (Flatpak/Distrobox on read-only base) — a UX reference for MiOS's liquid-glass shell. Single-user, no AI/VM/SSOT. **Reference.** |
| **Bottlerocket OS** ([repo](https://github.com/bottlerocket-os/bottlerocket)) | Image-based A/B partition flip + **dm-verity** verified root + **TUF-signed** updates; API-only, no shell/SSH; **not** ostree/bootc | AWS's single-purpose K8s/ECS worker node OS | Apache-2.0 / MIT | Most security-locked immutable host; the clearest "API-only appliance" contrast to MiOS's operator-driven mios.toml SSOT + Portal. Its dm-verity + TUF-signed model is a strong reference for MiOS's signed-UKI/greenboot/SBOM goals. AWS-bound, no AI/VM/hypervisor. **Reference (study verified-boot, don't adopt OS).** |

### Talos / Kairos / appliance OSes

| OS / Project | Substrate | Niche | License | vs MiOS |
|---|---|---|---|---|
| **Talos Linux** ([site](https://www.talos.dev/)) | Talos-API (custom); read-only SquashFS in RAM, atomic A/B; declarative machine-config over mTLS gRPC; GPU via signed sysext; **not** bootc/ostree | ~80MB K8s-only appliance, no SSH/shell/pkg-mgr | MPL-2.0 (Omni mgmt = BSL-1.1) | **Sharpest philosophical cousin** — minimal immutable API/SSOT-driven, anti-drift, no-shell. But K8s-ONLY on its own API substrate; VMs only via KubeVirt; no Windows guests, no /v1 AI plane. Reference for appliance-grade immutability + immutable-GPU patterns. **Reference.** |
| **Kairos** ([site](https://kairos.io/)) | OCI-image immutable rootfs + A/B upgrades from registries; cloud-init; BYOI meta-layer; exploring bootc collab | Distro-agnostic framework turning any base into an immutable edge/K8s OS; LocalAI lineage (Di Giacinto) | Apache-2.0; CNCF Sandbox | Closest in spirit to MiOS's "build immutable OS FROM a base image"; LocalAI connection maps to MiOS's /v1 plane. But targets K8s-edge fleets, not a single-node AI+hypervisor appliance; no Windows/SSOT. **Watch.** |
| **k3OS** ([repo](https://github.com/rancher/k3os)) | Alpine userspace + Ubuntu kernel, LinuxKit-style; read-only /usr; **not** ostree/bootc | Minimal single-purpose k3s appliance | Apache-2.0 | **DEAD — archived 2023-12-08, superseded by Elemental.** Historical only; confirms unmaintained substrates get superseded, reinforcing MiOS's bet on live bootc/ublue. **Reference.** |
| **Rancher Elemental** ([docs](https://elemental.docs.rancher.com/)) | Immutable image-based on SLE Micro via elemental-toolkit; A/B; **not** ostree/bootc | Rancher-managed K8s node fleets (k3OS successor) | Apache-2.0 | Shares OS-as-image + declarative-config DNA but tightly coupled to Rancher control plane + K8s node role. No VM/Windows/AI. **Reference.** |

### AI-OS / local-AI-appliance peers

| OS / Project | Substrate | Niche | License | vs MiOS |
|---|---|---|---|---|
| **Harvester / SUSE Virtualization** ([site](https://harvesterhci.io/)) | Immutable transactional host (Elemental/SLE Micro) + KubeVirt + KVM + Longhorn on K3s/RKE2; **not** bootc | Open-source HCI: VMs + containers + storage on bare metal | Apache-2.0 (paid enterprise SKU) | **Most direct hypervisor-router competitor** — VM+container HCI. But heavyweight (full K8s+KubeVirt+Longhorn), cluster-oriented, no /v1 AI plane, no single-file SSOT. MiOS is single-node bootc, AI-first, USB-delivered. **Watch.** |
| **NVIDIA DGX OS** (DGX Spark/GB10) ([docs](https://docs.nvidia.com/dgx/dgx-spark/dgx-os.html)) | Ubuntu 24.04-based, **MUTABLE** (apt/snap); **not** immutable/bootc | Turnkey local-AI appliance: full CUDA/vLLM/NeMo stack on DGX hardware | Proprietary over Ubuntu; hardware-locked | Same end-goal (drop-in vLLM behind OpenAI /v1) but polar-opposite substrate: proprietary, mutable, HW-tied, single-vendor GPU, no immutability/hypervisor/SSOT. The commercial north-star to benchmark AI-plane UX against; not adoptable. **Reference.** |
| **GPUStack** ([repo](https://github.com/gpustack/gpustack)) | Not an OS — orchestrator installing on any host | GPU-cluster LLM serving (vLLM/SGLang/llama.cpp) exposing OpenAI + Anthropic APIs | Apache-2.0 | Not a substrate competitor — a **candidate FOR** the MiOS AI plane. Already does the multi-backend /v1 gateway across mixed GPUs that MiOS hand-rolls. Nothing for host/hypervisor legs. **Watch (adopt-or-borrow for AI layer).** |
| **SanctumOS** ([site](https://sanctumos.org/)) | Not an OS — Python/Letta agent suite on a conventional host | Self-hosted "agentic OS": MCP server, router, agent runtime | Open source (~150 stars) | Different layer entirely: an agent/MCP app that runs ON a host like MiOS. Overlaps only MiOS's MCP-gateway lane, not the OS. Included to disambiguate "AI OS" naming. **Reference.** |
| **Talos Linux** (AI angle) ([site](https://www.talos.dev/)) | (as above) GPU via signed sysext, KubeVirt for VMs | Immutable substrate for local vLLM/inference K8s clusters | MPL-2.0 | Immutable+GPU reference but K8s-only and API-locked (no operator mutation) — opposite of MiOS's tunable SSOT + Portal. **Reference.** |

## 3. Where MiOS sits

MiOS occupies a niche **no confirmed-real peer fully covers**: a *single-node, bootc-immutable, SSOT-defined AI-OS that is simultaneously a Linux+Windows hypervisor-router and a self-hosted OpenAI /v1 AI plane, delivered to commodity hardware by a Ventoy USB (MiOS-Cat)*. Every peer covers at most two of those four legs:

- **Immutable bootc host** — shared with the whole Fedora/UBlue family and its foundation (bootc, uCore-hci).
- **Hypervisor for mixed Linux + Windows VMs** — approached only by Harvester (but cluster-scale K8s+KubeVirt) and uCore-hci's libvirt layer (MiOS's own substrate).
- **Self-hosted /v1 AI plane as the product** — approached only by DGX OS (proprietary/mutable/HW-locked) and, at the app layer, GPUStack.
- **Operator SSOT from one config file + universal USB deploy** — unique to MiOS; no peer has a mios.toml-style single config surface projected + drift-gated across every surface.

### Closest three competitors

1. **Fedora Hummingbird** — the existential thesis-validator. It proves Red Hat is productizing the minimal-immutable-bootc host, but its **distroless (no shell / no package manager)** model directly conflicts with MiOS carrying a rich SSOT toolchain and co-resident AI plane. Treat as a **hardening base/target to converge toward**, not a drop-in — MiOS's differentiators sit *above* it.
2. **Harvester / SUSE Virtualization** — the closest **hypervisor-router** competitor (VM + container HCI, positioned as a vSphere replacement). But it is heavyweight full-K8s+KubeVirt+Longhorn, cluster-oriented, with no AI plane and no single-file SSOT. MiOS wins on single-node simplicity, bootc-native updates, AI-first framing, and USB delivery.
3. **NVIDIA DGX OS** — the closest **AI-appliance** competitor and the commercial north-star for AI-plane UX (turnkey vLLM behind OpenAI /v1). But it is proprietary, mutable Ubuntu, hardware-locked to NVIDIA. MiOS is the vendor-neutral, immutable, commodity-hardware FOSS answer.

(Talos Linux is the sharpest *philosophical* cousin on API/SSOT-driven anti-drift immutability, but it is K8s-only on its own non-bootc substrate — a discipline reference, not a role competitor.)

### Adopt / Watch / Ignore

**Adopt now:**
- **containers/bootc** — already MiOS's foundation; stay on the stable line ([bootc](https://github.com/containers/bootc)).
- **osbuild/image-builder** (ex-bootc-image-builder) — the standard path to generate MiOS-Cat's installer ISO / raw image and fix the bare-metal leg via `bootc install --transport oci`; **repoint tooling since bootc-image-builder was archived 2026-06-18**.

**Watch:**
- **Fedora Hummingbird** — track the distroless convergence question; it could subsume or reframe MiOS's host layer.
- **Harvester** — reference for the hypervisor-router leg at enterprise scale.
- **GPUStack** — evaluate as adopt-or-borrow for the /v1 AI-serving layer instead of hand-rolling.
- **Kairos** — leading pattern for OCI-image OS lifecycle + LocalAI-on-immutable; borrow ideas, stay hypervisor/AI-centric.

**Ignore / reference-only:**
- **"PodmanOS"** — nonexistent; do not treat as a competitor.
- **k3OS** — dead (archived 2023); superseded by Elemental.
- **Bazzite / Aurora / Silverblue / Kinoite** — orthogonal desktop niches; delivery-polish and image-composition templates at most.
- **DGX OS, Bottlerocket, Flatcar, MicroOS/Aeon, Talos, Elemental, SanctumOS, podman-machine-os, Podman Desktop ext, FCOS** — study specific patterns (verified-boot/TUF, sysext, Btrfs-transactional, API-appliance discipline, agent/MCP layering) but none is adoptable as MiOS's OS, and none contests all four of MiOS's legs.

**Bottom line:** MiOS is not competing head-on with any single peer — it is *stacking* a hypervisor-router + self-hosted /v1 AI plane + operator SSOT + universal USB deploy on top of a substrate (bootc/uCore-hci) it shares with a crowded, well-validated immutable-OS ecosystem. Its defensible ground is the **combination**; its principal strategic risk is **Hummingbird** redefining the minimal-host baseline underneath it, and its principal build accelerators are **osbuild/image-builder** (deploy leg) and **GPUStack** (AI leg).