<!-- AI-hint: MiOS-Field hypervisor and blade architecture (milestone M7): the L0-L3 layer model, sibling L2 VMs on a RAM-resident SystemRescue admin plane, GPU arbitration, session paths, single-live Quadlets, spec corrections, decisions and phases F0-F10. -->
<!-- AI-related: usr/share/mios/mios.toml [field], [metal.gpu], [management_mesh], [blade], [ports], usr/share/doc/mios/adr/0016-blade-node-topology.md, usr/share/doc/mios/adr/0017-blade-workload-mobility.md, .devloop/GOALS.md, tasks.jsonl -->
# MiOS-Field hypervisor and blade architecture

A blade boots a RAM-resident SystemRescue hypervisor from the MiOS-Field USB. That hypervisor is the
admin plane. It runs sibling VMs: MiOS VMs, one of which is the users' graphical seat, and `mios-xbox`,
the Windows gaming VM. Services run as Quadlets, with exactly one live instance of each anywhere in the
fleet.

- **Status:** design for milestone M7 in `.devloop/GOALS.md`. The work is tracked under the M7 epic in
  `tasks.jsonl`.
- **Inputs:** the operator's MiOS-Field specification and the clarifications of 2026-10-09.
- **Diagrams:** the MiOS Topology Atlas, <https://claude.ai/artifact/3NcyFYkcsskVpfp4KurUoA>, is the one
  master page:
  - Part I holds Maps 1–7;
  - Part II covers D1, the GPU arbiter, the session paths and the flightpath;
  - Part III covers the spec check and the M7 roadmap.
- **Ports and keys:** ports are named by their `[ports]` key, with the value at the time of writing in
  parentheses. Tables are named, never restated.

## 1. Layers

| Layer | What it is | Who uses it |
|---|---|---|
| **L0** | The hardware: CPU, RAM, the discrete GPU (dGPU), the seat GPU, NICs, the IP-KVM. | — |
| **L1** | SystemRescue running from RAM (`copytoram`): the admin hypervisor. The installed alternative is MiOS-Metal (decision D2). | Admins only |
| **L2** | Sibling VMs on L1: one or more MiOS VMs (one of them the seat VM `mios`), and `mios-xbox`. | Users (the seat VM); gamers (`mios-xbox`) |
| **L3** | Quadlets: the services and servers. Any MiOS on L2 can host them, including the WSL2 MiOS inside `mios-xbox`. | Users and agents, through the services |

The spec's earlier names map as follows: Tier 1 is L1. Tier 2 is the L2 seat VM `mios`. The Tier 3
"MiOS services" are L3 Quadlets. The Tier 3 "MiOS-Xbox" is the L2 sibling `mios-xbox`.

### Operator rulings, 2026-10-09 (binding)
1. **The seat VM is the management layer.** The L2 VM `mios` is the management layer, and users
   interact with it directly and graphically. The Looking Glass client, kvmfr and Sunshine run there.
2. **L1 is the admin plane.** Local admins use it directly. Remote admins reach it through IP-KVMs
   (PiKVM) on the separate admin mesh, `[management_mesh]` (`wg-ipkvm`). That mesh is never folded
   into Headscale.
3. **L1 has a TUI.** MiOS-tmux plus the mios monitor, shipped as static Rust inside the SystemRescue
   module (SRM). It starts VMs, attaches to them and consoles into them. No user session runs on L1.
4. **The L2 VMs are siblings on L1** (decision D1). `mios-xbox` is not nested inside `mios`.
5. **Every MiOS VM runs a full, equivalent MiOS image**, and every image carries the full set of
   Quadlets and embedded layers. This includes the WSL2 MiOS inside `mios-xbox`. Any L2 can therefore
   take over any service.
6. **One live instance per Quadlet.** Across L2 and the fleet, each Quadlet has exactly one live
   instance. Every other copy is paused as a standby, and a paused copy takes over on failure, either
   locally or on a remote blade.
7. **Core services may be promoted.** A core service or module may move up a layer, from an L3
   Quadlet to a native unit of an L2 full image. Only services on an SSOT-declared list may do this.
8. **Hardware pressure sets the VM count.** The number of MiOS VMs on L2 follows CPU, RAM and GPU
   headroom.
9. **MiOS is self-hostable.** It hosts its own Forgejo (git, OCI registry and CI runner), builds
   itself, signs and publishes locally, and `bootc`-upgrades every MiOS it runs. It also hosts
   Headscale, CephFS, k3s and the AI plane. No external service is required. MiOS can also be its own
   L1 (MiOS-Metal, decision D2).

## 2. Components

**L1: admin hypervisor (MiOS-Field live)**
- **Base:** SystemRescue, version floating with an SSOT floor (13.02, linux 6.18.41 at the time of
  writing), built by `miosd artifact-build field-hypervisor`. The module (SRM) carries qemu-desktop,
  libvirt, edk2-ovmf, swtpm, dnsmasq, bridge-utils and the static Rust admin TUI.
- **What it owns:** IOMMU and VFIO, NUMA placement, the bridges, one swtpm per guest, and the IVSHMEM
  shared-memory file that the L2 siblings map.
- **Kernel arguments:** rendered from `[metal.gpu]`. They are the IOMMU switches, the vfio-pci claim
  for the dGPU by class selector, `kvm.ignore_msrs`, and nested virtualization. Nesting is needed
  because the WSL2 MiOS inside `mios-xbox` is a Hyper-V VM inside a KVM guest.
- **ACS override:** `pcie_acs_override` defeats IOMMU group isolation. It is a per-box opt-in in SSOT,
  never a default.
- **Early VFIO:** an initcpio hook, `driver_override`, and `modprobe.d` softdeps that load vfio-pci
  before the amdgpu, nvidia and nouveau drivers. All three are rendered from the same selectors.
- **Existing assets:** `[field]`, `[field.sysrescue]`, and `usr/share/mios/ventoy/` (the SystemRescue
  GRUB and syslinux entries, `ventoy.json`, and the autorun first-boot script). The launchers
  (`MiOS-Field.*`, `get_sysrescue_ver.ps1`) live in mios-bootstrap's `field/` (Law 15).

**L2 MiOS VMs (the seat VM `mios`, and further VMs by hardware pressure)**
- **Image:** the published MiOS image as a qcow2, built from the digest by `miosd artifact-build qcow2`.
- **Shape:** CPUs, NUMA node, RAM, seat GPU and VM count come from a new `[blade.mediator]` table. The
  guest budget stays `[metal].guest_cpu_percent` and `guest_ram_percent`; `[blade.mediator]` divides
  that budget and does not restate it.
- **Seat VM:**
  - the desktop on the seat GPU (decision D5);
  - the Looking Glass client and kvmfr (`automation/68-bake-kvmfr.sh`,
    `automation/69-bake-lookingglass-client.sh`);
  - Sunshine (`mios-sunshine.container`);
  - the ttyd and Hermes dashboard consoles;
  - the Headscale client;
  - the guest half of the GPU arbiter.

**L2 `mios-xbox`**
- **Image:** Windows 11 LTSC from UUP Dump with DISM, the MiOS-Xbox builder path.
- **Platform:** OVMF with Secure Boot, swtpm TPM 2.0, virtio-win, and the IVSHMEM driver.
- **Graphics:** the Looking Glass host app, and the dGPU over one VFIO hop from L1.
- **Settings and debloat:** from mios-bootstrap's `[autounattend]`, `[autounattend.uup_convert]` and
  `[autounattend.xbox]`, plus the edition's `autounattend.debloat_profile`.
- **WSL2 MiOS:** a full MiOS image inside the guest, which hosts L3 Quadlets like any other L2 MiOS.

**L3 Quadlets**
- **Placement:** every L2 MiOS carries every Quadlet. Placement decides which copy is live, and the rest
  stay paused.
- **Moves:**
  - a local move between L2s on one L1 is pause-here, resume-there;
  - a cross-blade move uses the fleet path (section 6).
- **Promotion:** a core service may run as a native unit of the L2 image instead of a Quadlet.
  - **The list:** no key names promotable services today. The nearest are:
    - `[blade.requires]`, which maps a unit to capabilities;
    - `[blade].seat_side`, the units a seat runs;
    - `[profiles.core]`, the core image: SSOT, miosd, agent-pipe, the datastore and the verbs.
  - **Proposal:** one list key, `[blade].promotable`, beside `seat_side`. Each entry must be a
    `[blade.requires]` unit inside the core profile.
  - **The gate:** it fails on any other entry, and on any placement that promotes an unlisted Quadlet.

## 3. Data and control paths

**dGPU.**
- **At boot:** L1 binds the dGPU to vfio-pci, by class selector.
- **Holders:** it is attached by one VFIO hop to exactly one L2 at a time. That is the MiOS VM running
  the heavy inference lane, or `mios-xbox` while a game runs.
- **The seat GPU** goes to the seat VM and never moves.

**Frames.**
1. In `mios-xbox`, the Looking Glass host app writes frames to an IVSHMEM device.
2. That device is backed by a shared-memory file on L1.
3. The seat VM maps the same file as an `ivshmem-plain` device.
4. kvmfr exposes it as `/dev/kvmfr0`.
5. The Looking Glass client shows it in a window on the seat.

No network and no port are involved. The file size comes from SSOT and is rendered into both the L1
domain and kvmfr's `static_size_mb`, which `usr/lib/modprobe.d/kvmfr.conf` hard-codes today.

**Two meshes, never routed to each other.**

| | Admin mesh | Blade mesh |
|---|---|---|
| SSOT | `[management_mesh]`: interface `wg-ipkvm`, its subnet, listen port and IP-KVM backends | `[metal.mesh]` (tailnet `vnet_cidr`), `[headscale]`, `[blade.mesh]` |
| Coordinator | none (static WireGuard peers) | Headscale on `[ports].headscale` (8085) |
| Members | L1 instances, IP-KVMs, admin workstations | L2 VMs, the services they host, users' devices |
| Never | an L2 VM or a user device | L1 |

**L2 to L1 control.** The GPU arbiter's request to move the dGPU goes from the MiOS VM to L1 over
virtio-vsock. It is a single verb with no IP path, so no user network reaches L1 (F6 settles the exact
shape).

## 4. Dynamic GPU arbitration

Today `[metal.gpu].arbitration` is `"static"`. The value `"dynamic"` enables the state machine below.
It needs no `[ports]` key: `[ports].arbiter` (8760) is the policy arbiter, a different component.

| State | Entered when | The arbiter does | On failure |
|---|---|---|---|
| AI | Boot, or a return completes | The dGPU sits in the MiOS VM; `llm-heavy` holds it through CDI | — |
| Draining | A gaming request | vLLM sleep mode (`/sleep`); agent-pipe routes `/v1` to `[ports].llm_light` (8500) | Wake and stay in AI |
| Released | The drain completes | Unbind the guest driver; L1 detaches the device from the MiOS VM | Re-attach, rebind, wake → AI |
| Gaming | The detach completes | L1 attaches the device to `mios-xbox` and starts or hot-plugs the guest | Detach, re-attach to the MiOS VM → AI |
| Returning | The guest exits or is stopped | Detach from `mios-xbox`, attach to the MiOS VM, rebind, `/wake_up`, restore `[ports].llm_heavy` (8520) routing | Retry once, then leave the dGPU on vfio-pci in L1 and raise an alert |

Two invariants hold throughout:
- No transition leaves the dGPU attached to two guests.
- No transition leaves `/v1` unanswered: the light lane serves throughout.

Running `llm-heavy` inside the WSL2 MiOS of `mios-xbox` while a game runs is co-tenancy. It is not part
of this machine.

## 5. Session paths

| Path | Who | Network | Reaches |
|---|---|---|---|
| Seat | A local user | none | The seat VM desktop on the seat GPU, with `mios-xbox` in a Looking Glass window |
| Stream | A remote user | Blade mesh | Sunshine in the seat VM, encoding on the seat GPU, to Moonlight |
| Consoles | A user or an agent | Blade mesh, HTTPS | `[ports].ttyd_bash` (8310), `[ports].ttyd_powershell` (8320), `[ports].hermes_dashboard` (8210) |
| Local admin | An admin at the box | none | The L1 TUI |
| Remote admin | An admin | Admin mesh | The IP-KVM (power, virtual media, pre-boot video), then the L1 TUI over SSH |

Once every GPU is bound to vfio-pci, L1 has no display of its own. The L1 TUI must therefore stay
reachable over SSH on the admin mesh and over a serial console. The display that serves the local
console is part of decision D5.

## 6. Fleet, mobility and self-hosting

These sections build on two ADRs and do not restate them:
- [ADR-0016](../../usr/share/doc/mios/adr/0016-blade-node-topology.md): what a blade, a node and a seat
  are, and the plane ownership.
- [ADR-0017](../../usr/share/doc/mios/adr/0017-blade-workload-mobility.md): two schedulers, degrade
  instead of refuse, local-first failover, anti-flap, and per-class divergence.

The values live in `[blades]` (fleet size), `[blade.archetypes]`, `[blade.placement]`,
`[blade.collapse]`, `[blade.reconcile]`, `[blade.fencing]` and `[blade.uplink]`.

**The roster.** The spec's blades B0–B5 are one example at `[blades].max_nodes`. Each blade's role is an
archetype, and the per-blade assignment is operator data.

**The single-live lease.** For Quadlets, use a k3s Lease (coordination.k8s.io) per Quadlet:
- Under ADR-0017 D1, k3s owns containers. A Lease is only a lock, so Pacemaker stays with VMs.
- The holder runs and the other copies stay paused.
- A holder that cannot renew pauses itself before the lease expires.
- Pacemaker `clone-max=1` is the alternative if the operator prefers it.

**The flightpath** moves an L2 VM to another blade, using ADR-0017 D1's VirtualDomain live migration.
It is new: ADR-0017 does not define it.
1. **Detach:** flush I/O, checkpoint the delta to CephFS, leave the bridge.
2. **Transit:** a direct WireGuard peer-to-peer path on the blade mesh.
3. **Attach:** refuse an architecture mismatch, join the bridge, mount CephFS, resume.

Safe migration needs fencing (`[blade.fencing]`) on any fleet larger than one node.

**Egress.**
- **Exit gateways:** each blade has one. Provider and region are SSOT data under `[blade.uplink]`.
- **Policy routing:** an nftables table, plus a translocation controller that changes the exit region
  without changing workload addresses. `[security.egress]` remains an allowlist, which is a different
  concern.
- **Background:**
  [mesh topology and WireGuard backbone](../../usr/share/doc/mios/concepts/mesh-topology-and-wireguard-backbone.md).

**Sandboxes**, from lightest to heaviest:
1. bwrap with Landlock;
2. rootless crun;
3. a krun microVM where `/dev/kvm` exists (ruling Q18);
4. a full KVM/VFIO guest on L1.

eBPF enforcement with Tetragon is decision D3.

**Self-hosting.** A blade needs nothing outside the fleet:
- **Forgejo on `[ports].forge_http` (8400)** holds git, the OCI registry and the CI runner.
- **Every MiOS updates from it:**
  - M5 self-build produces the image;
  - the signing ruling (Q4) signs it by digest;
  - `bootc` upgrades every MiOS from the local registry: L1 MiOS-Metal, the L2 VMs, the WSL2 MiOS, and
    cloud.
- **The fleet services run on the blades:** Headscale, CephFS, k3s and the AI plane.

## 7. The spec against the SSOT and upstream

| The spec says | Verified, or the SSOT says |
|---|---|
| Tier 1/2/3; nested or sibling | L0–L3, with sibling L2 VMs (operator, 2026-10-09). |
| IP-KVM folded into Headscale | It is the separate `wg-ipkvm` admin mesh in `[management_mesh]`. |
| SystemRescue 13.02, linux 6.18.41 | Confirmed against the upstream changelog. Released 2026-08-01. |
| ISO SHA-256 `f4b238a2…` | Upstream publishes `ad4d670b…6e7572`. Per [ADR-0003](../../usr/share/doc/mios/adr/0003-sbom-not-hardcode.md), the build reads the `.sha256` file and records it in the SBOM. Nothing is pinned. |
| `sysrescue-customize --recipe-chroot … --pack` | The real CLI is `--auto --source --dest --recipe-dir`, with the steps `iso_delete`, `iso_add` and `build_into_srm`. Packages ship as an SRM. |
| fs-verity checks `copytoram` | SystemRescue's own checksum boot option verifies the copy. fs-verity belongs to the MiOS image. |
| `vfio-pci.ids=10de:2484,10de:228b`, `0000:01:00.0` | These come from `[metal.gpu]` class selectors, and every consumer is rendered from them (Law 7). |
| LocalAI; `management_listen = "0.0.0.0:8642"` | LocalAI was removed, and the AI plane is OpenAI `/v1` only. 8642 is allocated to `[ports].field_live_chat` (8642), though unbound. Management binds a `[ports]` key on the blade mesh, never `0.0.0.0`. |
| `[ports].arbiter` (8760) for the GPU arbiter | That key is the policy arbiter. The GPU arbiter uses vsock and a local socket, with no port. |
| B1 compute on :8780 | That is `[ports].opencode_gateway` (8780), a loopback `/v1` shim, not a compute port. |
| `[blade.placement]` holds CPUs/NUMA/RAM; `[blade.reconcile]` holds auto-start/GPU policy | Both tables exist with other meanings: scheduler routing, and partition rules. The VM shape goes in a new `[blade.mediator]`. |
| Sunshine encodes with NVENC | It encodes on the seat GPU, never on the guest's dGPU. |
| `[xbox_features]`, `[debloat]` | Neither exists. The data is in mios-bootstrap's `[autounattend*]` tables and the edition key `autounattend.debloat_profile`. |
| "ADR-0017's flightpath" | ADR-0017 defines schedulers, failover and divergence. The three-phase flightpath is new. |
| Laws OFFLINE-FIRST, SPEC-DERIVED-TRUTH, DEGRADE-OPEN, DYNAMIC-ORDINALS | `[laws]` is canonical: 7 NO-HARDCODE, 8 SSOT-PROJECTION, 12 BAKE-NOT-FETCH, 16 ONE-TEMPLATE-PER-TYPE. |
| Law 3: every sidecar baked into `/usr/lib/bootc/storage` | Ruling Q1: sidecars are baked into the full image only. |
| An 11-phase Containerfile | `[legibility].max_automation_phases` governs the phase count. |
| Archetypes, reconcile rules, k3s + Pacemaker placement, sbd fencing | These already exist in `[blade.*]`. |
| Cilium Tetragon sensors | Not in MiOS today: decision D3. |
| A 4-tier sandbox ladder | bwrap and rootless crun ship. krun is ruling Q18. KVM/VFIO comes from L1. |

## 8. Decisions

- **D1, dGPU path. Resolved: siblings.** `mios-xbox` runs beside the MiOS VMs on L1. The dGPU crosses
  one VFIO hop and frames cross an IVSHMEM file on L1. The rejected nested layout needed two hops and
  a vIOMMU in the seat VM. Source: the operator's topology drawing, 2026-10-09.
- **D2, L1 flavours.** Should L1 be MiOS-Field live (SystemRescue, nothing installed) and MiOS-Metal
  installed (bootc MiOS as its own L1), sharing the L2 and L3 contracts?
  - The operator has said MiOS can be its own L1.
  - Still open: whether both ship, and which is the default.
- **D3, Tetragon.** Should MiOS adopt Cilium Tetragon for in-kernel enforcement, killing `execve` on
  protected paths?
  - Options: adopt it on L1 and the L2 MiOS VMs; adopt it on L2 only; defer it.
  - Evidence: an existing Tetragon task in `tasks.jsonl`, and
    [eBPF semantic enforcement](../../usr/share/doc/mios/concepts/ebpf-semantic-enforcement.md).
- **D5, seat GPU source.** Where does the seat VM's GPU come from?
  - Options:
    - the iGPU passed through VFIO, which leaves L1 no display;
    - an SR-IOV virtual function (Intel Xe iGPUs);
    - a second discrete card.
  - The answer also decides the L1 local-console display.
- **D4** is not carried in this roadmap.

## 9. Phases (milestone M7)

Each phase lands through tasks under the M7 epic. Every task carries a positive control and a
planted-defect control.

| Phase | Deliverable | Today |
|---|---|---|
| F0 | Decisions D1 (resolved), D2, D3, D5 | — |
| F1 | **L1 image:** `[field.hypervisor]` plus `miosd artifact-build field-hypervisor`, driving `sysrescue-customize --auto`; the version floats with an SSOT floor; the SHA-256 is recorded in the SBOM; a QEMU boot test (kvm and vfio loaded, libvirtd active, checksum passing). Plus the static Rust admin TUI in the SRM. | `miosd artifact-build` for bootc-image-builder formats |
| F2 | **MiOS-Field integration:** the version floor from SSOT in the launchers; the hypervisor Ventoy entry rendered from SSOT and mirrored to mios-bootstrap (Law 15) | the launchers, `[field.sysrescue]`, the SystemRescue GRUB entry |
| F3 | **Admin plane:** L1 joins `wg-ipkvm` at boot; the TUI is reachable only there; IP-KVMs are declared per blade; no route between the meshes | `[management_mesh]`; the IP-KVM task, reopened |
| F4 | **Early VFIO on L1:** class selectors; the initcpio hook, `modprobe.d` softdeps and kernel arguments, all rendered | `[metal.gpu]`; `mios-metal-vfio-gen` only echoes variables |
| F5 | **L2 MiOS VMs:** `[blade.mediator]`; libvirt domains generated from SSOT; the seat on the seat GPU; the VM count from hardware pressure | the qcow2 artifact path |
| F6 | **GPU arbiter:** the section 4 state machine, native, tested with mocked sysfs and QMP | `[metal.gpu].arbitration` |
| F7 | **Seat sessions:** Looking Glass across siblings; Sunshine on the seat GPU; consoles on the blade mesh only | the kvmfr and Looking Glass bakes, ttyd, Sunshine |
| F8 | **`mios-xbox` and L3:** the Windows sibling; Quadlet placement and local moves; the single-live lease and its gate; core promotion | the MiOS-Xbox builders |
| F9 | **Fleet:** the flightpath; egress gateways; reconcile tests; the sandbox ladder; an offline self-hosted blade | ADR-0016/0017, `[blade.*]`, Forgejo |
| F10 | **Projection:** this document's `[ports]` citations, and the Atlas's port and table labels, are checked against SSOT by a drift gate | — |
