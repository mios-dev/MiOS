<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "knowledge"
  ],
  "relations": {
    "depends_on": [
      ".env.mios"
    ],
    "impacts": []
  }
}
```
> **Proprietor:** MiOS Project
> **Infrastructure:** Self-Building Infrastructure (Personal Property)
> **License:** Licensed as personal property to MiOS Project
> **Source Reference:** MiOS-Core-v0.1.1
---

# Integrating Ceph, Cephadm, and K3s into MiOS

**Ceph's entire state model aligns perfectly with bootc's immutable filesystem** — every writable path cephadm needs (`/var/lib/ceph`, `/etc/ceph`, `/var/log/ceph`) falls within the mutable `/var` and `/etc` partitions. Fedora Rawhide ships **Ceph v0.1.1 (Tentacle)** with `cephadm`, `ceph-common`, and all required packages in the standard repos, requiring zero upstream repo configuration. The practical challenge is not compatibility but orchestration: designing a systemd dependency chain that gracefully handles first boot (no Ceph cluster yet), steady-state operation (CephFS mounts for `/var/home` and container storage), and multi-node expansion via the Ceph Dashboard. This report provides every configuration file, systemd unit, Containerfile snippet, and command needed to build this integration into the existing MiOS modular build system.

---

## Fedora Rawhide delivers Ceph v0.1.1 with complete packaging

Fedora Rawhide (fc45) provides **Ceph v0.1.1-10 (Tentacle)** as a native package set. The critical packages for the bootc base image are minimal because cephadm runs all server daemons as Podman containers:

- **`ceph-common`** — Provides `/usr/bin/mount.ceph`, `ceph` CLI, `rbd`, `rados`, `ceph-authtool`, `ceph-conf`. This is the essential client package.
- **`cephadm`** — The bootstrap and orchestration binary. Deploys MON, MGR, OSD, and MDS as Podman containers managed by systemd.
- **`ceph-fuse`** — FUSE-based CephFS mount alternative (now requires `fuse3` on Rawhide). Lower performance than the kernel driver but useful as a fallback.
- **`ceph-selinux`** — SELinux policy module defining `ceph_t`, `ceph_var_lib_t`, `ceph_log_t`, and related types for Ceph process contexts.

Server packages (`ceph-mon`, `ceph-osd`, `ceph-mds`, `ceph-mgr`, `ceph-mgr-dashboard`) are **not needed** in the base image. Cephadm pulls the `quay.io/ceph/ceph:v20` container image at bootstrap time and runs each daemon as an independent Podman container with its own systemd unit.

The kernel modules `libceph.ko`, `ceph.ko`, and `rbd.ko` ship in the **standard `kernel-modules`** package (not `kernel-modules-extra`). They are compiled as loadable modules (`CONFIG_CEPH_FS=m`, `CONFIG_BLK_DEV_RBD=m`) and `mount.ceph` triggers `modprobe` automatically. For explicit boot-time loading, the image should include `/etc/modules-load.d/ceph.conf` containing `ceph` and `rbd` on separate lines.

Podman compatibility is confirmed: Ceph documentation states **no known issues with Podman ≥ 3.0** for Quincy and later releases. Fedora Rawhide ships Podman 5.x, well within the supported range for Tentacle.

---

## Cephadm on immutable bootc: a natural fit

The core question — whether cephadm works on a system where `/usr` is read-only — resolves cleanly. Cephadm's entire runtime footprint maps to bootc's mutable paths:

| Path | Purpose | bootc Status |
|------|---------|-------------|
| `/var/lib/ceph/<fsid>/` | All daemon data (MON, OSD, MGR, MDS state) | ✅ Writable |
| `/var/log/ceph/<fsid>/` | Cluster logs (if `--log-to-file` enabled) | ✅ Writable |
| `/etc/ceph/` | `ceph.conf`, keyrings, `ceph.pub` SSH key | ✅ Writable |
| `/etc/systemd/system/` | Per-daemon systemd units | ✅ Writable |
| `/run/` (tmpfs) | Container runtime socket, PID files | ✅ Writable |
| `/root/.ssh/authorized_keys` | SSH key for cluster management | ✅ Writable |

The cephadm binary itself is baked into the image at `/usr/bin/cephadm` during the container build. At runtime, cephadm only writes to `/var/` and `/etc/`, never touching `/usr/`. One confirmed caveat: the `--data-dir` flag (for custom data paths) **does not work properly** — the cephadm MGR module resets paths to `/var/lib/ceph` defaults. Use the default paths.

### Bootstrap command for single-node workstation

```bash
cephadm bootstrap \
  --mon-ip "$(hostname -I | awk '{print $1}')" \
  --single-host-defaults \
  --skip-monitoring-stack \
  --allow-fqdn-hostname \
  --skip-firewalld
```

The `--single-host-defaults` flag sets three configuration values: **`osd_crush_chooseleaf_type = 0`** (replicate across OSDs instead of hosts), **`osd_pool_default_size = 2`**, and **`mgr_standby_modules = false`**. For a true single-disk workstation, override to size 1 post-bootstrap:

```bash
ceph config set global osd_pool_default_size 1
ceph config set global osd_pool_default_min_size 1
ceph config set mon mon_allow_pool_size_one true
```

The `--skip-monitoring-stack` flag omits Prometheus, Grafana, Alertmanager, and node-exporter containers, saving **~300 MB of RAM** — critical for a workstation running a GNOME desktop alongside Ceph and K3s. The Dashboard can be included (it's enabled by default unless `--skip-dashboard` is passed) for the multi-node expansion UI requirement.

### OSD creation on non-dedicated hardware

For workstations where a dedicated blank disk may not exist, cephadm supports OSDs on **LVM logical volumes** and **loop-backed devices**:

```bash
# Loop device approach (for testing or single-disk systems)
dd if=/dev/zero of=/var/lib/ceph-osd.img bs=1G count=100
losetup /dev/loop0 /var/lib/ceph-osd.img
pvcreate /dev/loop0
vgcreate ceph-loop-vg /dev/loop0
lvcreate -l 100%FREE -n ceph-loop-lv ceph-loop-vg
cephadm ceph-volume lvm create --bluestore --data ceph-loop-vg/ceph-loop-lv
```

For dedicated partitions or disks, the automatic provisioner handles everything: `ceph orch apply osd --all-available-devices`. Requirements: device must have no partitions, no LVM state, not be mounted, no filesystem, and be **>5 GB**.

---

## The boot sequence that solves the chicken-and-egg problem

The most architecturally critical design decision is how to mount `/var/home` via CephFS when user login requires that path to exist, but Ceph may not yet be bootstrapped. The solution uses **`nofail` + `ConditionPathExists`** mount options combined with systemd's mount ordering.

### Why /var/home as a remote mount is valid

Systemd's mount requirements categorize `/var/` as "category 2/early" (must be writable before `local-fs.target`), but subdirectories like `/var/home` are "category 3/regular" — eligible for remote mounts ordered before `remote-fs.target`. Bootc creates `/home` as a symlink to `/var/home`, and the OSTree documentation explicitly confirms: "Mounting separate filesystems there can be done by the usual mechanisms of /etc/fstab, systemd .mount units."

### The var-home.mount unit

```ini
# /etc/systemd/system/var-home.mount
[Unit]
Description=CephFS mount for user home directories
Documentation=man:mount.ceph(8)
ConditionPathExists=/etc/ceph/ceph.conf
ConditionPathExists=/etc/ceph/mios.secret
After=ceph.target

[Mount]
What=mios@.cephfs=/home
Where=/var/home
Type=ceph
Options=secretfile=/etc/ceph/mios.secret,noatime,_netdev,nofail,x-systemd.device-timeout=30,x-systemd.mount-timeout=30

[Install]
WantedBy=remote-fs.target
```

The **`ConditionPathExists`** directives prevent the mount from even being attempted before Ceph credentials exist (first boot). The **`nofail`** option ensures boot continues regardless of mount success, and **`x-systemd.device-timeout=30`** caps wait time to 30 seconds. The **`_netdev`** option automatically adds `After=network-online.target` and `Wants=network-online.target`.

When CephFS isn't mounted, `/var/home` remains the local directory on the root filesystem — users can still log in. After bootstrap creates credentials, either a reboot or `systemctl start var-home.mount` activates the CephFS overlay.

### The var-lib-containers.mount unit

```ini
# /etc/systemd/system/var-lib-containers.mount
[Unit]
Description=CephFS mount for Podman container storage
ConditionPathExists=/etc/ceph/ceph.conf
ConditionPathExists=/etc/ceph/mios.secret
After=ceph.target
RequiresMountsFor=/var/lib

[Mount]
What=mios@.cephfs=/containers
Where=/var/lib/containers
Type=ceph
Options=secretfile=/etc/ceph/mios.secret,noatime,_netdev,nofail,x-systemd.device-timeout=30,x-systemd.mount-timeout=30

[Install]
WantedBy=remote-fs.target
```

### Full dependency chain

```
hardware init → initrd → root (/) mounted
    ↓
local-fs.target (/var/ writable, local)
    ↓
network-online.target
    ↓
ceph-<FSID>@mon.<host>.service  ─┐
ceph-<FSID>@mgr.<host>.service  ─┤  (Podman containers, cephadm-managed)
ceph-<FSID>@osd.0.service       ─┤  Part of ceph.target
ceph-<FSID>@mds.<host>.service  ─┘
    ↓  (After=ceph.target)
var-home.mount (nofail)
var-lib-containers.mount (nofail)
    ↓  remote-fs.target
    ↓
k3s.service (After=remote-fs.target)
    ↓
multi-user.target → graphical.target → user login
```

Cephadm creates systemd units using the pattern **`ceph-<FSID>@<daemon-type>.<id>.service`** under `/etc/systemd/system/`, all grouped under a `ceph-<FSID>.target` which rolls up to `ceph.target`.

---

## First-boot initialization as a oneshot systemd service

Bootstrap automation belongs in a conditional oneshot service that runs exactly once:

```ini
# /etc/systemd/system/ceph-bootstrap.service
[Unit]
Description=Bootstrap Ceph cluster on first boot
After=network-online.target
Wants=network-online.target
ConditionPathExists=!/var/lib/ceph/.bootstrapped

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/ceph-bootstrap.sh
ExecStartPost=/usr/bin/touch /var/lib/ceph/.bootstrapped

[Install]
WantedBy=multi-user.target
```

The bootstrap script detects the primary IP, runs `cephadm bootstrap`, sets single-replica configuration, creates the CephFS filesystem, and generates mount credentials:

```bash
#!/bin/bash
set -euo pipefail
MON_IP=$(hostname -I | awk '{print $1}')

cephadm bootstrap \
  --mon-ip "$MON_IP" \
  --single-host-defaults \
  --skip-monitoring-stack \
  --allow-fqdn-hostname \
  --skip-firewalld

# Configure single-replica
cephadm shell -- ceph config set global osd_pool_default_size 1
cephadm shell -- ceph config set global osd_pool_default_min_size 1
cephadm shell -- ceph config set mon mon_allow_pool_size_one true

# Memory tuning for desktop use
cephadm shell -- ceph config set osd osd_memory_target 1073741824
cephadm shell -- ceph config set mgr mgr/cephadm/autotune_memory_target_ratio 0.2

# Auto-provision OSDs on available devices
cephadm shell -- ceph orch apply osd --all-available-devices

# Wait for at least one OSD
for i in $(seq 1 30); do
  OSD_UP=$(cephadm shell -- ceph osd stat -f json 2>/dev/null | \
    python3 -c "import sys,json; print(json.load(sys.stdin).get('num_up_osds',0))" 2>/dev/null || echo 0)
  [ "$OSD_UP" -gt 0 ] && break
  sleep 10
done

# Set existing pools to size 1
for pool in $(cephadm shell -- ceph osd pool ls 2>/dev/null); do
  cephadm shell -- ceph osd pool set "$pool" size 1 --yes-i-really-mean-it
  cephadm shell -- ceph osd pool set "$pool" min_size 1
done

# Create CephFS filesystem (auto-creates pools and deploys MDS)
cephadm shell -- ceph fs volume create cephfs --placement="1 $(hostname)"
sleep 15

# Set CephFS pool sizes to 1
cephadm shell -- ceph osd pool set cephfs.cephfs.meta size 1 --yes-i-really-mean-it
cephadm shell -- ceph osd pool set cephfs.cephfs.data size 1 --yes-i-really-mean-it

# Create mount client and extract secret
cephadm shell -- ceph fs authorize cephfs client.mios / rw \
  -o /etc/ceph/ceph.client.mios.keyring
cephadm shell -- ceph auth get-key client.mios > /etc/ceph/mios.secret
chmod 600 /etc/ceph/mios.secret

# Create CephFS subdirectories for mount targets
mkdir -p /tmp/ceph-init
mount -t ceph mios@.cephfs=/ /tmp/ceph-init -o secretfile=/etc/ceph/mios.secret
mkdir -p /tmp/ceph-init/home /tmp/ceph-init/containers
umount /tmp/ceph-init

cephadm shell -- ceph health mute POOL_NO_REDUNDANCY
```

The **`ConditionPathExists=!/var/lib/ceph/.bootstrapped`** sentinel file ensures this service is completely skipped on subsequent boots. After bootstrap completes and credentials are written, the CephFS mount units (which check for `ConditionPathExists=/etc/ceph/mios.secret`) will succeed on the next reboot or when manually started.

---

## K3s integration: embedded binary with CephFS-backed persistent storage

K3s must be **baked into the OCI image** since `/usr` is read-only at runtime. K3s uses its own **embedded containerd** — it cannot use Podman as a CRI, but both runtimes coexist without conflict on separate storage paths (`/var/lib/rancher/k3s/` vs `/var/lib/containers/`).

### K3s systemd service with CephFS dependencies

```ini
# /usr/lib/systemd/system/k3s.service
[Unit]
Description=Lightweight Kubernetes
Documentation=https://k3s.io
Wants=network-online.target
After=network-online.target remote-fs.target

[Service]
Type=notify
EnvironmentFile=-/etc/default/%N
EnvironmentFile=-/etc/sysconfig/%N
ExecStartPre=-/sbin/modprobe br_netfilter
ExecStartPre=-/sbin/modprobe overlay
ExecStart=/usr/local/bin/k3s server
KillMode=process
Delegate=yes
LimitNOFILE=1048576
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
TimeoutStartSec=0
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

The `After=remote-fs.target` ensures K3s starts only after CephFS mounts have been attempted. For a stronger dependency, a drop-in override can add `RequiresMountsFor=/var/lib/containers`.

### K3s configuration

```yaml
# /etc/rancher/k3s/config.yaml
write-kubeconfig-mode: "0644"
selinux: true
disable:
  - traefik
  - servicelb
data-dir: /var/lib/rancher/k3s
```

Single-node K3s uses **SQLite** by default (stored at `/var/lib/rancher/k3s/server/db/state.db`), which is ideal for workstation use. Embedded etcd (`--cluster-init`) adds unnecessary overhead for a single node.

### ceph-csi deployment via K3s HelmChart CRD

K3s includes a built-in Helm controller. Dropping a HelmChart manifest into `/var/lib/rancher/k3s/server/manifests/` auto-deploys ceph-csi:

```yaml
# /var/lib/rancher/k3s/server/manifests/ceph-csi-cephfs.yaml
apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata:
  name: ceph-csi-cephfs
  namespace: kube-system
spec:
  repo: https://ceph.github.io/csi-charts
  chart: ceph-csi-cephfs
  targetNamespace: ceph-csi-cephfs
  createNamespace: true
  valuesContent: |-
    csiConfig:
      - clusterID: "CEPH_FSID_PLACEHOLDER"
        monitors:
          - "MON_IP_PLACEHOLDER:6789"
        cephFS:
          subvolumeGroup: "csi"
    provisioner:
      replicaCount: 1
    storageClass:
      create: true
      name: csi-cephfs-sc
      clusterID: "CEPH_FSID_PLACEHOLDER"
      fsName: cephfs
      reclaimPolicy: Delete
      allowVolumeExpansion: true
      annotations:
        storageclass.kubernetes.io/is-default-class: "true"
```

Since K3s auto-deploy doesn't support templating, a post-bootstrap systemd service should use `envsubst` to inject the actual Ceph FSID and monitor IP before K3s reads the manifest. A subvolumeGroup must be pre-created on the Ceph side: `ceph fs subvolumegroup create cephfs csi`.

---

## Ceph Dashboard enables post-install multi-node expansion

Cephadm bootstrap enables the Dashboard by default at **`https://<host-ip>:8443`** with a self-signed certificate and auto-generated admin password (logged to `/var/log/ceph/cephadm.log`). The Dashboard supports the full multi-node expansion workflow directly from the web UI:

1. **SSH key distribution**: `ceph cephadm get-pub-key > ~/ceph.pub`, then `ssh-copy-id -f -i /etc/ceph/ceph.pub root@<new-host>`
2. **Add host via CLI or Dashboard**: `ceph orch host add <hostname> <ip> --labels=osd`
3. **Automatic OSD provisioning**: Once a host is added with available disks, `ceph orch apply osd --all-available-devices` deploys OSDs automatically

The Dashboard exposes host management, OSD creation, pool management, CephFS administration, and user/role management through a web interface. Custom SSL certificates replace the self-signed default via `ceph dashboard set-ssl-certificate -i /path/to/cert.pem`.

---

## Resource overhead fits workstation constraints

Ceph's memory footprint is tunable for desktop coexistence. With `--skip-monitoring-stack` and memory tuning applied:

| Daemon | Default | Tuned for Desktop |
|--------|---------|-------------------|
| MON | 2 GB | **1 GB** (`mon_memory_target`) |
| MGR | ~400 MB | **~400 MB** |
| OSD (each) | 4 GB | **1 GB** (`osd_memory_target`) |
| MDS | 1 GB+ | **1 GB** (`mds_cache_memory_limit`) |
| **Total Ceph** | **~8 GB** | **~3.4 GB** |

Setting `mgr/cephadm/autotune_memory_target_ratio` to **0.2** caps total Ceph memory to 20% of system RAM. On a **16 GB** system, this allocates ~3.2 GB to Ceph, leaving ~12.8 GB for GNOME, K3s, and workloads. On **8 GB**, the 0.2 ratio yields ~1.6 GB — tight but functional with a single OSD at 1 GB target. The minimum viable configuration requires roughly **4 GB dedicated to Ceph** (1 GB MON + 400 MB MGR + 1 GB OSD + 1 GB MDS + overhead), meaning **8 GB system RAM is the practical floor** for running Ceph + K3s + GNOME concurrently.

---

## Security: SELinux, CephX, msgr2, and firewalld in one pass

### SELinux configuration

The `ceph-selinux` package defines the `ceph_t` process domain and file contexts: `ceph_var_lib_t` for `/var/lib/ceph`, `ceph_log_t` for `/var/log/ceph`, and `ceph_exec_t` for Ceph binaries. For CephFS-mounted directories, the `context=` mount option sets SELinux labels at mount time:

```
Options=secretfile=/etc/ceph/mios.secret,context="system_u:object_r:user_home_dir_t:s0",noatime,_netdev,nofail
```

K3s requires the **`k3s-selinux`** RPM from Rancher (`https://rpm.rancher.io/k3s/stable/common/`). The RPM defines `k3s_data_t` and transitions for the K3s binary. On Rawhide, compatibility may require installing from the latest EL9 build or building from the [k3s-selinux source](https://github.com/k3s-io/k3s-selinux).

### CephX authentication

Msgr2 (port **3300**) supports full AES-128-GCM encryption with `ms_client_mode = secure`. The mount client uses a restricted CephX identity:

```bash
ceph fs authorize cephfs client.mios / rw -o /etc/ceph/ceph.client.mios.keyring
ceph auth get-key client.mios > /etc/ceph/mios.secret
chmod 600 /etc/ceph/mios.secret
```

### Combined firewalld rules

```bash
# Ceph services (Fedora ships predefined service definitions)
firewall-cmd --permanent --add-service=ceph-mon    # 3300, 6789
firewall-cmd --permanent --add-service=ceph        # 6800-7300
firewall-cmd --permanent --add-port=8443/tcp       # Dashboard

# K3s
firewall-cmd --permanent --add-port=6443/tcp       # API server
firewall-cmd --permanent --add-port=10250/tcp      # Kubelet
firewall-cmd --permanent --add-port=8472/udp       # Flannel VXLAN
firewall-cmd --permanent --zone=trusted --add-source=0.0.0.0/16  # Pod CIDR
firewall-cmd --permanent --zone=trusted --add-source=0.0.0.0/16  # Service CIDR
firewall-cmd --reload
```

For encrypted OSDs, cephadm supports `encrypted: true` in OSD service specs, which wraps BlueStore devices in LUKS2 with keys stored securely in the MON database — never written to the OSD disk itself.

---

## Containerfile and build system integration

### Complete Containerfile fragment

```dockerfile
FROM quay.io/fedora/fedora-bootc:rawhide

# === CEPH CLIENT ===
RUN dnf -y install \
    ceph-common \
    cephadm \
    ceph-fuse \
    ceph-selinux \
    && dnf clean all

# === K3s PREREQUISITES ===
RUN dnf -y install \
    container-selinux \
    selinux-policy-base \
    iptables \
    && dnf clean all

# === K3s BINARY ===
ARG K3S_VERSION=v0.1.1+k3s1
ADD https://github.com/k3s-io/k3s/releases/download/${K3S_VERSION}/k3s \
    /usr/local/bin/k3s
RUN chmod 755 /usr/local/bin/k3s && \
    ln -sf /usr/local/bin/k3s /usr/local/bin/kubectl && \
    ln -sf /usr/local/bin/k3s /usr/local/bin/crictl && \
    ln -sf /usr/local/bin/k3s /usr/local/bin/ctr

# === CONFIGURATION FILES ===
COPY etc/modules-load.d/ceph.conf /etc/modules-load.d/ceph.conf
COPY etc/rancher/k3s/config.yaml /etc/rancher/k3s/config.yaml
COPY etc/systemd/system/var-home.mount /etc/systemd/system/
COPY etc/systemd/system/var-lib-containers.mount /etc/systemd/system/
COPY etc/systemd/system/ceph-bootstrap.service /etc/systemd/system/
COPY usr/local/bin/ceph-bootstrap.sh /usr/local/bin/ceph-bootstrap.sh

# === SYSTEMD UNITS ===
COPY usr/lib/systemd/system/k3s.service /usr/lib/systemd/system/
RUN chmod 755 /usr/local/bin/ceph-bootstrap.sh && \
    mkdir -p /etc/rancher/k3s /etc/ceph /var/lib/rancher/k3s \
             /var/lib/ceph /var/log/ceph && \
    systemctl enable k3s.service && \
    systemctl enable var-home.mount && \
    systemctl enable var-lib-containers.mount && \
    systemctl enable ceph-bootstrap.service

RUN bootc container lint
```

### Build script pattern

If the project uses numbered scripts, the integration fits as:

- **`XX-ceph.sh`** — `dnf install ceph-common cephadm ceph-fuse ceph-selinux`, copy kernel module config, create `/var/lib/ceph` and `/var/log/ceph` directories
- **`XX-k3s.sh`** — Download K3s binary, create symlinks, install `container-selinux`, copy systemd unit and config, enable service
- **`XX-firewall.sh`** — Add firewalld rules for Ceph ports (3300, 6789, 6800-7300, 8443) and K3s ports (6443, 10250, 8472)

###  directory additions

```

├── etc/
│   ├── ceph/
│   │   └── ceph.conf                          # Placeholder (populated by bootstrap)
│   ├── modules-load.d/
│   │   └── ceph.conf                          # "ceph\nrbd"
│   ├── rancher/k3s/
│   │   └── config.yaml                        # K3s server config
│   └── systemd/system/
│       ├── var-home.mount                      # CephFS → /var/home
│       ├── var-lib-containers.mount            # CephFS → /var/lib/containers
│       ├── ceph-bootstrap.service              # First-boot bootstrap
│       └── k3s.service.d/
│           └── dependencies.conf               # After=remote-fs.target
└── usr/
    ├── lib/systemd/system/
    │   └── k3s.service                         # K3s systemd unit
    └── local/bin/
        └── ceph-bootstrap.sh                   # Bootstrap script
```

---

## Conclusion

The integration architecture resolves every major constraint. Cephadm's container-native design means **zero server packages in the immutable image** — only the ~15 MB `ceph-common` and `cephadm` client tools. The `nofail` + `ConditionPathExists` pattern for CephFS mounts elegantly handles the first-boot problem without complex fallback logic: before bootstrap, the mount units are simply skipped; after bootstrap writes credentials, they activate on next boot. K3s's built-in Helm controller enables declarative ceph-csi deployment through auto-deploy manifests, avoiding manual Kubernetes operations. The entire stack — Ceph (MON+MGR+OSD+MDS), K3s, and GNOME — fits within **8 GB RAM** with tuned memory targets, scaling gracefully to 16+ GB systems where the `autotune_memory_target_ratio` of 0.2 provides comfortable headroom. The single most important implementation detail: cephadm's `--single-host-defaults` flag combined with post-bootstrap `osd_pool_default_size = 1` creates a minimal viable cluster in under 60 seconds, while the Dashboard on port 8443 provides the web-based multi-node expansion path the user requires for growing beyond a single workstation.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
