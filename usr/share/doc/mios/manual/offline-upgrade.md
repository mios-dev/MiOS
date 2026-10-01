<!-- AI-hint: Explains signed offline OCI upgrades and persistent host state. -->
<!-- AI-doc: usr/share/doc/mios/manual/offline-upgrade.md -->

# MiOS Manual: Offline Atomic OCI Upgrade Path

> Section: Core OS Infrastructure & Lifecycle Operations  
> Source Reference: `automation/50-uupd-installer.sh`  
> Applicable Runtimes: MiOS-Metal Bare-Metal Blades, bootc/OSTree Compute Nodes, Air-Gapped Edge Workstations

---

## 1. Overview and Architectural Context

MiOS is an immutable, transactional operating system distributed as an OCI container image and booted via `bootc` and Unified Kernel Images (UKI). In conventional connected environments, updates are pulled continuously from container registries via `uupd.timer` or `bootc-fetch-apply-updates.timer`.

However, mission-critical edge deployments, secure computational blades, and air-gapped installations operate completely disconnected from external wide-area networks (WAN). The **Offline Atomic OCI Upgrade Path** provides a secure, deterministic, and transaction-safe mechanism to upgrade air-gapped MiOS hosts directly from physical USB media or offline external storage carrying standard OCI container image archives or layouts.

### Load-Bearing Invariants Maintained During Upgrade
1. **`/var` Persists by Default (Invariant 1)**: All local machine databases, agent memories in pgvector, container data, and model caches stored under `/var` persist without loss across transactional root filesystem switches.
2. **Unified Kernel Image Signing Chain (Invariant 2)**: The bootloader and kernel signing chain (`shim -> systemd-boot -> signed UKI`) strictly enforces cryptographic authenticity. Any kernel update delivered offline must be encapsulated in a verified signed UKI.
3. **No Driver Intrusion on Driver-Free Passthrough (Invariant 4)**: Host-side VFIO bindings (`vfio-pci`) and graphics configurations remain intact across upgrades.
4. **Blade Ownership & Guest Obfuscation (Invariant 5)**: Hardware-facing roles remain isolated to the host blade, preventing guest plane configuration corruption.

---

## 2. Staging Media Preparation (Online Host)

Before executing an offline upgrade on an air-gapped host, the operator or deployment pipeline prepares an OCI image on external USB media from an internet-connected workstation or CI/CD builder.

### Option A: OCI Directory Layout (Recommended for Fast Local Swapping)
An OCI directory layout adheres to the open OCI Image Specification (`index.json`, `blobs/sha256/*`, `oci-layout`).

```bash
# Format USB media with ext4 or exFAT
# Example: mount USB drive at /media/usb-build

# Export directly from local Podman or Docker daemon
skopeo copy \
    docker-daemon:ghcr.io/mios-dev/mios:latest \
    oci:/media/usb-build/mios-oci:latest

# Or pull directly from the remote container registry
skopeo copy \
    docker://ghcr.io/mios-dev/mios:v0.3.0 \
    oci:/media/usb-build/mios-oci:v0.3.0
```

### Option B: OCI Archive Tarball (Single File Portable Bundle)
An OCI archive packages all layers into a single uncompressed or compressed `.tar` file.

```bash
# Export container image to a single portable OCI archive
skopeo copy \
    docker://ghcr.io/mios-dev/mios:latest \
    oci-archive:/media/usb-build/mios-update-v0.3.0.tar:latest

# Generate SHA256 checksum for cryptographic verification on air-gapped host
cd /media/usb-build
sha256sum mios-update-v0.3.0.tar > mios-update-v0.3.0.tar.sha256
```

---

## 3. Offline Upgrade Execution on the Air-Gapped Host

When the physical USB drive is inserted into the air-gapped host, the media is mounted (e.g. automatically under `/run/media/$USER/<LABEL>` or manually under `/mnt/usb`).

### Automated Workflow via `mios-offline-upgrade`
MiOS provides the `mios-offline-upgrade` command (installed and configured via `automation/50-uupd-installer.sh`), which automates detection, verification, staging, and reboot differentiation.

```bash
# Automated discovery and execution:
# Scans /run/media, /media, /mnt for OCI bundles and executes optimal upgrade
sudo mios-offline-upgrade

# Explicit media specification:
sudo mios-offline-upgrade --media /run/media/admin/USB-DRIVE/mios-oci

# Explicit archive specification:
sudo mios-offline-upgrade --media /run/media/admin/USB-DRIVE/mios-update-v0.3.0.tar

# Dry-run inspection (checks media, compares kernels, reports planned action):
sudo mios-offline-upgrade --media /run/media/admin/USB-DRIVE/mios-oci --dry-run
```

### Manual Step-by-Step Execution
For operators performing granular manual administration, the upgrade consists of three distinct phases:

#### Step 1: Ingesting into Local Container Storage
```bash
# Import the OCI layout or tarball into localhost containers-storage
sudo skopeo copy \
    oci:/run/media/admin/USB-DRIVE/mios-oci \
    containers-storage:localhost/mios:offline-update

# Or import from an OCI archive tarball:
sudo skopeo copy \
    oci-archive:/run/media/admin/USB-DRIVE/mios-update-v0.3.0.tar \
    containers-storage:localhost/mios:offline-update
```

#### Step 2: Transactional Deployment Staging via `bootc switch`
```bash
# Stage the local container image into a new transactional OSTree deployment
sudo bootc switch --transport containers-storage localhost/mios:offline-update

# Alternatively, if direct OCI transport is supported:
sudo bootc switch --transport oci /run/media/admin/USB-DRIVE/mios-oci
```
The `bootc switch` command stages the target root filesystem in an atomic OSTree deployment without disturbing the currently booted and running system.

---

## 4. Kernel vs Userspace Differentiation & Soft-Reboot Mechanics

Traditional operating system updates require a full system power cycle or BIOS/UEFI reboot, incurring hardware initialization delays (RAM training, PCIe link enumeration, IPMI handshakes) that can take several minutes on server blades.

MiOS differentiates between **kernel updates** and **userspace-only updates**, leveraging `systemctl soft-reboot` to apply non-kernel updates in seconds without a BIOS/hardware reboot.

### Differentiation Algorithm
1. **Running Kernel Identification**:
   - Query running kernel release: `RUNNING_KERNEL="$(uname -r)"`
   - Inspect active baked UKI parameters in `/proc/cmdline`.
2. **Staged Kernel Identification**:
   - Query staged deployment modules directory in `/ostree/deploy/mios/deploy/<STAGED_HASH>.0/usr/lib/modules/`.
   - Inspect staged UKI binary: `/usr/lib/modules/<KVER>/vmlinuz` or `/boot/EFI/Linux/*.efi`.
3. **Comparison & Decision Matrix**:
   - **Case A: Kernel Version or UKI Differs**:
     `STAGED_KERNEL != RUNNING_KERNEL` or binary hash mismatch in `vmlinuz`/UKI.
     *Action*: Full power-cycle / firmware reboot (`systemctl reboot`).
     *Rationale*: The running Linux kernel cannot be replaced in-memory without kexec or full bootloader handoff; loading a new UKI with new signed modules requires firmware bootloader execution.
   - **Case B: Kernel Version and UKI Match**:
     `STAGED_KERNEL == RUNNING_KERNEL` and UKI binary identical.
     *Action*: Fast userspace soft-reboot (`systemctl soft-reboot`).
     *Rationale*: The underlying kernel, device drivers, and hardware state remain valid. Only userspace binaries, systemd units, configuration files, and container runtimes have updated.

```
+-------------------------------------------------------------+
|               Staged OCI Update Inspection                  |
+-------------------------------------------------------------+
                              |
              Does staged kernel == uname -r?
             /                               \
           YES                                NO
           /                                   \
   Compare UKI binaries                 Kernel release changed
   and module trees                               |
         /      \                                 |
     MATCH     DIFF                               |
      /          \                                |
     V            V                               V
+---------------+ +-------------------------------------------+
| Userspace-Only| |               Kernel Update               |
|    Update     | |                                           |
|               | | Requires UEFI / UKI bootloader execution  |
| Trigger:      | | Trigger:                                  |
|   systemctl   | |   systemctl reboot                        |
|  soft-reboot  | |                                           |
|               | | Full hardware cycle, RAM training, BIOS   |
| Zero BIOS POST| +-------------------------------------------+
| Minimal delay |
+---------------+
```

### Soft-Reboot Execution
When `systemctl soft-reboot` is executed:
1. Systemd stops all active userspace services and daemon targets in reverse dependency order.
2. Systemd isolates file systems, unmounts userspace filesystems, and pivots root (`switch_root`) into `/run/nextroot` (the newly staged deployment root).
3. Systemd re-executes itself as PID 1 from the new deployment image.
4. Userspace targets (`multi-user.target`, `graphical.target`) initialize fresh with updated binaries.
5. The entire transition occurs in 1–3 seconds, preserving PCIe links, GPU memory reservations, and host networking interfaces without hardware power-cycling.

---

## 5. Verification, Rollback, and Status Reporting

### Verifying the Update
After reboot or soft-reboot, verify that the deployment switched successfully:

```bash
# Verify active deployment status
sudo bootc status

# Check the running kernel
uname -r

# Inspect upgrade transaction history
cat /var/lib/mios/upgrade-history.tsv

# Inspect last upgrade status JSON
cat /run/mios/upgrade-status.json
```

Example `/run/mios/upgrade-status.json`:
```json
{
  "timestamp": "2026-09-29T13:10:00Z",
  "media_path": "/run/media/admin/USB-DRIVE/mios-oci",
  "transport": "oci",
  "running_kernel": "6.11.0-200.fc40.x86_64",
  "staged_kernel": "6.11.0-200.fc40.x86_64",
  "update_type": "userspace-only",
  "recommended_action": "soft-reboot"
}
```

### Greenboot Health Checks and Automated Rollback
MiOS integrates `greenboot` (`greenboot-healthcheck.service`). On boot or soft-reboot:
- Greenboot runs health checks defined in `/usr/lib/greenboot/check/required.d/`.
- If critical system daemons fail or core filesystems fail to initialize within configured retry limits, Greenboot triggers an automatic rollback to the previous deployment.

### Manual Rollback
If an operator needs to roll back immediately:
```bash
# Roll back to the preceding staged deployment
sudo bootc rollback

# Apply rollback:
# For userspace-only rollback:
sudo systemctl soft-reboot

# For kernel-level rollback:
sudo systemctl reboot
```

---

## 6. Troubleshooting and Operational Edge Cases

| Symptom | Probable Cause | Resolution |
| :--- | :--- | :--- |
| `skopeo: command not found` | Offline minimal image lacking tools | Use `podman load -i <archive.tar>` or direct `bootc switch --transport oci <path>`. |
| `bootc switch failed: storage full` | Insufficient space in `/var` | Clear container caches via `podman system prune -a` and ensure `/var` has at least 2x the image uncompressed size. |
| `systemctl soft-reboot failed` | Custom non-reentrant service blocking shutdown | `50-uupd-installer.sh` automatically falls back to `systemctl reboot` on soft-reboot failure. |
| Architecture mismatch warning | Staged image built for aarch64 on x86_64 | Verify container image build architecture with `skopeo inspect oci:<path>`. |
| USB drive not detected | Mount path permissions or missing automount | Mount manually with `sudo mount /dev/sdX1 /mnt/usb` and pass `--media /mnt/usb`. |
