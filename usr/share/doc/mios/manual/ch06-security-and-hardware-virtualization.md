<!-- AI-hint: Chapter 06: Security and Hardware Virtualization. Explains composefs sealing of the read-only /usr directory and fs-verity. Details defense-in-depth mechanisms via CrowdSec, fapolicyd, and USBGuard. Covers OCI validation and authentication via Sigstore and cosign. Documents user permission tiers required to execute services via rootless Podman. -->

# Chapter 06: Security and Hardware Virtualization

> Part II: The Agentic AI Stack of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Security and Hardware Virtualization** under MiOS.

### <a name="06_immutable_root_and_integrity"></a>06.Immutable Root and Integrity: Immutable Root and Integrity

> Path Reference: `/usr/share/doc/mios/manual.md#06_immutable_root_and_integrity`

#### Overview

System integrity on MiOS is guaranteed through cryptographic filesystem sealing:

- **Immutable Directories**: The system binaries under `/usr` are mounted as a read-only composefs image.
- **Integrity Validation**: Files are monitored using `fs-verity`. Any attempt to modify a binary on disk is blocked by the kernel.
- **Upgrades**: Upgrades are delivered as updated OCI image layers. The bootc agent writes the new layers to a separate partition index and atomically updates the EFI boot variables to point to the new composefs root on reboot.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 43** (vLLM): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L116)
- **Row 44** (llama.cpp server): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L117)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="06_runtime_guards"></a>06.Runtime Guards: Runtime Guards

> Path Reference: `/usr/share/doc/mios/manual.md#06_runtime_guards`

#### Overview

To defend against intrusion and unauthorized executions, MiOS deploys three automated guard systems:

1. **fapolicyd**: Denies execution of any binary or script not matching the trust database in `/etc/fapolicyd/fapolicyd.trust`.
2. **USBGuard**: Blocks unauthorized USB device connections to prevent keystroke injection attacks (rules in `/etc/usbguard/usbguard-daemon.conf`).
3. **CrowdSec**: Monitors logs to detect suspicious activities and blocks offending network hosts at the firewall level.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 45** (LM Studio): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L118)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="06_keyless_image_signing"></a>06.Keyless Image Signing: Keyless Image Signing

> Path Reference: `/usr/share/doc/mios/manual.md#06_keyless_image_signing`

#### Overview

To secure the OCI software supply chain, all MiOS OCI images must be cryptographically signed before deployment.

- **Verification Tools**: Integrated via **Sigstore** and **cosign**.
- **Keyless Signature**: In CI/CD pipelines, images are signed using OIDC tokens, verifying that the build originated from the official pipeline.
- **Verification Rule**: The host's container policy config ([49-cosign-policy.sh](automation/49-cosign-policy.sh)) enforces validation check rules, blocking container pulls of unsigned or unrecognized images.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 46** (LiteLLM): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L119)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="06_unprivileged_quadlet_model"></a>06.Unprivileged Quadlet Model: Unprivileged Quadlet Model

> Path Reference: `/usr/share/doc/mios/manual.md#06_unprivileged_quadlet_model`

#### Overview

All daemonized AI containers on MiOS are run inside unprivileged user namespaces to minimize potential host escalation risks.

- **Quadlet Design**: Podman Quadlets are stored under `/usr/share/containers/systemd/`.
- **Least Privilege**: Each Quadlet file must declare `User=mios`, `Group=mios`, and `Delegate=yes` bounds. This maps the container's internal root user (UID 0) to an unprivileged host user (UID 1000+), preventing sandbox escapes from gaining host root access.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 7** (bootc (CNCF Sandbox)): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L50)
- **Row 47** (OpenRouter): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L120)
- **Row 48** (llama.cpp (engine)): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L121)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="06_hardware_passthrough"></a>06.Hardware Passthrough: Hardware Passthrough

> Path Reference: `/usr/share/doc/mios/manual.md#06_hardware_passthrough`

#### Overview

For high-performance AI inference and gaming, MiOS isolates and passes physical graphics cards directly to VM and container environments.

- **VFIO Isolation**: Target GPUs are bound to the `vfio-pci` driver during boot, disabling the host display driver.
- **Libvirt Integration**: VMs request GPU resources via direct PCI pass-through paths.
- **Container Acceleration**: Containers request GPU hardware using CDI (Container Device Interface) profiles generated dynamically based on active hardware, allowing CUDA runtimes to execute in rootless Podman tasks.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 1** (Linux kernel): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L39)
- **Row 49** (API Reference (root)): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L130)
- **Row 50** (Models catalog): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L131)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
