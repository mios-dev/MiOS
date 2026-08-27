# AI-hint: Core thesis, nature, designed vs. observed scope, and architectural pillars for MiOS.
# MiOS Core Thesis & Nature

> **Status:** Core Architectural Definition & Scope Statement
> **Classification:** Research Vehicle / Proof of Concept

## 1. What MiOS Is (and Is Not)

**MiOS is a research vehicle and a proof of an idea, not a commercial product.**

Its sole deliverable is **this repository itself**—a self-contained, rebuildable blueprint for an immutable container-workstation and agentic OS runtime. It is designed to demonstrate that an operating system can be synthesized from declarative SSOT configurations, drive its own inference/tooling pipelines, and maintain self-replication discipline across diverse execution targets.

## 2. The Four Pillars of the MiOS Thesis

The MiOS thesis rests on four core hypotheses that stand or fall together:

1. **Immutable Container-OS Foundation**: An operating system represented strictly as an OCI image (`bootc`) provides deterministic, single-artifact upgrade and rollback capabilities (`bootc upgrade` / `bootc rollback`).
2. **Single Local AI Front Door**: All system intelligence, CLI tools, daemons, and IDE integration route through a single local endpoint (`MIOS_AI_ENDPOINT`) fronting function-named inference lanes (`mios-llm-light`, `mios-llm-heavy`).
3. **Repo-Is-Root Self-Replication**: The repository layout directly mirrors the target OS root `/`, allowing the system to inspect, build, repair, and re-create itself using its own in-tree driver pipelines (`/usr/libexec/mios/mios-build-driver`).
4. **Declarative SSOT Governance & Zero-Drift Gates**: All configuration, systemd units, network ports, and image manifests derive from a single source of truth (`usr/share/mios/mios.toml`), strictly policed by automated drift-check gates.

## 3. Scope vs. Observed Runtime Reality

It is essential to distinguish between **designed deployment scope** and **empirically observed environments**:

* **Designed Deployment Scope (Universal Target Shapes)**:
  - Bare-metal live media and installer (`MiOS-Cat` Ventoy/MediCat payload).
  - Edge micro-mesh runtime (`mios-node` 16-byte wire protocol framing).
  - Multi-node blades & Kubernetes expansion (`k3s` + CephFS).
  - Cloud OCI images & Anaconda ISO matrix.
* **Empirically Observed Scope (Tested & Proven)**:
  - **WSL2** (Windows Subsystem for Linux distro target).
  - **Development Virtual Machine** (KVM / QEMU / Hyper-V VM execution).

> [!WARNING]
> Bare-metal installation, edge micro-mesh deployment across heterogeneous physical hardware, and production blade cluster automation represent **designed target shapes** under active research. They are **not** currently certified as fully observed or turnkey production runtime surfaces.
