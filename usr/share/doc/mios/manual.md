<!-- AI-hint: Unified All-in-One User Manual for MiOS. Consolidates all 50 chapters and 152 pages into a single document. -->
# MiOS All-in-One User Manual & System Documentation

Welcome to the comprehensive, All-in-One User Manual and System Documentation for **MiOS** (pronounced *"MyOS"*). 

This unified document consolidates the entire 50-chapter documentation suite, detailing the system's dual nature as an immutable, bootc-managed Fedora workstation and a sovereign, offline-first agentic AI OS.

---

## Table of Contents

### Part I: Foundations & Philosophy
* **Chapter 01: Introduction and Core Concepts**
  * [What is MiOS](#01_what_is_mios): Defines the dual nature of MiOS as an immutable, bootc Fedora workstation and a local agentic OS.
  * [Repo IS Root Paradigm](#01_repo_is_root_paradigm): Explains how the Git repository tree directly mirrors the deployed OS filesystem at the system root.
  * [The Seven Architectural Laws](#01_the_seven_architectural_laws): Details the non-negotiable mandates: USR-OVER-ETC, NO-MKDIR-IN-VAR, BOUND-IMAGES, etc.
* **Chapter 02: Installation and Deployment**
  * [Day-0 Bootstrap](#02_day_0_bootstrap): Covers provisioning the MiOS-DEV seed environment via Windows PowerShell or the Linux just runner.
  * [First Boot Initialization](#02_first_boot_initialization): Outlines the provisioning sequence for the build plane, CDI, libvirt, and AI plane on first boot.
  * [Day-N Self-Replication](#02_day_n_self_replication): Details the continuous CI/CD loop where a running MiOS host builds and updates its own OCI images.
  * [Deployment Targets](#02_deployment_targets): Provides recipes for deploying the MiOS image to bare-metal hosts, VHDX, RAW, WSL2, and ISO.
* **Chapter 03: System Configuration and Governance**
  * [Single Source of Truth](#03_single_source_of_truth): Explains the management of packages, AI lanes, and quadlets centrally via mios.toml.
  * [Three-Layer Override Model](#03_three_layer_override_model): Maps configuration resolution precedence across vendor, host, and user levels.
  * [Declarative Package Management](#03_declarative_package_management): Documents DNF5 integration, flatpak configurations, and the separation of PACKAGES.md.

### Part II: The Agentic AI Stack
* **Chapter 04: The Agentic AI Stack**
  * [Unified AI Endpoint](#04_unified_ai_endpoint): Describes the routing of all AI interactions through the MIOS_AI_ENDPOINT on port 8080.
  * [Agent Pipe Orchestrator](#04_agent_pipe_orchestrator): Details the primary front door on port 8640 used to route requests and fan out tasks.
  * [MiOS Hermes Gateway](#04_mios_hermes_gateway): Outlines the operation of the tool-loop gateway and session manager running on port 8642.
  * [Inference Lanes](#04_inference_lanes): Maps the local token generation engines, llama.cpp proxy, and VRAM-gated heavy lanes.
  * [Unified Agent Memory](#04_unified_agent_memory): Covers episodic and long-term knowledge storage using PostgreSQL and pgvector.
* **Chapter 05: Federation and Computer Use**
  * [Model Context Protocol](#05_model_context_protocol): Details the standardized MCP interface utilized by agents to discover external tools.
  * [Agent-to-Agent Delegation](#05_agent_to_agent_delegation): Documents the A2A JSON-RPC specifications for peer delegation.
  * [Vision and OS Control](#05_vision_and_os_control): Explains Wayland automation, vision grounding via UI-TARS, and pc-control tools.
* **Chapter 06: Security and Hardware Virtualization**
  * [Immutable Root and Integrity](#06_immutable_root_and_integrity): Explains composefs sealing of the read-only /usr directory and fs-verity.
  * [Runtime Guards](#06_runtime_guards): Details defense-in-depth mechanisms via CrowdSec, fapolicyd, and USBGuard.
  * [Keyless Image Signing](#06_keyless_image_signing): Covers OCI validation and authentication via Sigstore and cosign.
  * [Unprivileged Quadlet Model](#06_unprivileged_quadlet_model): Documents user permission tiers required to execute services via rootless Podman.
  * [Hardware Passthrough](#06_hardware_passthrough): Maps GPU exposure to virtual machines and containers via VFIO-PCI and CDI.
* **Chapter 07: Cluster and Storage Fabric**
  * [K3s Kubernetes Integration](#07_k3s_kubernetes_integration): Outlines the mechanisms for expanding the workstation into a Kubernetes cluster.
  * [Ceph Distributed Storage](#07_ceph_distributed_storage): Explains CephFS containerized storage deployments and privileged exemptions.

### Part III: Core OS Infrastructure
* **Chapter 08: Bootloader and Unified Kernel Images (UKI)**
  * [UKI Layout and Baking](#08_uki_layout_and_baking): Covers compilation and structure of Unified Kernel Images via systemd-ukify.
  * [Secure Boot Integrity](#08_secure_boot_integrity): Details kernel module signing, trust models, and cryptographic verification chains.
  * [Kernel Arguments and Gating](#08_kernel_arguments_and_gating): Explains static kernel arguments in kargs.d mapping to VM and GPU isolation.
* **Chapter 09: Systemd and Quadlet Orchestration**
  * [Unprivileged Systemd Tiers](#09_unprivileged_systemd_tiers): Defines user-space daemon layers and systemd-generator permissions configuration.
  * [Quadlet Configuration Syntax](#09_quadlet_configuration_syntax): Explains how podman quadlets render systemd unit files on startup.
  * [Dynamic Service Activation](#09_dynamic_service_activation): Details service lifecycle states triggered by sync-env or user edits.

### Part IV: Detailed Inference & Execution Layers
* **Chapter 10: Local Inference Lanes and llama.cpp**
  * [Llama-Swap Proxy Architecture](#10_llama_swap_proxy_architecture): Covers how llama-swap handles hot swapping and KV paging on port 11450.
  * [Embedded Inference Setup](#10_embedded_inference_setup): Maps GPU context management, prompt template bindings, and model formats.
  * [Model Map and Hot Swapping](#10_model_map_and_hot_swapping): Documents model map configuration file and resource optimization strategies.
* **Chapter 11: Heavy GPU Lanes and SGLang/vLLM**
  * [SGLang GPU Gating Policies](#11_sglang_gpu_gating_policies): Defines how SGLang is conditionally run depending on VRAM and workloads.
  * [vLLM Swarm Workers](#11_vllm_swarm_workers): Explains multi-model scaling and distributed worker configurations.
  * [VRAM Allocation and Scheduling](#11_vram_allocation_and_scheduling): Covers pre-allocation thresholds and dynamic offloading policies.
* **Chapter 12: Unified Memory and pgvector Schema**
  * [PostgreSQL Integration](#12_postgresql_integration): Details pgvector database container setup, connection pools, and permissions.
  * [Semantic Knowledge Recall](#12_semantic_knowledge_recall): Explains cosine-similarity searches utilizing vector retrieval.
  * [Epistemic Memory Pruning](#12_epistemic_memory_pruning): Covers background archival workers and semantic consolidation.
* **Chapter 13: Model Context Protocol Integration**
  * [Custom MCP Server Design](#13_custom_mcp_server_design): Describes how to write custom Python or Go MCP servers.
  * [Tool Discovery Protocols](#13_tool_discovery_protocols): Covers how the AI gateway queries the system tool registry.
  * [Security Sandboxing for MCP](#13_security_sandboxing_for_mcp): Details how tools run in sandboxed namespaces to prevent host escapes.
* **Chapter 14: Agent-to-Agent Delegation Protocols**
  * [JSON-RPC Delegation Specification](#14_json_rpc_delegation_specification): Details the communications standard and payload schema for agent delegation.
  * [OpenCode Specialist Handoffs](#14_opencode_specialist_handoffs): Explains how the coding subagent (MiOS-OpenCode) takes over code modification.
  * [Peer-to-Peer Trust Models](#14_peer_to_peer_trust_models): Defines the capability-based security mapping across cooperative agents.
* **Chapter 15: Computer Use and Desktop Control**
  * [UI-TARS Vision Grounding](#15_ui_tars_vision_grounding): Details coordinate grounding on Wayland screens via vision models.
  * [Wayland Input Automation](#15_wayland_input_automation): Explains input emulation via the mios-pc-control command suite.
  * [AT-SPI Accessibility Tuning](#15_at_spi_accessibility_tuning): Documents screen tree traversal for structural UI reasoning.

### Part V: Deep Security, Cryptography & Hardware
* **Chapter 16: Immutable Root and Composefs Sealing**
  * [Composefs Read-Only Mounts](#16_composefs_read_only_mounts): Explains composefs structures and /usr partition read-only mounts.
  * [fs-verity Signature Verification](#16_fs_verity_signature_verification): Covers system file validation against trusted cryptographic hashes.
  * [Host Upgrade Reconciliation](#16_host_upgrade_reconciliation): Describes how upgrades resolve changes between base and current states.
* **Chapter 17: Defense in Depth Hardening**
  * [CrowdSec Intrusion Prevention](#17_crowdsec_intrusion_prevention): Covers telemetry monitoring, IP bans, and custom local parsers.
  * [fapolicyd Application Whitelisting](#17_fapolicyd_application_whitelisting): Details binary execution blocking on unauthorized directories.
  * [USBGuard Hardware Control](#17_usbguard_hardware_control): Explains protection policies against rogue USB devices.
* **Chapter 18: Supply Chain and Image Integrity**
  * [Sigstore Verification Policies](#18_sigstore_verification_policies): Defines policy-based verification of OCI signatures at pull time.
  * [Keyless Cosign Signing](#18_keyless_cosign_signing): Covers keyless image signing using OIDC identity providers.
  * [Build-Time Attestation](#18_build_time_attestation): Explains the generation and verification of build SBOMs.
* **Chapter 19: Hardware Passthrough and VFIO-PCI**
  * [GPU Isolation via VFIO](#19_gpu_isolation_via_vfio): Details binding GPUs to vfio-pci on boot, bypassing host drivers.
  * [Libvirt PCI Routing](#19_libvirt_pci_routing): Explains the XML schema mapping for physical GPU passthrough to guests.
  * [Guest Drivers Enforcement](#19_guest_drivers_enforcement): Documents driver setups in guest OS to avoid error codes.
* **Chapter 20: Container Device Interface Plumbing**
  * [Nvidia CDI Automation](#20_nvidia_cdi_automation): Covers CDI spec generation for CUDA applications running in rootless podman.
  * [AMD ROCm CDI Mappings](#20_amd_rocm_cdi_mappings): Explains ROCm/KFD driver mounts and container bindings.
  * [Intel GPU CDI Specs](#20_intel_gpu_cdi_specs): Documents Intel graphics acceleration CDI specs.
* **Chapter 21: Looking Glass B7 and KVMFR**
  * [KVMFR Kernel Module Bake](#21_kvmfr_kernel_module_bake): Explains building and signing KVMFR module from source.
  * [Shared Memory Framebuffer](#21_shared_memory_framebuffer): Details allocations under /dev/shm for low-latency memory copy.
  * [Looking Glass Client Setup](#21_looking_glass_client_setup): Documents Wayland client build and input mappings.
* **Chapter 22: CPU Topology and Performance Pinning**
  * [Thread Allocation Strategies](#22_thread_allocation_strategies): Maps CPU pinning allocations for isolated workloads.
  * [NUMA Node Awareness](#22_numa_node_awareness): Details memory node alignment for reduced guest latencies.
  * [Low-Latency VM Tuning](#22_low_latency_vm_tuning): Covers scheduling priority and emulatorpin adjustments.

### Part VI: Storage, Network & Web Planes
* **Chapter 23: Single-Node Kubernetes Expansion**
  * [K3s Workstation Coexistence](#23_k3s_workstation_coexistence): Covers resource boundaries between GNOME and K3s services.
  * [Local Ingress and Routing](#23_local_ingress_and_routing): Details ingress routing rules in single-node clusters.
  * [K3s SELinux Policy Enforcement](#23_k3s_selinux_policy_enforcement): Explains custom security policies allowing cluster containers.
* **Chapter 24: CephFS Local Storage Cluster**
  * [Containerized Ceph Deployments](#24_containerized_ceph_deployments): Covers Ceph Quadlet definitions and storage config.
  * [Storage Daemon Permissions](#24_storage_daemon_permissions): Details block device access exemptions.
  * [XDG Directory Integrations](#24_xdg_directory_integrations): Maps user directories onto CephFS mounts for auto-backups.
* **Chapter 25: Local Search Engine and SearXNG**
  * [SearXNG Sovereign Search](#25_searxng_sovereign_search): Explains local container setup and engines configuration.
  * [Agent Search API Plumbing](#25_agent_search_api_plumbing): Covers query routing from search tools to SearXNG.
  * [Web Scraping and Ingest](#25_web_scraping_and_ingest): Details parsing HTML results into Markdown for LLM ingestion.
* **Chapter 26: Unified Knowledge Base Ingestion**
  * [Document Parsing and Embedding](#26_document_parsing_and_embedding): Explains document indexing and embedding tasks.
  * [Ingest Pipeline Schema](#26_ingest_pipeline_schema): Maps ingestion pipeline and database tables layout.
  * [Semantic Indexing Maintenance](#26_semantic_indexing_maintenance): Covers re-indexing databases and recall optimizations.
* **Chapter 27: Shell Configuration and Environment Cascade**
  * [Environment Defaults and Precedence](#27_environment_defaults_and_precedence): Maps configuration overrides bubbling up to login shells.
  * [Oh My Posh Prompt Theming](#27_oh_my_posh_prompt_theming): Covers theme configuration and prompt status icons.
  * [User Locale Standardization](#27_user_locale_standardization): Documents timezone and UTF-8 locale staging setups.
* **Chapter 28: Dynamic Network and Firewall Management**
  * [Firewalld Rule Generation](#28_firewalld_rule_generation): Covers managing port firewalls via firewalld command hooks.
  * [Dynamic Port Allocation](#28_dynamic_port_allocation): Explains how ports are dynamically resolved and bound.
  * [VPN and Tailscale Routing](#28_vpn_and_tailscale_routing): Documents Tailscale integration with system firewall rules.
* **Chapter 29: Web Management and Configurator UI**
  * [MiOS HTML TOML Editor](#29_mios_html_toml_editor): Covers configuration editing via the static index HTML form.
  * [Host-to-Container Portal](#29_host_to_container_portal): Details how the UI panel maps active container metrics.
  * [Settings Sync Mechanisms](#29_settings_sync_mechanisms): Explains TOML serialization and service reload hooks.

### Part VII: Build, Test & Upstream Maintenance
* **Chapter 30: System Auditing and Drift Verification**
  * [Automated Postcheck Suite](#30_automated_postcheck_suite): Documents checks run by 99-postcheck.sh at build-time.
  * [Hardcode Lint Rules](#30_hardcode_lint_rules): Explains build constraints blocking hardcoded URLs or ports.
  * [Security Policy Compliance](#30_security_policy_compliance): Maps validation against our target zero-trust hardening profile.
* **Chapter 31: Desktop Applications and Flatpaks**
  * [Declarative Flatpak Bake](#31_declarative_flatpak_bake): Covers pre-downloading and staging Flatpaks inside the image.
  * [Application Permissions Gating](#31_application_permissions_gating): Explains locking Flatpak permissions using Flatseal overrides.
  * [Desktop Shortcuts Sync](#31_desktop_shortcuts_sync): Details sync hooks registering menus and MIME shortcuts.
* **Chapter 32: Swarm Worker Clusters**
  * [Swarm Node Provisioning](#32_swarm_node_provisioning): Covers dynamic worker provisioning via Quadlet templates.
  * [Dynamic Fanout Orchestration](#32_dynamic_fanout_orchestration): Details task partitioning and worker aggregation pipelines.
  * [Load Balancing Lanes](#32_load_balancing_lanes): Explains scheduling and routing algorithms across worker processes.
* **Chapter 33: Sandboxed Execution and Coder Sandbox**
  * [Coder Sandbox Quadlet](#33_coder_sandbox_quadlet): Covers configuring unprivileged containers for code interpretation.
  * [SELinux Sandbox Policies](#33_selinux_sandbox_policies): Details how policies restrict container sandbox processes.
  * [Safe Code Interpretation](#33_safe_code_interpretation): Explains output validation and script execution controls.
* **Chapter 34: Identity Management and FreeIPA**
  * [FreeIPA Client Configuration](#34_freeipa_client_configuration): Covers configuring FreeIPA libraries inside Fedora overlay.
  * [Enforced User Sysusers](#34_enforced_user_sysusers): Details staging user and system accounts prior to install.
  * [Domain Join Automation](#34_domain_join_automation): Explains automatic domain enrollment on first boot.
* **Chapter 35: System Monitoring and Telemetry**
  * [Prometheus Exporter Setup](#35_prometheus_exporter_setup): Covers collecting CPU, RAM, and GPU stats via node-exporters.
  * [AI Gateway Telemetry](#35_ai_gateway_telemetry): Details tracking query duration, tokens, and routing lanes.
  * [Grafana_Dashboard_Profiles](#35_grafana_dashboard_profiles): Maps visual dashboards for monitoring resource use.
* **Chapter 36: Greenboot Health Check and Recovery**
  * [Automatic OS Health Checks](#36_automatic_os_health_checks): Covers greenboot scripts verifying service states.
  * [Rollback Trigger Policies](#36_rollback_trigger_policies): Explains atomic image swap checks triggered on boot failures.
  * [Recovery State Scripts](#36_recovery_state_scripts): Documents dynamic cleanup tasks executed during recoveries.
* **Chapter 37: GPU Capability Detection and Passthrough Shims**
  * [CDI Refresh Mechanisms](#37_cdi_refresh_mechanisms): Covers spec updates triggered when hardware states change.
  * [Runtime GPU Gating](#37_runtime_gpu_gating): Details device locking and lockouts during state transitions.
  * [Dynamic Driver Loading](#37_dynamic_driver_loading): Explains dynamic module load decisions during bootstrap.
* **Chapter 38: Remote Desktop and GNOME GRD**
  * [Remote Wayland Sessions](#38_remote_wayland_sessions): Covers running GNOME inside headless Wayland sessions.
  * [Secure RDP Authentication](#38_secure_rdp_authentication): Details TLS encryption and user credential checks.
  * [Headless Desktop Toggle](#38_headless_desktop_toggle): Documents setting up virtual display outputs on headless hosts.
* **Chapter 39: Host-Guest Shared Filesystems**
  * [Virtiofs Performance Tuning](#39_virtiofs_performance_tuning): Covers high-speed file sharing cache configurations.
  * [Shared Directories Overlay](#39_shared_directories_overlay): Details exposing system paths inside guest virtual overlays.
  * [Permission Translation Models](#39_permission_translation_models): Explains UID/GID mappings translation across OS barriers.
* **Chapter 40: System Log Aggregation**
  * [Journald Sync to Bootstrap](#40_journald_sync_to_bootstrap): Covers sync hooks pulling logs into bootstrap sectors.
  * [Log-Copy Daemon Configuration](#40_log_copy_daemon_configuration): Details systemd service parameters for log copy tasks.
  * [Diagnostic Log Bundles](#40_diagnostic_log_bundles): Explains compiling system diagnostics into single archives.
* **Chapter 41: Machine Owner Key Management**
  * [Private Key Generation](#41_private_key_generation): Covers generating secure build-keys inside automation.
  * [Secure Boot Enrollment Flow](#41_secure_boot_enrollment_flow): Details UEFI enrollment prompts triggered on boots.
  * [Automatic Module Signing](#41_automatic_module_signing): Explains dynamic module signatures added on kernel upgrades.
* **Chapter 42: Kernel Upgrade and Build Pipelines**
  * [Stable LTS Kernel Updates](#42_stable_lts_kernel_updates): Covers base image upgrades and validation procedures.
  * [Akmod Compilation Guards](#42_akmod_compilation_guards): Details compilation gating rules verifying module states.
  * [BIB Disk Image Generation](#42_bib_disk_image_generation): Explains bootc-image-builder actions transforming OCI tags.
* **Chapter 43: Local Registry and OCI Distribution**
  * [Private Registry Quadlets](#43_private_registry_quadlets): Covers OCI distribution containers used in replication loop.
  * [Image Caching Strategies](#43_image_caching_strategies): Details cache boundaries speeding up successive image builds.
  * [Deployed Ref Updates](#43_deployed_ref_updates): Explains pulling local registries and switching host roots.
* **Chapter 44: Host Package Overrides and DNF5**
  * [USR vs ETC Overrides](#44_usr_vs_etc_overrides): Covers configurations prioritization mappings.
  * [RPM-OSTree Exemptions](#44_rpm_ostree_exemptions): Details manual package installations resolving hardware conflicts.
  * [Dependency Conflict Resolution](#44_dependency_conflict_resolution): Explains troubleshooting procedures for dnf packages errors.
* **Chapter 45: Diagnostic Tools and Profilers**
  * [Hardware Capability Profiling](#45_hardware_capability_profiling): Covers physical adapter checks run by system-profilers.
  * [Egress Firewall Verification](#45_egress_firewall_verification): Details checks verifying container loopback containment.
  * [Profile Comparison Utilities](#45_profile_comparison_utilities): Explains comparing active setups against templates.
* **Chapter 46: User Persona Staging**
  * [Default User Creation](#46_default_user_creation): Covers default accounts, credentials, and settings groups.
  * [Stagings Dotfiles Overlay](#46_stagings_dotfiles_overlay): Details template overlay merging home profile files.
  * [Multi-User Sandboxes](#46_multi_user_sandboxes): Explains isolation policies across different accounts.
* **Chapter 47: Virtual Machine Templates**
  * [Windows 11 SecureBoot XML](#47_windows_11_secureboot_xml): Details template variables enabling vTPM and Secure Boot.
  * [Linux Guest Cloud-Init](#47_linux_guest_cloud_init): Covers automating guest staging using init data.
  * [VM Lifecycle Management](#47_vm_lifecycle_management): Explains hypervisor guest actions executed via virsh.
* **Chapter 48: Local AI Web Consoles**
  * [Open WebUI Deployment](#48_open_webui_deployment): Covers Open WebUI Quadlet parameters and local mapping.
  * [Interface Customization](#48_interface_customization): Details interface layout settings and custom models aliases.
  * [Token-based Access Control](#48_token_based_access_control): Explains console access security using token authentication.
* **Chapter 49: Offline-First Governance**
  * [Local Package Mirrors](#49_local_package_mirrors): Covers staging local mirror caches inside container build overlay.
  * [Sovereign Model Storage](#49_sovereign_model_storage): Details models weights verification loaded under /srv/ai.
  * [Non-Network Degradation Modes](#49_non_network_degradation_modes): Explains fallback behaviors resolving missing active gateways.
* **Chapter 50: Upstream Tracking and Maintenance**
  * [Upstream Drift Monitor](#50_upstream_drift_monitor): Covers checking changes between host and remote overlays.
  * [Justfile Pipeline Automation](#50_justfile_pipeline_automation): Details Justfile build automation and check goals.
  * [Release Maturity Runbook](#50_release_maturity_runbook): Explains checklist targets required to tag release stages.

---

# Part I: Foundations & Philosophy

## Chapter 01: Introduction and Core Concepts

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
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="01_repo_is_root_paradigm"></a>01.Repo IS Root Paradigm: Repo IS Root Paradigm

> Path Reference: `/usr/share/doc/mios/manual.md#01_repo_is_root_paradigm`

#### Overview

The `mios.git` repository root *is* the running host's system root (`/`). There is no temporary build directory, no intermediate staging workspace, and no Ansible configuration playbooks.

- **Structure**: The files in the repository (e.g. `usr/`, `etc/`, `srv/`, `var/`) are mapped directly to their FHS positions on the booted system.
- **Overlay Application**: During the container image build, the script [08-system-files-overlay.sh](file:///C:/MiOS/automation/08-system-files-overlay.sh) applies the overlay files directly to the rootfs.
- **Developer Workflow**: To change a configuration or utility in the OS, you edit it at its natural path inside the repository and trigger a rebuild. When the OCI image is updated, `bootc` handles the transactional merge on the target machine.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 3** (dracut): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L41)
- **Row 4** (FHS 3.0): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L42)
- **Row 5** (Linux kernel parameters guide): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L43)
- **Row 6** (Linux sysctl reference): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L44)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="01_the_seven_architectural_laws"></a>01.The Seven Architectural Laws: The Seven Architectural Laws

> Path Reference: `/usr/share/doc/mios/manual.md#01_the_seven_architectural_laws`

#### Overview

Governance of MiOS is defined by seven strict, non-negotiable mandates enforced at build-time by [38-ssot-lint.sh](file:///C:/MiOS/automation/38-ssot-lint.sh), [38-drift-checks.sh](file:///C:/MiOS/automation/38-drift-checks.sh), and [99-postcheck.sh](file:///C:/MiOS/automation/99-postcheck.sh):

1. **USR-OVER-ETC**: Static system configs must reside in `/usr/lib/<component>.d/`. The `/etc/` directory is reserved solely for administrative overrides.
2. **NO-MKDIR-IN-VAR**: Build-time scripts must never call `mkdir` inside `/var/`. All `/var/` paths must be declared declaratively via `usr/lib/tmpfiles.d/*.conf`.
3. **BOUND-IMAGES**: Every Podman Quadlet container image must be symlinked under `/usr/lib/bootc/bound-images.d/` and baked into `/usr/lib/containers/storage` at build-time.
4. **BOOTC-CONTAINER-LINT**: The last instruction of the `Containerfile` must be `RUN bootc container lint`. A failing lint fails the build.
5. **UNIFIED-AI-REDIRECTS**: All local services, tools, and agents must communicate with `MIOS_AI_ENDPOINT` (defaulting to `http://localhost:8080/v1`). No vendor-hardcoded URLs are allowed.
6. **UNPRIVILEGED-QUADLETS**: All Quadlet units must declare `User=`, `Group=`, and `Delegate=yes` configuration bounds. The only exceptions are `mios-ceph` and `mios-k3s` (which require root block device access).
7. **NO-HARDCODE**: Nothing operator-tunable, including model names, ports, or scoring parameters, may be hardcoded. Values must resolve via the `mios.toml` configuration cascade.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 7** (bootc (CNCF Sandbox)): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L50)
- **Row 8** (ostree / libostree): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L51)
- **Row 9** (composefs): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L52)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 02: Installation and Deployment

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
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="02_first_boot_initialization"></a>02.First Boot Initialization: First Boot Initialization

> Path Reference: `/usr/share/doc/mios/manual.md#02_first_boot_initialization`

#### Overview

Once the OCI image is generated and written, the system boots into the First Boot phase (Phase-1 and Phase-2 of the bootstrap chain).

The first-boot sequence processes:
1. **Container Device Interface (CDI)**: Probes physical graphics adapters and renders CDI schemas under `/var/run/cdi/`.
2. **Account Staging**: Staged accounts defined under `/usr/lib/sysusers.d/` are initialized with home directory paths by [31-user.sh](file:///C:/MiOS/automation/31-user.sh).
3. **Libvirt & Virtualization**: The virtual networking layers, VM templates, and CPU affinity shims are initialized.
4. **AI Services Plane**: The PostgreSQL database and the llama-swap proxy are initialized.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 14** (ucore-hci): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L65)
- **Row 15** (ccos): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L66)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
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
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
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
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 03: System Configuration and Governance

This chapter covers the documentation for **System Configuration and Governance** under MiOS.

### <a name="03_single_source_of_truth"></a>03.Single Source Of Truth: Single Source of Truth

> Path Reference: `/usr/share/doc/mios/manual.md#03_single_source_of_truth`

#### Overview

System configuration on MiOS is managed centrally via one configuration format: `mios.toml`.

This file controls user parameters, package selections, Flatpaks, AI stack configurations, and hardware allocations. A graphical configurator tool is shipped at [mios.html](file:///C:/MiOS/usr/share/mios/configurator/mios.html). Running `sudo mios-sync-env` refreshes `/etc/mios/install.env` to align systemd environment variables.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 20** (Buildah): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L78)
- **Row 21** (Skopeo): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L79)
- **Row 22** (dnf5): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L80)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="03_three_layer_override_model"></a>03.Three Layer Override Model: Three-Layer Override Model

> Path Reference: `/usr/share/doc/mios/manual.md#03_three_layer_override_model`

#### Overview

Configuration resolution follows a strict three-layer precedence model to ensure system immutable integrity while allowing flexible per-user settings:

1. `~/.config/mios/mios.toml` -- per-user override (highest precedence)
2. `/etc/mios/mios.toml` -- host/admin override (shipped by bootstrap)
3. `/usr/share/mios/mios.toml` -- vendor defaults (shipped by image, lowest precedence)

All settings are merged key-by-key at runtime, where higher layers supersede lower layers.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 23** (bootc-image-builder (BIB)): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L81)
- **Row 24** (image-builder-cli): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L82)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="03_declarative_package_management"></a>03.Declarative Package Management: Declarative Package Management

> Path Reference: `/usr/share/doc/mios/manual.md#03_declarative_package_management`

#### Overview

To ensure that the root remains clean and deterministic, packages are declared statically in the system configuration.

- **System Packages**: Declared in `/usr/share/mios/mios.toml` under `[packages.<section>].pkgs` and installed using DNF5.
- **Flatpaks**: Desktop GUI apps are declared in the same file under `[flatpaks]` and baked into the image Flatpak store.
- **Package Rationale**: Human-readable descriptions are documented in [PACKAGES.md](file:///C:/MiOS/usr/share/doc/mios/reference/PACKAGES.md).

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 25** (rechunk): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L83)
- **Row 26** (Anaconda): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L84)
- **Row 27** (Renovate): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L85)
- **Row 28** (GitHub Actions): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L86)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

# Part II: The Agentic AI Stack

## Chapter 04: The Agentic AI Stack

This chapter covers the documentation for **The Agentic AI Stack** under MiOS.

### <a name="04_unified_ai_endpoint"></a>04.Unified AI Endpoint: Unified AI Endpoint

> Path Reference: `/usr/share/doc/mios/manual.md#04_unified_ai_endpoint`

#### Overview

To avoid hardcoded vendor SDK dependencies, all intelligence pipelines on MiOS are routed through a single local endpoint on loopback: `http://localhost:8080/v1` (`MIOS_AI_ENDPOINT`). This endpoint abstractly translates chat-completions and embeddings requests to the active inference backend, ensuring client compatibility.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 1** (Linux kernel): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L39)
- **Row 29** (GHCR): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L87)
- **Row 30** (Sigstore / cosign): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L88)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="04_agent_pipe_orchestrator"></a>04.Agent Pipe Orchestrator: Agent Pipe Orchestrator

> Path Reference: `/usr/share/doc/mios/manual.md#04_agent_pipe_orchestrator`

#### Overview

The Agent Pipe Orchestrator (port **8640**) acts as the cognitive router for all user-facing interfaces.

When a prompt is submitted, the orchestrator performs intention refinement, decomposes the query into a task graph, coordinates sub-agents, executes tool loops, and streams aggregated answers back to client views.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 31** (syft): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L89)
- **Row 32** (shellcheck): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L90)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="04_mios_hermes_gateway"></a>04.MiOS Hermes Gateway: MiOS Hermes Gateway

> Path Reference: `/usr/share/doc/mios/manual.md#04_mios_hermes_gateway`

#### Overview

MiOS Hermes (port **8642**) is the core session and tool-loop execution manager.

- **Session Ownership**: Tracks state and history for active contexts.
- **Tool-Loop Execution**: Validates and executes tool calls sent by LLMs.
- **Skills Management**: Manages reusable python code blocks ("skills") loaded from system configurations.
- **Telemetry**: Exposes the Hermes Dashboard on port 9119 to monitor session states and tool logs.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 31** (syft): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L89)
- **Row 33** (hadolint): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L91)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="04_inference_lanes"></a>04.Inference Lanes: Inference Lanes

> Path Reference: `/usr/share/doc/mios/manual.md#04_inference_lanes`

#### Overview

MiOS splits LLM inference across separate functional lanes to match the host hardware resources:

1. **Light Lane (`mios-llm-light`)**: Running llama.cpp with a llama-swap proxy on port `11450` for everyday chat, code assistance, and embeddings.
2. **Heavy Lane (`mios-llm-heavy` / `mios-llm-heavy-alt`)**: Running SGLang (port `11441`) or vLLM (port `11440`) for large reasoning models, gated off by default.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 34** (openssl): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L92)
- **Row 35** (Podman Quadlet): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L98)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="04_unified_agent_memory"></a>04.Unified Agent Memory: Unified Agent Memory

> Path Reference: `/usr/share/doc/mios/manual.md#04_unified_agent_memory`

#### Overview

The persistent memory plane of MiOS is structured within a PostgreSQL database with the `pgvector` extension, running inside the `mios-pgvector` container (port 5432).

It stores raw session logs as episodic memory, and vector-embedded knowledge chunks as semantic memory. Dynamic cosine-similarity searches inject historical context directly into agent prompts.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 1** (Linux kernel): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L39)
- **Row 32** (shellcheck): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L90)
- **Row 36** (Container Device Interface (CDI)): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L99)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 05: Federation and Computer Use

This chapter covers the documentation for **Federation and Computer Use** under MiOS.

### <a name="05_model_context_protocol"></a>05.Model Context Protocol: Model Context Protocol

> Path Reference: `/usr/share/doc/mios/manual.md#05_model_context_protocol`

#### Overview

The Model Context Protocol (MCP) defines the standard interface for how agents discover and execute system tools.

- **Registry**: Configured dynamically under `/usr/share/mios/ai/v1/mcp.json`.
- **Pre-installed Servers**: Includes `mios-fs` (filesystem), `mios-kb` (vector recall), and `mios-forge` (git repository control).
- **Confinement**: MCP servers execute tool scripts inside unprivileged namespaces.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 37** (containers.conf / storage.conf): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L100)
- **Row 38** (containers/storage): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L101)
- **Row 39** (containers/image): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L102)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="05_agent_to_agent_delegation"></a>05.Agent To Agent Delegation: Agent-to-Agent Delegation

> Path Reference: `/usr/share/doc/mios/manual.md#05_agent_to_agent_delegation`

#### Overview

Complex tasks are fanned out to specialized sub-agents using the Agent-to-Agent (A2A) protocol.

- **Communication**: Uses a JSON-RPC payload schema over standard loopback ports.
- **Discovery**: Agents query the registry at `/v1/agents` to discover capabilities.
- **Delegation**: The orchestrator delegates code tasks to the `mios-opencode` coding agent (port 8633), which modifies files and returns validation results.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 34** (openssl): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L92)
- **Row 37** (containers.conf / storage.conf): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L100)
- **Row 38** (containers/storage): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L101)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="05_vision_and_os_control"></a>05.Vision and OS Control: Vision and OS Control

> Path Reference: `/usr/share/doc/mios/manual.md#05_vision_and_os_control`

#### Overview

MiOS provides agents with the ability to interact directly with the GNOME desktop environment.

- **Vision Grounding**: Agents utilize the UI-TARS vision-language model to translate user requests into click coordinates on the Wayland display server.
- **Accessibility Tree**: Traversals are aided by the AT-SPI semantic screen tree, providing structural context for UI elements.
- **Execution**: Physical actions (mouse moves, clicks, keystrokes) are simulated using the custom `mios-pc-control` command suite.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 40** (nvidia-container-toolkit): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L103)
- **Row 41** (LocalAI): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L114)
- **Row 42** (Ollama): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L115)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 06: Security and Hardware Virtualization

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
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
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
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="06_keyless_image_signing"></a>06.Keyless Image Signing: Keyless Image Signing

> Path Reference: `/usr/share/doc/mios/manual.md#06_keyless_image_signing`

#### Overview

To secure the OCI software supply chain, all MiOS OCI images must be cryptographically signed before deployment.

- **Verification Tools**: Integrated via **Sigstore** and **cosign**.
- **Keyless Signature**: In CI/CD pipelines, images are signed using OIDC tokens, verifying that the build originated from the official pipeline.
- **Verification Rule**: The host's container policy config ([42-cosign-policy.sh](file:///C:/MiOS/automation/42-cosign-policy.sh)) enforces validation check rules, blocking container pulls of unsigned or unrecognized images.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 46** (LiteLLM): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L119)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
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
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
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
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 07: Cluster and Storage Fabric

This chapter covers the documentation for **Cluster and Storage Fabric** under MiOS.

### <a name="07_k3s_kubernetes_integration"></a>07.K3s Kubernetes Integration: K3s Kubernetes Integration

> Path Reference: `/usr/share/doc/mios/manual.md#07_k3s_kubernetes_integration`

#### Overview

MiOS workstation hosts can expand dynamically into single-node high-availability Kubernetes clusters.

- **Runtime daemon**: Managed via `mios-k3s.service` Quadlet.
- **Network Isolation**: Traefik acts as the ingress controller, managing routing protocols on standard cluster ports.
- **SELinux Policies**: Custom SELinux policies are applied by [19-k3s-selinux.sh](file:///C:/MiOS/automation/19-k3s-selinux.sh) to ensure containerized cluster tasks do not violate host read-only security bounds.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 1** (Linux kernel): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L39)
- **Row 51** (Responses API): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L132)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="07_ceph_distributed_storage"></a>07.Ceph Distributed Storage: Ceph Distributed Storage

> Path Reference: `/usr/share/doc/mios/manual.md#07_ceph_distributed_storage`

#### Overview

Distributed storage clustering on MiOS is provisioned via containerized CephFS data planes and privileged exemptions.

- **Service quadlet**: Managed via `mios-ceph.service`.
- **Permissions**: Ceph requires low-level block device access, making it one of the few services exempt from Law 6 (running as host root).
- **User Integration**: User desktop directories (e.g. `~/Documents`) can be mapped directly onto local CephFS shares, enabling automated, encrypted background backups across the storage network.

#### Citation & Attribution References

This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):
- **Row 1** (Linux kernel): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L39)
- **Row 52** (Chat Completions): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L133)
- **Row 53** (Function calling / tools): [Attribution Reference](file:///usr/share/doc/mios/reference/credits.md#L134)

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

# Part III: Core OS Infrastructure

## Chapter 08: Bootloader and Unified Kernel Images (UKI)

This chapter covers the documentation for **Bootloader and Unified Kernel Images (UKI)** under MiOS.

### <a name="08_uki_layout_and_baking"></a>08.UKI Layout and Baking: UKI Layout and Baking

> Path Reference: `/usr/share/doc/mios/manual.md#08_uki_layout_and_baking`

#### Overview

Unified Kernel Images (UKIs) combine the Linux kernel, initramfs, and kernel command-line arguments into a single EFI executable. This ensures that the system boot configuration cannot be altered by modifying individual config files on disk.

## Implementation Details
- **Build tool**: Compiled via `systemd-ukify` during the OCI build.
- **Baking script**: Executed by [23-uki-render.sh](file:///C:/MiOS/automation/23-uki-render.sh).
- **Output**: The output `.efi` image is placed directly in the EFI system partition under `/boot/EFI/Linux/`.
- **Validation**: Verified by `validate-kargs.py` to ensure core arguments are baked into the UKI.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="08_secure_boot_integrity"></a>08.Secure Boot Integrity: Secure Boot Integrity

> Path Reference: `/usr/share/doc/mios/manual.md#08_secure_boot_integrity`

#### Overview

Secure Boot ensures that only cryptographically signed binaries can be executed during the boot phase.

## Validation Chain
1. **UEFI Keys**: The motherboard firmware holds the PK (Platform Key), KEK (Key Exchange Key), and db (Signature Database).
2. **Custom Keys**: MiOS signs custom kernel modules (like ZFS and KVMFR) using a Machine Owner Key (MOK).
3. **MOK Enrollment**: Handled via [enroll-mok.sh](file:///C:/MiOS/automation/enroll-mok.sh) and [generate-mok-key.sh](file:///C:/MiOS/automation/generate-mok-key.sh).
4. **Enforcement**: Secure Boot enforces that all drivers compiled at build time are verified against the MOK database before launching the kernel.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="08_kernel_arguments_and_gating"></a>08.Kernel Arguments and Gating: Kernel Arguments and Gating

> Path Reference: `/usr/share/doc/mios/manual.md#08_kernel_arguments_and_gating`

#### Overview

Kernel arguments customize hardware and hypervisor settings during system launch.

## Active Arguments
- **VFIO Isolation**: `intel_iommu=on` or `amd_iommu=on` and `iommu=pt` to enable PCI passthrough.
- **Immutable Root**: `ostree=` and `composefs=` parameters directing ostree to mount `/usr` as a composefs index.
- **Gating**: Verified dynamically during early boot. Incorrect configurations trigger fallback states.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 09: Systemd and Quadlet Orchestration

This chapter covers the documentation for **Systemd and Quadlet Orchestration** under MiOS.

### <a name="09_unprivileged_systemd_tiers"></a>09.Unprivileged Systemd Tiers: Unprivileged Systemd Tiers

> Path Reference: `/usr/share/doc/mios/manual.md#09_unprivileged_systemd_tiers`

#### Overview

MiOS uses unprivileged systemd user services to run AI components safely within user space boundaries.

## Architecture
- **User Unit Path**: `/usr/lib/systemd/user/` or `~/.config/systemd/user/`.
- **System-User Map**: Enforced via systemd sysusers templates in [31-user.sh](file:///C:/MiOS/automation/31-user.sh).
- **Execution Limits**: Systemd user instances map execution boundaries using user namespaces, isolating processes from direct host root access.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="09_quadlet_configuration_syntax"></a>09.Quadlet Configuration Syntax: Quadlet Configuration Syntax

> Path Reference: `/usr/share/doc/mios/manual.md#09_quadlet_configuration_syntax`

#### Overview

Podman Quadlets simplify systemd container management by translating `.container`, `.volume`, and `.network` configuration files into native systemd units on boot.

## Code Conventions
- **Source Paths**: Shipped under `/usr/share/containers/systemd/` or `/etc/containers/systemd/`.
- **Translation Engine**: Parsed by `podman-systemd-generator`.
- **Key Settings**: `[Container]` section specifying images, mounts, and network bridges; `User=mios` and `Group=mios` limits.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="09_dynamic_service_activation"></a>09.Dynamic Service Activation: Dynamic Service Activation

> Path Reference: `/usr/share/doc/mios/manual.md#09_dynamic_service_activation`

#### Overview

Services are dynamically activated, stopped, or scaled based on host states and profile settings.

## Execution Flows
- **Trigger**: Run `mios-sync-env` to regenerate `/etc/mios/install.env`.
- **Service Reload**: Triggers `systemctl daemon-reload` and user daemon reloads to parse environment updates.
- **Gating**: Services check system status indicators (`ConditionPathExists`, etc.) before completing startup.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

# Part IV: Detailed Inference & Execution Layers

## Chapter 10: Local Inference Lanes and llama.cpp

This chapter covers the documentation for **Local Inference Lanes and llama.cpp** under MiOS.

### <a name="10_llama_swap_proxy_architecture"></a>10.Llama Swap Proxy Architecture: Llama-Swap Proxy Architecture

> Path Reference: `/usr/share/doc/mios/manual.md#10_llama_swap_proxy_architecture`

#### Overview

The llama-swap proxy manages model requests on port **11450**, serving as the single entry point for light inference tasks.

## Routing Logic
1. **Model Swap**: Swaps the underlying `llama-server` process on-demand to match the requested model name.
2. **Context Saving**: Pages the KV context of inactive conversations to disk using `--slot-save-path`.
3. **KV Restoring**: Reloads KV pages on subsequent requests via `POST /slots/{id}` calls.
4. **Performance**: Reduces memory use by ensuring only active models remain resident in VRAM/RAM.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="10_embedded_inference_setup"></a>10.Embedded Inference Setup: Embedded Inference Setup

> Path Reference: `/usr/share/doc/mios/manual.md#10_embedded_inference_setup`

#### Overview

Embedded inference on MiOS uses optimized GGUF format weights to enable local execution on GPU or CPU.

## Setup Details
- **Context Size**: Standardized context boundaries are mapped dynamically in [38-llamacpp-prep.sh](file:///C:/MiOS/automation/38-llamacpp-prep.sh).
- **Embeddings**: An embedding-configured llama-server runs in parallel to handle vector queries.
- **Safety**: Uses static model limits and resource controls to prevent container memory limit crashes.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="10_model_map_and_hot_swapping"></a>10.Model Map and Hot Swapping: Model Map and Hot Swapping

> Path Reference: `/usr/share/doc/mios/manual.md#10_model_map_and_hot_swapping`

#### Overview

Models are mapped in [mios-llm-light.yaml](file:///C:/MiOS/usr/share/mios/llamacpp/mios-llm-light.yaml), defining served model aliases and parameters.

## Configuration
- **Model Keys**: Mapping `granite4.1:8b` (default chat), `nomic-embed-text` (embeddings), and `mios-opencode` (coding model).
- **Auto-swap Gating**: llama-swap monitors inbound request headers to spin down idle processes and start target weights.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 11: Heavy GPU Lanes and SGLang/vLLM

This chapter covers the documentation for **Heavy GPU Lanes and SGLang/vLLM** under MiOS.

### <a name="11_sglang_gpu_gating_policies"></a>11.SGLang GPU Gating Policies: SGLang GPU Gating Policies

> Path Reference: `/usr/share/doc/mios/manual.md#11_sglang_gpu_gating_policies`

#### Overview

The heavy reasoning lane utilizes SGLang (port **11441**) to serve large language models when hardware allows.

## Policies
- **VRAM Gating**: Checked at startup using `ConditionPathExists=/usr/share/mios/sglang/model/config.json`.
- **Exclusion**: SGLang and vLLM are mutually exclusive to prevent VRAM allocation conflicts.
- **Host Check**: Probes dGPU memory to verify available resources before launching SGLang containers.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="11_vllm_swarm_workers"></a>11.VLLM Swarm Workers: vLLM Swarm Workers

> Path Reference: `/usr/share/doc/mios/manual.md#11_vllm_swarm_workers`

#### Overview

The alternate heavy lane uses vLLM (port **11440**) to run swarm worker instances.

## Operations
- **PagedAttention**: Uses vLLM's memory manager to scale batch concurrency.
- **Swarm worker**: Workers can be dynamically spun up using `mios-llm-worker@.service` templates.
- **Load Balancing**: Distributes token generation tasks across workers for high-volume jobs.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="11_vram_allocation_and_scheduling"></a>11.VRAM Allocation and Scheduling: VRAM Allocation and Scheduling

> Path Reference: `/usr/share/doc/mios/manual.md#11_vram_allocation_and_scheduling`

#### Overview

VRAM scheduling isolates graphics memory resources between virtual machines (Looking Glass) and heavy reasoning lanes.

## Boundaries
- **VM Priority**: Virtual machines claim allocated VRAM statically at boot.
- **AI lane scaling**: Heavy LLM lanes adjust context sizes and batch bounds dynamically based on remaining VRAM.
- **Recovery**: Automatic shutdown of heavy lanes if a primary VM requests resources.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 12: Unified Memory and pgvector Schema

This chapter covers the documentation for **Unified Memory and pgvector Schema** under MiOS.

### <a name="12_postgresql_integration"></a>12.PostgreSQL Integration: PostgreSQL Integration

> Path Reference: `/usr/share/doc/mios/manual.md#12_postgresql_integration`

#### Overview

MiOS integrates PostgreSQL inside rootless Podman to serve as the unified agent datastore.

## Settings
- **Service**: `mios-pgvector.service` running on port 5432.
- **User Mapping**: Maps host UID 826 to container database root.
- **Connection**: Supports secure loopback socket connections for local services.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="12_semantic_knowledge_recall"></a>12.Semantic Knowledge Recall: Semantic Knowledge Recall

> Path Reference: `/usr/share/doc/mios/manual.md#12_semantic_knowledge_recall`

#### Overview

Memory and knowledge tables are queried using semantic vector searches.

## Query Pipeline
- **Embedding**: Prompt vectors are generated using the `nomic-embed-text` lane.
- **SQL Query**: Searches the `knowledge` table using pgvector's HNSW index operators:
  ```sql
  SELECT content FROM knowledge ORDER BY embedding <=> $1 LIMIT 5;
  ```
- **Injection**: Retrieved content is injected into agent context to guide response generation.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="12_epistemic_memory_pruning"></a>12.Epistemic Memory Pruning: Epistemic Memory Pruning

> Path Reference: `/usr/share/doc/mios/manual.md#12_epistemic_memory_pruning`

#### Overview

To maintain search performance, memory indexes are optimized via background pruning.

## Methods
- **Consolidation**: Consolidates multiple redundant logs into single semantic entries.
- **Archiving**: Moves historical logs to offline JSON archives.
- **Index Cleanup**: Runs `VACUUM ANALYZE` on memory tables to rebuild HNSW graphs.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 13: Model Context Protocol Integration

This chapter covers the documentation for **Model Context Protocol Integration** under MiOS.

### <a name="13_custom_mcp_server_design"></a>13.Custom MCP Server Design: Custom MCP Server Design

> Path Reference: `/usr/share/doc/mios/manual.md#13_custom_mcp_server_design`

#### Overview

Developers can extend agent capabilities by writing custom Model Context Protocol (MCP) servers.

## Guidelines
- **Language**: Python or Go is recommended.
- **Communication**: Uses JSON-RPC over stdin/stdout or SSE transport.
- **Registration**: Register the server in `/usr/share/mios/ai/v1/mcp.json` or `~/.config/mios/mcp.json`.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="13_tool_discovery_protocols"></a>13.Tool Discovery Protocols: Tool Discovery Protocols

> Path Reference: `/usr/share/doc/mios/manual.md#13_tool_discovery_protocols`

#### Overview

The system uses dynamic tool discovery to collect active MCP tools at session start.

## Flow
1. **Parse Manifest**: Reads the registered MCP server list in `/v1/mcp`.
2. **Tool Handshake**: Connects to each server to fetch supported tools.
3. **API Mapping**: Maps tool capabilities to standard OpenAI-compatible function schemas.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="13_security_sandboxing_for_mcp"></a>13.Security Sandboxing for MCP: Security Sandboxing for MCP

> Path Reference: `/usr/share/doc/mios/manual.md#13_security_sandboxing_for_mcp`

#### Overview

To prevent malicious tool execution, MCP server processes are sandboxed.

## Sandboxing Details
- **Namespace Isolation**: Runs inside rootless container namespaces.
- **SELinux confinement**: Confinded using strict SELinux policies.
- **Filesystem Access**: Limited to designated sandbox directory spaces.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 14: Agent-to-Agent Delegation Protocols

This chapter covers the documentation for **Agent-to-Agent Delegation Protocols** under MiOS.

### <a name="14_json_rpc_delegation_specification"></a>14.JSON-RPC Delegation Spec: JSON-RPC Delegation Specification

> Path Reference: `/usr/share/doc/mios/manual.md#14_json_rpc_delegation_specification`

#### Overview

The Agent-to-Agent (A2A) protocol defines how agents delegate tasks to peer nodes.

## Payload Example
```json
{
  "jsonrpc": "2.0",
  "method": "delegate_task",
  "params": {
    "task": "Refactor install.sh line 42",
    "specialist": "mios-opencode"
  },
  "id": 1
}
```

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="14_opencode_specialist_handoffs"></a>14.OpenCode Specialist Handoffs: OpenCode Specialist Handoffs

> Path Reference: `/usr/share/doc/mios/manual.md#14_opencode_specialist_handoffs`

#### Overview

Coding tasks are fanned out to the `mios-opencode` coding specialist on port **8633**.

## Execution Flow
1. **Identify Task**: The orchestrator detects code modifications.
2. **RPC Handoff**: Delegates the file editing task to the coding agent.
3. **Execution**: The coding agent edits the target files.
4. **Verification**: Runs tests in the sandboxed container and returns the results.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="14_peer_to_peer_trust_models"></a>14.Peer-to-Peer Trust Models: Peer-to-Peer Trust Models

> Path Reference: `/usr/share/doc/mios/manual.md#14_peer_to_peer_trust_models`

#### Overview

A2A communications are secured through capability-based access controls.

## Details
- **Tokens**: Loopback calls are secured via dynamically rotated tokens.
- **Verification**: Agents verify peer signatures before executing tasks.
- **Audit Logs**: All delegated tasks are logged in the Postgres database.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 15: Computer Use and Desktop Control

This chapter covers the documentation for **Computer Use and Desktop Control** under MiOS.

### <a name="15_ui_tars_vision_grounding"></a>15.UI-TARS Vision Grounding: UI-TARS Vision Grounding

> Path Reference: `/usr/share/doc/mios/manual.md#15_ui_tars_vision_grounding`

#### Overview

Desktop automation uses UI-TARS models to translate visual displays into action coordinates.

## Operations
- **Screen Capture**: Grabs active Wayland framebuffer frames.
- **Grounding**: Processes frames to return clickable target coordinates.
- **Scaling**: Coordinates are scaled to match the physical resolution.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="15_wayland_input_automation"></a>15.Wayland Input Automation: Wayland Input Automation

> Path Reference: `/usr/share/doc/mios/manual.md#15_wayland_input_automation`

#### Overview

Inputs are emulated on Wayland through secure input modules.

## Flow
- **Utility**: Uses the `mios-pc-control` command suite.
- **Input Emulation**: Emulates mouse movement, click actions, and key events.
- **Containment**: Actions are confined to approved display boundaries.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="15_at_spi_accessibility_tuning"></a>15.AT-SPI Accessibility Tuning: AT-SPI Accessibility Tuning

> Path Reference: `/usr/share/doc/mios/manual.md#15_at_spi_accessibility_tuning`

#### Overview

AT-SPI screen trees allow agents to navigate UI hierarchies programmatically.

## Methods
- **Traversal**: Traverses active GUI trees to identify component properties.
- **Fallback**: Serves as a semantic fallback when visual coordinate grounding is blocked.
- **Speed**: Improves automation speed by returning direct text content without visual delays.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

# Part V: Deep Security, Cryptography & Hardware

## Chapter 16: Immutable Root and Composefs Sealing

This chapter covers the documentation for **Immutable Root and Composefs Sealing** under MiOS.

### <a name="16_composefs_read_only_mounts"></a>16.Composefs Read-Only Mounts: Composefs Read-Only Mounts

> Path Reference: `/usr/share/doc/mios/manual.md#16_composefs_read_only_mounts`

#### Overview

The system root `/usr` is mounted as a read-only composefs image to prevent run-time modification.

## Features
- **Integrity**: Block device files are read-only at the kernel level.
- **Storage**: System files are stored inside content-addressed OCI indexes.
- **Baking**: Composefs files are rendered during the OCI build.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="16_fs_verity_signature_verification"></a>16.Fs-Verity Signature Verification: fs-verity Signature Verification

> Path Reference: `/usr/share/doc/mios/manual.md#16_fs_verity_signature_verification`

#### Overview

fs-verity protects binaries from offline tampering.

## Operations
- **Hashes**: Cryptographic signature blocks are generated for system files.
- **Verification**: The kernel verifies hashes on open operations.
- **Enforcement**: Any modification to signed binaries triggers block errors.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="16_host_upgrade_reconciliation"></a>16.Host Upgrade Reconciliation: Host Upgrade Reconciliation

> Path Reference: `/usr/share/doc/mios/manual.md#16_host_upgrade_reconciliation`

#### Overview

System updates are applied transactionally on booted hosts.

## Process
1. **Trigger**: Run `bootc upgrade` to fetch updated image layers.
2. **Reconciliation**: System files under `/usr` are replaced by the new image, while host settings in `/etc` are merged.
3. **Activation**: Cleans inactive files and switches to the new index on reboot.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 17: Defense in Depth Hardening

This chapter covers the documentation for **Defense in Depth Hardening** under MiOS.

### <a name="17_crowdsec_intrusion_prevention"></a>17.CrowdSec Intrusion Prevention: CrowdSec Intrusion Prevention

> Path Reference: `/usr/share/doc/mios/manual.md#17_crowdsec_intrusion_prevention`

#### Overview

CrowdSec monitors local logs to detect threat activities.

## Settings
- **Logs**: Parses system logs, SSH, and container logs.
- **Enforcement**: Blocks attackers using local firewalld rules.
- **Sovereign Mode**: Runs offline without requiring cloud accounts.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="17_fapolicyd_application_whitelisting"></a>17.Fapolicyd Application Whitelisting: fapolicyd Application Whitelisting

> Path Reference: `/usr/share/doc/mios/manual.md#17_fapolicyd_application_whitelisting`

#### Overview

fapolicyd blocks execution of untrusted scripts and binaries.

## Rules
- **Policy**: Denies execution of all files outside `/usr` and trusted directories.
- **Paths**: Blocks executions inside `/tmp`, `/var`, or user home directories.
- **Trust DB**: Managed in `/etc/fapolicyd/fapolicyd.trust`.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="17_usbguard_hardware_control"></a>17.USBGuard Hardware Control: USBGuard Hardware Control

> Path Reference: `/usr/share/doc/mios/manual.md#17_usbguard_hardware_control`

#### Overview

USBGuard safeguards against hardware security exploits.

## Details
- **Policy**: Blocks unauthorized USB devices at connection.
- **Rules**: Allows only authorized USB controllers and keyboards.
- **Logs**: Hardware actions are logged in system journals.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 18: Supply Chain and Image Integrity

This chapter covers the documentation for **Supply Chain and Image Integrity** under MiOS.

### <a name="18_sigstore_verification_policies"></a>18.Sigstore Verification Policies: Sigstore Verification Policies

> Path Reference: `/usr/share/doc/mios/manual.md#18_sigstore_verification_policies`

#### Overview

Sigstore policies ensure only trusted images can be executed.

## Enforcements
- **Signature Check**: Validates signatures on container pulls.
- **Policy Config**: Configured in [42-cosign-policy.sh](file:///C:/MiOS/automation/42-cosign-policy.sh).
- **Rules**: Rejects unsigned images or those with invalid certs.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="18_keyless_cosign_signing"></a>18.Keyless Cosign Signing: Keyless Cosign Signing

> Path Reference: `/usr/share/doc/mios/manual.md#18_keyless_cosign_signing`

#### Overview

Keyless signing uses OIDC trust systems to sign OCI container images.

## Features
- **Keys**: No private keys are stored; signatures use ephemeral certificates.
- **Logs**: Certs are logged in public Rekor transparency ledgers.
- **CI**: Integrates with GitHub and local runner actions.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="18_build_time_attestation"></a>18.Build Time Attestation: Build-Time Attestation

> Path Reference: `/usr/share/doc/mios/manual.md#18_build_time_attestation`

#### Overview

Attestations verify the build origin and contents of OCI images.

## Output
- **SBOM**: Generates a CycloneDX SBOM during the OCI build.
- **Attestation**: Baked directly into the image layers.
- **Verification**: Validated during deployment checks.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 19: Hardware Passthrough and VFIO-PCI

This chapter covers the documentation for **Hardware Passthrough and VFIO-PCI** under MiOS.

### <a name="19_gpu_isolation_via_vfio"></a>19.GPU Isolation VFIO: GPU Isolation via VFIO

> Path Reference: `/usr/share/doc/mios/manual.md#19_gpu_isolation_via_vfio`

#### Overview

Isolating host graphics cards allows direct passthrough to virtual guests.

## Methods
- **Driver Bind**: Target GPUs are bound to the `vfio-pci` driver during early boot.
- **Script**: Configured via [rtx4090-vfio-configurator.sh](file:///C:/MiOS/tools/rtx4090-vfio-configurator.sh).
- **Verification**: Run `vfio-verify.sh` to check GPU binding status.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="19_libvirt_pci_routing"></a>19.Libvirt PCI Routing: Libvirt PCI Routing

> Path Reference: `/usr/share/doc/mios/manual.md#19_libvirt_pci_routing`

#### Overview

PCI routing maps isolated hardware into VM XML configurations.

## XML Structure
- **Device Node**: Defines target host PCI addresses.
- **Guest Bus**: Maps physical hardware to virtual guest PCIe slots.
- **Configuration**: Uses custom XML tags to bypass hypervisor detection.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="19_guest_drivers_enforcement"></a>19.Guest Drivers Enforcement: Guest Drivers Enforcement

> Path Reference: `/usr/share/doc/mios/manual.md#19_guest_drivers_enforcement`

#### Overview

Guest systems require clean driver configurations to utilize passed hardware.

## Tuning
- **Hypervisor Gating**: Hides hypervisor signatures from Windows guests.
- **Driver Setup**: Installs clean driver packages inside guests.
- **Validation**: Checks driver device status after startup.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 20: Container Device Interface Plumbing

This chapter covers the documentation for **Container Device Interface Plumbing** under MiOS.

### <a name="20_nvidia_cdi_automation"></a>20.Nvidia CDI Automation: Nvidia CDI Automation

> Path Reference: `/usr/share/doc/mios/manual.md#20_nvidia_cdi_automation`

#### Overview

NVIDIA CDI specs enable CUDA applications inside rootless containers.

## Setup
- **CDI Specs**: Generated automatically under `/var/run/cdi/`.
- **Refresh**: Refreshed via [45-nvidia-cdi-refresh.sh](file:///C:/MiOS/automation/45-nvidia-cdi-refresh.sh).
- **Quadlets**: Containers request graphics resources via `CDIDevices=` entries.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="20_amd_rocm_cdi_mappings"></a>20.AMD ROCm CDI Mappings: AMD ROCm CDI Mappings

> Path Reference: `/usr/share/doc/mios/manual.md#20_amd_rocm_cdi_mappings`

#### Overview

AMD CDI profiles map compute hardware to container environments.

## Operations
- **Mappings**: Maps `/dev/kfd` and AMD compute files.
- **Settings**: Configured in [41-gpu-cdi-toolkits.sh](file:///C:/MiOS/automation/41-gpu-cdi-toolkits.sh).
- **Verification**: Validates GPU compute access inside containers.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="20_intel_gpu_cdi_specs"></a>20.Intel GPU CDI Specs: Intel GPU CDI Specs

> Path Reference: `/usr/share/doc/mios/manual.md#20_intel_gpu_cdi_specs`

#### Overview

Intel CDI maps integrated and discrete Intel graphics processors.

## Details
- **Specs**: Exposes Intel integrated and discrete graphics processors.
- **Conventions**: Exposes GPU nodes inside container layers.
- **Confinement**: Isolates GPU access boundaries to specific containers.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 21: Looking Glass B7 and KVMFR

This chapter covers the documentation for **Looking Glass B7 and KVMFR** under MiOS.

### <a name="21_kvmfr_kernel_module_bake"></a>21.KVMFR Kernel Module Bake: KVMFR Kernel Module Bake

> Path Reference: `/usr/share/doc/mios/manual.md#21_kvmfr_kernel_module_bake`

#### Overview

Looking Glass requires the KVM Framebuffer (KVMFR) driver to share screen memory.

## Build
- **Compilation**: Compiled from source during [52-bake-kvmfr.sh](file:///C:/MiOS/automation/52-bake-kvmfr.sh).
- **Signing**: Signed automatically with the host's MOK.
- **Verification**: Loaded on boot to expose the virtual memory channel.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="21_shared_memory_framebuffer"></a>21.Shared Memory Framebuffer: Shared Memory Framebuffer

> Path Reference: `/usr/share/doc/mios/manual.md#21_shared_memory_framebuffer`

#### Overview

Looking Glass uses host shared memory to pass frames.

## Setup
- **Allocation**: Configured via tmpfiles configuration templates.
- **Buffer**: Creates `/dev/shm/looking-glass` with correct permissions.
- **Tuning**: Size boundaries are calculated based on guest resolution.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="21_looking_glass_client_setup"></a>21.Looking Glass Client Setup: Looking Glass Client Setup

> Path Reference: `/usr/share/doc/mios/manual.md#21_looking_glass_client_setup`

#### Overview

The host client renders guest framebuffers on the Wayland display.

## Execution
- **Client**: Shipped inside [53-bake-lookingglass-client.sh](file:///C:/MiOS/automation/53-bake-lookingglass-client.sh).
- **Command**: Launches the Wayland-native client to display virtual displays.
- **Tuning**: Configured for mouse and audio integration.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 22: CPU Topology and Performance Pinning

This chapter covers the documentation for **CPU Topology and Performance Pinning** under MiOS.

### <a name="22_thread_allocation_strategies"></a>22.Thread Allocation Strategies: Thread Allocation Strategies

> Path Reference: `/usr/share/doc/mios/manual.md#22_thread_allocation_strategies`

#### Overview

CPU pinning partitions processing cores between virtual machines and the host.

## Policies
- **P-cores**: Assigned to virtual guest tasks.
- **E-cores**: Bound to host tasks and background AI lanes.
- **Automation**: Executed dynamically by [vm-cpu-pin-manager.sh](file:///C:/MiOS/tools/vm-cpu-pin-manager.sh).

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="22_numa_node_awareness"></a>22.NUMA Node Awareness: NUMA Node Awareness

> Path Reference: `/usr/share/doc/mios/manual.md#22_numa_node_awareness`

#### Overview

NUMA alignment optimizes memory access times by keeping tasks close to memory nodes.

## Tuning
- **Alignment**: Virtual CPUs are pinned to matching physical RAM nodes.
- **Benefits**: Reduces cross-node latency and increases frame rates.
- **Controls**: Configured inside libvirt templates.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="22_low_latency_vm_tuning"></a>22.Low-Latency VM Tuning: Low-Latency VM Tuning

> Path Reference: `/usr/share/doc/mios/manual.md#22_low_latency_vm_tuning`

#### Overview

Tuning settings reduce virtualization scheduling latencies.

## Settings
- **Scheduling**: Prioritizes VM processes using real-time schedulers.
- **Emulator Pinning**: Isolates emulator tasks from primary worker threads.
- **Configurations**: Settings are managed in VM XML configurations.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

# Part VI: Storage, Network & Web Planes

## Chapter 23: Single-Node Kubernetes Expansion

This chapter covers the documentation for **Single-Node Kubernetes Expansion** under MiOS.

### <a name="23_k3s_workstation_coexistence"></a>23.K3s Workstation Coexistence: K3s Workstation Coexistence

> Path Reference: `/usr/share/doc/mios/manual.md#23_k3s_workstation_coexistence`

#### Overview

Integrating single-node K3s allows container orchestration without affecting GNOME resources.

## Operations
- **Isolation**: Runs K3s inside isolated runtime namespaces.
- **Gating**: Starts only when active profiles have cluster features enabled.
- **Limits**: Implements resource bounds to protect desktop tasks.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="23_local_ingress_and_routing"></a>23.Local Ingress and Routing: Local Ingress and Routing

> Path Reference: `/usr/share/doc/mios/manual.md#23_local_ingress_and_routing`

#### Overview

Ingress configs manage external routing into local cluster services.

## Setup
- **Ingress**: Uses Traefik on port 6443.
- **Routing**: Routes local domains to active pods.
- **Ports**: Exposes services to the host network interface.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="23_k3s_selinux_policy_enforcement"></a>23.K3s SELinux Policy Enforcement: K3s SELinux Policy Enforcement

> Path Reference: `/usr/share/doc/mios/manual.md#23_k3s_selinux_policy_enforcement`

#### Overview

Custom SELinux rules protect the host from cluster workloads.

## Policies
- **Rules**: Applied by [19-k3s-selinux.sh](file:///C:/MiOS/automation/19-k3s-selinux.sh).
- **Bounds**: Blocks cluster tasks from modifying read-only system files.
- **Validation**: Enforces SELinux policies at runtime.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 24: CephFS Local Storage Cluster

This chapter covers the documentation for **CephFS Local Storage Cluster** under MiOS.

### <a name="24_containerized_ceph_deployments"></a>24.Containerized Ceph Deployments: Containerized Ceph Deployments

> Path Reference: `/usr/share/doc/mios/manual.md#24_containerized_ceph_deployments`

#### Overview

Ceph storage daemons are orchestrated inside unprivileged containers.

## Orchestration
- **Service**: Managed via `mios-ceph.service` Quadlet.
- **Containers**: Includes Ceph monitors and OSD engines.
- **Mounts**: Exposes storage block paths.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="24_storage_daemon_permissions"></a>24.Storage Daemon Permissions: Storage Daemon Permissions

> Path Reference: `/usr/share/doc/mios/manual.md#24_storage_daemon_permissions`

#### Overview

Ceph requires block access permissions, making it one of the few root exemptions.

## Details
- **Exceptions**: Documented inside systemd templates.
- **Permissions**: Runs with permissions required to interact with hardware blocks.
- **Hardening**: Limits network execution boundaries to loopback interfaces.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="24_xdg_directory_integrations"></a>24.XDG Directory Integrations: XDG Directory Integrations

> Path Reference: `/usr/share/doc/mios/manual.md#24_xdg_directory_integrations`

#### Overview

Desktop directories are synced to CephFS mounts for automatic backups.

## Setup
- **Integrations**: Mounts local directories (e.g. `~/Documents`) directly on CephFS.
- **Backups**: Saves changes across the local storage network.
- **Config**: Settings are stored inside XDG configuration files.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 25: Local Search Engine and SearXNG

This chapter covers the documentation for **Local Search Engine and SearXNG** under MiOS.

### <a name="25_searxng_sovereign_search"></a>25.SearXNG Sovereign Search: SearXNG Sovereign Search

> Path Reference: `/usr/share/doc/mios/manual.md#25_searxng_sovereign_search`

#### Overview

Sovereign search services are provided locally by containerized SearXNG.

## Setup
- **Endpoint**: Runs on port 8888.
- **Security**: Disables logging and upstream search tracking.
- **Performance**: Returns results offline or via private search.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="25_agent_search_api_plumbing"></a>25.Agent Search API Plumbing: Agent Search API Plumbing

> Path Reference: `/usr/share/doc/mios/manual.md#25_agent_search_api_plumbing`

#### Overview

Agents execute search queries using SearXNG API endpoints.

## Pipeline
- **API**: Queries local endpoints on port 8888.
- **Authentication**: secured via loopback trust.
- **Integration**: Backs the agent's web search tools.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="25_web_scraping_and_ingest"></a>25.Web Scraping and Ingest: Web Scraping and Ingest

> Path Reference: `/usr/share/doc/mios/manual.md#25_web_scraping_and_ingest`

#### Overview

Parsed search results are transformed into Markdown for inference ingestion.

## Details
- **Scraper**: Grabs target pages from search outputs.
- **Parser**: Formats raw HTML into clean markdown.
- **Gating**: Blocks scripts to prevent cross-site execution.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 26: Unified Knowledge Base Ingestion

This chapter covers the documentation for **Unified Knowledge Base Ingestion** under MiOS.

### <a name="26_document_parsing_and_embedding"></a>26.Document Parsing and Embedding: Document Parsing and Embedding

> Path Reference: `/usr/share/doc/mios/manual.md#26_document_parsing_and_embedding`

#### Overview

Ingested documents are parsed and vectorized to build the knowledge base.

## Flow
- **Parser**: Converts PDFs, text, and code files.
- **Embedding**: Generates vectors using the light embedding lane.
- **Utility**: Run [generate-unified-knowledge.py](file:///C:/MiOS/tools/generate-unified-knowledge.py).

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="26_ingest_pipeline_schema"></a>26.Ingest Pipeline Schema: Ingest Pipeline Schema

> Path Reference: `/usr/share/doc/mios/manual.md#26_ingest_pipeline_schema`

#### Overview

The ingest pipeline maps content to Postgres database tables.

## Structure
- **Tables**: Mapped in `usr/share/mios/postgres/schema-init.sql`.
- **Columns**: Stores content, source reference, and vectors.
- **Constraints**: Enforces unique sources to prevent duplicate index entries.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="26_semantic_indexing_maintenance"></a>26.Semantic Indexing Maintenance: Semantic Indexing Maintenance

> Path Reference: `/usr/share/doc/mios/manual.md#26_semantic_indexing_maintenance`

#### Overview

Maintaining vector indexes keeps similarity query times fast.

## Operations
- **Indexing**: Uses HNSW graphs for semantic retrieval.
- **Pruning**: Consolidates duplicate and stale data.
- **Reindexing**: Rebuilds database indexes after import tasks.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 27: Shell Configuration and Environment Cascade

This chapter covers the documentation for **Shell Configuration and Environment Cascade** under MiOS.

### <a name="27_environment_defaults_and_precedence"></a>27.Env Defaults and Precedence: Environment Defaults and Precedence

> Path Reference: `/usr/share/doc/mios/manual.md#27_environment_defaults_and_precedence`

#### Overview

Environment variables are resolved through a multi-layer cascade.

## Cascade
1. `~/.config/mios/env` (highest precedence)
2. `/etc/mios/install.env`
3. `/etc/mios/env.d/*.env`
4. `/usr/share/mios/env.defaults` (lowest precedence)

Use `mios-env --explain` to trace key resolution layers.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="27_oh_my_posh_prompt_theming"></a>27.Oh My Posh Prompt Theming: Oh My Posh Prompt Theming

> Path Reference: `/usr/share/doc/mios/manual.md#27_oh_my_posh_prompt_theming`

#### Overview

The system shell uses Oh My Posh themes to show system status.

## Themes
- **Prompt**: Configured in [38-oh-my-posh.sh](file:///C:/MiOS/automation/38-oh-my-posh.sh).
- **Icons**: Displays git status, active model, and CPU usage.
- **Themes File**: Stored inside `/usr/share/mios/shell/`.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="27_user_locale_standardization"></a>27.User Locale Standardization: User Locale Standardization

> Path Reference: `/usr/share/doc/mios/manual.md#27_user_locale_standardization`

#### Overview

Standard locale and time formats are staging targets during deployment.

## Settings
- **Locale**: Sets UTF-8 encoding.
- **Timezone**: Set in [30-locale-theme.sh](file:///C:/MiOS/automation/30-locale-theme.sh).
- **Customizations**: Customized in `mios.toml`.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 28: Dynamic Network and Firewall Management

This chapter covers the documentation for **Dynamic Network and Firewall Management** under MiOS.

### <a name="28_firewalld_rule_generation"></a>28.Firewalld Rule Generation: Firewalld Rule Generation

> Path Reference: `/usr/share/doc/mios/manual.md#28_firewalld_rule_generation`

#### Overview

Firewall rules isolate host services and control outbound networks.

## Rules
- **Tool**: Configured via firewalld policies.
- **Gating**: Outbound requests are limited by [generate-egress-firewall.py](file:///C:/MiOS/tools/generate-egress-firewall.py).
- **Logs**: Blocked network events are logged in system journals.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="28_dynamic_port_allocation"></a>28.Dynamic Port Allocation: Dynamic Port Allocation

> Path Reference: `/usr/share/doc/mios/manual.md#28_dynamic_port_allocation`

#### Overview

Ports are allocated dynamically during build and boot phases.

## Allocation
- **Script**: Handled by [16-render-ports.sh](file:///C:/MiOS/automation/16-render-ports.sh).
- **Mappings**: Maps host interfaces to container ports.
- **Validation**: Enforces unique allocations to prevent startup collisions.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="28_vpn_and_tailscale_routing"></a>28.VPN and Tailscale Routing: VPN and Tailscale Routing

> Path Reference: `/usr/share/doc/mios/manual.md#28_vpn_and_tailscale_routing`

#### Overview

VPN integrations secure communication across network devices.

## Settings
- **Interface**: Uses Tailscale virtual adapters.
- **Routing**: Resolves local addresses through private tunnels.
- **Firewall**: Integrates VPN paths with local rules.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 29: Web Management and Configurator UI

This chapter covers the documentation for **Web Management and Configurator UI** under MiOS.

### <a name="29_mios_html_toml_editor"></a>29.Mios HTML TOML Editor: MiOS HTML TOML Editor

> Path Reference: `/usr/share/doc/mios/manual.md#29_mios_html_toml_editor`

#### Overview

The configuration dashboard allows graphical form editing of system parameters.

## Details
- **Dashboard**: Shipped in [mios.html](file:///C:/MiOS/usr/share/mios/configurator/mios.html).
- **Precedence**: Writes updates back to user and host files.
- **Sync**: Triggers `mios-sync-env` to apply updates.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="29_host_to_container_portal"></a>29.Host-to-Container Portal: Host-to-Container Portal

> Path Reference: `/usr/share/doc/mios/manual.md#29_host_to_container_portal`

#### Overview

The web panel monitors resource usages and active containers.

## Metrics
- **Resource Monitoring**: Tracks system usage (VRAM, CPU, RAM).
- **Service Management**: Allows quick container restarts.
- **Host View**: Integrates with Cockpit metrics interfaces.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="29_settings_sync_mechanisms"></a>29.Settings Sync Mechanisms: Settings Sync Mechanisms

> Path Reference: `/usr/share/doc/mios/manual.md#29_settings_sync_mechanisms`

#### Overview

Config settings are synchronized back to target system files on save.

## Mechanisms
- **Sync script**: Syncing handled by Python and PowerShell tools.
- **Update Checks**: Validates configuration integrity before reboot.
- **State Merging**: Merges updates without breaking custom changes.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

# Part VII: Build, Test & Upstream Maintenance

## Chapter 30: System Auditing and Drift Verification

This chapter covers the documentation for **System Auditing and Drift Verification** under MiOS.

### <a name="30_automated_postcheck_suite"></a>30.Automated Postcheck Suite: Automated Postcheck Suite

> Path Reference: `/usr/share/doc/mios/manual.md#30_automated_postcheck_suite`

#### Overview

The postcheck suite validates system state compliance before image builds finish.

## Checks
- **Script**: Configured in [99-postcheck.sh](file:///C:/MiOS/automation/99-postcheck.sh).
- **Tests**: Validates container layers, CDI specs, and FHS structures.
- **Gating**: Failing checks block OCI image output.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="30_hardcode_lint_rules"></a>30.Hardcode Lint Rules: Hardcode Lint Rules

> Path Reference: `/usr/share/doc/mios/manual.md#30_hardcode_lint_rules`

#### Overview

Build rules prohibit hardcoded keys, URLs, and settings.

## Rules
- **Linter**: Executed by [mios-hardcode-lint](file:///C:/MiOS/usr/libexec/mios/mios-hardcode-lint) inside automation scripts.
- **Violations**: Hardcoded ports, IPs, or vendor links trigger build failures.
- **Bypasses**: Requires variables to resolve via config cascades.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="30_security_policy_compliance"></a>30.Security Policy Compliance: Security Policy Compliance

> Path Reference: `/usr/share/doc/mios/manual.md#30_security_policy_compliance`

#### Overview

Verifies that active system configurations meet zero-trust security profiles.

## Auditing
- **Checks**: Scans permissions, SELinux states, and whitelists.
- **Output**: Reports are logged under `/usr/share/doc/mios/audits/`.
- **Validation**: Enforces integrity checks on core files.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 31: Desktop Applications and Flatpaks

This chapter covers the documentation for **Desktop Applications and Flatpaks** under MiOS.

### <a name="31_declarative_flatpak_bake"></a>31.Declarative Flatpak Bake: Declarative Flatpak Bake

> Path Reference: `/usr/share/doc/mios/manual.md#31_declarative_flatpak_bake`

#### Overview

Flatpaks are defined in system configs and pre-downloaded to reduce setup times.

## Setup
- **Declarations**: Listed in `mios.toml` under `[flatpaks]`.
- **Bake Script**: Configured in [40-flatpak-bake.sh](file:///C:/MiOS/automation/40-flatpak-bake.sh).
- **Details**: Pre-downloads application runtimes into the image storage.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="31_application_permissions_gating"></a>31.Application Permissions Gating: Application Permissions Gating

> Path Reference: `/usr/share/doc/mios/manual.md#31_application_permissions_gating`

#### Overview

Flatpak permissions are confined using Flatseal profiles.

## Hardening
- **Confinement**: Restricts access to host files, network, and sockets.
- **Exceptions**: Allows necessary GPU access paths.
- **Overrides**: Controlled via custom scripts on first boot.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="31_desktop_shortcuts_sync"></a>31.Desktop Shortcuts Sync: Desktop Shortcuts Sync

> Path Reference: `/usr/share/doc/mios/manual.md#31_desktop_shortcuts_sync`

#### Overview

Syncs application icons and shortcuts to the GNOME desktop launcher menu.

## Flow
- **Script**: Managed via [refresh-flatpak-shortcuts.ps1](file:///C:/MiOS/tools/refresh-flatpak-shortcuts.ps1).
- **Sync**: Maps application desktop files to target directory folders.
- **Updates**: Refreshed dynamically on configuration changes.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 32: Swarm Worker Clusters

This chapter covers the documentation for **Swarm Worker Clusters** under MiOS.

### <a name="32_swarm_node_provisioning"></a>32.Swarm Node Provisioning: Swarm Node Provisioning

> Path Reference: `/usr/share/doc/mios/manual.md#32_swarm_node_provisioning`

#### Overview

Adding swarm worker instances scales execution capacities dynamically.

## Steps
- **Template**: Uses `mios-llm-worker@.service` templates.
- **Target**: Spawns single-model processes on worker endpoints.
- **Discovery**: Automatically joins active host networks.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="32_dynamic_fanout_orchestration"></a>32.Dynamic Fanout Orchestration: Dynamic Fanout Orchestration

> Path Reference: `/usr/share/doc/mios/manual.md#32_dynamic_fanout_orchestration`

#### Overview

The system splits complex queries and routes them to parallel workers.

## Pipeline
- **Fanout**: Tasks are split into independent components.
- **Routing**: Dynamic routing to active worker slots.
- **Synthesis**: Aggregates output files into a cohesive result.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="32_load_balancing_lanes"></a>32.Load Balancing Lanes: Load Balancing Lanes

> Path Reference: `/usr/share/doc/mios/manual.md#32_load_balancing_lanes`

#### Overview

Balances parallel model tasks based on health status metrics.

## Policies
- **Checking**: Probes worker load levels and memory limits.
- **Balancing**: Directs queries to the fastest available worker.
- **Failover**: Handles worker recovery on model load failures.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 33: Sandboxed Execution and Coder Sandbox

This chapter covers the documentation for **Sandboxed Execution and Coder Sandbox** under MiOS.

### <a name="33_coder_sandbox_quadlet"></a>33.Coder Sandbox Quadlet: Coder Sandbox Quadlet

> Path Reference: `/usr/share/doc/mios/manual.md#33_coder_sandbox_quadlet`

#### Overview

Confines untrusted coding tasks within rootless containers.

## Settings
- **Service**: Mapped in `mios-coderun-sandbox@` Quadlet.
- **User**: Runs with unprivileged user namespace limits.
- **Bridges**: Disables host networks to prevent outbound leaks.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="33_selinux_sandbox_policies"></a>33.SELinux Sandbox Policies: SELinux Sandbox Policies

> Path Reference: `/usr/share/doc/mios/manual.md#33_selinux_sandbox_policies`

#### Overview

Custom SELinux profiles prevent sandbox escape actions.

## Policies
- **Rules**: Applied on first boot configuration.
- **Bounds**: Blocks container escape vulnerabilities.
- **Verification**: Logs violations inside audit files.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="33_safe_code_interpretation"></a>33.Safe Code Interpretation: Safe Code Interpretation

> Path Reference: `/usr/share/doc/mios/manual.md#33_safe_code_interpretation`

#### Overview

Validates code actions and sanitizes script outputs securely.

## Methods
- **Sanitizer**: Filters execution outputs to remove credentials.
- **Validation**: Enforces strict timeout limits on executions.
- **Logs**: Processes are logged in system containers.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 34: Identity Management and FreeIPA

This chapter covers the documentation for **Identity Management and FreeIPA** under MiOS.

### <a name="34_freeipa_client_configuration"></a>34.FreeIPA Client Configuration: FreeIPA Client Configuration

> Path Reference: `/usr/share/doc/mios/manual.md#34_freeipa_client_configuration`

#### Overview

Resolves host client authentication with central FreeIPA domains.

## Details
- **Script**: Staged via [22-freeipa-client.sh](file:///C:/MiOS/automation/22-freeipa-client.sh).
- **Client**: Integrates SSSD services inside Fedora core layers.
- **Policies**: Handles identity resolving and domain settings.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="34_enforced_user_sysusers"></a>34.Enforced User Sysusers: Enforced User Sysusers

> Path Reference: `/usr/share/doc/mios/manual.md#34_enforced_user_sysusers`

#### Overview

Sysusers definitions pre-stage user and system accounts prior to install.

## Rules
- **Templates**: Stored under `/usr/lib/sysusers.d/*.conf`.
- **System Accounts**: Configures IDs for database and daemon tasks.
- **Integrity**: Prevents changes during deployment overlays.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="34_domain_join_automation"></a>34.Domain Join Automation: Domain Join Automation

> Path Reference: `/usr/share/doc/mios/manual.md#34_domain_join_automation`

#### Overview

Automates joining host systems to corporate domains.

## Flow
- **Execution**: Connects to IPA servers using OIDC tokens.
- **Certificates**: Generates secure host certificates on setup.
- **Renewals**: Handles automatic credential ticket updates.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 35: System Monitoring and Telemetry

This chapter covers the documentation for **System Monitoring and Telemetry** under MiOS.

### <a name="35_prometheus_exporter_setup"></a>35.Prometheus Exporter Setup: Prometheus Exporter Setup

> Path Reference: `/usr/share/doc/mios/manual.md#35_prometheus_exporter_setup`

#### Overview

Exporters collect system metrics from physical hardware.

## Settings
- **Exporters**: System and GPU metrics collection daemons.
- **Ports**: Exposes metrics on localhost ports.
- **Frequency**: Configured to scrape resources at regular intervals.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="35_ai_gateway_telemetry"></a>35.AI Gateway Telemetry: AI Gateway Telemetry

> Path Reference: `/usr/share/doc/mios/manual.md#35_ai_gateway_telemetry`

#### Overview

Logs query times, token counts, and routing states.

## Diagnostics
- **Recording**: Mapped inside the Postgres log tables.
- **Metrics**: Logs tokens per second and model swap speeds.
- **Anonymization**: Filters queries to protect credentials.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="35_grafana_dashboard_profiles"></a>35.Grafana Dashboard Profiles: Grafana_Dashboard_Profiles

> Path Reference: `/usr/share/doc/mios/manual.md#35_grafana_dashboard_profiles`

#### Overview

Configures dashboards to monitor system and AI workloads.

## Details
- **Widgets**: Mapped inside cockpit or local dashboards.
- **Alerts**: Triggers notifications on VRAM threshold limits.
- **Tuning**: Configured in system monitoring profiles.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 36: Greenboot Health Check and Recovery

This chapter covers the documentation for **Greenboot Health Check and Recovery** under MiOS.

### <a name="36_automatic_os_health_checks"></a>36.Automatic OS Health Checks: Automatic OS Health Checks

> Path Reference: `/usr/share/doc/mios/manual.md#36_automatic_os_health_checks`

#### Overview

Greenboot verifies service status after system upgrades.

## Flow
- **Script**: Checked in [46-greenboot.sh](file:///C:/MiOS/automation/46-greenboot.sh).
- **Actions**: Checks core components (systemd, drivers, AI gateways).
- **Timing**: Enforces timeout limits for checks.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="36_rollback_trigger_policies"></a>36.Rollback Trigger Policies: Rollback Trigger Policies

> Path Reference: `/usr/share/doc/mios/manual.md#36_rollback_trigger_policies`

#### Overview

Rollback triggers swap root partition indexes back to working slots on boot failures.

## Policies
- **Threshold**: Triggers rollback after 3 failed boot attempts.
- **Actions**: Atomic switch of boot partition variables.
- **Logs**: Records rollback events inside bootstrap logs.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="36_recovery_state_scripts"></a>36.Recovery State Scripts: Recovery State Scripts

> Path Reference: `/usr/share/doc/mios/manual.md#36_recovery_state_scripts`

#### Overview

Automated scripts attempt self-repair tasks on service start failures.

## Settings
- **Scripts**: Mapped in `/etc/greenboot/red.d/`.
- **Actions**: Restarts containers and purges stale caches.
- **Controls**: Logs status diagnostics for operator review.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 37: GPU Capability Detection and Passthrough Shims

This chapter covers the documentation for **GPU Capability Detection and Passthrough Shims** under MiOS.

### <a name="37_cdi_refresh_mechanisms"></a>37.CDI Refresh Mechanisms: CDI Refresh Mechanisms

> Path Reference: `/usr/share/doc/mios/manual.md#37_cdi_refresh_mechanisms`

#### Overview

Refreshes CDI specs automatically when graphics adapters change.

## Setup
- **Checks**: Scans physical devices on boot using [34-gpu-detect.sh](file:///C:/MiOS/automation/34-gpu-detect.sh).
- **Utility**: Invokes [45-nvidia-cdi-refresh.sh](file:///C:/MiOS/automation/45-nvidia-cdi-refresh.sh).
- **Execution**: Updates container CDI files in `/var/run/cdi/`.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="37_runtime_gpu_gating"></a>37.Runtime GPU Gating: Runtime GPU Gating

> Path Reference: `/usr/share/doc/mios/manual.md#37_runtime_gpu_gating`

#### Overview

Gating mechanisms control GPU resource allocations between containers and hypervisors.

## Gating
- **Shim**: Implemented via [35-gpu-pv-shim.sh](file:///C:/MiOS/automation/35-gpu-pv-shim.sh).
- **Locking**: Locks device files to prevent parallel utilization conflicts.
- **Policies**: Shunts GPU compute priorities to virtual guests.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="37_dynamic_driver_loading"></a>37.Dynamic Driver Loading: Dynamic Driver Loading

> Path Reference: `/usr/share/doc/mios/manual.md#37_dynamic_driver_loading`

#### Overview

Loads host display drivers based on profile settings.

## Flow
- **Checks**: Verifies system variables at boot.
- **Action**: Loads target GPU drivers or binds cards to VFIO.
- **Integrity**: Enforces signed drivers validation.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 38: Remote Desktop and GNOME GRD

This chapter covers the documentation for **Remote Desktop and GNOME GRD** under MiOS.

### <a name="38_remote_wayland_sessions"></a>38.Remote Wayland Sessions: Remote Wayland Sessions

> Path Reference: `/usr/share/doc/mios/manual.md#38_remote_wayland_sessions`

#### Overview

Enables GUI remote management when running headless.

## Details
- **Script**: Configured via [26-gnome-remote-desktop.sh](file:///C:/MiOS/automation/26-gnome-remote-desktop.sh).
- **Engine**: Integrates with GNOME Remote Desktop.
- **Bridges**: Exposes Wayland displays on ports.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="38_secure_rdp_authentication"></a>38.Secure RDP Authentication: Secure RDP Authentication

> Path Reference: `/usr/share/doc/mios/manual.md#38_secure_rdp_authentication`

#### Overview

Secures remote display sessions using TLS certificates.

## Setup
- **Credentials**: Configures certs and local PAM hooks.
- **Rules**: Restricts RDP connection requests to authorized IP slots.
- **Auditing**: Session access is logged in the system records.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="38_headless_desktop_toggle"></a>38.Headless Desktop Toggle: Headless Desktop Toggle

> Path Reference: `/usr/share/doc/mios/manual.md#38_headless_desktop_toggle`

#### Overview

Allows toggling display signals for virtual desktop environments.

## Actions
- **Toggle tool**: Executed via [mios-toggle-headless](file:///C:/MiOS/automation/mios-toggle-headless).
- **Resolution**: Sets virtual display limits.
- **Tuning**: Optimizes screen frame buffers to save VRAM.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 39: Host-Guest Shared Filesystems

This chapter covers the documentation for **Host-Guest Shared Filesystems** under MiOS.

### <a name="39_virtiofs_performance_tuning"></a>39.Virtiofs Performance Tuning: Virtiofs Performance Tuning

> Path Reference: `/usr/share/doc/mios/manual.md#39_virtiofs_performance_tuning`

#### Overview

Tuning virtiofs settings allows high-speed file sharing with guests.

## Setup
- **Mounts**: Exposes host folders using XML templates.
- **Caching**: Configures high-performance host caches.
- **Tuning**: Optimizes thread limits inside libvirt.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="39_shared_directories_overlay"></a>39.Shared Directories Overlay: Shared Directories Overlay

> Path Reference: `/usr/share/doc/mios/manual.md#39_shared_directories_overlay`

#### Overview

Overlay folders expose host configurations to guest runtimes.

## Flow
- **Overlay**: Exposes `/usr/share/` and guest dotfiles.
- **Sandboxing**: Restricts write access inside guests.
- **Conventions**: Maps locations securely inside hypervisor targets.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="39_permission_translation_models"></a>39.Permission Translation Models: Permission Translation Models

> Path Reference: `/usr/share/doc/mios/manual.md#39_permission_translation_models`

#### Overview

Maps user IDs across host and guest environments.

## Details
- **Mapping**: Translates guest UIDs to matching host accounts.
- **Security**: Prevents guest root tasks from escaping permissions.
- **Verification**: Validates folder access credentials.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 40: System Log Aggregation

This chapter covers the documentation for **System Log Aggregation** under MiOS.

### <a name="40_journald_sync_to_bootstrap"></a>40.Journald Sync to Bootstrap: Journald Sync to Bootstrap

> Path Reference: `/usr/share/doc/mios/manual.md#40_journald_sync_to_bootstrap`

#### Overview

Copies system journals to bootstrap drives for offline diagnostics.

## Flow
- **Script**: Executed by [log-to-bootstrap.sh](file:///C:/MiOS/tools/log-to-bootstrap.sh).
- **Logs**: Copies core files, boot output, and services records.
- **Targets**: Mapped directly onto host storage sectors.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="40_log_copy_daemon_configuration"></a>40.Log-Copy Daemon Configuration: Log-Copy Daemon Configuration

> Path Reference: `/usr/share/doc/mios/manual.md#40_log_copy_daemon_configuration`

#### Overview

Configures background daemons to aggregate container logs.

## Setup
- **Unit**: Configured in [50-enable-log-copy-service.sh](file:///C:/MiOS/automation/50-enable-log-copy-service.sh).
- **Service**: Runs system log synchronization helpers.
- **Storage**: Mapped inside `/var/log/mios/`.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="40_diagnostic_log_bundles"></a>40.Diagnostic Log Bundles: Diagnostic Log Bundles

> Path Reference: `/usr/share/doc/mios/manual.md#40_diagnostic_log_bundles`

#### Overview

Assembles diagnostic packages to simplify system troubleshooting.

## Details
- **Bundler**: Bundles active logs, specs, and status variables.
- **Output**: Generates compressed archives.
- **Triggers**: Executed on system health checks failures.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 41: Machine Owner Key Management

This chapter covers the documentation for **Machine Owner Key Management** under MiOS.

### <a name="41_private_key_generation"></a>41.Private Key Generation: Private Key Generation

> Path Reference: `/usr/share/doc/mios/manual.md#41_private_key_generation`

#### Overview

Generates secure signature keys for custom kernel drivers.

## Details
- **Keys**: Cryptographic keys are generated inside automation layers.
- **Script**: Managed via [generate-mok-key.sh](file:///C:/MiOS/automation/generate-mok-key.sh).
- **Storage**: Keys are isolated in root-only directories.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="41_secure_boot_enrollment_flow"></a>41.Secure Boot Enrollment Flow: Secure Boot Enrollment Flow

> Path Reference: `/usr/share/doc/mios/manual.md#41_secure_boot_enrollment_flow`

#### Overview

Enrolls Machine Owner Keys (MOK) inside host firmware.

## Flow
1. **Trigger**: Run [enroll-mok.sh](file:///C:/MiOS/automation/enroll-mok.sh).
2. **Registration**: Imports certificates to system structures.
3. **Enrollment**: Prompts enrollment on subsequent reboot.
4. **Validation**: Verified by Secure Boot on driver loading.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="41_automatic_module_signing"></a>41.Automatic Module Signing: Automatic Module Signing

> Path Reference: `/usr/share/doc/mios/manual.md#41_automatic_module_signing`

#### Overview

Signs compiled driver binaries automatically during kernel upgrades.

## Processes
- **Compilation**: Triggers driver compile actions on kernel changes.
- **Signing**: Signs binaries using registered MOK keys.
- **Verification**: Confirms signed driver loading logs.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 42: Kernel Upgrade and Build Pipelines

This chapter covers the documentation for **Kernel Upgrade and Build Pipelines** under MiOS.

### <a name="42_stable_lts_kernel_updates"></a>42.Stable LTS Kernel Updates: Stable LTS Kernel Updates

> Path Reference: `/usr/share/doc/mios/manual.md#42_stable_lts_kernel_updates`

#### Overview

Upgrading host kernels relies on stable LTS packages.

## Guidelines
- **Base image**: Kernel packages inherit from uCore base structures.
- **Updates**: Applied transactionally using system image updates.
- **Verification**: Run preflight checks before updating core kernels.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="42_akmod_compilation_guards"></a>42.Akmod Compilation Guards: Akmod Compilation Guards

> Path Reference: `/usr/share/doc/mios/manual.md#42_akmod_compilation_guards`

#### Overview

Guards compilation tasks to prevent boot failures from driver updates.

## Details
- **Guards**: Enabled via [36-akmod-guards.sh](file:///C:/MiOS/automation/36-akmod-guards.sh).
- **Validation**: Enforces driver binary compilation checks.
- **Actions**: Restores previous functional configurations on failure.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="42_bib_disk_image_generation"></a>42.BIB Disk Image Generation: BIB Disk Image Generation

> Path Reference: `/usr/share/doc/mios/manual.md#42_bib_disk_image_generation`

#### Overview

Compiling images relies on bootc-image-builder (BIB) containers.

## Runtimes
- **BIB target**: Executed inside `just vhdx` / `just raw` targets.
- **Pipeline**: Converts OCI image outputs to UEFI disk configurations.
- **Output**: Writes boot images directly to host directories.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 43: Local Registry and OCI Distribution

This chapter covers the documentation for **Local Registry and OCI Distribution** under MiOS.

### <a name="43_private_registry_quadlets"></a>43.Private Registry Quadlets: Private Registry Quadlets

> Path Reference: `/usr/share/doc/mios/manual.md#43_private_registry_quadlets`

#### Overview

Sets up private registry containers for local image hosting.

## Settings
- **Service**: Managed via registry Quadlet files.
- **Ports**: Exposes local registry endpoints on loopbacks.
- **Security**: Restricts pull requests to local adapters.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="43_image_caching_strategies"></a>43.Image Caching Strategies: Image Caching Strategies

> Path Reference: `/usr/share/doc/mios/manual.md#43_image_caching_strategies`

#### Overview

Caching static container layers reduces OCI build times.

## Setup
- **Storage**: Caches OCI layers inside local disks.
- **Mechanisms**: Re-uses unchanged base steps.
- **Tuning**: Configured in build scripts.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="43_deployed_ref_updates"></a>43.Deployed Ref Updates: Deployed Ref Updates

> Path Reference: `/usr/share/doc/mios/manual.md#43_deployed_ref_updates`

#### Overview

Upgrades local hosts using updated image references.

## Actions
- **Update**: executes `bootc switch` pointing to local registries.
- **Reconciliation**: Applies structural merges to configurations.
- **Verification**: Checks image metadata on next boot.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 44: Host Package Overrides and DNF5

This chapter covers the documentation for **Host Package Overrides and DNF5** under MiOS.

### <a name="44_usr_vs_etc_overrides"></a>44.USR vs ETC Overrides: USR vs ETC Overrides

> Path Reference: `/usr/share/doc/mios/manual.md#44_usr_vs_etc_overrides`

#### Overview

Manages file priority rules across system overlays.

## Overrides
- **USR**: Contains static default settings.
- **ETC**: Contains host-specific override scripts.
- **Priority**: System units parse ETC files before defaults.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="44_rpm_ostree_exemptions"></a>44.RPM OSTree Exemptions: RPM-OSTree Exemptions

> Path Reference: `/usr/share/doc/mios/manual.md#44_rpm_ostree_exemptions`

#### Overview

Exemptions allow manual packages installation for debugging.

## Rules
- **Access**: Enables installing individual debug packages.
- **Actions**: Restricts packages to target runtime slots.
- **Audit**: Logged in system configuration tracking.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="44_dependency_conflict_resolution"></a>44.Dependency Conflict Resolution: Dependency Conflict Resolution

> Path Reference: `/usr/share/doc/mios/manual.md#44_dependency_conflict_resolution`

#### Overview

Solves dependency conflicts during system builds.

## Troubleshooting
- **Helpers**: uses DNF5 commands with resolution flags.
- **Guards**: Stops builds on unresolvable conflict errors.
- **Testing**: Validates package versions integrity.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 45: Diagnostic Tools and Profilers

This chapter covers the documentation for **Diagnostic Tools and Profilers** under MiOS.

### <a name="45_hardware_capability_profiling"></a>45.Hardware Capability Profiling: Hardware Capability Profiling

> Path Reference: `/usr/share/doc/mios/manual.md#45_hardware_capability_profiling`

#### Overview

Profiles system capabilities using profiling scripts.

## Operations
- **Profiler**: Executed via [system-profiler.sh](file:///C:/MiOS/tools/system-profiler.sh).
- **Run tool**: Runs [run-all-profilers.sh](file:///C:/MiOS/tools/run-all-profilers.sh).
- **Output**: Logs system properties for review.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="45_egress_firewall_verification"></a>45.Egress Firewall Verification: Egress Firewall Verification

> Path Reference: `/usr/share/doc/mios/manual.md#45_egress_firewall_verification`

#### Overview

Validates outbound networking rules.

## Setup
- **Verify tool**: Run [generate-egress-firewall.py](file:///C:/MiOS/tools/generate-egress-firewall.py).
- **Checks**: Audits active rules inside firewall filters.
- **Safety**: Confines network execution blocks.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="45_profile_comparison_utilities"></a>45.Profile Comparison Utilities: Profile Comparison Utilities

> Path Reference: `/usr/share/doc/mios/manual.md#45_profile_comparison_utilities`

#### Overview

Compares configuration states against templates.

## Utilities
- **Script**: Run [profile-compare.sh](file:///C:/MiOS/tools/profile-compare.sh).
- **Checks**: Scans active configs against reference parameters.
- **Gating**: Detects drift parameters.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 46: User Persona Staging

This chapter covers the documentation for **User Persona Staging** under MiOS.

### <a name="46_default_user_creation"></a>46.Default User Creation: Default User Creation

> Path Reference: `/usr/share/doc/mios/manual.md#46_default_user_creation`

#### Overview

Sets up user accounts and home layouts.

## Configurations
- **Creation**: Executed via sysusers configs.
- **Script**: Handled by [31-user.sh](file:///C:/MiOS/automation/31-user.sh).
- **Rights**: Adds user accounts to virtual and container groups.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="46_stagings_dotfiles_overlay"></a>46.Stagings Dotfiles Overlay: Stagings Dotfiles Overlay

> Path Reference: `/usr/share/doc/mios/manual.md#46_stagings_dotfiles_overlay`

#### Overview

Deploys template configuration files to user home folders.

## Flow
- **Dotfiles**: Seeds user folders (e.g. `~/.config/mios/`).
- **Templates**: Sourced from `/etc/skel/`.
- **Integrity**: Merges parameters without destroying custom changes.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="46_multi_user_sandboxes"></a>46.Multi-User Sandboxes: Multi-User Sandboxes

> Path Reference: `/usr/share/doc/mios/manual.md#46_multi_user_sandboxes`

#### Overview

Isolates configuration environments across different user accounts.

## Details
- **Sandboxing**: Confines user environments.
- **Groups**: Restricts group permissions.
- **Access**: Prevents cross-user configuration editing.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 47: Virtual Machine Templates

This chapter covers the documentation for **Virtual Machine Templates** under MiOS.

### <a name="47_windows_11_secureboot_xml"></a>47.Windows 11 SecureBoot XML: Windows 11 SecureBoot XML

> Path Reference: `/usr/share/doc/mios/manual.md#47_windows_11_secureboot_xml`

#### Overview

Provides VM templates meeting Windows 11 Secure Boot specifications.

## Template
- **File**: Shipped in [win11-secureboot-template.xml](file:///C:/MiOS/tools/win11-secureboot-template.xml).
- **Features**: Includes vTPM, SecureBoot, and UEFI firmware settings.
- **Isolation**: Optimizes settings for VFIO passthrough.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="47_linux_guest_cloud_init"></a>47.Linux Guest Cloud-Init: Linux Guest Cloud-Init

> Path Reference: `/usr/share/doc/mios/manual.md#47_linux_guest_cloud_init`

#### Overview

Deploy virtual machines using pre-configured cloud-init settings.

## Operations
- **Cloud-Init**: Staged inside default VM tools.
- **Setup**: Configures default networks, accounts, and keys.
- **Tuning**: Speeds up guest environment provisioning.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="47_vm_lifecycle_management"></a>47.VM Lifecycle Management: VM Lifecycle Management

> Path Reference: `/usr/share/doc/mios/manual.md#47_vm_lifecycle_management`

#### Overview

Manages virtual guests using command tools.

## Actions
- **CLI**: Executed using libvirt's `virsh` tools.
- **States**: Starts, stops, and scales VM instances.
- **Tuning**: Configured in VM xml configurations.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 48: Local AI Web Consoles

This chapter covers the documentation for **Local AI Web Consoles** under MiOS.

### <a name="48_open_webui_deployment"></a>48.Open WebUI Deployment: Open WebUI Deployment

> Path Reference: `/usr/share/doc/mios/manual.md#48_open_webui_deployment`

#### Overview

Deploys Open WebUI as the primary browser chat interface.

## Details
- **Port**: Serves requests on port 3030.
- **Service**: Managed via `mios-owui` Quadlet.
- **Connection**: Connects internally to `/v1/chat/completions` on the local endpoint.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="48_interface_customization"></a>48.Interface Customization: Interface Customization

> Path Reference: `/usr/share/doc/mios/manual.md#48_interface_customization`

#### Overview

Customizes panels and options in the web interface.

## Settings
- **Customizations**: Configures defaults inside Open WebUI.
- **Tuning**: Integrates with local search tool paths.
- **Features**: Restricts outbound options.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="48_token_based_access_control"></a>48.Token-based Access Control: Token-based Access Control

> Path Reference: `/usr/share/doc/mios/manual.md#48_token_based_access_control`

#### Overview

Secures web access using credentials tokens.

## Details
- **Authentication**: secured via token strings.
- **Logs**: User connection actions are tracked.
- **Security**: Restricts local web console access.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 49: Offline-First Governance

This chapter covers the documentation for **Offline-First Governance** under MiOS.

### <a name="49_local_package_mirrors"></a>49.Local Package Mirrors: Local Package Mirrors

> Path Reference: `/usr/share/doc/mios/manual.md#49_local_package_mirrors`

#### Overview

Configures local update repositories to support air-gapped runtimes.

## Setup
- **Mirrors**: Maps DNF5 to local package directories.
- **Baking**: Packages are pre-loaded during image generation.
- **Rules**: Avoids network access requests on host update calls.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="49_sovereign_model_storage"></a>49.Sovereign Model Storage: Sovereign Model Storage

> Path Reference: `/usr/share/doc/mios/manual.md#49_sovereign_model_storage`

#### Overview

Caches model weights locally to prevent telemetry leaks.

## Storage
- **Weights**: Safely stored inside `/srv/ai/models/`.
- **Gating**: Missing weights prevent inference lanes from starting.
- **Updates**: Models are updated via offline imports.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="49_non_network_degradation_modes"></a>49.Non-Network Degradation Modes: Non-Network Degradation Modes

> Path Reference: `/usr/share/doc/mios/manual.md#49_non_network_degradation_modes`

#### Overview

Ensures local tools remain functional when offline.

## Settings
- **Degradation**: Disables search queries when offline.
- **Core Stacks**: Keeps local inference lanes active.
- **Governance**: Complies with the OFFLINE-FIRST law.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

## Chapter 50: Upstream Tracking and Maintenance

This chapter covers the documentation for **Upstream Tracking and Maintenance** under MiOS.

### <a name="50_upstream_drift_monitor"></a>50.Upstream Drift Monitor: Upstream Drift Monitor

> Path Reference: `/usr/share/doc/mios/manual.md#50_upstream_drift_monitor`

#### Overview

Monitors updates and changes inside upstream base OCI images.

## Details
- **Monitor**: Run [mios-upstream-monitor.sh](file:///C:/MiOS/tools/mios-upstream-monitor.sh).
- **Checks**: Compares package indexes against target reference lists.
- **Gating**: Detects drift parameters.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="50_justfile_pipeline_automation"></a>50.Justfile Pipeline Automation: Justfile Pipeline Automation

> Path Reference: `/usr/share/doc/mios/manual.md#50_justfile_pipeline_automation`

#### Overview

Automates repetitive build and test targets using Justfile.

## Tasks
- **Build**: Compiles image files using `just build`.
- **Verification**: Runs validations using `just lint`.
- **Packaging**: Packages artifacts using target tags.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="50_release_maturity_runbook"></a>50.Release Maturity Runbook: Release Maturity Runbook

> Path Reference: `/usr/share/doc/mios/manual.md#50_release_maturity_runbook`

#### Overview

Runbook steps guide moving image builds to release configurations.

## Flow
- **Runbook**: Mapped in [maturity-and-release-runbook.md](file:///C:/MiOS/usr/share/doc/mios/reference/maturity-and-release-runbook.md).
- **Checkpoints**: Verifies tests, SBOM compliance, and signatures.
- **Tagging**: Publishes checked builds under stable tags.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: `http://localhost:8080/v1`

#### Guidelines & Best Practices

1. Adhere to the Seven Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

