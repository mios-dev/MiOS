<!-- AI-hint: Chapter 02: Installation and Deployment. Covers provisioning the MiOS-DEV seed environment via Windows PowerShell or the Linux just runner. Outlines the provisioning sequence for the build plane, CDI, libvirt, and AI plane on first boot. Details the continuous CI/CD loop where a running MiOS host builds and updates its own OCI images. -->

# Chapter 02: Installation and Deployment

> Part I: Foundations & Philosophy of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Installation and Deployment** under MiOS.

### <a name="02_day_0_bootstrap"></a>02.Day-0 Bootstrap: Day-0 Bootstrap

> Path Reference: `/usr/share/doc/mios/manual.md#02_day_0_bootstrap`

#### Overview

Day-0 refers to provisioning the initial developer workstation (`MiOS-DEV`) before the OCI image is compiled.

## Windows Bootstrap
The canonical entry is a single command executed from the Windows Run dialog (`Win+R`):
```text
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1 | iex"
```
The script `Get-MiOS.ps1` checks preflight requirements, self-elevates, allocates an `M:\` drive (256 GB NTFS), installs Podman, clones the repository, and triggers the OCI build.

## Linux Bootstrap
Developers on bare-metal Linux can initialize the environment using:
```bash
git clone https://github.com/mios-dev/MiOS.git && cd MiOS
just preflight
just build
```

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 10** (Fedora bootc base images): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L53)
- **Row 11** (RHEL image mode): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L54)
- **Row 12** (Universal Blue): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L63)
- **Row 13** (ucore): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L64)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="02_first_boot_initialization"></a>02.First Boot Initialization: First Boot Initialization

> Path Reference: `/usr/share/doc/mios/manual.md#02_first_boot_initialization`

#### Overview

Once the OCI image is generated and written, the system boots into the First Boot phase (Phase-1 and Phase-2 of the bootstrap chain).

The first-boot sequence processes:
1. **Container Device Interface (CDI)**: Probes physical graphics adapters and renders CDI schemas under `/var/run/cdi/`.
2. **Account Staging**: Staged accounts defined under `/usr/lib/sysusers.d/` are initialized with home directory paths by [11-user.sh](automation/11-user.sh).
3. **Libvirt & Virtualization**: The virtual networking layers, VM templates, and CPU affinity shims are initialized.
4. **AI Services Plane**: The PostgreSQL database and the llama-swap proxy are initialized.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 14** (ucore-hci): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L65)
- **Row 15** (ccos): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L66)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="02_day_n_self_replication"></a>02.Day-N Self Replication: Day-N Self-Replication

> Path Reference: `/usr/share/doc/mios/manual.md#02_day_n_self_replication`

#### Overview

A deployed MiOS host is fully self-replicating. It contains all the compilers, container tools, and build runners required to recreate itself.

## Self-Replication Loop
1. **Local Repository**: An in-distro git server (Forgejo, port 3000) hosts the system configuration repository.
2. **CI/CD Runner**: A containerized runner (`mios-forgejo-runner`) listens for pushes to the system config repository.
3. **Build Target**: When an operator pushes changes to the local repo, the runner triggers a local build and executes a local bootc upgrade: `sudo bootc upgrade --apply` to swap the active root filesystem transactional index.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 11** (RHEL image mode): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L54)
- **Row 16** (Bluefin / Aurora / Bazzite): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L67)
- **Row 17** (Containerfile): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L75)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="02_deployment_targets"></a>02.Deployment Targets: Deployment Targets

> Path Reference: `/usr/share/doc/mios/manual.md#02_deployment_targets`

#### Overview

The compiled OCI container image can be transformed into multiple deployment targets using the bootc-image-builder (BIB) utility.

The `Justfile` provides direct wrappers for compiling these artifacts:
- **Bare-metal**: RAW image for flashing to physical disks (`just raw`)
- **Hyper-V**: VHDX virtual disk with staged UEFI (`just vhdx`)
- **QEMU/KVM**: QCOW2 virtual disk (`just qcow2`)
- **WSL2**: `tar.gz` distribution file (`just wsl2`)
- **ISO**: Anaconda installer ISO for manual setups (`just iso`)

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 18** (Justfile): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L76)
- **Row 19** (Podman): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L77)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
