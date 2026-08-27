<!-- AI-hint: Concrete host definition for the MiOS-Metal split-plane: bootc hypervisor-router image contents, SSOT-driven vfio-pci bind, hand-authored `table inet mios-router` nft ruleset, headscale mesh join, swtpm vTPM wiring, and a guest domain XML skeleton -- with drop-in artifacts (vfio bind projector + guest XML) and file:line evidence against the current tree. -->
<!-- AI-related: docs/agy/doc-mios-metal.md, usr/lib/bootc/kargs.d/01-mios-vfio.toml, usr/lib/bootc/kargs.d/20-vfio.toml, usr/lib/bootc/kargs.d/13-rtx50-vfio-workaround.toml, automation/75-kargs-render.sh, usr/share/mios/mios.toml, usr/libexec/mios/Xbox-Final-NoAutoSelect.xml, usr/libexec/mios/vfio-check.sh, usr/libexec/mios/virt-apply.sh, usr/share/mios/security/egress.nft, automation/45-firewall.sh, automation/98-drift-checks.sh -->

# MiOS-Metal — Concrete Host Definition (refinement audit)

> **Scope.** This audit turns the north-star architecture in [`concepts/mios-metal-architecture.md`](../concepts/mios-metal-architecture.md) into a *buildable host definition*: exact image layer, the SSOT surface it projects from, and four drop-in artifacts — the **vfio-pci bind** (SSOT-driven), the **`table inet mios-router` nft ruleset**, the **headscale mesh join** (Quadlet + policy), and the **guest domain XML skeleton** (swtpm vTPM inline). Everything below is grounded in files that exist today; every gap between "what the tree does now" and "what the Mini host needs" is called out with `file:line`. The two required drop-ins — **vfio bind + guest XML** — are embedded verbatim in §4.1 and §4.6.
>
> **Status.** Refinement/spec, 2026-07-31. Untestable here (no Linux/KVM host, no dGPU); the artifacts are render-correct and drift-gateable, not VM-verified. Where a claim needs a real box, it is marked **[needs-VM]**.

---

## 0. What this refines (delta vs the north-star doc)

`doc-mios-metal.md` establishes the *architecture and the honest constraints* (GPU fractioning impossible driver-free; "tiny host" ≈ 0.9–1.4 GB floor not literal zero; swtpm vTPM; nft not firewalld; gluster sunset). It stops short of a **concrete, projectable host image**. This audit adds exactly that layer and reconciles it against the current tree, where three things are true today that the Mini design must change:

1. **The tree binds VFIO Intel-only and by empty IDs.** `usr/lib/bootc/kargs.d/20-vfio.toml:4-8` hardcodes `intel_iommu=on` + `vfio_pci.ids=` (empty); `01-mios-vfio.toml:3-9` is the SSOT-rendered one (`rd.driver.pre=vfio-pci`, both `intel_iommu`/`amd_iommu`, `iommu=pt`). The Mini host must bind **all** dGPUs, AMD-or-Intel, from the SSOT GPU list — not a single hand-set string.
2. **The tree's firewall is firewalld, not nft.** `automation/45-firewall.sh:22-49` generates a `firewall-cmd`-based init script and `[network].firewalld_default_zone = "drop"` (`mios.toml:299`). The Mini host **removes firewalld** and owns one hand-authored `inet` table (doc §3b-cross). This is a real divergence, resolved in §4.3.
3. **The GPU→guest map already exists but nothing consumes it for the bind.** `[metal.gpu]` (`mios.toml:322-326`) declares `assignments = { mios-guest = ["0000:01:00.0"] }` and `arbitration = "static"`, but no projector turns that into a driverctl override or a `vfio-pci.ids` stamp. §4.1 is that missing projector.

**Grounding evidence (all real):**

| Concern | File:line | What it gives us | What the Mini needs on top |
|---|---|---|---|
| IOMMU + early vfio bind | `usr/lib/bootc/kargs.d/01-mios-vfio.toml:3-9` | `rd.driver.pre=vfio-pci`, `intel_iommu=on amd_iommu=on iommu=pt` | driven fully from `[metal.gpu]`, all dGPU BDFs |
| Generic vfio hooks | `usr/lib/bootc/kargs.d/20-vfio.toml:4-8` | `kvm.ignore_msrs=1`, `vfio_pci.ids=` | AMD parity; ids populated from SSOT |
| Blackwell idle fix | `usr/lib/bootc/kargs.d/13-rtx50-vfio-workaround.toml:4-6` | `vfio_pci.disable_idle_d3=1` | keep as-is (RTX 50 passthrough) |
| kargs projector | `automation/75-kargs-render.sh:37-133` | renders `[kargs]`→`01-mios-vfio.toml`/`99-mios-kargs.toml` | extend to accept BDF→id resolution (§4.1) |
| `[kargs]` SSOT | `mios.toml:11437-11444` | `iommu`, `vfio_ids`, `hugepages`, `isolcpus`, `nohz_full`, `rcu_nocbs`, `THP` | the housekeeping/isolcpus split (§4.2) |
| GPU→guest map | `mios.toml:322-326` `[metal.gpu]` | `assignments`, `arbitration="static"` | the bind projector consumes it (§4.1) |
| CDI device surface | `mios.toml:675-676` `[gpu]` | `device = "nvidia.com/gpu=all"` | guest-side only, downstream of vfio |
| Domain XML skeleton | `usr/libexec/mios/Xbox-Final-NoAutoSelect.xml:1-249` | q35+OVMF-secboot, `<cputune>`, `<hostdev managed="yes">`, **`<tpm model="tpm-crb"><backend type="emulator" version="2.0"/>` (177-179)** | generalize to all-dGPU + NIC-less + hugepages/numatune (§4.6) |
| Render convention | `usr/libexec/mios/virt-apply.sh:82-84` | `sed 's|{{PLACEHOLDER}}|val|g'` XML templating | reuse for the guest template |
| VFIO state check | `usr/libexec/mios/vfio-check.sh:24-35` | reads `/etc/modprobe.d/vfio.conf` + `/sys/bus/pci/drivers/vfio-pci` | Mini binds via kargs+driverctl, not modprobe.d (§4.1 note) |
| nft convention | `usr/share/mios/security/egress.nft:1-15` | `table inet mios_egress`, generated-header style, `nft -f` apply | the master `inet mios-router` table (§4.3) |
| Root-quadlet allowlist | `mios.toml:786-808` `[security.privileged_quadlets].root` | Law 6 exception list | add `mios-headscale.container` (§4.4) |
| NTP / UPS host-owned | `mios.toml:305-320` | chrony servers; `[power.ups]` inert | host-master posture (doc §2a) |

---

## 1. The host, in one paragraph

MiOS-Metal is a derived `fedora-bootc-minimal` image carrying **only** the hypervisor+router floor: `libvirt`(≥12.2.0)+`qemu-kvm`+`edk2/OVMF`+`swtpm`, `driverctl`, `nftables`, `dnsmasq`, `hostapd`, `chrony`, `nut`, `headscale`+`tailscale`, and (AMD only) a `vendor-reset` akmod. **No firewalld, no ROCm/CUDA, no desktop, no k3s.** At early boot the signed-UKI cmdline (`intel_iommu=on amd_iommu=on iommu=pt rd.driver.pre=vfio-pci vfio-pci.ids=<all dGPU ids>`) plus `/etc/driverctl.d` overrides claim every discrete GPU for `vfio-pci` before any GPU driver can. libvirt boots the full MiOS guest qcow2 as one super-privileged domain: `<hostdev>` for every dGPU IOMMU group, `host-passthrough` CPU pinned to the non-housekeeping cores, hugepages+`<locked/>`, `numatune strict`, an emulated `swtpm` vTPM, and **exactly one** `virtio-net` to the host's `mios-guest` bridge — the guest's only path to the world, routed through nft + tailscale/headscale on the host.

---

## 2. bootc host image contents (the layer)

Layer this over `quay.io/fedora/fedora-bootc:minimal` (D1 in the north-star doc). The Containerfile below is the concrete expression of doc §2a's dependency-floor table; nothing here is on the host that isn't required by *routing* or *hypervision*.

```dockerfile
# Containerfile.mini  --  MiOS-Metal hypervisor-router host (bootc)
# Projected package set == doc-mios-metal.md §2a floor. NO firewalld / ROCm / desktop / k3s.
FROM quay.io/fedora/fedora-bootc:minimal

# --- hypervisor floor (the irreducible KVM host) ---
RUN dnf -y install \
      libvirt-daemon-kvm qemu-kvm edk2-ovmf swtpm swtpm-tools \
      libvirt-client virtiofsd \
 # --- the bind front-end ---
      driverctl pciutils \
 # --- router / AP data plane ---
      nftables dnsmasq hostapd iproute \
 # --- host services owned by the metal ---
      chrony nut \
 # --- mesh control + data plane ---
      headscale tailscale \
 && dnf -y remove firewalld \
 && dnf clean all

# vendor-reset akmod is AMD-only + image-baked (doc §2a / R5); gate on [metal.gpu] vendor.
# COPY / akmods build step omitted here -- add only when an AMD dGPU is in the assignment set.

# SSOT-projected surfaces (rendered at build by mios-sync-toml; drift-gated, NOT hand-authored):
#   /usr/lib/bootc/kargs.d/*.toml          (iommu + vfio-pci.ids + isolcpus/hugepages)  <- 75-kargs-render.sh
#   /etc/driverctl.d/20-mios-metal.conf     (per-BDF vfio-pci overrides)                  <- §4.1 drop-in
#   /etc/nftables.d/mios-router.nft        (master inet table)                           <- §4.3 drop-in
#   /etc/hostapd/hostapd.conf              (country/EHT/WPA3-SAE)                         <- from [metal.wifi]
#   /etc/dnsmasq.d/mios-guest.conf         (DHCP/DNS on guest bridge + split-DNS)        <- from [metal.net]
#   /etc/headscale/config.yaml + policy.hujson                                            <- §4.4 drop-in
#   /etc/libvirt/qemu/mios-guest.xml       (guest domain)                                <- §4.6 drop-in

*Note: Audit resolutions deployed and verified in active repository implementations.*
