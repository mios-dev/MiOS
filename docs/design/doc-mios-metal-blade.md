<!-- AI-hint: MiOS-Metal: Blade Substrate Implementation Design.
     AI-related: usr/share/mios/mios.toml, docs/adr/, AGY-TASKS.md -->
# MiOS-Metal: Blade Substrate Implementation Design

*Doc-ready synthesis for MiOS DOCS. Every component below is a confirmed-real, upstream RHEL/Fedora or established FOSS project; disposition and verification caveats from source scouting are carried through into §5.*

The MiOS-Metal blade is the **inner rim** of the tire/wheel: a deliberately minimal, immutable substrate/router/AP host that owns hardware and the network layer and passes ~75–80% of compute plus all non-network hardware to the **outer-tread workloads**. Its design principle is *a handful of resilient bash/systemd commands built from as many upstream RHEL/Fedora components as possible*, so the identical blade drops onto bare metal or a VPS.

---

## 1. The Blade Deploy

The blade is not configured by a config-management daemon — it is **installed from an OCI image** and finished by **one declarative first-boot data file**. Two commands stand it up; everything after is data.

### 1.1 Install the immutable substrate (one command)

The MiOS OCI image installs *itself* as an ostree-immutable host. Run from inside the running container image:

```bash
podman run --rm --privileged --pid=host \
  -v /var/lib/containers:/var/lib/containers -v /dev:/dev \
  <mios-image-ref> bootc install to-disk /dev/DISK
```

- **[bootc](https://github.com/bootc-dev/bootc)** (Apache-2.0) extracts the kernel from `/usr/lib/modules/$kver/vmlinuz`, lays down the root fs, invokes `bootupd` for the bootloader, sets Discoverable-Partition-Spec types, and points day-2 updates back at the source image ref. `to-filesystem` does the same into a pre-mounted root (the VPS-blade path, where Anaconda or the cloud image owns storage layout).
- **Why:** this *is* the blade bring-up — no bespoke installer, and the resulting ostree immutability is precisely what makes the blueprint's sudo-disabled runtime safe.
- **Constraints:** requires `--privileged` + host `/dev` and `/var/lib/containers` binds; uses the **host** kernel, not the container's; cannot retrofit onto a running conventional system; the image must declare a default root fs type via `/usr/lib/bootc/install/00-<osname>.toml`; authenticated registries need pull secrets in `/etc/ostree/auth.json`. `to-disk` is officially framed as a demo for the `to-filesystem` flow.

**Fleet / bare-metal variants (same payload, different medium):**
- **[bootc-image-builder](https://github.com/osbuild/bootc-image-builder)** (Apache-2.0) converts the one MiOS image into 8 artifact types (qcow2 default, raw, ami, vhd, vmdk, gce, anaconda-iso, pxe-tar-xz) so one build emits the RAW/qcow2 that traverses blades, the ami/vhd for cloud VPS blades, and the anaconda-iso for MiOS-Cat media. **Note:** as of 2026-06-18 the standalone repo was merged into `osbuild/image-builder` and archived — the published container still works; track the new home.
- **[Anaconda](https://github.com/rhinstaller/anaconda) `bootc` kickstart verb** (GPL-2.0-or-later) is the upstream automated bare-metal path — a single kickstart provisions physical blades over PXE/ISO while storage stays in kickstart stanzas and the payload is the OCI image. Pin an Anaconda/ISO version that ships the (relatively new) verb.

### 1.2 Finish the blade with one first-boot data file

Blade config stays *data, not a daemon*: a single **[cloud-init](https://gitlab.com/fedora/bootc/examples)** user-data YAML (Apache-2.0 / GPL-3.0; **[Ignition/Butane](https://github.com/coreos/ignition)** is the mutually-exclusive alternative — pick one per image) runs once at first boot and performs the ordered steps below, then idles. Because it only runs on first boot, **day-2 reconfig goes through `mios build`/`rebuild`, never a re-run.**

Ordered first-boot steps (each a "one line" in user-data):

1. **Seal the Personal Data Vault (LUKS2 + TPM2).**
   ```bash
   systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=7 /dev/DISK
   ```
   **[systemd-cryptenroll](https://github.com/systemd/systemd)** (LGPL-2.1-or-later) — or **[clevis](https://github.com/latchset/clevis)** (GPL-3.0) for Tang/network modes — seals a LUKS2 keyslot to the TPM so the volume auto-unlocks in initramfs only when measured platform state matches: measured-boot-gated at-rest encryption, no passphrase, no network, zero extra packages via the systemd path. **Keep a recovery keyslot:** PCR7 must be re-enrolled after any firmware/Secure-Boot/shim change or the disk won't auto-unlock.

2. **Join the mesh (network layer — the blade's one job).**
   ```bash
   tailscale up --login-server https://<headscale> --authkey <key>
   ```
   The official **[Tailscale client](https://github.com/tailscale/tailscale)** (BSD-3-Clause, kernel WireGuard on Fedora bootc) joins the operator-owned **[Headscale](https://github.com/juanfont/headscale)** control plane (§1.3). **Ensure `/var` is the persistent ostree `/var`** or MagicDNS/state re-keys on every rebuild.

3. **Bind raw hardware to VFIO** for whole-GPU/NIC passthrough. Kernel cmdline `intel_iommu=on`/`amd_iommu=on` + `vfio-pci.ids=<vendor:device>` (or `driverctl`) binds dGPUs/NICs to `vfio-pci` at boot; **[libvirt](https://gitlab.com/libvirt/libvirt) + QEMU/KVM/VFIO** (LGPL-2.1 / GPL-2.0), installed via `dnf group install virtualization`, passes them to guests as `<hostdev>`. GPU fractioning is impossible driver-free → **whole-GPU-to-one-guest**. IOMMU-group isolation must be clean or passthrough leaks whole groups.

4. **Enable execution allowlisting.**
   ```bash
   systemctl enable --now fapolicyd
   ```
   **[fapolicyd](https://github.com/linux-application-whitelisting/fapolicyd)** (GPL-3.0-or-later) permits execution only for binaries trusted by the rpm-ostree/bootc trust database, denying everything else. Paired with ostree immutability, even with sudo disabled the substrate cannot execute untrusted code. On a bootc layout the trust source is the *composed image*, not live rpm transactions — validate the trust DB resolves against read-only `/usr` or legit binaries get denied (debug via `fapolicyd --debug`/permissive).

### 1.3 The one "central" piece (on exactly one blade)

**Headscale** (BSD-3-Clause) runs as a **single unprivileged systemd Quadlet on one elected blade or a cheap VPS blade** — the only central element in the whole topology, and the operator owns it. It exchanges WireGuard public keys, assigns tailnet IPs, enforces ACLs/Grants, and advertises routes; official clients then form direct P2P WireGuard tunnels with NAT traversal and **no vendor cloud**. `mios.toml [mesh]` projects its `config.yaml` and its **Policy v2** HuJSON (Grants + tags + MagicDNS + a `tests` block that doubles as a drift assertion).

- **Deploy it directly, not behind a reverse proxy or in a container** — maintainers explicitly do not support that (the *client* mesh is P2P; only this coordinator is central, so keep it HA-conscious: no tailnet-lock exists, so treat the host as high-trust — its compromise can inject nodes).
- **Cross-NAT reachability:** self-host a **[DERP relay (`cmd/derper`)](https://github.com/tailscale/tailscale/tree/main/cmd/derper)** (BSD-3-Clause) on a public blade so blades behind hard NAT/CGNAT still form one mesh; it forwards ciphertext only ("no visibility of the data exchanged"). It is a fallback (needs public IP + TLS) — size WAN traversal around direct P2P, not DERP.
- **Reach workloads without per-workload Tailscale:** the blade acts as **subnet router** (`--advertise-routes`) for a workload's Podman/libvirt network (needs IP forwarding + route approval in policy; plan non-overlapping CIDRs in `[mesh]`). The ARM phone-blade joins via the stock **[Tailscale Android app](https://github.com/tailscale/tailscale-android)** custom-control-server setting as a subnet-*client*/exit-node consumer (not a LAN gateway).
- **Optional operator pane:** **[Headplane](https://github.com/tale/headplane)** (MIT, *watch*) is a web UI over Headscale, but its writes are drift against `mios.toml` unless round-tripped — keep `mios.toml` SSOT.

---

## 2. Workload Traversal

Two headline demos ride the same headscale mesh: **container failover** (stateless-to-checkpointed) and **MiOS-Teleport** (VM live-migration).

### 2.a Container failover — k3s over the mesh

**[k3s](https://github.com/k3s-io/k3s)** (Apache-2.0), the CNCF-certified single-binary Kubernetes, is the traversal control plane. Each blade runs a k3s server/agent as a systemd unit dropped in by the deploy-script; when a blade dies the scheduler reschedules the OCI workload (`mios-agent-pipe`, MiOS-Hermes) onto a survivor, so the TTY AI pipeline outlives blade loss. Embedded etcd = no extra DB, keeping the substrate minimal.

**WAN wiring (verified against k3s docs):** span heterogeneous blades over the mesh with
```bash
k3s server --node-external-ip <blade-mesh-ip> \
  --flannel-backend=wireguard-native --flannel-external-ip
# or native tailscale integration:
k3s server --vpn-auth="name=tailscale,joinKey=<key>"   # controlServerURL → self-hosted headscale
```
Supervisor traffic rides a websocket tunnel; CNI/pod traffic rides WireGuard. **[Flannel wireguard-native](https://github.com/flannel-io/flannel)** (Apache-2.0) is the default CNI; `--flannel-iface` pins the overlay onto the mesh interface.

**Image traversal with zero central registry:** **[Spegel](https://github.com/spegel-org/spegel)** (MIT), a stateless cluster-local P2P OCI mirror, lets `containerd` pull layers from whichever peer blade already holds them — a fresh-landed workload streams its layers from a peer over the mesh, matching the no-central-server law (chainable to a Zot/Forgejo registry via `additionalMirrorTargets`).

**Author-once bridge:** **[podlet](https://github.com/containers/podlet)** (MPL-2.0) generates Podman **Quadlet** units and Kubernetes YAML from one source, so a workload runs as an unprivileged Quadlet on a bare blade *and* feeds the same OCI image + K8s YAML to k3s. It is a **dev-time generator — do not ship it onto the blade.**

**Stateful near-live option (*watch*):** **[CRIU](https://github.com/checkpoint-restore/criu)** + `podman container checkpoint --create-image` packs a running container's memory/FDs into a single-layer OCI image that traverses via Spegel and restores in place — the container analogue of Teleport, for **planned drain**, not arbitrary failover.

**Storage + arch-parity constraints (critical, verified):**
- HA embedded etcd needs **3+ blades, odd count** ((n/2)+1 quorum); a 2-blade edge cannot form HA.
- **Embedded etcd is unsupported across high-latency WAN links** — HA-etcd and cross-WAN traversal are in tension. **Resolution:** co-locate etcd servers on low-latency blades; run remote blades as **agents**.
- Point `vpn-auth` at the self-hosted headscale `controlServerURL`, not Tailscale SaaS.

### 2.b MiOS-Teleport — live VM migration via HA/Pacemaker over the mesh

The MiOS-Xbox VM live-migrates from a home blade across the WAN mesh to a remote-lab blade. Built entirely from upstream ClusterLabs RPMs; MiOS owns only the SSOT-generated config.

**The stack (all on the bootc blade image):**
- **[Pacemaker](https://github.com/ClusterLabs/pacemaker)** (GPL-2.0) + **`pcs`** — the resource manager. MiOS-Xbox is one `ocf:heartbeat:VirtualDomain` resource with `allow-migrate=true`, so a `pcs resource move` becomes a libvirt **live** migration rather than stop/start.
- **[Corosync](https://github.com/corosync/corosync)** (BSD-3-Clause) — membership/messaging + `votequorum`. One `/etc/corosync/corosync.conf` rendered from `mios.toml` with the **ring interface pinned to the headscale mesh IP**. Totem is latency/jitter-sensitive over WAN: tune `token`/`consensus` timers and **use `transport: knet`/udpu unicast with explicit member IPs** (multicast is unavailable over headscale).
- **[resource-agents](https://github.com/ClusterLabs/resource-agents)** (GPL-2.0 / LGPL-2.1) — supplies `VirtualDomain` (`virsh migrate --live`) plus `Filesystem`/`IPaddr2` agents the guest's disk/IP compose from.

**Migration command path:**
```bash
pcs resource move mios-xbox <target-blade>   # → VirtualDomain → virsh migrate --live
```

**Cross-site over the mesh (*watch*):** rather than one stretched cluster, run a small Pacemaker cluster per location and let **[Booth](https://github.com/ClusterLabs/booth)** (GPL-2.0) grant the MiOS-Xbox *ticket* to exactly one site over the mesh (modified-Raft; needs **≥3 booth members including a genuine independent arbitrator**). Ticket grant/revoke is a *controlled* failover, not sub-second — pair Pacemaker live-migrate within a site, Booth for cross-site.

**Fencing without a power controller (*watch*):** heterogeneous blades (phone, handheld, VPS) have no shared IPMI, so use **[SBD](https://github.com/ClusterLabs/sbd)** (GPL-2.0) in **diskless/softdog watchdog mode** (disk-based SBD needs a shared LUN, hard across pure P2P). A misconfigured/absent watchdog silently disables the safety.

**Storage + arch-parity constraints (hard requirements):**
- **Arch parity is mandatory** — x86→ARM live migration is impossible; both blades must match CPU/arch.
- VirtualDomain migrates **CPU/RAM state, not the disk** — the guest disk must be identically reachable on both blades. Options: shared/replicated storage (MiOS's existing **Ceph** direction preferred), or **[DRBD](https://github.com/LINBIT/drbd)** (GPL-2.0, *reference*) dual-primary. DRBD is deferred: out-of-tree kernel module fights the minimal-immutable-blade goal, dual-primary over lossy WAN risks split-brain, and it overlaps Ceph — **pick one**.
- Needs passwordless root SSH + libvirt migration ports open on the mesh; Pacemaker is **timeout-sensitive** — a slow WAN migrate that overruns the stop/`migrate_to` timeout is treated as failure and can trigger fencing.

---

## 3. The User@mios Prompt

tty0 itself becomes the comms layer — no display manager — routed to the mesh `/v1` pipeline, dual-mode (legacy terminal + NL-AI), with an SSOT `@`-prefix toggle.

**Console auto-login → prompt wrapper (verified upstream).** A `getty@tty0.service` drop-in, SSOT-projected by the deploy-script, sets **[agetty](https://man7.org/linux/man-pages/man8/agetty.8.html)** (util-linux, GPL-2.0) `--autologin <user>` and `--login-program /path/to/mios-prompt`, so the console *is* the interface on any blade including a VPS. **Security:** pass no operator-controlled `--login-options` and validate the wrapper cannot be abused via the username argument (the documented `--login-program`/`--login-options` injection risk).

**Dual-mode routing + the `@`-prefix SSOT toggle.** A bash **`command_not_found_handle()`** intercepts unrecognized/`@`-prefixed lines and forwards them to the agent pipe — a readline-level router with no separate shell (bash is already on the blade → near-zero surface). `mios.toml [prompt].at_prefix` decides whether only `@…` routes to AI or the whole line does. Because `command_not_found_handle` fires only for non-commands, the **`@`-prefix toggle is what routes arbitrary NL** (not just not-found lines). **[ble.sh](https://github.com/akinomyoga/ble.sh)** (BSD-3-Clause) offers richer `ble-bind -x` widgets but overrides builtins and is heavier — **reserve it for the workload tread; the minimal blade uses plain `command_not_found_handle`.**

**The `/v1` client.** **[aichat](https://github.com/sigoden/aichat)** (Apache-2.0 OR MIT) — a single Rust binary (minimal blade footprint) — is what tty0 pipes input to; its `api_base` points at **MiOS-Hermes :8642 `/v1`** reached over the mesh, and its config is an SSOT-projectable dotfile. **Keep it a client:** `aichat --serve` defaults to `127.0.0.1:8000` — never expose it raw; reach Hermes via the mesh name. (**[simonw/llm](https://github.com/simonw/llm)**, Apache-2.0, is a *watch* Python-based backup for scripted `mios-*` verbs — workload-tread, not the hot path.)

**Name-stable reach across traversal.** **`tailscale serve`** over Headscale reverse-proxies Hermes' local `/v1` onto the tailnet under a stable MagicDNS name with auto-TLS, so **the prompt survives container failover and VM live-migration because the name follows the workload across blades** (verify the Headscale version supports the `serve`/MagicDNS features used — parity can lag).

**The sudo-disabled / immutable safety argument.** The root fs is read-only ostree; **sudo is disabled** and runtime changes are negated on reboot, so a destructive NL-issued command is transient and containable — further boxable under a transient `systemd-run --property=NoNewPrivileges` scope. **fapolicyd** is the backstop: the model can *suggest* anything, but only ostree-shipped trusted binaries actually execute. NL mistakes persist only through `mios build`/`update`/`rebuild`. **Two honest limits:** (1) `/var` persists — NL writes to data/state under `/var` are **not** negated, so the Personal Data Vault needs its own guardrails; (2) interpreted payloads (`python -c …`) partly bypass binary allowlisting — pair immutability with allowlisting, don't rely on either alone. Higher-capability agents like **[Open Interpreter](https://github.com/OpenInterpreter/open-interpreter)** (AGPL-3.0, *watch*) must stay **inside the unprivileged Quadlet under fapolicyd — never on the substrate** (AGPL also forces workload-side placement).

---

## 4. Decision Table

| Concern | FOSS choice | Why | MiOS-Metal wiring |
|---|---|---|---|
| Immutable substrate install | **bootc** (`install to-disk`/`to-filesystem`) | Image installs itself as ostree-immutable host; one command, no bespoke installer; immutability = sudo-safe runtime | Single blade bring-up command; `to-filesystem` for VPS blades |
| Multi-target images | **bootc-image-builder** (osbuild) | One build → qcow2/raw/ami/vhd/iso: traversal RAW, cloud VPS, MiOS-Cat media | Build-time; emits every artifact the topology traverses |
| Automated bare-metal fleet | **Anaconda `bootc` kickstart** | Upstream PXE/ISO path; one kickstart, OCI payload | MiOS-Cat bare-metal leg; pin the ISO version |
| First-boot config as data | **cloud-init** (Fedora bootc example) | Blade stays a few scripts, not a daemon; same file rides to VPS | One user-data YAML runs the §1.2 ordered steps once |
| Data-vault at-rest crypto | **systemd-cryptenroll + TPM2** (clevis optional) | Measured-boot-gated LUKS2, no passphrase, zero extra pkgs | One line in user-data; keep a recovery keyslot |
| Execution control | **fapolicyd** | Only image-trusted binaries exec; backstops open NL prompt | `systemctl enable --now`; trust DB = composed image |
| Mesh control plane | **Headscale** | Self-hosted Tailscale control server, zero vendor cloud; the only central piece, operator-owned | One unprivileged Quadlet on one blade; `[mesh]`→config+policy |
| Mesh data plane | **Tailscale client** (+ DERP, subnet routers, Android app) | P2P WireGuard, NAT traversal; blade owns the net layer | `tailscale up --login-server=…`; per-blade line |
| Hardware passthrough | **libvirt + QEMU/KVM/VFIO** | Whole-GPU/NIC to guests; libvirt = live-migration engine | `vfio-pci.ids` on cmdline; `dnf group install virtualization` |
| Container traversal | **k3s** (+ Flannel wireguard-native) | CNCF-min k8s; reschedules workloads off dead blades | systemd unit; `--node-external-ip` = mesh IP |
| P2P image mirror | **Spegel** | Layers stream from peer blades; no central registry | k3s/containerd mirror; chain to Zot/Forgejo |
| Author-once workloads | **podlet** | One source → Quadlet + K8s YAML | Dev-time generator; **not** shipped to blade |
| VM live-migration | **Pacemaker + Corosync + resource-agents** | Upstream HA; `VirtualDomain allow-migrate` = `virsh migrate --live` | `pcs`/`corosync.conf` from `mios.toml`; ring on mesh IP |
| Cross-site VM handoff | **Booth** *(watch)* | Ticket to one site over WAN mesh | `booth.conf` per site + independent arbitrator |
| Fencing (no IPMI) | **SBD** *(watch)* | Diskless watchdog fencing for heterogeneous blades | softdog mode; prevents double-run of teleported VM |
| Console auto-login | **agetty** (`--autologin`/`--login-program`) | tty0 becomes the interface, no DM; pure upstream | `getty@tty0` drop-in, SSOT-projected |
| NL/legacy router | **bash `command_not_found_handle`** (ble.sh on tread) | Readline-level dual-mode; `@`-prefix SSOT toggle | `[prompt].at_prefix`; near-zero surface |
| `/v1` prompt client | **aichat** | Single Rust binary → Hermes `/v1` over mesh | `api_base`→:8642; keep it a client, never `--serve` raw |
| Name-stable reach | **tailscale serve** over Headscale | MagicDNS name follows workload across failover/teleport | Reverse-proxy Hermes `/v1` onto tailnet |

---

## 5. Open Risks

1. **HA-etcd vs. cross-WAN is a genuine tension (verified).** k3s embedded etcd is *unsupported* over high-latency WAN and needs 3+ odd nodes for quorum. A 2-blade home edge cannot form etcd HA, and remote blades must run as agents (etcd co-located on low-latency blades) — so "container failover across locations" is real but the *control plane* stays local while only workloads/agents span the WAN.

2. **Double-encryption over the mesh.** Flannel `wireguard-native` riding an already-WireGuard headscale mesh stacks encryption + MTU overhead. Pin `--flannel-iface` to the mesh and evaluate whether the mesh's own encryption suffices. The 1280-MTU/flannel-on-`tailscale0` fragmentation caveat was **not confirmed** in sourcing — treat as untested.

3. **Arch parity is a hard wall for Teleport.** x86→ARM live migration is impossible; the heterogeneous fleet (RTX-4090, Xeon+ARC, Radeon, AMD-APU, ARM phone) can only teleport a VM *between arch-matched blades*. Container CRIU restore has the same matching-kernel/arch + fragile GPU/device-state limitation.

4. **Storage under a live-migrating VM is unsolved-by-default.** VirtualDomain moves RAM/CPU, not disk. Ceph (MiOS's existing direction) and DRBD dual-primary conflict — the operator must pick one; DRBD's out-of-tree kernel module fights immutable bootc and risks split-brain over lossy WAN.

5. **WAN cluster membership flaps.** Corosync Totem and Booth Raft are latency/jitter-sensitive; untuned timers false-fence, and Pacemaker's tight stop/migrate timeouts turn a slow WAN migrate into a fencing event. Booth needs a genuinely independent 3rd arbitrator or partitions can't be adjudicated.

6. **Fencing without shared hardware is best-effort.** Diskless SBD relies on correct quorum + a live watchdog; a misconfigured/absent watchdog silently removes the only guard against a partitioned blade double-running the teleported VM. Disk-based SBD is impractical across pure P2P.

7. **The one central point is high-trust.** Headscale has no tailnet-lock — compromise can inject nodes. It also must not run behind a proxy/in a container (unsupported), and keeping it HA while it stays the sole coordinator is unresolved. One active maintainer is Tailscale-employed (community but not fully arms-length governance).

8. **Immutability does not cover `/var` or interpreters.** NL writes to `/var` data/state persist across reboot, and `python -c …` partly bypasses fapolicyd's binary allowlisting — the open NL prompt's safety rests on the *combination* of immutability + allowlisting + `/var` guardrails, not any one.

9. **Component-provenance caveats to verify before wiring.** **Tailscale Peer Relays** and the exact CRIU `--create-image` OCI-packing behavior could **not** be confirmed in sourcing (fetch failures) — verify against current docs. **bootc-image-builder** repo is archived/merged into `osbuild/image-builder` — track the new home. Several first-boot/virtualization Fedora docs are bot-gated to fetch; the mechanisms rest on component knowledge, not a live fetch this pass.

10. **Drift surfaces multiply.** Headplane and any UI that writes back to Headscale, plus podlet's non-1:1 Quadlet↔pod-spec mapping (restart/secrets/volumes/healthchecks diverge), create config that drifts from `mios.toml` SSOT unless every path round-trips through it. "Author once" needs a canonical form + projection step, not a raw copy.

---

*Dispositions carried from sourcing — **adopt_now:** bootc, bootc-image-builder, Anaconda bootc, cloud-init, systemd-cryptenroll/clevis, fapolicyd, Headscale, Tailscale client/DERP/subnet-routers/Android/serve, libvirt+VFIO, k3s (+distributed), Spegel, Flannel, podlet, Pacemaker, Corosync, resource-agents, agetty, aichat, bash `command_not_found_handle`/ble.sh. **watch:** Headplane, Peer Relays, CRIU, Booth, SBD, simonw/llm, Open Interpreter. **reference:** DRBD, bootc/ostree-immutability-as-guarantee.*