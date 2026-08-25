<!-- AI-hint: Chapter 01: Introduction and Core Concepts. Defines the dual nature of MiOS as an immutable, bootc Fedora workstation and a local agentic OS. Explains how the Git repository tree directly mirrors the deployed OS filesystem at the system root. Details the non-negotiable mandates: USR-OVER-ETC, NO-MKDIR-IN-VAR, BOUND-IMAGES, etc. -->

# Chapter 01: Introduction and Core Concepts

> Part I: Foundations & Philosophy of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Introduction and Core Concepts** under MiOS.

### <a name="01_what_is_mios"></a>01.What is MiOS: What is MiOS

> Path Reference: `/usr/share/doc/mios/manual.md#01_what_is_mios`

#### Overview

MiOS (pronounced *"MyOS"*) is a specialized operating system built to serve two roles simultaneously:

1. **Immutable Workstation**: It is a Fedora-based, bootc-native OCI container image. The entire OS is compiled, linted, and distributed as a single OCI container. The running system operates on a read-only rootfs (`/usr` composefs/ostree mount), meaning updates are transactional (similar to a `git pull`) and rollbacks are atomic.
2. **Local Agentic AI OS**: It is a sovereign, self-contained AI-powered operating system. The desktop interface is tightly integrated with a local inference engine, model-swapping proxies, an agent router, and pgvector semantic database memory. All agent tools, terminal interfaces, and desktop widgets interact with a unified local endpoint, enabling the system to inspect, run code, and configure itself completely offline.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 1** (Linux kernel): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L39)
- **Row 2** (systemd): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L40)
- **Row 3** (dracut): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L41)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="01_repo_is_root_paradigm"></a>01.Repo IS Root Paradigm: Repo IS Root Paradigm

> Path Reference: `/usr/share/doc/mios/manual.md#01_repo_is_root_paradigm`

#### Overview

The `mios.git` repository root *is* the running host's system root (`/`). There is no temporary build directory, no intermediate staging workspace, and no Ansible configuration playbooks.

- **Structure**: The files in the repository (e.g. `usr/`, `etc/`, `srv/`, `var/`) are mapped directly to their FHS positions on the booted system.
- **Overlay Application**: During the container image build, the script [01-system-files-overlay.sh](automation/01-system-files-overlay.sh) applies the overlay files directly to the rootfs.
- **Developer Workflow**: To change a configuration or utility in the OS, you edit it at its natural path inside the repository and trigger a rebuild. When the OCI image is updated, `bootc` handles the transactional merge on the target machine.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 3** (dracut): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L41)
- **Row 4** (FHS 3.0): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L42)
- **Row 5** (Linux kernel parameters guide): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L43)
- **Row 6** (Linux sysctl reference): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L44)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="01_the_seven_architectural_laws"></a>01.The Architectural Laws: The Architectural Laws

> Path Reference: `/usr/share/doc/mios/manual.md#01_the_seven_architectural_laws`

#### Overview

Governance of MiOS is defined by strict, non-negotiable mandates enforced at
build-time by `automation/97-ssot-lint.sh`, `automation/98-drift-checks.sh` and
`automation/99-postcheck.sh`. The registry below is derived from
`usr/share/mios/mios.toml [laws]`, so it cannot fall behind the law set the way
a hand-written list does — this section previously described seven laws when
there were sixteen.

<!-- MIOS-GEN:laws -->
| # | Law | Applies to | Enforced by |
|---|---|---|---|

<!-- derived from usr/share/mios/mios.toml [laws].laws -->
<!-- /MIOS-GEN:laws -->

Law 6 (UNPRIVILEGED-QUADLETS) permits root only for the units registered in
`[security.privileged_quadlets]`, each with a justification:

<!-- MIOS-GEN:root-exceptions -->
| Quadlet | Runs as root because |
|---|---|

<!-- derived from usr/share/mios/mios.toml [security.privileged_quadlets].root -->
<!-- /MIOS-GEN:root-exceptions -->

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 7** (bootc (CNCF Sandbox)): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L50)
- **Row 8** (ostree / libostree): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L51)
- **Row 9** (composefs): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L52)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
