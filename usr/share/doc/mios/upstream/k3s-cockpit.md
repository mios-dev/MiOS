<!-- AI-hint: Documentation for the K3s + Cockpit (+ Ceph, libvirt/QEMU) cluster/admin surface of MiOS; explains how the same immutable bootc image that ships the desktop and the local agent stack can also grow in-place into a one-node Kubernetes+Ceph cluster, the K3s native-service vs Podman-Quadlet paths, the Cockpit web console on :9090 (and the mios-cockpit-link discovery shim on :19090), and the LAW 6 (UNPRIVILEGED-QUADLETS) exceptions for the root-privileged mios-k3s/mios-ceph containers.
     AI-related: mios-k3s, mios-ceph, mios-k3s.container, mios-ceph.container, mios-cockpit-link, mios-cockpit-link.container, k3s.service, mios-k3s-init.service, cockpit.socket, 13-ceph-k3s.sh, 19-k3s-selinux.sh -->
# K3s + Cockpit on MiOS

> **What this is.** The cluster-and-administration face of MiOS. MiOS is one
> thing built two ways at once: an immutable, bootc/OCI-shaped Fedora
> workstation (the whole OS is a single container image — boot it,
> `bootc upgrade` it like a `git pull`, `bootc rollback` it like a Ctrl-Z) that
> is *also* a local, self-replicating, agentic AI operating system. This
> document covers the piece of that whole that lets the workstation **grow
> in-place into a one-node Kubernetes + Ceph cluster** and be **administered
> from a browser** — without ever re-imaging the box.
>
> **Why it belongs in the image.** Because MiOS is one rebuildable image, the
> cluster path is not a separate product you bolt on later: K3s, Ceph client
> tooling, Cockpit, and libvirt/QEMU are all baked into the same immutable
> image, version-locked to the OS, and reproduced exactly on every host that
> pulls the ref. The cluster bits stay inert (gated off) until an admin opts
> in, so a plain desktop install pays no runtime cost for capability it isn't
> using yet.
>
> **The LAW 6 exception this doc documents.** MiOS Architectural Law 6
> (UNPRIVILEGED-QUADLETS) requires every Quadlet to declare `User=`, `Group=`,
> and `Delegate=yes`. `mios-k3s` and `mios-ceph` are documented exceptions:
> they declare `User=root`/`Group=root` explicitly because K3s and Ceph
> require uid 0 and privileged host access. (The third sanctioned exception,
> `mios-forgejo-runner`, is unrelated to this surface.)

## K3s — the one-node-cluster path

- Project: <https://k3s.io/>
- Repo: <https://github.com/k3s-io/k3s>
- Version pin: `docker.io/rancher/k3s:v1.32.1-k3s1` (`k3s_version` /
  `k3s` in `mios.toml [versions]`); the native-service path bakes the matching
  binary into `/usr/bin/k3s`.
- API server: `https://<host>:6443` after boot (`k3s_api = 6443`)
- Install step: `automation/13-ceph-k3s.sh` (installs Ceph client tools, the
  K3s prerequisites, and the K3s binary + install script — vendored-offline if
  `/usr/share/mios/vendored/k3s` exists, else fetched + SHA256-verified).
- SELinux integration: `automation/19-k3s-selinux.sh` compiles the custom
  `k3s-selinux` policy from source.

### Two K3s shapes ship; both gate off cleanly

The image carries **two** ways to run K3s, so an admin can pick the one that
fits the host:

1. **Native systemd service — `k3s.service`.** Runs the baked
   `/usr/bin/k3s server --disable traefik` directly on the host (no container
   layer). The binary lives at `/usr/bin/k3s` (the immutable image surface;
   `/usr/local/bin` is `→/var/usrlocal/bin` on bootc/FCOS and mutable per-host,
   so the unit pins to `/usr/bin`). Ordered after `mios-k3s-init.service`, which
   stages the manifests. `kubectl`/`crictl`/`ctr` are symlinks to the same
   binary when no RPM claims those names. K3s manifests are shipped read-only at
   `/usr/share/mios/k3s-manifests/` (never in `/var` — that would violate Law 2,
   NO-MKDIR-IN-VAR) and copied to
   `/var/lib/rancher/k3s/server/manifests/` at first boot.

2. **Podman Quadlet — `mios-k3s.container`.** Runs the
   `docker.io/rancher/k3s:v1.32.1-k3s1` image under Podman with
   `PodmanArgs=--privileged` (the portable form; the `Privileged=` key needs
   podman 5.7+ and is silently dropped by older quadlet-generators). It binds the
   same `/usr/share/mios/k3s-manifests` read-only and the `/var/lib/rancher/k3s`
   state volume, runs `server --disable=traefik`, and carries the default
   cluster token `K3S_TOKEN=mios-cluster-secret` (the bootstrap repo overrides
   it via a `token.conf` drop-in at ignition — the in-image default is visible
   and must never be set to a real secret).

Both K3s shapes need cgroup v2, eBPF, and full kernel namespaces, none of which
work reliably under WSL2 or inside a nested container — so the Quadlet gates on:

```
ConditionVirtualization=!wsl
ConditionVirtualization=!container
```

The Quadlet is enabled by default (the "defaults policy: enabled, auto-skips on
incompatible hosts") and simply no-ops on WSL2/container shapes rather than
failing. Profile control over which cluster Quadlets ship is in
`mios.toml [quadlets.enable]` (`mios-k3s = true`).

### Why K3s, not a full kubeadm cluster

K3s is a single binary that wants to manage cgroups, iptables, and overlay
filesystems directly — exactly the kind of privileged, host-level orchestrator
the immutable-image discipline is built to deliver reproducibly. Shipping it
inside the image (rather than expecting a Day-2 `dnf`/`curl|sh`) means a host can
become a cluster node with no out-of-band install and no drift: the same `bootc
upgrade` that moves the OS forward moves the orchestrator with it. That is the
whole-system promise applied to clustering — Law 3 (BOUND-IMAGES) is why the
`rancher/k3s` image rides *inside* the host, and Law 6's documented `User=root`
exception is what lets a least-privilege agent plane coexist with a
deliberately-privileged orchestrator.

## Cockpit — the browser admin console

- Project: <https://cockpit-project.org/>
- Inherited from the `ucore-hci` base; the full suite is pinned in
  `mios.toml [packages.cockpit]`.
- Runs as a **host systemd service** (`cockpit.socket` bound to `:9090`), not
  in a container.
- Port: `9090/tcp` (`cockpit = 9090`; firewalld `allow_cockpit = true` opens it
  in the default `drop` zone alongside ssh).
- Auth: host PAM. On the dev VM the default `mios / mios` credential is the SSOT
  advertised to Cockpit, the Portal, the Ceph dashboard, and Forge.
- Modules MiOS ships:
  - `cockpit-podman` — manage Quadlet sidecars from the browser
  - `cockpit-machines` — libvirt/KVM VM dashboard
  - `cockpit-storaged` — disk/LVM/Btrfs management (not ZFS — Cockpit doesn't
    speak ZFS)
  - `cockpit-networkmanager` — network interface admin
  - `cockpit-selinux` — view denials, toggle booleans
  - `cockpit-ostree` — bootc/ostree deployment view (matches the
    image-as-OS lifecycle)
  - `cockpit-system`, `cockpit-ws`, `cockpit-bridge`, `cockpit-files`,
    `cockpit-sosreport`, `cockpit-kdump` — base console, web server, host bridge,
    file browser, support-report and kdump tooling. (`cockpit-packagekit` is
    intentionally omitted on an image-managed OS; there is no `cockpit-pcp`
    package on Fedora 44 — its metrics history is read via the PCP stack.)

### Cockpit serves the whole-system story

Cockpit is how an operator *sees* the rest of this document from a browser:
`cockpit-machines` fronts the libvirt/QEMU VMs (below), `cockpit-podman` fronts
the agent-plane Quadlets, `cockpit-ostree` fronts the bootc deployments, and
`cockpit-storaged` fronts local disks. It is the human admin surface that sits
alongside the *agentic* admin surface (the local agent stack on
`MIOS_AI_ENDPOINT`) — two ways to drive the same immutable host.

### mios-cockpit-link — Podman Desktop discovery shim

Because Cockpit runs as a host service (not a Quadlet), Podman Desktop's
container view normally can't render a clickable link to it. `mios-cockpit-link`
(`mios-cockpit-link.container`) is a tiny `alpine/socat` relay (~3 MB, idle)
that publishes `localhost:19090 → host:9090` and carries OCI labels Podman
Desktop renders as an "open Cockpit" link. The alternate port `19090`
(`cockpit_link = 19090`) avoids colliding with the host's `:9090`. It is an
unprivileged Quadlet (`User=65534`/`Group=65534`, the `nobody` uid/gid — Law 6
compliant, no exception needed) and gates on `ConditionVirtualization=!wsl,!container`
plus the presence of `cockpit.socket` (on WSL2, Windows-side Podman Desktop
reaches `https://localhost:9090/` directly, so the shim is pointless there).
Disable it via `mios.toml [quadlets.enable]`.

### Verification

```bash
sudo systemctl status cockpit.socket
firewall-cmd --list-services | grep -q cockpit
# Then browse https://<host>:9090 (host PAM auth; cockpit-ws self-signed cert)
```

## Ceph — distributed storage for the cluster path

- Project: <https://ceph.io/>
- cephadm: <https://docs.ceph.com/en/latest/cephadm/>
- Version pin: `quay.io/ceph/ceph:v19` (Squid; `ceph_version = "v19"`).
- Dashboard: `https://<host>:8443` after bootstrap (`ceph_dashboard = 8443`).
- Install step: `automation/13-ceph-k3s.sh` bakes only the **client tools +
  cephadm** (`ceph-common`, `cephadm`, `ceph-fuse`, `ceph-selinux`); cephadm
  runs all server daemons as Podman containers.
- Bootstrap: `/usr/libexec/mios/ceph-bootstrap.sh` (driven by
  `mios-ceph-bootstrap.service`); the minimal monitor runs via the
  `mios-ceph.container` Quadlet under the dedicated `mios-ceph` service user.

### Gating and the LAW 6 exception

`mios-ceph.container` requires a configured cluster — without
`/etc/ceph/ceph.conf` the monitor cannot bootstrap — so the Quadlet gates on:

```
ConditionPathExists=/etc/ceph/ceph.conf
ConditionVirtualization=!container
```

When that file is absent (the default workstation profile), the `Condition*`
no-ops the unit cleanly. Like K3s, the Quadlet declares `User=root`/`Group=root`
explicitly: a documented exception to **LAW 6 (UNPRIVILEGED-QUADLETS)** because
Ceph requires uid 0 and privileged storage access. Multi-node deployments use
cephadm; single-node MiOS workstations typically use BlueStore on a dedicated
disk via a separate bootstrap step. Profile control: `mios.toml [quadlets.enable]`
(`mios-ceph = true`).

## libvirt / QEMU — the virtualization plane Cockpit fronts

- libvirt: <https://libvirt.org/>
- QEMU: <https://www.qemu.org/>
- Inherited from the `ucore-hci` base; the package set is in
  `mios.toml [packages.virt]` (`qemu-kvm`, `libvirt`, `libvirt-daemon`,
  `qemu-img`, virtio-gpu display, guest agent, libvirt NSS, …).
- Used for KVM VMs and VFIO-PCI passthrough; firewalld
  `allow_libvirt_bridge = true` enables VM networking.
- Wired to Cockpit's `machines` module for a browser VM dashboard. The same CDI
  GPU wiring that lets the local inference lanes claim hardware is what lets a
  passthrough VM claim a discrete GPU — one GPU-sharing story, two consumers.

## Where this fits in the whole system

The image you `bootc switch`/`upgrade` carries the desktop, the local AI plane
(inference lanes → agent-pipe/Hermes orchestration → PostgreSQL+pgvector memory
→ MCP/A2A, all behind `MIOS_AI_ENDPOINT`), **and** this cluster/admin surface.
The build pipeline (`automation/13-ceph-k3s.sh`, `19-k3s-selinux.sh`,
`15-render-quadlets.sh`) assembles all of it into one OCI image; the bootc
lifecycle carries it forward and rolls it back atomically. The cluster pieces
sit dormant behind their `Condition*` gates until an admin opts in — so a laptop
desktop and a one-node cluster node are the *same image* in two states, not two
products.

## Cross-refs

- `usr/share/doc/mios/reference/api.md` (the unified AI surface this admin
  plane sits alongside)
- `usr/share/doc/mios/upstream/podman.md` (Quadlets — how `mios-k3s`,
  `mios-ceph`, `mios-cockpit-link` are generated and gated)
- `usr/share/doc/mios/upstream/looking-glass-kvmfr.md` (VFIO passthrough +
  cross-VM display, the consumer side of the libvirt/QEMU plane)
- `usr/share/doc/mios/upstream/ucore-hci.md` (the base that supplies Cockpit and
  libvirt/QEMU)
- `usr/share/doc/mios/concepts/architecture.md` (the UNPRIVILEGED-EXECUTION /
  LAW 6 exceptions in full)
