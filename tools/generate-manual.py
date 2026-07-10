#!/usr/bin/env python3
# AI-hint: A generation tool to compile and structure the complete 50-chapter MiOS User Manual into a single All-in-One file, cleaning up modular directories.
# AI-functions: main
import os
import argparse
import shutil

def main():
    parser = argparse.ArgumentParser(description="MiOS User Manual Generator")
    parser.add_argument(
        "--output",
        default=None,
        help="Target output file (defaults to usr/share/doc/mios/manual.md relative to repo root)"
    )
    args = parser.parse_args()

    # Determine script root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, ".."))

    if args.output:
        manual_path = os.path.abspath(args.output)
    else:
        manual_path = os.path.join(repo_root, "usr", "share", "doc", "mios", "manual.md")

    print(f"Target manual file: {manual_path}")

    # Clean up old modular directory folders (01_* through 50_*) if they exist under usr/share/doc/mios/manual/
    manual_dir = os.path.join(repo_root, "usr", "share", "doc", "mios", "manual")
    if os.path.exists(manual_dir):
        print(f"Cleaning up old manual directory: {manual_dir}")
        shutil.rmtree(manual_dir)

    # Ensure parent directory of manual.md exists
    parent_dir = os.path.dirname(manual_path)
    os.makedirs(parent_dir, exist_ok=True)

    # Credits mapping lookup matching rows in credits.md
    credits_map = {
        1: ("Linux kernel", "file:///usr/share/doc/mios/reference/credits.md#L39"),
        2: ("systemd", "file:///usr/share/doc/mios/reference/credits.md#L40"),
        3: ("dracut", "file:///usr/share/doc/mios/reference/credits.md#L41"),
        4: ("FHS 3.0", "file:///usr/share/doc/mios/reference/credits.md#L42"),
        5: ("Linux kernel parameters guide", "file:///usr/share/doc/mios/reference/credits.md#L43"),
        6: ("Linux sysctl reference", "file:///usr/share/doc/mios/reference/credits.md#L44"),
        7: ("bootc (CNCF Sandbox)", "file:///usr/share/doc/mios/reference/credits.md#L50"),
        8: ("ostree / libostree", "file:///usr/share/doc/mios/reference/credits.md#L51"),
        9: ("composefs", "file:///usr/share/doc/mios/reference/credits.md#L52"),
        10: ("Fedora bootc base images", "file:///usr/share/doc/mios/reference/credits.md#L53"),
        11: ("RHEL image mode", "file:///usr/share/doc/mios/reference/credits.md#L54"),
        12: ("Universal Blue", "file:///usr/share/doc/mios/reference/credits.md#L63"),
        13: ("ucore", "file:///usr/share/doc/mios/reference/credits.md#L64"),
        14: ("ucore-hci", "file:///usr/share/doc/mios/reference/credits.md#L65"),
        15: ("ccos", "file:///usr/share/doc/mios/reference/credits.md#L66"),
        16: ("Bluefin / Aurora / Bazzite", "file:///usr/share/doc/mios/reference/credits.md#L67"),
        17: ("Containerfile", "file:///usr/share/doc/mios/reference/credits.md#L75"),
        18: ("Justfile", "file:///usr/share/doc/mios/reference/credits.md#L76"),
        19: ("Podman", "file:///usr/share/doc/mios/reference/credits.md#L77"),
        20: ("Buildah", "file:///usr/share/doc/mios/reference/credits.md#L78"),
        21: ("Skopeo", "file:///usr/share/doc/mios/reference/credits.md#L79"),
        22: ("dnf5", "file:///usr/share/doc/mios/reference/credits.md#L80"),
        23: ("bootc-image-builder (BIB)", "file:///usr/share/doc/mios/reference/credits.md#L81"),
        24: ("image-builder-cli", "file:///usr/share/doc/mios/reference/credits.md#L82"),
        25: ("rechunk", "file:///usr/share/doc/mios/reference/credits.md#L83"),
        26: ("Anaconda", "file:///usr/share/doc/mios/reference/credits.md#L84"),
        27: ("Renovate", "file:///usr/share/doc/mios/reference/credits.md#L85"),
        28: ("GitHub Actions", "file:///usr/share/doc/mios/reference/credits.md#L86"),
        29: ("GHCR", "file:///usr/share/doc/mios/reference/credits.md#L87"),
        30: ("Sigstore / cosign", "file:///usr/share/doc/mios/reference/credits.md#L88"),
        31: ("syft", "file:///usr/share/doc/mios/reference/credits.md#L89"),
        32: ("shellcheck", "file:///usr/share/doc/mios/reference/credits.md#L90"),
        33: ("hadolint", "file:///usr/share/doc/mios/reference/credits.md#L91"),
        34: ("openssl", "file:///usr/share/doc/mios/reference/credits.md#L92"),
        35: ("Podman Quadlet", "file:///usr/share/doc/mios/reference/credits.md#L98"),
        36: ("Container Device Interface (CDI)", "file:///usr/share/doc/mios/reference/credits.md#L99"),
        37: ("containers.conf / storage.conf", "file:///usr/share/doc/mios/reference/credits.md#L100"),
        38: ("containers/storage", "file:///usr/share/doc/mios/reference/credits.md#L101"),
        39: ("containers/image", "file:///usr/share/doc/mios/reference/credits.md#L102"),
        40: ("nvidia-container-toolkit", "file:///usr/share/doc/mios/reference/credits.md#L103"),
        41: ("LocalAI", "file:///usr/share/doc/mios/reference/credits.md#L114"),
        42: ("Ollama", "file:///usr/share/doc/mios/reference/credits.md#L115"),
        43: ("vLLM", "file:///usr/share/doc/mios/reference/credits.md#L116"),
        44: ("llama.cpp server", "file:///usr/share/doc/mios/reference/credits.md#L117"),
        45: ("LM Studio", "file:///usr/share/doc/mios/reference/credits.md#L118"),
        46: ("LiteLLM", "file:///usr/share/doc/mios/reference/credits.md#L119"),
        47: ("OpenRouter", "file:///usr/share/doc/mios/reference/credits.md#L120"),
        48: ("llama.cpp (engine)", "file:///usr/share/doc/mios/reference/credits.md#L121"),
        49: ("API Reference (root)", "file:///usr/share/doc/mios/reference/credits.md#L130"),
        50: ("Models catalog", "file:///usr/share/doc/mios/reference/credits.md#L131"),
        51: ("Responses API", "file:///usr/share/doc/mios/reference/credits.md#L132"),
        52: ("Chat Completions", "file:///usr/share/doc/mios/reference/credits.md#L133"),
        53: ("Function calling / tools", "file:///usr/share/doc/mios/reference/credits.md#L134")
    }

    # Comprehensive chapter data mapping (50 chapters, 152 pages total)
    chapters = [
        {
            "num": "01",
            "title": "Introduction_and_Core_Concepts",
            "display": "Introduction and Core Concepts",
            "pages": {
                "What_is_MiOS.md": {
                    "title": "What is MiOS",
                    "desc": "Defines the dual nature of MiOS as an immutable, bootc Fedora workstation and a local agentic OS.",
                    "citations": [1, 2, 3],
                    "content": "MiOS (pronounced *\"MyOS\"*) is a specialized operating system built to serve two roles simultaneously:\n\n1. **Immutable Workstation**: It is a Fedora-based, bootc-native OCI container image. The entire OS is compiled, linted, and distributed as a single OCI container. The running system operates on a read-only rootfs (`/usr` composefs/ostree mount), meaning updates are transactional (similar to a `git pull`) and rollbacks are atomic.\n2. **Local Agentic AI OS**: It is a sovereign, self-contained AI-powered operating system. The desktop interface is tightly integrated with a local inference engine, model-swapping proxies, an agent router, and pgvector semantic database memory. All agent tools, terminal interfaces, and desktop widgets interact with a unified local endpoint, enabling the system to inspect, run code, and configure itself completely offline."
                },
                "Repo_IS_Root_Paradigm.md": {
                    "title": "Repo IS Root Paradigm",
                    "desc": "Explains how the Git repository tree directly mirrors the deployed OS filesystem at the system root.",
                    "citations": [3, 4, 5, 6],
                    "content": "The `mios.git` repository root *is* the running host's system root (`/`). There is no temporary build directory, no intermediate staging workspace, and no Ansible configuration playbooks.\n\n- **Structure**: The files in the repository (e.g. `usr/`, `etc/`, `srv/`, `var/`) are mapped directly to their FHS positions on the booted system.\n- **Overlay Application**: During the container image build, the script [08-system-files-overlay.sh](file:///C:/MiOS/automation/08-system-files-overlay.sh) applies the overlay files directly to the rootfs.\n- **Developer Workflow**: To change a configuration or utility in the OS, you edit it at its natural path inside the repository and trigger a rebuild. When the OCI image is updated, `bootc` handles the transactional merge on the target machine."
                },
                "The_Seven_Architectural_Laws.md": {
                    "title": "The Seven Architectural Laws",
                    "desc": "Details the non-negotiable mandates: USR-OVER-ETC, NO-MKDIR-IN-VAR, BOUND-IMAGES, etc.",
                    "citations": [7, 8, 9],
                    "content": "Governance of MiOS is defined by seven strict, non-negotiable mandates enforced at build-time by [38-ssot-lint.sh](file:///C:/MiOS/automation/38-ssot-lint.sh), [38-drift-checks.sh](file:///C:/MiOS/automation/38-drift-checks.sh), and [99-postcheck.sh](file:///C:/MiOS/automation/99-postcheck.sh):\n\n1. **USR-OVER-ETC**: Static system configs must reside in `/usr/lib/<component>.d/`. The `/etc/` directory is reserved solely for administrative overrides.\n2. **NO-MKDIR-IN-VAR**: Build-time scripts must never call `mkdir` inside `/var/`. All `/var/` paths must be declared declaratively via `usr/lib/tmpfiles.d/*.conf`.\n3. **BOUND-IMAGES**: Every Podman Quadlet container image must be symlinked under `/usr/lib/bootc/bound-images.d/` and baked into `/usr/lib/containers/storage` at build-time.\n4. **BOOTC-CONTAINER-LINT**: The last instruction of the `Containerfile` must be `RUN bootc container lint`. A failing lint fails the build.\n5. **UNIFIED-AI-REDIRECTS**: All local services, tools, and agents must communicate with `MIOS_AI_ENDPOINT`. No vendor-hardcoded URLs are allowed.\n6. **UNPRIVILEGED-QUADLETS**: All Quadlet units must declare `User=`, `Group=`, and `Delegate=yes` configuration bounds. The only exceptions are `mios-ceph` and `mios-k3s` (which require root block device access).\n7. **NO-HARDCODE**: Nothing operator-tunable, including model names, ports, or scoring parameters, may be hardcoded. Values must resolve via the `mios.toml` configuration cascade."
                }
            }
        },
        {
            "num": "02",
            "title": "Installation_and_Deployment",
            "display": "Installation and Deployment",
            "pages": {
                "Day-0_Bootstrap.md": {
                    "title": "Day-0 Bootstrap",
                    "desc": "Covers provisioning the MiOS-DEV seed environment via Windows PowerShell or the Linux just runner.",
                    "citations": [10, 11, 12, 13],
                    "content": "Day-0 refers to provisioning the initial developer workstation (`MiOS-DEV`) before the OCI image is compiled.\n\n## Windows Bootstrap\nThe canonical entry is a single command executed from the Windows Run dialog (`Win+R`):\n```text\npowershell -ExecutionPolicy Bypass -Command \"irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1 | iex\"\n```\nThe script `Get-MiOS.ps1` checks preflight requirements, self-elevates, allocates an `M:\\` drive (256 GB NTFS), installs Podman, clones the repository, and triggers the OCI build.\n\n## Linux Bootstrap\nDevelopers on bare-metal Linux can initialize the environment using:\n```bash\ngit clone https://github.com/mios-dev/MiOS.git && cd MiOS\njust preflight\njust build\n```"
                },
                "First_Boot_Initialization.md": {
                    "title": "First Boot Initialization",
                    "desc": "Outlines the provisioning sequence for the build plane, CDI, libvirt, and AI plane on first boot.",
                    "citations": [14, 15],
                    "content": "Once the OCI image is generated and written, the system boots into the First Boot phase (Phase-1 and Phase-2 of the bootstrap chain).\n\nThe first-boot sequence processes:\n1. **Container Device Interface (CDI)**: Probes physical graphics adapters and renders CDI schemas under `/var/run/cdi/`.\n2. **Account Staging**: Staged accounts defined under `/usr/lib/sysusers.d/` are initialized with home directory paths by [31-user.sh](file:///C:/MiOS/automation/31-user.sh).\n3. **Libvirt & Virtualization**: The virtual networking layers, VM templates, and CPU affinity shims are initialized.\n4. **AI Services Plane**: The PostgreSQL database and the llama-swap proxy are initialized."
                },
                "Day-N_Self_Replication.md": {
                    "title": "Day-N Self-Replication",
                    "desc": "Details the continuous CI/CD loop where a running MiOS host builds and updates its own OCI images.",
                    "citations": [11, 16, 17],
                    "content": "A deployed MiOS host is fully self-replicating. It contains all the compilers, container tools, and build runners required to recreate itself.\n\n## Self-Replication Loop\n1. **Local Repository**: An in-distro git server (Forgejo, port 3000) hosts the system configuration repository.\n2. **CI/CD Runner**: A containerized runner (`mios-forgejo-runner`) listens for pushes to the system config repository.\n3. **Build Target**: When an operator pushes changes to the local repo, the runner triggers a local build and executes a local bootc upgrade: `sudo bootc upgrade --apply` to swap the active root filesystem transactional index."
                },
                "Deployment_Targets.md": {
                    "title": "Deployment Targets",
                    "desc": "Provides recipes for deploying the MiOS image to bare-metal hosts, VHDX, RAW, WSL2, and ISO.",
                    "citations": [18, 19],
                    "content": "The compiled OCI container image can be transformed into multiple deployment targets using the bootc-image-builder (BIB) utility.\n\nThe `Justfile` provides direct wrappers for compiling these artifacts:\n- **Bare-metal**: RAW image for flashing to physical disks (`just raw`)\n- **Hyper-V**: VHDX virtual disk with staged UEFI (`just vhdx`)\n- **QEMU/KVM**: QCOW2 virtual disk (`just qcow2`)\n- **WSL2**: `tar.gz` distribution file (`just wsl2`)\n- **ISO**: Anaconda installer ISO for manual setups (`just iso`)"
                }
            }
        },
        {
            "num": "03",
            "title": "System_Configuration_and_Governance",
            "display": "System Configuration and Governance",
            "pages": {
                "Single_Source_Of_Truth.md": {
                    "title": "Single Source of Truth",
                    "desc": "Explains the management of packages, AI lanes, and quadlets centrally via mios.toml.",
                    "citations": [20, 21, 22],
                    "content": "System configuration on MiOS is managed centrally via one configuration format: `mios.toml`.\n\nThis file controls user parameters, package selections, Flatpaks, AI stack configurations, and hardware allocations. A graphical configurator tool is shipped at [mios.html](file:///C:/MiOS/usr/share/mios/configurator/mios.html). Running `sudo mios-sync-env` refreshes `/etc/mios/install.env` to align systemd environment variables."
                },
                "Three_Layer_Override_Model.md": {
                    "title": "Three-Layer Override Model",
                    "desc": "Maps configuration resolution precedence across vendor, host, and user levels.",
                    "citations": [23, 24],
                    "content": "Configuration resolution follows a strict three-layer precedence model to ensure system immutable integrity while allowing flexible per-user settings:\n\n1. `~/.config/mios/mios.toml` -- per-user override (highest precedence)\n2. `/etc/mios/mios.toml` -- host/admin override (shipped by bootstrap)\n3. `/usr/share/mios/mios.toml` -- vendor defaults (shipped by image, lowest precedence)\n\nAll settings are merged key-by-key at runtime, where higher layers supersede lower layers."
                },
                "Declarative_Package_Management.md": {
                    "title": "Declarative Package Management",
                    "desc": "Documents DNF5 integration, flatpak configurations, and the separation of PACKAGES.md.",
                    "citations": [25, 26, 27, 28],
                    "content": "To ensure that the root remains clean and deterministic, packages are declared statically in the system configuration.\n\n- **System Packages**: Declared in `/usr/share/mios/mios.toml` under `[packages.<section>].pkgs` and installed using DNF5.\n- **Flatpaks**: Desktop GUI apps are declared in the same file under `[flatpaks]` and baked into the image Flatpak store.\n- **Package Rationale**: Human-readable descriptions are documented in [PACKAGES.md](file:///C:/MiOS/usr/share/doc/mios/reference/PACKAGES.md)."
                }
            }
        },
        {
            "num": "04",
            "title": "The_Agentic_AI_Stack",
            "display": "The Agentic AI Stack",
            "pages": {
                "Unified_AI_Endpoint.md": {
                    "title": "Unified AI Endpoint",
                    "desc": "Describes the routing of all AI interactions through the MIOS_AI_ENDPOINT (Hermes gateway, port 8642).",
                    "citations": [1, 29, 30],
                    "content": "To avoid hardcoded vendor SDK dependencies, all intelligence pipelines on MiOS are routed through a single local endpoint on loopback named by `MIOS_AI_ENDPOINT` (the Hermes gateway on `:8642`). This endpoint abstractly translates chat-completions and embeddings requests to the active inference backend, ensuring client compatibility."
                },
                "Agent_Pipe_Orchestrator.md": {
                    "title": "Agent Pipe Orchestrator",
                    "desc": "Details the primary front door on port 8640 used to route requests and fan out tasks.",
                    "citations": [31, 32],
                    "content": "The Agent Pipe Orchestrator (port **8640**) acts as the cognitive router for all user-facing interfaces.\n\nWhen a prompt is submitted, the orchestrator performs intention refinement, decomposes the query into a task graph, coordinates sub-agents, executes tool loops, and streams aggregated answers back to client views."
                },
                "MiOS_Hermes_Gateway.md": {
                    "title": "MiOS Hermes Gateway",
                    "desc": "Outlines the operation of the tool-loop gateway and session manager running on port 8642.",
                    "citations": [31, 33],
                    "content": "MiOS Hermes (port **8642**) is the core session and tool-loop execution manager.\n\n- **Session Ownership**: Tracks state and history for active contexts.\n- **Tool-Loop Execution**: Validates and executes tool calls sent by LLMs.\n- **Skills Management**: Manages reusable python code blocks (\"skills\") loaded from system configurations.\n- **Telemetry**: Exposes the Hermes Dashboard on port 9119 to monitor session states and tool logs."
                },
                "Inference_Lanes.md": {
                    "title": "Inference Lanes",
                    "desc": "Maps the local token generation engines, llama.cpp proxy, and VRAM-gated heavy lanes.",
                    "citations": [34, 35],
                    "content": "MiOS splits LLM inference across separate functional lanes to match the host hardware resources:\n\n1. **Light Lane (`mios-llm-light`)**: Running llama.cpp with a llama-swap proxy on port `11450` for everyday chat, code assistance, and embeddings.\n2. **Heavy Lane (`mios-llm-heavy` / `mios-llm-heavy-alt`)**: Running SGLang (port `11441`) or vLLM (port `11440`) for large reasoning models, gated off by default."
                },
                "Unified_Agent_Memory.md": {
                    "title": "Unified Agent Memory",
                    "desc": "Covers episodic and long-term knowledge storage using PostgreSQL and pgvector.",
                    "citations": [1, 32, 36],
                    "content": "The persistent memory plane of MiOS is structured within a PostgreSQL database with the `pgvector` extension, running inside the `mios-pgvector` container (port 5432).\n\nIt stores raw session logs as episodic memory, and vector-embedded knowledge chunks as semantic memory. Dynamic cosine-similarity searches inject historical context directly into agent prompts."
                }
            }
        },
        {
            "num": "05",
            "title": "Federation_and_Computer_Use",
            "display": "Federation and Computer Use",
            "pages": {
                "Model_Context_Protocol.md": {
                    "title": "Model Context Protocol",
                    "desc": "Details the standardized MCP interface utilized by agents to discover external tools.",
                    "citations": [37, 38, 39],
                    "content": "The Model Context Protocol (MCP) defines the standard interface for how agents discover and execute system tools.\n\n- **Registry**: Configured dynamically under `/usr/share/mios/ai/v1/mcp.json`.\n- **Pre-installed Servers**: Includes `mios-fs` (filesystem), `mios-kb` (vector recall), and `mios-forge` (git repository control).\n- **Confinement**: MCP servers execute tool scripts inside unprivileged namespaces."
                },
                "Agent_To_Agent_Delegation.md": {
                    "title": "Agent-to-Agent Delegation",
                    "desc": "Documents the A2A JSON-RPC specifications for peer delegation.",
                    "citations": [34, 37, 38],
                    "content": "Complex tasks are fanned out to specialized sub-agents using the Agent-to-Agent (A2A) protocol.\n\n- **Communication**: Uses a JSON-RPC payload schema over standard loopback ports.\n- **Discovery**: Agents query the registry at `/v1/agents` to discover capabilities.\n- **Delegation**: The orchestrator delegates code tasks to the `mios-opencode` coding agent (port 8633), which modifies files and returns validation results."
                },
                "Vision_and_OS_Control.md": {
                    "title": "Vision and OS Control",
                    "desc": "Explains Wayland automation, vision grounding via UI-TARS, and pc-control tools.",
                    "citations": [40, 41, 42],
                    "content": "MiOS provides agents with the ability to interact directly with the GNOME desktop environment.\n\n- **Vision Grounding**: Agents utilize the UI-TARS vision-language model to translate user requests into click coordinates on the Wayland display server.\n- **Accessibility Tree**: Traversals are aided by the AT-SPI semantic screen tree, providing structural context for UI elements.\n- **Execution**: Physical actions (mouse moves, clicks, keystrokes) are simulated using the custom `mios-pc-control` command suite."
                }
            }
        },
        {
            "num": "06",
            "title": "Security_and_Hardware_Virtualization",
            "display": "Security and Hardware Virtualization",
            "pages": {
                "Immutable_Root_and_Integrity.md": {
                    "title": "Immutable Root and Integrity",
                    "desc": "Explains composefs sealing of the read-only /usr directory and fs-verity.",
                    "citations": [43, 44],
                    "content": "System integrity on MiOS is guaranteed through cryptographic filesystem sealing:\n\n- **Immutable Directories**: The system binaries under `/usr` are mounted as a read-only composefs image.\n- **Integrity Validation**: Files are monitored using `fs-verity`. Any attempt to modify a binary on disk is blocked by the kernel.\n- **Upgrades**: Upgrades are delivered as updated OCI image layers. The bootc agent writes the new layers to a separate partition index and atomically updates the EFI boot variables to point to the new composefs root on reboot."
                },
                "Runtime_Guards.md": {
                    "title": "Runtime Guards",
                    "desc": "Details defense-in-depth mechanisms via CrowdSec, fapolicyd, and USBGuard.",
                    "citations": [45],
                    "content": "To defend against intrusion and unauthorized executions, MiOS deploys three automated guard systems:\n\n1. **fapolicyd**: Denies execution of any binary or script not matching the trust database in `/etc/fapolicyd/fapolicyd.trust`.\n2. **USBGuard**: Blocks unauthorized USB device connections to prevent keystroke injection attacks (rules in `/etc/usbguard/usbguard-daemon.conf`).\n3. **CrowdSec**: Monitors logs to detect suspicious activities and blocks offending network hosts at the firewall level."
                },
                "Keyless_Image_Signing.md": {
                    "title": "Keyless Image Signing",
                    "desc": "Covers OCI validation and authentication via Sigstore and cosign.",
                    "citations": [46],
                    "content": "To secure the OCI software supply chain, all MiOS OCI images must be cryptographically signed before deployment.\n\n- **Verification Tools**: Integrated via **Sigstore** and **cosign**.\n- **Keyless Signature**: In CI/CD pipelines, images are signed using OIDC tokens, verifying that the build originated from the official pipeline.\n- **Verification Rule**: The host's container policy config ([42-cosign-policy.sh](file:///C:/MiOS/automation/42-cosign-policy.sh)) enforces validation check rules, blocking container pulls of unsigned or unrecognized images."
                },
                "Unprivileged_Quadlet_Model.md": {
                    "title": "Unprivileged Quadlet Model",
                    "desc": "Documents user permission tiers required to execute services via rootless Podman.",
                    "citations": [7, 47, 48],
                    "content": "All daemonized AI containers on MiOS are run inside unprivileged user namespaces to minimize potential host escalation risks.\n\n- **Quadlet Design**: Podman Quadlets are stored under `/usr/share/containers/systemd/`.\n- **Least Privilege**: Each Quadlet file must declare `User=mios`, `Group=mios`, and `Delegate=yes` bounds. This maps the container's internal root user (UID 0) to an unprivileged host user (UID 1000+), preventing sandbox escapes from gaining host root access."
                },
                "Hardware_Passthrough.md": {
                    "title": "Hardware Passthrough",
                    "desc": "Maps GPU exposure to virtual machines and containers via VFIO-PCI and CDI.",
                    "citations": [1, 49, 50],
                    "content": "For high-performance AI inference and gaming, MiOS isolates and passes physical graphics cards directly to VM and container environments.\n\n- **VFIO Isolation**: Target GPUs are bound to the `vfio-pci` driver during boot, disabling the host display driver.\n- **Libvirt Integration**: VMs request GPU resources via direct PCI pass-through paths.\n- **Container Acceleration**: Containers request GPU hardware using CDI (Container Device Interface) profiles generated dynamically based on active hardware, allowing CUDA runtimes to execute in rootless Podman tasks."
                }
            }
        },
        {
            "num": "07",
            "title": "Cluster_and_Storage_Fabric",
            "display": "Cluster and Storage Fabric",
            "pages": {
                "K3s_Kubernetes_Integration.md": {
                    "title": "K3s Kubernetes Integration",
                    "desc": "Outlines the mechanisms for expanding the workstation into a Kubernetes cluster.",
                    "citations": [1, 51],
                    "content": "MiOS workstation hosts can expand dynamically into single-node high-availability Kubernetes clusters.\n\n- **Runtime daemon**: Managed via `mios-k3s.service` Quadlet.\n- **Network Isolation**: Traefik acts as the ingress controller, managing routing protocols on standard cluster ports.\n- **SELinux Policies**: Custom SELinux policies are applied by [19-k3s-selinux.sh](file:///C:/MiOS/automation/19-k3s-selinux.sh) to ensure containerized cluster tasks do not violate host read-only security bounds."
                },
                "Ceph_Distributed_Storage.md": {
                    "title": "Ceph Distributed Storage",
                    "desc": "Explains CephFS containerized storage deployments and privileged exemptions.",
                    "citations": [1, 52, 53],
                    "content": "Distributed storage clustering on MiOS is provisioned via containerized CephFS data planes and privileged exemptions.\n\n- **Service quadlet**: Managed via `mios-ceph.service`.\n- **Permissions**: Ceph requires low-level block device access, making it one of the few services exempt from Law 6 (running as host root).\n- **User Integration**: User desktop directories (e.g. `~/Documents`) can be mapped directly onto local CephFS shares, enabling automated, encrypted background backups across the storage network."
                }
            }
        },
        {
            "num": "08",
            "title": "Bootloader_and_Unified_Kernel_Images",
            "display": "Bootloader and Unified Kernel Images (UKI)",
            "pages": {
                "UKI_Layout_and_Baking.md": {
                    "title": "UKI Layout and Baking",
                    "desc": "Covers compilation and structure of Unified Kernel Images via systemd-ukify.",
                    "content": "Unified Kernel Images (UKIs) combine the Linux kernel, initramfs, and kernel command-line arguments into a single EFI executable. This ensures that the system boot configuration cannot be altered by modifying individual config files on disk.\n\n## Implementation Details\n- **Build tool**: Compiled via `systemd-ukify` during the OCI build.\n- **Baking script**: Executed by [23-uki-render.sh](file:///C:/MiOS/automation/23-uki-render.sh).\n- **Output**: The output `.efi` image is placed directly in the EFI system partition under `/boot/EFI/Linux/`.\n- **Validation**: Verified by `validate-kargs.py` to ensure core arguments are baked into the UKI."
                },
                "Secure_Boot_Integrity.md": {
                    "title": "Secure Boot Integrity",
                    "desc": "Details kernel module signing, trust models, and cryptographic verification chains.",
                    "content": "Secure Boot ensures that only cryptographically signed binaries can be executed during the boot phase.\n\n## Validation Chain\n1. **UEFI Keys**: The motherboard firmware holds the PK (Platform Key), KEK (Key Exchange Key), and db (Signature Database).\n2. **Custom Keys**: MiOS signs custom kernel modules (like ZFS and KVMFR) using a Machine Owner Key (MOK).\n3. **MOK Enrollment**: Handled via [enroll-mok.sh](file:///C:/MiOS/automation/enroll-mok.sh) and [generate-mok-key.sh](file:///C:/MiOS/automation/generate-mok-key.sh).\n4. **Enforcement**: Secure Boot enforces that all drivers compiled at build time are verified against the MOK database before launching the kernel."
                },
                "Kernel_Arguments_and_Gating.md": {
                    "title": "Kernel Arguments and Gating",
                    "desc": "Explains static kernel arguments in kargs.d mapping to VM and GPU isolation.",
                    "content": "Kernel arguments customize hardware and hypervisor settings during system launch.\n\n## Active Arguments\n- **VFIO Isolation**: `intel_iommu=on` or `amd_iommu=on` and `iommu=pt` to enable PCI passthrough.\n- **Immutable Root**: `ostree=` and `composefs=` parameters directing ostree to mount `/usr` as a composefs index.\n- **Gating**: Verified dynamically during early boot. Incorrect configurations trigger fallback states."
                }
            }
        },
        {
            "num": "09",
            "title": "Systemd_and_Quadlet_Orchestration",
            "display": "Systemd and Quadlet Orchestration",
            "pages": {
                "Unprivileged_Systemd_Tiers.md": {
                    "title": "Unprivileged Systemd Tiers",
                    "desc": "Defines user-space daemon layers and systemd-generator permissions configuration.",
                    "content": "MiOS uses unprivileged systemd user services to run AI components safely within user space boundaries.\n\n## Architecture\n- **User Unit Path**: `/usr/lib/systemd/user/` or `~/.config/systemd/user/`.\n- **System-User Map**: Enforced via systemd sysusers templates in [31-user.sh](file:///C:/MiOS/automation/31-user.sh).\n- **Execution Limits**: Systemd user instances map execution boundaries using user namespaces, isolating processes from direct host root access."
                },
                "Quadlet_Configuration_Syntax.md": {
                    "title": "Quadlet Configuration Syntax",
                    "desc": "Explains how podman quadlets render systemd unit files on startup.",
                    "content": "Podman Quadlets simplify systemd container management by translating `.container`, `.volume`, and `.network` configuration files into native systemd units on boot.\n\n## Code Conventions\n- **Source Paths**: Shipped under `/usr/share/containers/systemd/` or `/etc/containers/systemd/`.\n- **Translation Engine**: Parsed by `podman-systemd-generator`.\n- **Key Settings**: `[Container]` section specifying images, mounts, and network bridges; `User=mios` and `Group=mios` limits."
                },
                "Dynamic_Service_Activation.md": {
                    "title": "Dynamic Service Activation",
                    "desc": "Details service lifecycle states triggered by sync-env or user edits.",
                    "content": "Services are dynamically activated, stopped, or scaled based on host states and profile settings.\n\n## Execution Flows\n- **Trigger**: Run `mios-sync-env` to regenerate `/etc/mios/install.env`.\n- **Service Reload**: Triggers `systemctl daemon-reload` and user daemon reloads to parse environment updates.\n- **Gating**: Services check system status indicators (`ConditionPathExists`, etc.) before completing startup."
                }
            }
        },
        {
            "num": "10",
            "title": "Local_Inference_Lanes_and_Llamacpp",
            "display": "Local Inference Lanes and llama.cpp",
            "pages": {
                "Llama_Swap_Proxy_Architecture.md": {
                    "title": "Llama-Swap Proxy Architecture",
                    "desc": "Covers how llama-swap handles hot swapping and KV paging on port 11450.",
                    "content": "The llama-swap proxy manages model requests on port **11450**, serving as the single entry point for light inference tasks.\n\n## Routing Logic\n1. **Model Swap**: Swaps the underlying `llama-server` process on-demand to match the requested model name.\n2. **Context Saving**: Pages the KV context of inactive conversations to disk using `--slot-save-path`.\n3. **KV Restoring**: Reloads KV pages on subsequent requests via `POST /slots/{id}` calls.\n4. **Performance**: Reduces memory use by ensuring only active models remain resident in VRAM/RAM."
                },
                "Embedded_Inference_Setup.md": {
                    "title": "Embedded Inference Setup",
                    "desc": "Maps GPU context management, prompt template bindings, and model formats.",
                    "content": "Embedded inference on MiOS uses optimized GGUF format weights to enable local execution on GPU or CPU.\n\n## Setup Details\n- **Context Size**: Standardized context boundaries are mapped dynamically in [38-llamacpp-prep.sh](file:///C:/MiOS/automation/38-llamacpp-prep.sh).\n- **Embeddings**: An embedding-configured llama-server runs in parallel to handle vector queries.\n- **Safety**: Uses static model limits and resource controls to prevent container memory limit crashes."
                },
                "Model_Map_and_Hot_Swapping.md": {
                    "title": "Model Map and Hot Swapping",
                    "desc": "Documents model map configuration file and resource optimization strategies.",
                    "content": "Models are mapped in [mios-llm-light.yaml](file:///C:/MiOS/usr/share/mios/llamacpp/mios-llm-light.yaml), defining served model aliases and parameters.\n\n## Configuration\n- **Model Keys**: Mapping `granite4.1:8b` (default chat), `nomic-embed-text` (embeddings), and `mios-opencode` (coding model).\n- **Auto-swap Gating**: llama-swap monitors inbound request headers to spin down idle processes and start target weights."
                }
            }
        },
        {
            "num": "11",
            "title": "Heavy_GPU_Lanes_and_SGLang_vLLM",
            "display": "Heavy GPU Lanes and SGLang/vLLM",
            "pages": {
                "SGLang_GPU_Gating_Policies.md": {
                    "title": "SGLang GPU Gating Policies",
                    "desc": "Defines how SGLang is conditionally run depending on VRAM and workloads.",
                    "content": "The heavy reasoning lane utilizes SGLang (port **11441**) to serve large language models when hardware allows.\n\n## Policies\n- **VRAM Gating**: Checked at startup using `ConditionPathExists=/usr/share/mios/sglang/model/config.json`.\n- **Exclusion**: SGLang and vLLM are mutually exclusive to prevent VRAM allocation conflicts.\n- **Host Check**: Probes dGPU memory to verify available resources before launching SGLang containers."
                },
                "VLLM_Swarm_Workers.md": {
                    "title": "vLLM Swarm Workers",
                    "desc": "Explains multi-model scaling and distributed worker configurations.",
                    "content": "The alternate heavy lane uses vLLM (port **11440**) to run swarm worker instances.\n\n## Operations\n- **PagedAttention**: Uses vLLM's memory manager to scale batch concurrency.\n- **Swarm worker**: Workers can be dynamically spun up using `mios-llm-worker@.service` templates.\n- **Load Balancing**: Distributes token generation tasks across workers for high-volume jobs."
                },
                "VRAM_Allocation_and_Scheduling.md": {
                    "title": "VRAM Allocation and Scheduling",
                    "desc": "Covers pre-allocation thresholds and dynamic offloading policies.",
                    "content": "VRAM scheduling isolates graphics memory resources between virtual machines (Looking Glass) and heavy reasoning lanes.\n\n## Boundaries\n- **VM Priority**: Virtual machines claim allocated VRAM statically at boot.\n- **AI lane scaling**: Heavy LLM lanes adjust context sizes and batch bounds dynamically based on remaining VRAM.\n- **Recovery**: Automatic shutdown of heavy lanes if a primary VM requests resources."
                }
            }
        },
        {
            "num": "12",
            "title": "Unified_Memory_and_Pgvector_Schema",
            "display": "Unified Memory and pgvector Schema",
            "pages": {
                "PostgreSQL_Integration.md": {
                    "title": "PostgreSQL Integration",
                    "desc": "Details pgvector database container setup, connection pools, and permissions.",
                    "content": "MiOS integrates PostgreSQL inside rootless Podman to serve as the unified agent datastore.\n\n## Settings\n- **Service**: `mios-pgvector.service` running on port 5432.\n- **User Mapping**: Maps host UID 826 to container database root.\n- **Connection**: Supports secure loopback socket connections for local services."
                },
                "Semantic_Knowledge_Recall.md": {
                    "title": "Semantic Knowledge Recall",
                    "desc": "Explains cosine-similarity searches utilizing vector retrieval.",
                    "content": "Memory and knowledge tables are queried using semantic vector searches.\n\n## Query Pipeline\n- **Embedding**: Prompt vectors are generated using the `nomic-embed-text` lane.\n- **SQL Query**: Searches the `knowledge` table using pgvector's HNSW index operators:\n  ```sql\n  SELECT content FROM knowledge ORDER BY embedding <=> $1 LIMIT 5;\n  ```\n- **Injection**: Retrieved content is injected into agent context to guide response generation."
                },
                "Epistemic_Memory_Pruning.md": {
                    "title": "Epistemic Memory Pruning",
                    "desc": "Covers background archival workers and semantic consolidation.",
                    "content": "To maintain search performance, memory indexes are optimized via background pruning.\n\n## Methods\n- **Consolidation**: Consolidates multiple redundant logs into single semantic entries.\n- **Archiving**: Moves historical logs to offline JSON archives.\n- **Index Cleanup**: Runs `VACUUM ANALYZE` on memory tables to rebuild HNSW graphs."
                }
            }
        },
        {
            "num": "13",
            "title": "Model_Context_Protocol_Integration",
            "display": "Model Context Protocol Integration",
            "pages": {
                "Custom_MCP_Server_Design.md": {
                    "title": "Custom MCP Server Design",
                    "desc": "Describes how to write custom Python or Go MCP servers.",
                    "content": "Developers can extend agent capabilities by writing custom Model Context Protocol (MCP) servers.\n\n## Guidelines\n- **Language**: Python or Go is recommended.\n- **Communication**: Uses JSON-RPC over stdin/stdout or SSE transport.\n- **Registration**: Register the server in `/usr/share/mios/ai/v1/mcp.json` or `~/.config/mios/mcp.json`."
                },
                "Tool_Discovery_Protocols.md": {
                    "title": "Tool Discovery Protocols",
                    "desc": "Covers how the AI gateway queries the system tool registry.",
                    "content": "The system uses dynamic tool discovery to collect active MCP tools at session start.\n\n## Flow\n1. **Parse Manifest**: Reads the registered MCP server list in `/v1/mcp`.\n2. **Tool Handshake**: Connects to each server to fetch supported tools.\n3. **API Mapping**: Maps tool capabilities to standard OpenAI-compatible function schemas."
                },
                "Security_Sandboxing_for_MCP.md": {
                    "title": "Security Sandboxing for MCP",
                    "desc": "Details how tools run in sandboxed namespaces to prevent host escapes.",
                    "content": "To prevent malicious tool execution, MCP server processes are sandboxed.\n\n## Sandboxing Details\n- **Namespace Isolation**: Runs inside rootless container namespaces.\n- **SELinux confinement**: Confinded using strict SELinux policies.\n- **Filesystem Access**: Limited to designated sandbox directory spaces."
                }
            }
        },
        {
            "num": "14",
            "title": "Agent_to_Agent_Delegation_Protocols",
            "display": "Agent-to-Agent Delegation Protocols",
            "pages": {
                "JSON-RPC_Delegation_Spec.md": {
                    "title": "JSON-RPC Delegation Specification",
                    "desc": "Details the communications standard and payload schema for agent delegation.",
                    "content": "The Agent-to-Agent (A2A) protocol defines how agents delegate tasks to peer nodes.\n\n## Payload Example\n```json\n{\n  \"jsonrpc\": \"2.0\",\n  \"method\": \"delegate_task\",\n  \"params\": {\n    \"task\": \"Refactor install.sh line 42\",\n    \"specialist\": \"mios-opencode\"\n  },\n  \"id\": 1\n}\n```"
                },
                "OpenCode_Specialist_Handoffs.md": {
                    "title": "OpenCode Specialist Handoffs",
                    "desc": "Explains how the coding subagent (MiOS-OpenCode) takes over code modification.",
                    "content": "Coding tasks are fanned out to the `mios-opencode` coding specialist on port **8633**.\n\n## Execution Flow\n1. **Identify Task**: The orchestrator detects code modifications.\n2. **RPC Handoff**: Delegates the file editing task to the coding agent.\n3. **Execution**: The coding agent edits the target files.\n4. **Verification**: Runs tests in the sandboxed container and returns the results."
                },
                "Peer-to-Peer_Trust_Models.md": {
                    "title": "Peer-to-Peer Trust Models",
                    "desc": "Defines the capability-based security mapping across cooperative agents.",
                    "content": "A2A communications are secured through capability-based access controls.\n\n## Details\n- **Tokens**: Loopback calls are secured via dynamically rotated tokens.\n- **Verification**: Agents verify peer signatures before executing tasks.\n- **Audit Logs**: All delegated tasks are logged in the Postgres database."
                }
            }
        },
        {
            "num": "15",
            "title": "Computer_Use_and_Desktop_Control",
            "display": "Computer Use and Desktop Control",
            "pages": {
                "UI-TARS_Vision_Grounding.md": {
                    "title": "UI-TARS Vision Grounding",
                    "desc": "Details coordinate grounding on Wayland screens via vision models.",
                    "content": "Desktop automation uses UI-TARS models to translate visual displays into action coordinates.\n\n## Operations\n- **Screen Capture**: Grabs active Wayland framebuffer frames.\n- **Grounding**: Processes frames to return clickable target coordinates.\n- **Scaling**: Coordinates are scaled to match the physical resolution."
                },
                "Wayland_Input_Automation.md": {
                    "title": "Wayland Input Automation",
                    "desc": "Explains input emulation via the mios-pc-control command suite.",
                    "content": "Inputs are emulated on Wayland through secure input modules.\n\n## Flow\n- **Utility**: Uses the `mios-pc-control` command suite.\n- **Input Emulation**: Emulates mouse movement, click actions, and key events.\n- **Containment**: Actions are confined to approved display boundaries."
                },
                "AT-SPI_Accessibility_Tuning.md": {
                    "title": "AT-SPI Accessibility Tuning",
                    "desc": "Documents screen tree traversal for structural UI reasoning.",
                    "content": "AT-SPI screen trees allow agents to navigate UI hierarchies programmatically.\n\n## Methods\n- **Traversal**: Traverses active GUI trees to identify component properties.\n- **Fallback**: Serves as a semantic fallback when visual coordinate grounding is blocked.\n- **Speed**: Improves automation speed by returning direct text content without visual delays."
                }
            }
        },
        {
            "num": "16",
            "title": "Immutable_Root_and_Composefs_Sealing",
            "display": "Immutable Root and Composefs Sealing",
            "pages": {
                "Composefs_Read-Only_Mounts.md": {
                    "title": "Composefs Read-Only Mounts",
                    "desc": "Explains composefs structures and /usr partition read-only mounts.",
                    "content": "The system root `/usr` is mounted as a read-only composefs image to prevent run-time modification.\n\n## Features\n- **Integrity**: Block device files are read-only at the kernel level.\n- **Storage**: System files are stored inside content-addressed OCI indexes.\n- **Baking**: Composefs files are rendered during the OCI build."
                },
                "Fs-Verity_Signature_Verification.md": {
                    "title": "fs-verity Signature Verification",
                    "desc": "Covers system file validation against trusted cryptographic hashes.",
                    "content": "fs-verity protects binaries from offline tampering.\n\n## Operations\n- **Hashes**: Cryptographic signature blocks are generated for system files.\n- **Verification**: The kernel verifies hashes on open operations.\n- **Enforcement**: Any modification to signed binaries triggers block errors."
                },
                "Host_Upgrade_Reconciliation.md": {
                    "title": "Host Upgrade Reconciliation",
                    "desc": "Describes how upgrades resolve changes between base and current states.",
                    "content": "System updates are applied transactionally on booted hosts.\n\n## Process\n1. **Trigger**: Run `bootc upgrade` to fetch updated image layers.\n2. **Reconciliation**: System files under `/usr` are replaced by the new image, while host settings in `/etc` are merged.\n3. **Activation**: Cleans inactive files and switches to the new index on reboot."
                }
            }
        },
        {
            "num": "17",
            "title": "Defense_in_Depth_Hardening",
            "display": "Defense in Depth Hardening",
            "pages": {
                "CrowdSec_Intrusion_Prevention.md": {
                    "title": "CrowdSec Intrusion Prevention",
                    "desc": "Covers telemetry monitoring, IP bans, and custom local parsers.",
                    "content": "CrowdSec monitors local logs to detect threat activities.\n\n## Settings\n- **Logs**: Parses system logs, SSH, and container logs.\n- **Enforcement**: Blocks attackers using local firewalld rules.\n- **Sovereign Mode**: Runs offline without requiring cloud accounts."
                },
                "Fapolicyd_Application_Whitelisting.md": {
                    "title": "fapolicyd Application Whitelisting",
                    "desc": "Details binary execution blocking on unauthorized directories.",
                    "content": "fapolicyd blocks execution of untrusted scripts and binaries.\n\n## Rules\n- **Policy**: Denies execution of all files outside `/usr` and trusted directories.\n- **Paths**: Blocks executions inside `/tmp`, `/var`, or user home directories.\n- **Trust DB**: Managed in `/etc/fapolicyd/fapolicyd.trust`."
                },
                "USBGuard_Hardware_Control.md": {
                    "title": "USBGuard Hardware Control",
                    "desc": "Explains protection policies against rogue USB devices.",
                    "content": "USBGuard safeguards against hardware security exploits.\n\n## Details\n- **Policy**: Blocks unauthorized USB devices at connection.\n- **Rules**: Allows only authorized USB controllers and keyboards.\n- **Logs**: Hardware actions are logged in system journals."
                }
            }
        },
        {
            "num": "18",
            "title": "Supply_Chain_and_Image_Integrity",
            "display": "Supply Chain and Image Integrity",
            "pages": {
                "Sigstore_Verification_Policies.md": {
                    "title": "Sigstore Verification Policies",
                    "desc": "Defines policy-based verification of OCI signatures at pull time.",
                    "content": "Sigstore policies ensure only trusted images can be executed.\n\n## Enforcements\n- **Signature Check**: Validates signatures on container pulls.\n- **Policy Config**: Configured in [42-cosign-policy.sh](file:///C:/MiOS/automation/42-cosign-policy.sh).\n- **Rules**: Rejects unsigned images or those with invalid certs."
                },
                "Keyless_Cosign_Signing.md": {
                    "title": "Keyless Cosign Signing",
                    "desc": "Covers keyless image signing using OIDC identity providers.",
                    "content": "Keyless signing uses OIDC trust systems to sign OCI container images.\n\n## Features\n- **Keys**: No private keys are stored; signatures use ephemeral certificates.\n- **Logs**: Certs are logged in public Rekor transparency ledgers.\n- **CI**: Integrates with GitHub and local runner actions."
                },
                "Build_Time_Attestation.md": {
                    "title": "Build-Time Attestation",
                    "desc": "Explains the generation and verification of build SBOMs.",
                    "content": "Attestations verify the build origin and contents of OCI images.\n\n## Output\n- **SBOM**: Generates a CycloneDX SBOM during the OCI build.\n- **Attestation**: Baked directly into the image layers.\n- **Verification**: Validated during deployment checks."
                }
            }
        },
        {
            "num": "19",
            "title": "Hardware_Passthrough_and_VFIO_PCI",
            "display": "Hardware Passthrough and VFIO-PCI",
            "pages": {
                "GPU_Isolation_VFIO.md": {
                    "title": "GPU Isolation via VFIO",
                    "desc": "Details binding GPUs to vfio-pci on boot, bypassing host drivers.",
                    "content": "Isolating host graphics cards allows direct passthrough to virtual guests.\n\n## Methods\n- **Driver Bind**: Target GPUs are bound to the `vfio-pci` driver during early boot.\n- **Script**: Configured via [rtx4090-vfio-configurator.sh](file:///C:/MiOS/tools/rtx4090-vfio-configurator.sh).\n- **Verification**: Run `vfio-verify.sh` to check GPU binding status."
                },
                "Libvirt_PCI_Routing.md": {
                    "title": "Libvirt PCI Routing",
                    "desc": "Explains the XML schema mapping for physical GPU passthrough to guests.",
                    "content": "PCI routing maps isolated hardware into VM XML configurations.\n\n## XML Structure\n- **Device Node**: Defines target host PCI addresses.\n- **Guest Bus**: Maps physical hardware to virtual guest PCIe slots.\n- **Configuration**: Uses custom XML tags to bypass hypervisor detection."
                },
                "Guest_Drivers_Enforcement.md": {
                    "title": "Guest Drivers Enforcement",
                    "desc": "Documents driver setups in guest OS to avoid error codes.",
                    "content": "Guest systems require clean driver configurations to utilize passed hardware.\n\n## Tuning\n- **Hypervisor Gating**: Hides hypervisor signatures from Windows guests.\n- **Driver Setup**: Installs clean driver packages inside guests.\n- **Validation**: Checks driver device status after startup."
                }
            }
        },
        {
            "num": "20",
            "title": "Container_Device_Interface_Plumbing",
            "display": "Container Device Interface Plumbing",
            "pages": {
                "Nvidia_CDI_Automation.md": {
                    "title": "Nvidia CDI Automation",
                    "desc": "Covers CDI spec generation for CUDA applications running in rootless podman.",
                    "content": "NVIDIA CDI specs enable CUDA applications inside rootless containers.\n\n## Setup\n- **CDI Specs**: Generated automatically under `/var/run/cdi/`.\n- **Refresh**: Refreshed via [45-nvidia-cdi-refresh.sh](file:///C:/MiOS/automation/45-nvidia-cdi-refresh.sh).\n- **Quadlets**: Containers request graphics resources via `CDIDevices=` entries."
                },
                "AMD_ROCm_CDI_Mappings.md": {
                    "title": "AMD ROCm CDI Mappings",
                    "desc": "Explains ROCm/KFD driver mounts and container bindings.",
                    "content": "AMD CDI profiles map compute hardware to container environments.\n\n## Operations\n- **Mappings**: Maps `/dev/kfd` and AMD compute files.\n- **Settings**: Configured in [41-gpu-cdi-toolkits.sh](file:///C:/MiOS/automation/41-gpu-cdi-toolkits.sh).\n- **Verification**: Validates GPU compute access inside containers."
                },
                "Intel_GPU_CDI_Specs.md": {
                    "title": "Intel GPU CDI Specs",
                    "desc": "Documents Intel graphics acceleration CDI specs.",
                    "content": "Intel CDI maps integrated and discrete Intel graphics processors.\n\n## Details\n- **Specs**: Exposes Intel integrated and discrete graphics processors.\n- **Conventions**: Exposes GPU nodes inside container layers.\n- **Confinement**: Isolates GPU access boundaries to specific containers."
                }
            }
        },
        {
            "num": "21",
            "title": "Looking_Glass_B7_and_KVMFR",
            "display": "Looking Glass B7 and KVMFR",
            "pages": {
                "KVMFR_Kernel_Module_Bake.md": {
                    "title": "KVMFR Kernel Module Bake",
                    "desc": "Explains building and signing KVMFR module from source.",
                    "content": "Looking Glass requires the KVM Framebuffer (KVMFR) driver to share screen memory.\n\n## Build\n- **Compilation**: Compiled from source during [52-bake-kvmfr.sh](file:///C:/MiOS/automation/52-bake-kvmfr.sh).\n- **Signing**: Signed automatically with the host's MOK.\n- **Verification**: Loaded on boot to expose the virtual memory channel."
                },
                "Shared_Memory_Framebuffer.md": {
                    "title": "Shared Memory Framebuffer",
                    "desc": "Details allocations under /dev/shm for low-latency memory copy.",
                    "content": "Looking Glass uses host shared memory to pass frames.\n\n## Setup\n- **Allocation**: Configured via tmpfiles configuration templates.\n- **Buffer**: Creates `/dev/shm/looking-glass` with correct permissions.\n- **Tuning**: Size boundaries are calculated based on guest resolution."
                },
                "Looking_Glass_Client_Setup.md": {
                    "title": "Looking Glass Client Setup",
                    "desc": "Documents Wayland client build and input mappings.",
                    "content": "The host client renders guest framebuffers on the Wayland display.\n\n## Execution\n- **Client**: Shipped inside [53-bake-lookingglass-client.sh](file:///C:/MiOS/automation/53-bake-lookingglass-client.sh).\n- **Command**: Launches the Wayland-native client to display virtual displays.\n- **Tuning**: Configured for mouse and audio integration."
                }
            }
        },
        {
            "num": "22",
            "title": "CPU_Topology_and_Performance_Pinning",
            "display": "CPU Topology and Performance Pinning",
            "pages": {
                "Thread_Allocation_Strategies.md": {
                    "title": "Thread Allocation Strategies",
                    "desc": "Maps CPU pinning allocations for isolated workloads.",
                    "content": "CPU pinning partitions processing cores between virtual machines and the host.\n\n## Policies\n- **P-cores**: Assigned to virtual guest tasks.\n- **E-cores**: Bound to host tasks and background AI lanes.\n- **Automation**: Executed dynamically by [vm-cpu-pin-manager.sh](file:///C:/MiOS/tools/vm-cpu-pin-manager.sh)."
                },
                "NUMA_Node_Awareness.md": {
                    "title": "NUMA Node Awareness",
                    "desc": "Details memory node alignment for reduced guest latencies.",
                    "content": "NUMA alignment optimizes memory access times by keeping tasks close to memory nodes.\n\n## Tuning\n- **Alignment**: Virtual CPUs are pinned to matching physical RAM nodes.\n- **Benefits**: Reduces cross-node latency and increases frame rates.\n- **Controls**: Configured inside libvirt templates."
                },
                "Low-Latency_VM_Tuning.md": {
                    "title": "Low-Latency VM Tuning",
                    "desc": "Covers scheduling priority and emulatorpin adjustments.",
                    "content": "Tuning settings reduce virtualization scheduling latencies.\n\n## Settings\n- **Scheduling**: Prioritizes VM processes using real-time schedulers.\n- **Emulator Pinning**: Isolates emulator tasks from primary worker threads.\n- **Configurations**: Settings are managed in VM XML configurations."
                }
            }
        },
        {
            "num": "23",
            "title": "Single_Node_Kubernetes_Expansion",
            "display": "Single-Node Kubernetes Expansion",
            "pages": {
                "K3s_Workstation_Coexistence.md": {
                    "title": "K3s Workstation Coexistence",
                    "desc": "Covers resource boundaries between GNOME and K3s services.",
                    "content": "Integrating single-node K3s allows container orchestration without affecting GNOME resources.\n\n## Operations\n- **Isolation**: Runs K3s inside isolated runtime namespaces.\n- **Gating**: Starts only when active profiles have cluster features enabled.\n- **Limits**: Implements resource bounds to protect desktop tasks."
                },
                "Local_Ingress_and_Routing.md": {
                    "title": "Local Ingress and Routing",
                    "desc": "Details ingress routing rules in single-node clusters.",
                    "content": "Ingress configs manage external routing into local cluster services.\n\n## Setup\n- **Ingress**: Uses Traefik on port 6443.\n- **Routing**: Routes local domains to active pods.\n- **Ports**: Exposes services to the host network interface."
                },
                "K3s_SELinux_Policy_Enforcement.md": {
                    "title": "K3s SELinux Policy Enforcement",
                    "desc": "Explains custom security policies allowing cluster containers.",
                    "content": "Custom SELinux rules protect the host from cluster workloads.\n\n## Policies\n- **Rules**: Applied by [19-k3s-selinux.sh](file:///C:/MiOS/automation/19-k3s-selinux.sh).\n- **Bounds**: Blocks cluster tasks from modifying read-only system files.\n- **Validation**: Enforces SELinux policies at runtime."
                }
            }
        },
        {
            "num": "24",
            "title": "CephFS_Local_Storage_Cluster",
            "display": "CephFS Local Storage Cluster",
            "pages": {
                "Containerized_Ceph_Deployments.md": {
                    "title": "Containerized Ceph Deployments",
                    "desc": "Covers Ceph Quadlet definitions and storage config.",
                    "content": "Ceph storage daemons are orchestrated inside unprivileged containers.\n\n## Orchestration\n- **Service**: Managed via `mios-ceph.service` Quadlet.\n- **Containers**: Includes Ceph monitors and OSD engines.\n- **Mounts**: Exposes storage block paths."
                },
                "Storage_Daemon_Permissions.md": {
                    "title": "Storage Daemon Permissions",
                    "desc": "Details block device access exemptions.",
                    "content": "Ceph requires block access permissions, making it one of the few root exemptions.\n\n## Details\n- **Exceptions**: Documented inside systemd templates.\n- **Permissions**: Runs with permissions required to interact with hardware blocks.\n- **Hardening**: Limits network execution boundaries to loopback interfaces."
                },
                "XDG_Directory_Integrations.md": {
                    "title": "XDG Directory Integrations",
                    "desc": "Maps user directories onto CephFS mounts for auto-backups.",
                    "content": "Desktop directories are synced to CephFS mounts for automatic backups.\n\n## Setup\n- **Integrations**: Mounts local directories (e.g. `~/Documents`) directly on CephFS.\n- **Backups**: Saves changes across the local storage network.\n- **Config**: Settings are stored inside XDG configuration files."
                }
            }
        },
        {
            "num": "25",
            "title": "Local_Search_Engine_and_SearXNG",
            "display": "Local Search Engine and SearXNG",
            "pages": {
                "SearXNG_Sovereign_Search.md": {
                    "title": "SearXNG Sovereign Search",
                    "desc": "Explains local container setup and engines configuration.",
                    "content": "Sovereign search services are provided locally by containerized SearXNG.\n\n## Setup\n- **Endpoint**: Runs on port 8888.\n- **Security**: Disables logging and upstream search tracking.\n- **Performance**: Returns results offline or via private search."
                },
                "Agent_Search_API_Plumbing.md": {
                    "title": "Agent Search API Plumbing",
                    "desc": "Covers query routing from search tools to SearXNG.",
                    "content": "Agents execute search queries using SearXNG API endpoints.\n\n## Pipeline\n- **API**: Queries local endpoints on port 8888.\n- **Authentication**: secured via loopback trust.\n- **Integration**: Backs the agent's web search tools."
                },
                "Web_Scraping_and_Ingest.md": {
                    "title": "Web Scraping and Ingest",
                    "desc": "Details parsing HTML results into Markdown for LLM ingestion.",
                    "content": "Parsed search results are transformed into Markdown for inference ingestion.\n\n## Details\n- **Scraper**: Grabs target pages from search outputs.\n- **Parser**: Formats raw HTML into clean markdown.\n- **Gating**: Blocks scripts to prevent cross-site execution."
                }
            }
        },
        {
            "num": "26",
            "title": "Unified_Knowledge_Base_Ingestion",
            "display": "Unified Knowledge Base Ingestion",
            "pages": {
                "Document_Parsing_and_Embedding.md": {
                    "title": "Document Parsing and Embedding",
                    "desc": "Explains document indexing and embedding tasks.",
                    "content": "Ingested documents are parsed and vectorized to build the knowledge base.\n\n## Flow\n- **Parser**: Converts PDFs, text, and code files.\n- **Embedding**: Generates vectors using the light embedding lane.\n- **Utility**: Run [generate-unified-knowledge.py](file:///C:/MiOS/tools/generate-unified-knowledge.py)."
                },
                "Ingest_Pipeline_Schema.md": {
                    "title": "Ingest Pipeline Schema",
                    "desc": "Maps ingestion pipeline and database tables layout.",
                    "content": "The ingest pipeline maps content to Postgres database tables.\n\n## Structure\n- **Tables**: Mapped in `usr/share/mios/postgres/schema-init.sql`.\n- **Columns**: Stores content, source reference, and vectors.\n- **Constraints**: Enforces unique sources to prevent duplicate index entries."
                },
                "Semantic_Indexing_Maintenance.md": {
                    "title": "Semantic Indexing Maintenance",
                    "desc": "Covers re-indexing databases and recall optimizations.",
                    "content": "Maintaining vector indexes keeps similarity query times fast.\n\n## Operations\n- **Indexing**: Uses HNSW graphs for semantic retrieval.\n- **Pruning**: Consolidates duplicate and stale data.\n- **Reindexing**: Rebuilds database indexes after import tasks."
                }
            }
        },
        {
            "num": "27",
            "title": "Shell_Configuration_and_Environment_Cascade",
            "display": "Shell Configuration and Environment Cascade",
            "pages": {
                "Env_Defaults_and_Precedence.md": {
                    "title": "Environment Defaults and Precedence",
                    "desc": "Maps configuration overrides bubbling up to login shells.",
                    "content": "Environment variables are resolved through a multi-layer cascade.\n\n## Cascade\n1. `~/.config/mios/env` (highest precedence)\n2. `/etc/mios/install.env`\n3. `/etc/mios/env.d/*.env`\n4. `/usr/share/mios/env.defaults` (lowest precedence)\n\nUse `mios-env --explain` to trace key resolution layers."
                },
                "Oh_My_Posh_Prompt_Theming.md": {
                    "title": "Oh My Posh Prompt Theming",
                    "desc": "Covers theme configuration and prompt status icons.",
                    "content": "The system shell uses Oh My Posh themes to show system status.\n\n## Themes\n- **Prompt**: Configured in [38-oh-my-posh.sh](file:///C:/MiOS/automation/38-oh-my-posh.sh).\n- **Icons**: Displays git status, active model, and CPU usage.\n- **Themes File**: Stored inside `/usr/share/mios/shell/`."
                },
                "User_Locale_Standardization.md": {
                    "title": "User Locale Standardization",
                    "desc": "Documents timezone and UTF-8 locale staging setups.",
                    "content": "Standard locale and time formats are staging targets during deployment.\n\n## Settings\n- **Locale**: Sets UTF-8 encoding.\n- **Timezone**: Set in [30-locale-theme.sh](file:///C:/MiOS/automation/30-locale-theme.sh).\n- **Customizations**: Customized in `mios.toml`."
                }
            }
        },
        {
            "num": "28",
            "title": "Dynamic_Network_and_Firewall_Management",
            "display": "Dynamic Network and Firewall Management",
            "pages": {
                "Firewalld_Rule_Generation.md": {
                    "title": "Firewalld Rule Generation",
                    "desc": "Covers managing port firewalls via firewalld command hooks.",
                    "content": "Firewall rules isolate host services and control outbound networks.\n\n## Rules\n- **Tool**: Configured via firewalld policies.\n- **Gating**: Outbound requests are limited by [generate-egress-firewall.py](file:///C:/MiOS/tools/generate-egress-firewall.py).\n- **Logs**: Blocked network events are logged in system journals."
                },
                "Dynamic_Port_Allocation.md": {
                    "title": "Dynamic Port Allocation",
                    "desc": "Explains how ports are dynamically resolved and bound.",
                    "content": "Ports are allocated dynamically during build and boot phases.\n\n## Allocation\n- **Script**: Handled by [16-render-ports.sh](file:///C:/MiOS/automation/16-render-ports.sh).\n- **Mappings**: Maps host interfaces to container ports.\n- **Validation**: Enforces unique allocations to prevent startup collisions."
                },
                "VPN_and_Tailscale_Routing.md": {
                    "title": "VPN and Tailscale Routing",
                    "desc": "Documents Tailscale integration with system firewall rules.",
                    "content": "VPN integrations secure communication across network devices.\n\n## Settings\n- **Interface**: Uses Tailscale virtual adapters.\n- **Routing**: Resolves local addresses through private tunnels.\n- **Firewall**: Integrates VPN paths with local rules."
                }
            }
        },
        {
            "num": "29",
            "title": "Web_Management_and_Configurator_UI",
            "display": "Web Management and Configurator UI",
            "pages": {
                "Mios_HTML_TOML_Editor.md": {
                    "title": "MiOS HTML TOML Editor",
                    "desc": "Covers configuration editing via the static index HTML form.",
                    "content": "The configuration dashboard allows graphical form editing of system parameters.\n\n## Details\n- **Dashboard**: Shipped in [mios.html](file:///C:/MiOS/usr/share/mios/configurator/mios.html).\n- **Precedence**: Writes updates back to user and host files.\n- **Sync**: Triggers `mios-sync-env` to apply updates."
                },
                "Host-to-Container_Portal.md": {
                    "title": "Host-to-Container Portal",
                    "desc": "Details how the UI panel maps active container metrics.",
                    "content": "The web panel monitors resource usages and active containers.\n\n## Metrics\n- **Resource Monitoring**: Tracks system usage (VRAM, CPU, RAM).\n- **Service Management**: Allows quick container restarts.\n- **Host View**: Integrates with Cockpit metrics interfaces."
                },
                "Settings_Sync_Mechanisms.md": {
                    "title": "Settings Sync Mechanisms",
                    "desc": "Explains TOML serialization and service reload hooks.",
                    "content": "Config settings are synchronized back to target system files on save.\n\n## Mechanisms\n- **Sync script**: Syncing handled by Python and PowerShell tools.\n- **Update Checks**: Validates configuration integrity before reboot.\n- **State Merging**: Merges updates without breaking custom changes."
                }
            }
        },
        {
            "num": "30",
            "title": "System_Auditing_and_Drift_Verification",
            "display": "System Auditing and Drift Verification",
            "pages": {
                "Automated_Postcheck_Suite.md": {
                    "title": "Automated Postcheck Suite",
                    "desc": "Documents checks run by 99-postcheck.sh at build-time.",
                    "content": "The postcheck suite validates system state compliance before image builds finish.\n\n## Checks\n- **Script**: Configured in [99-postcheck.sh](file:///C:/MiOS/automation/99-postcheck.sh).\n- **Tests**: Validates container layers, CDI specs, and FHS structures.\n- **Gating**: Failing checks block OCI image output."
                },
                "Hardcode_Lint_Rules.md": {
                    "title": "Hardcode Lint Rules",
                    "desc": "Explains build constraints blocking hardcoded URLs or ports.",
                    "content": "Build rules prohibit hardcoded keys, URLs, and settings.\n\n## Rules\n- **Linter**: Executed by [mios-hardcode-lint](file:///C:/MiOS/usr/libexec/mios/mios-hardcode-lint) inside automation scripts.\n- **Violations**: Hardcoded ports, IPs, or vendor links trigger build failures.\n- **Bypasses**: Requires variables to resolve via config cascades."
                },
                "Security_Policy_Compliance.md": {
                    "title": "Security Policy Compliance",
                    "desc": "Maps validation against our target zero-trust hardening profile.",
                    "content": "Verifies that active system configurations meet zero-trust security profiles.\n\n## Auditing\n- **Checks**: Scans permissions, SELinux states, and whitelists.\n- **Output**: Reports are logged under `/usr/share/doc/mios/audits/`.\n- **Validation**: Enforces integrity checks on core files."
                }
            }
        },
        {
            "num": "31",
            "title": "Desktop_Applications_and_Flatpaks",
            "display": "Desktop Applications and Flatpaks",
            "pages": {
                "Declarative_Flatpak_Bake.md": {
                    "title": "Declarative Flatpak Bake",
                    "desc": "Covers pre-downloading and staging Flatpaks inside the image.",
                    "content": "Flatpaks are defined in system configs and pre-downloaded to reduce setup times.\n\n## Setup\n- **Declarations**: Listed in `mios.toml` under `[flatpaks]`.\n- **Bake Script**: Configured in [40-flatpak-bake.sh](file:///C:/MiOS/automation/40-flatpak-bake.sh).\n- **Details**: Pre-downloads application runtimes into the image storage."
                },
                "Application_Permissions_Gating.md": {
                    "title": "Application Permissions Gating",
                    "desc": "Explains locking Flatpak permissions using Flatseal overrides.",
                    "content": "Flatpak permissions are confined using Flatseal profiles.\n\n## Hardening\n- **Confinement**: Restricts access to host files, network, and sockets.\n- **Exceptions**: Allows necessary GPU access paths.\n- **Overrides**: Controlled via custom scripts on first boot."
                },
                "Desktop_Shortcuts_Sync.md": {
                    "title": "Desktop Shortcuts Sync",
                    "desc": "Details sync hooks registering menus and MIME shortcuts.",
                    "content": "Syncs application icons and shortcuts to the GNOME desktop launcher menu.\n\n## Flow\n- **Script**: Managed via [refresh-flatpak-shortcuts.ps1](file:///C:/MiOS/tools/refresh-flatpak-shortcuts.ps1).\n- **Sync**: Maps application desktop files to target directory folders.\n- **Updates**: Refreshed dynamically on configuration changes."
                }
            }
        },
        {
            "num": "32",
            "title": "Swarm_Worker_Clusters",
            "display": "Swarm Worker Clusters",
            "pages": {
                "Swarm_Node_Provisioning.md": {
                    "title": "Swarm Node Provisioning",
                    "desc": "Covers dynamic worker provisioning via Quadlet templates.",
                    "content": "Adding swarm worker instances scales execution capacities dynamically.\n\n## Steps\n- **Template**: Uses `mios-llm-worker@.service` templates.\n- **Target**: Spawns single-model processes on worker endpoints.\n- **Discovery**: Automatically joins active host networks."
                },
                "Dynamic_Fanout_Orchestration.md": {
                    "title": "Dynamic Fanout Orchestration",
                    "desc": "Details task partitioning and worker aggregation pipelines.",
                    "content": "The system splits complex queries and routes them to parallel workers.\n\n## Pipeline\n- **Fanout**: Tasks are split into independent components.\n- **Routing**: Dynamic routing to active worker slots.\n- **Synthesis**: Aggregates output files into a cohesive result."
                },
                "Load_Balancing_Lanes.md": {
                    "title": "Load Balancing Lanes",
                    "desc": "Explains scheduling and routing algorithms across worker processes.",
                    "content": "Balances parallel model tasks based on health status metrics.\n\n## Policies\n- **Checking**: Probes worker load levels and memory limits.\n- **Balancing**: Directs queries to the fastest available worker.\n- **Failover**: Handles worker recovery on model load failures."
                }
            }
        },
        {
            "num": "33",
            "title": "Sandboxed_Execution_and_Coder_Sandbox",
            "display": "Sandboxed Execution and Coder Sandbox",
            "pages": {
                "Coder_Sandbox_Quadlet.md": {
                    "title": "Coder Sandbox Quadlet",
                    "desc": "Covers configuring unprivileged containers for code interpretation.",
                    "content": "Confines untrusted coding tasks within rootless containers.\n\n## Settings\n- **Service**: Mapped in `mios-coderun-sandbox@` Quadlet.\n- **User**: Runs with unprivileged user namespace limits.\n- **Bridges**: Disables host networks to prevent outbound leaks."
                },
                "SELinux_Sandbox_Policies.md": {
                    "title": "SELinux Sandbox Policies",
                    "desc": "Details how policies restrict container sandbox processes.",
                    "content": "Custom SELinux profiles prevent sandbox escape actions.\n\n## Policies\n- **Rules**: Applied on first boot configuration.\n- **Bounds**: Blocks container escape vulnerabilities.\n- **Verification**: Logs violations inside audit files."
                },
                "Safe_Code_Interpretation.md": {
                    "title": "Safe Code Interpretation",
                    "desc": "Explains output validation and script execution controls.",
                    "content": "Validates code actions and sanitizes script outputs securely.\n\n## Methods\n- **Sanitizer**: Filters execution outputs to remove credentials.\n- **Validation**: Enforces strict timeout limits on executions.\n- **Logs**: Processes are logged in system containers."
                }
            }
        },
        {
            "num": "34",
            "title": "Identity_Management_and_FreeIPA",
            "display": "Identity Management and FreeIPA",
            "pages": {
                "FreeIPA_Client_Configuration.md": {
                    "title": "FreeIPA Client Configuration",
                    "desc": "Covers configuring FreeIPA libraries inside Fedora overlay.",
                    "content": "Resolves host client authentication with central FreeIPA domains.\n\n## Details\n- **Script**: Staged via [22-freeipa-client.sh](file:///C:/MiOS/automation/22-freeipa-client.sh).\n- **Client**: Integrates SSSD services inside Fedora core layers.\n- **Policies**: Handles identity resolving and domain settings."
                },
                "Enforced_User_Sysusers.md": {
                    "title": "Enforced User Sysusers",
                    "desc": "Details staging user and system accounts prior to install.",
                    "content": "Sysusers definitions pre-stage user and system accounts prior to install.\n\n## Rules\n- **Templates**: Stored under `/usr/lib/sysusers.d/*.conf`.\n- **System Accounts**: Configures IDs for database and daemon tasks.\n- **Integrity**: Prevents changes during deployment overlays."
                },
                "Domain_Join_Automation.md": {
                    "title": "Domain Join Automation",
                    "desc": "Explains automatic domain enrollment on first boot.",
                    "content": "Automates joining host systems to corporate domains.\n\n## Flow\n- **Execution**: Connects to IPA servers using OIDC tokens.\n- **Certificates**: Generates secure host certificates on setup.\n- **Renewals**: Handles automatic credential ticket updates."
                }
            }
        },
        {
            "num": "35",
            "title": "System_Monitoring_and_Telemetry",
            "display": "System Monitoring and Telemetry",
            "pages": {
                "Prometheus_Exporter_Setup.md": {
                    "title": "Prometheus Exporter Setup",
                    "desc": "Covers collecting CPU, RAM, and GPU stats via node-exporters.",
                    "content": "Exporters collect system metrics from physical hardware.\n\n## Settings\n- **Exporters**: System and GPU metrics collection daemons.\n- **Ports**: Exposes metrics on localhost ports.\n- **Frequency**: Configured to scrape resources at regular intervals."
                },
                "AI_Gateway_Telemetry.md": {
                    "title": "AI Gateway Telemetry",
                    "desc": "Details tracking query duration, tokens, and routing lanes.",
                    "content": "Logs query times, token counts, and routing states.\n\n## Diagnostics\n- **Recording**: Mapped inside the Postgres log tables.\n- **Metrics**: Logs tokens per second and model swap speeds.\n- **Anonymization**: Filters queries to protect credentials."
                },
                "Grafana_Dashboard_Profiles.md": {
                    "title": "Grafana_Dashboard_Profiles",
                    "desc": "Maps visual dashboards for monitoring resource use.",
                    "content": "Configures dashboards to monitor system and AI workloads.\n\n## Details\n- **Widgets**: Mapped inside cockpit or local dashboards.\n- **Alerts**: Triggers notifications on VRAM threshold limits.\n- **Tuning**: Configured in system monitoring profiles."
                }
            }
        },
        {
            "num": "36",
            "title": "Greenboot_Health_Check_and_Recovery",
            "display": "Greenboot Health Check and Recovery",
            "pages": {
                "Automatic_OS_Health_Checks.md": {
                    "title": "Automatic OS Health Checks",
                    "desc": "Covers greenboot scripts verifying service states.",
                    "content": "Greenboot verifies service status after system upgrades.\n\n## Flow\n- **Script**: Checked in [46-greenboot.sh](file:///C:/MiOS/automation/46-greenboot.sh).\n- **Actions**: Checks core components (systemd, drivers, AI gateways).\n- **Timing**: Enforces timeout limits for checks."
                },
                "Rollback_Trigger_Policies.md": {
                    "title": "Rollback Trigger Policies",
                    "desc": "Explains atomic image swap checks triggered on boot failures.",
                    "content": "Rollback triggers swap root partition indexes back to working slots on boot failures.\n\n## Policies\n- **Threshold**: Triggers rollback after 3 failed boot attempts.\n- **Actions**: Atomic switch of boot partition variables.\n- **Logs**: Records rollback events inside bootstrap logs."
                },
                "Recovery_State_Scripts.md": {
                    "title": "Recovery State Scripts",
                    "desc": "Documents dynamic cleanup tasks executed during recoveries.",
                    "content": "Automated scripts attempt self-repair tasks on service start failures.\n\n## Settings\n- **Scripts**: Mapped in `/etc/greenboot/red.d/`.\n- **Actions**: Restarts containers and purges stale caches.\n- **Controls**: Logs status diagnostics for operator review."
                }
            }
        },
        {
            "num": "37",
            "title": "GPU_Capability_Detection_and_Passthrough_Shims",
            "display": "GPU Capability Detection and Passthrough Shims",
            "pages": {
                "CDI_Refresh_Mechanisms.md": {
                    "title": "CDI Refresh Mechanisms",
                    "desc": "Covers spec updates triggered when hardware states change.",
                    "content": "Refreshes CDI specs automatically when graphics adapters change.\n\n## Setup\n- **Checks**: Scans physical devices on boot using [34-gpu-detect.sh](file:///C:/MiOS/automation/34-gpu-detect.sh).\n- **Utility**: Invokes [45-nvidia-cdi-refresh.sh](file:///C:/MiOS/automation/45-nvidia-cdi-refresh.sh).\n- **Execution**: Updates container CDI files in `/var/run/cdi/`."
                },
                "Runtime_GPU_Gating.md": {
                    "title": "Runtime GPU Gating",
                    "desc": "Details device locking and lockouts during state transitions.",
                    "content": "Gating mechanisms control GPU resource allocations between containers and hypervisors.\n\n## Gating\n- **Shim**: Implemented via [35-gpu-pv-shim.sh](file:///C:/MiOS/automation/35-gpu-pv-shim.sh).\n- **Locking**: Locks device files to prevent parallel utilization conflicts.\n- **Policies**: Shunts GPU compute priorities to virtual guests."
                },
                "Dynamic_Driver_Loading.md": {
                    "title": "Dynamic Driver Loading",
                    "desc": "Explains dynamic module load decisions during bootstrap.",
                    "content": "Loads host display drivers based on profile settings.\n\n## Flow\n- **Checks**: Verifies system variables at boot.\n- **Action**: Loads target GPU drivers or binds cards to VFIO.\n- **Integrity**: Enforces signed drivers validation."
                }
            }
        },
        {
            "num": "38",
            "title": "Remote_Desktop_and_GNOME_GRD",
            "display": "Remote Desktop and GNOME GRD",
            "pages": {
                "Remote_Wayland_Sessions.md": {
                    "title": "Remote Wayland Sessions",
                    "desc": "Covers running GNOME inside headless Wayland sessions.",
                    "content": "Enables GUI remote management when running headless.\n\n## Details\n- **Script**: Configured via [26-gnome-remote-desktop.sh](file:///C:/MiOS/automation/26-gnome-remote-desktop.sh).\n- **Engine**: Integrates with GNOME Remote Desktop.\n- **Bridges**: Exposes Wayland displays on ports."
                },
                "Secure_RDP_Authentication.md": {
                    "title": "Secure RDP Authentication",
                    "desc": "Details TLS encryption and user credential checks.",
                    "content": "Secures remote display sessions using TLS certificates.\n\n## Setup\n- **Credentials**: Configures certs and local PAM hooks.\n- **Rules**: Restricts RDP connection requests to authorized IP slots.\n- **Auditing**: Session access is logged in the system records."
                },
                "Headless_Desktop_Toggle.md": {
                    "title": "Headless Desktop Toggle",
                    "desc": "Documents setting up virtual display outputs on headless hosts.",
                    "content": "Allows toggling display signals for virtual desktop environments.\n\n## Actions\n- **Toggle tool**: Executed via [mios-toggle-headless](file:///C:/MiOS/automation/mios-toggle-headless).\n- **Resolution**: Sets virtual display limits.\n- **Tuning**: Optimizes screen frame buffers to save VRAM."
                }
            }
        },
        {
            "num": "39",
            "title": "Host_Guest_Shared_Filesystems",
            "display": "Host-Guest Shared Filesystems",
            "pages": {
                "Virtiofs_Performance_Tuning.md": {
                    "title": "Virtiofs Performance Tuning",
                    "desc": "Covers high-speed file sharing cache configurations.",
                    "content": "Tuning virtiofs settings allows high-speed file sharing with guests.\n\n## Setup\n- **Mounts**: Exposes host folders using XML templates.\n- **Caching**: Configures high-performance host caches.\n- **Tuning**: Optimizes thread limits inside libvirt."
                },
                "Shared_Directories_Overlay.md": {
                    "title": "Shared Directories Overlay",
                    "desc": "Details exposing system paths inside guest virtual overlays.",
                    "content": "Overlay folders expose host configurations to guest runtimes.\n\n## Flow\n- **Overlay**: Exposes `/usr/share/` and guest dotfiles.\n- **Sandboxing**: Restricts write access inside guests.\n- **Conventions**: Maps locations securely inside hypervisor targets."
                },
                "Permission_Translation_Models.md": {
                    "title": "Permission Translation Models",
                    "desc": "Explains UID/GID mappings translation across OS barriers.",
                    "content": "Maps user IDs across host and guest environments.\n\n## Details\n- **Mapping**: Translates guest UIDs to matching host accounts.\n- **Security**: Prevents guest root tasks from escaping permissions.\n- **Verification**: Validates folder access credentials."
                }
            }
        },
        {
            "num": "40",
            "title": "System_Log_Aggregation",
            "display": "System Log Aggregation",
            "pages": {
                "Journald_Sync_to_Bootstrap.md": {
                    "title": "Journald Sync to Bootstrap",
                    "desc": "Covers sync hooks pulling logs into bootstrap sectors.",
                    "content": "Copies system journals to bootstrap drives for offline diagnostics.\n\n## Flow\n- **Script**: Executed by [log-to-bootstrap.sh](file:///C:/MiOS/tools/log-to-bootstrap.sh).\n- **Logs**: Copies core files, boot output, and services records.\n- **Targets**: Mapped directly onto host storage sectors."
                },
                "Log-Copy_Daemon_Configuration.md": {
                    "title": "Log-Copy Daemon Configuration",
                    "desc": "Details systemd service parameters for log copy tasks.",
                    "content": "Configures background daemons to aggregate container logs.\n\n## Setup\n- **Unit**: Configured in [50-enable-log-copy-service.sh](file:///C:/MiOS/automation/50-enable-log-copy-service.sh).\n- **Service**: Runs system log synchronization helpers.\n- **Storage**: Mapped inside `/var/log/mios/`."
                },
                "Diagnostic_Log_Bundles.md": {
                    "title": "Diagnostic Log Bundles",
                    "desc": "Explains compiling system diagnostics into single archives.",
                    "content": "Assembles diagnostic packages to simplify system troubleshooting.\n\n## Details\n- **Bundler**: Bundles active logs, specs, and status variables.\n- **Output**: Generates compressed archives.\n- **Triggers**: Executed on system health checks failures."
                }
            }
        },
        {
            "num": "41",
            "title": "Machine_Owner_Key_Management",
            "display": "Machine Owner Key Management",
            "pages": {
                "Private_Key_Generation.md": {
                    "title": "Private Key Generation",
                    "desc": "Covers generating secure build-keys inside automation.",
                    "content": "Generates secure signature keys for custom kernel drivers.\n\n## Details\n- **Keys**: Cryptographic keys are generated inside automation layers.\n- **Script**: Managed via [generate-mok-key.sh](file:///C:/MiOS/automation/generate-mok-key.sh).\n- **Storage**: Keys are isolated in root-only directories."
                },
                "Secure_Boot_Enrollment_Flow.md": {
                    "title": "Secure Boot Enrollment Flow",
                    "desc": "Details UEFI enrollment prompts triggered on boots.",
                    "content": "Enrolls Machine Owner Keys (MOK) inside host firmware.\n\n## Flow\n1. **Trigger**: Run [enroll-mok.sh](file:///C:/MiOS/automation/enroll-mok.sh).\n2. **Registration**: Imports certificates to system structures.\n3. **Enrollment**: Prompts enrollment on subsequent reboot.\n4. **Validation**: Verified by Secure Boot on driver loading."
                },
                "Automatic_Module_Signing.md": {
                    "title": "Automatic Module Signing",
                    "desc": "Explains dynamic module signatures added on kernel upgrades.",
                    "content": "Signs compiled driver binaries automatically during kernel upgrades.\n\n## Processes\n- **Compilation**: Triggers driver compile actions on kernel changes.\n- **Signing**: Signs binaries using registered MOK keys.\n- **Verification**: Confirms signed driver loading logs."
                }
            }
        },
        {
            "num": "42",
            "title": "Kernel_Upgrade_and_Build_Pipelines",
            "display": "Kernel Upgrade and Build Pipelines",
            "pages": {
                "Stable_LTS_Kernel_Updates.md": {
                    "title": "Stable LTS Kernel Updates",
                    "desc": "Covers base image upgrades and validation procedures.",
                    "content": "Upgrading host kernels relies on stable LTS packages.\n\n## Guidelines\n- **Base image**: Kernel packages inherit from uCore base structures.\n- **Updates**: Applied transactionally using system image updates.\n- **Verification**: Run preflight checks before updating core kernels."
                },
                "Akmod_Compilation_Guards.md": {
                    "title": "Akmod Compilation Guards",
                    "desc": "Details compilation gating rules verifying module states.",
                    "content": "Guards compilation tasks to prevent boot failures from driver updates.\n\n## Details\n- **Guards**: Enabled via [36-akmod-guards.sh](file:///C:/MiOS/automation/36-akmod-guards.sh).\n- **Validation**: Enforces driver binary compilation checks.\n- **Actions**: Restores previous functional configurations on failure."
                },
                "BIB_Disk_Image_Generation.md": {
                    "title": "BIB Disk Image Generation",
                    "desc": "Explains bootc-image-builder actions transforming OCI tags.",
                    "content": "Compiling images relies on bootc-image-builder (BIB) containers.\n\n## Runtimes\n- **BIB target**: Executed inside `just vhdx` / `just raw` targets.\n- **Pipeline**: Converts OCI image outputs to UEFI disk configurations.\n- **Output**: Writes boot images directly to host directories."
                }
            }
        },
        {
            "num": "43",
            "title": "Local_Registry_and_OCI_Distribution",
            "display": "Local Registry and OCI Distribution",
            "pages": {
                "Private_Registry_Quadlets.md": {
                    "title": "Private Registry Quadlets",
                    "desc": "Covers OCI distribution containers used in replication loop.",
                    "content": "Sets up private registry containers for local image hosting.\n\n## Settings\n- **Service**: Managed via registry Quadlet files.\n- **Ports**: Exposes local registry endpoints on loopbacks.\n- **Security**: Restricts pull requests to local adapters."
                },
                "Image_Caching_Strategies.md": {
                    "title": "Image Caching Strategies",
                    "desc": "Details cache boundaries speeding up successive image builds.",
                    "content": "Caching static container layers reduces OCI build times.\n\n## Setup\n- **Storage**: Caches OCI layers inside local disks.\n- **Mechanisms**: Re-uses unchanged base steps.\n- **Tuning**: Configured in build scripts."
                },
                "Deployed_Ref_Updates.md": {
                    "title": "Deployed Ref Updates",
                    "desc": "Explains pulling local registries and switching host roots.",
                    "content": "Upgrades local hosts using updated image references.\n\n## Actions\n- **Update**: executes `bootc switch` pointing to local registries.\n- **Reconciliation**: Applies structural merges to configurations.\n- **Verification**: Checks image metadata on next boot."
                }
            }
        },
        {
            "num": "44",
            "title": "Host_Package_Overrides_and_DNF5",
            "display": "Host Package Overrides and DNF5",
            "pages": {
                "USR_vs_ETC_Overrides.md": {
                    "title": "USR vs ETC Overrides",
                    "desc": "Covers configurations prioritization mappings.",
                    "content": "Manages file priority rules across system overlays.\n\n## Overrides\n- **USR**: Contains static default settings.\n- **ETC**: Contains host-specific override scripts.\n- **Priority**: System units parse ETC files before defaults."
                },
                "RPM_OSTree_Exemptions.md": {
                    "title": "RPM-OSTree Exemptions",
                    "desc": "Details manual package installations resolving hardware conflicts.",
                    "content": "Exemptions allow manual packages installation for debugging.\n\n## Rules\n- **Access**: Enables installing individual debug packages.\n- **Actions**: Restricts packages to target runtime slots.\n- **Audit**: Logged in system configuration tracking."
                },
                "Dependency_Conflict_Resolution.md": {
                    "title": "Dependency Conflict Resolution",
                    "desc": "Explains troubleshooting procedures for dnf packages errors.",
                    "content": "Solves dependency conflicts during system builds.\n\n## Troubleshooting\n- **Helpers**: uses DNF5 commands with resolution flags.\n- **Guards**: Stops builds on unresolvable conflict errors.\n- **Testing**: Validates package versions integrity."
                }
            }
        },
        {
            "num": "45",
            "title": "Diagnostic_Tools_and_Profilers",
            "display": "Diagnostic Tools and Profilers",
            "pages": {
                "Hardware_Capability_Profiling.md": {
                    "title": "Hardware Capability Profiling",
                    "desc": "Covers physical adapter checks run by system-profilers.",
                    "content": "Profiles system capabilities using profiling scripts.\n\n## Operations\n- **Profiler**: Executed via [system-profiler.sh](file:///C:/MiOS/tools/system-profiler.sh).\n- **Run tool**: Runs [run-all-profilers.sh](file:///C:/MiOS/tools/run-all-profilers.sh).\n- **Output**: Logs system properties for review."
                },
                "Egress_Firewall_Verification.md": {
                    "title": "Egress Firewall Verification",
                    "desc": "Details checks verifying container loopback containment.",
                    "content": "Validates outbound networking rules.\n\n## Setup\n- **Verify tool**: Run [generate-egress-firewall.py](file:///C:/MiOS/tools/generate-egress-firewall.py).\n- **Checks**: Audits active rules inside firewall filters.\n- **Safety**: Confines network execution blocks."
                },
                "Profile_Comparison_Utilities.md": {
                    "title": "Profile Comparison Utilities",
                    "desc": "Explains comparing active setups against templates.",
                    "content": "Compares configuration states against templates.\n\n## Utilities\n- **Script**: Run [profile-compare.sh](file:///C:/MiOS/tools/profile-compare.sh).\n- **Checks**: Scans active configs against reference parameters.\n- **Gating**: Detects drift parameters."
                }
            }
        },
        {
            "num": "46",
            "title": "User_Persona_Staging",
            "display": "User Persona Staging",
            "pages": {
                "Default_User_Creation.md": {
                    "title": "Default User Creation",
                    "desc": "Covers default accounts, credentials, and settings groups.",
                    "content": "Sets up user accounts and home layouts.\n\n## Configurations\n- **Creation**: Executed via sysusers configs.\n- **Script**: Handled by [31-user.sh](file:///C:/MiOS/automation/31-user.sh).\n- **Rights**: Adds user accounts to virtual and container groups."
                },
                "Stagings_Dotfiles_Overlay.md": {
                    "title": "Stagings Dotfiles Overlay",
                    "desc": "Details template overlay merging home profile files.",
                    "content": "Deploys template configuration files to user home folders.\n\n## Flow\n- **Dotfiles**: Seeds user folders (e.g. `~/.config/mios/`).\n- **Templates**: Sourced from `/etc/skel/`.\n- **Integrity**: Merges parameters without destroying custom changes."
                },
                "Multi-User_Sandboxes.md": {
                    "title": "Multi-User Sandboxes",
                    "desc": "Explains isolation policies across different accounts.",
                    "content": "Isolates configuration environments across different user accounts.\n\n## Details\n- **Sandboxing**: Confines user environments.\n- **Groups**: Restricts group permissions.\n- **Access**: Prevents cross-user configuration editing."
                }
            }
        },
        {
            "num": "47",
            "title": "Virtual_Machine_Templates",
            "display": "Virtual Machine Templates",
            "pages": {
                "Windows_11_SecureBoot_XML.md": {
                    "title": "Windows 11 SecureBoot XML",
                    "desc": "Details template variables enabling vTPM and Secure Boot.",
                    "content": "Provides VM templates meeting Windows 11 Secure Boot specifications.\n\n## Template\n- **File**: Shipped in [win11-secureboot-template.xml](file:///C:/MiOS/tools/win11-secureboot-template.xml).\n- **Features**: Includes vTPM, SecureBoot, and UEFI firmware settings.\n- **Isolation**: Optimizes settings for VFIO passthrough."
                },
                "Linux_Guest_Cloud-Init.md": {
                    "title": "Linux Guest Cloud-Init",
                    "desc": "Covers automating guest staging using init data.",
                    "content": "Deploy virtual machines using pre-configured cloud-init settings.\n\n## Operations\n- **Cloud-Init**: Staged inside default VM tools.\n- **Setup**: Configures default networks, accounts, and keys.\n- **Tuning**: Speeds up guest environment provisioning."
                },
                "VM_Lifecycle_Management.md": {
                    "title": "VM Lifecycle Management",
                    "desc": "Explains hypervisor guest actions executed via virsh.",
                    "content": "Manages virtual guests using command tools.\n\n## Actions\n- **CLI**: Executed using libvirt's `virsh` tools.\n- **States**: Starts, stops, and scales VM instances.\n- **Tuning**: Configured in VM xml configurations."
                }
            }
        },
        {
            "num": "48",
            "title": "Local_AI_Web_Consoles",
            "display": "Local AI Web Consoles",
            "pages": {
                "Open_WebUI_Deployment.md": {
                    "title": "Open WebUI Deployment",
                    "desc": "Covers Open WebUI Quadlet parameters and local mapping.",
                    "content": "Deploys Open WebUI as the primary browser chat interface.\n\n## Details\n- **Port**: Serves requests on port 3030.\n- **Service**: Managed via `mios-owui` Quadlet.\n- **Connection**: Connects internally to `/v1/chat/completions` on the local endpoint."
                },
                "Interface_Customization.md": {
                    "title": "Interface Customization",
                    "desc": "Details interface layout settings and custom models aliases.",
                    "content": "Customizes panels and options in the web interface.\n\n## Settings\n- **Customizations**: Configures defaults inside Open WebUI.\n- **Tuning**: Integrates with local search tool paths.\n- **Features**: Restricts outbound options."
                },
                "Token-based_Access_Control.md": {
                    "title": "Token-based Access Control",
                    "desc": "Explains console access security using token authentication.",
                    "content": "Secures web access using credentials tokens.\n\n## Details\n- **Authentication**: secured via token strings.\n- **Logs**: User connection actions are tracked.\n- **Security**: Restricts local web console access."
                }
            }
        },
        {
            "num": "49",
            "title": "Offline_First_Governance",
            "display": "Offline-First Governance",
            "pages": {
                "Local_Package_Mirrors.md": {
                    "title": "Local Package Mirrors",
                    "desc": "Covers staging local mirror caches inside container build overlay.",
                    "content": "Configures local update repositories to support air-gapped runtimes.\n\n## Setup\n- **Mirrors**: Maps DNF5 to local package directories.\n- **Baking**: Packages are pre-loaded during image generation.\n- **Rules**: Avoids network access requests on host update calls."
                },
                "Sovereign_Model_Storage.md": {
                    "title": "Sovereign Model Storage",
                    "desc": "Details models weights verification loaded under /srv/ai.",
                    "content": "Caches model weights locally to prevent telemetry leaks.\n\n## Storage\n- **Weights**: Safely stored inside `/srv/ai/models/`.\n- **Gating**: Missing weights prevent inference lanes from starting.\n- **Updates**: Models are updated via offline imports."
                },
                "Non-Network_Degradation_Modes.md": {
                    "title": "Non-Network Degradation Modes",
                    "desc": "Explains fallback behaviors resolving missing active gateways.",
                    "content": "Ensures local tools remain functional when offline.\n\n## Settings\n- **Degradation**: Disables search queries when offline.\n- **Core Stacks**: Keeps local inference lanes active.\n- **Governance**: Complies with the OFFLINE-FIRST law."
                }
            }
        },
        {
            "num": "50",
            "title": "Upstream_Tracking_and_Maintenance",
            "display": "Upstream Tracking and Maintenance",
            "pages": {
                "Upstream_Drift_Monitor.md": {
                    "title": "Upstream Drift Monitor",
                    "desc": "Covers checking changes between host and remote overlays.",
                    "content": "Monitors updates and changes inside upstream base OCI images.\n\n## Details\n- **Monitor**: Run [mios-upstream-monitor.sh](file:///C:/MiOS/tools/mios-upstream-monitor.sh).\n- **Checks**: Compares package indexes against target reference lists.\n- **Gating**: Detects drift parameters."
                },
                "Justfile_Pipeline_Automation.md": {
                    "title": "Justfile Pipeline Automation",
                    "desc": "Details Justfile build automation and check goals.",
                    "content": "Automates repetitive build and test targets using Justfile.\n\n## Tasks\n- **Build**: Compiles image files using `just build`.\n- **Verification**: Runs validations using `just lint`.\n- **Packaging**: Packages artifacts using target tags."
                },
                "Release_Maturity_Runbook.md": {
                    "title": "Release Maturity Runbook",
                    "desc": "Explains checklist targets required to tag release stages.",
                    "content": "Runbook steps guide moving image builds to release configurations.\n\n## Flow\n- **Runbook**: Mapped in [maturity-and-release-runbook.md](file:///C:/MiOS/usr/share/doc/mios/reference/maturity-and-release-runbook.md).\n- **Checkpoints**: Verifies tests, SBOM compliance, and signatures.\n- **Tagging**: Publishes checked builds under stable tags."
                }
            }
        }
    ]

    # Write unified master manual.md (All-in-One Manual) generation
    aio_content = """<!-- AI-hint: Unified All-in-One User Manual for MiOS. Consolidates all 50 chapters and 152 pages into a single document. -->
# MiOS All-in-One User Manual & System Documentation

Welcome to the comprehensive, All-in-One User Manual and System Documentation for **MiOS** (pronounced *"MyOS"*). 

This unified document consolidates the entire 50-chapter documentation suite, detailing the system's dual nature as an immutable, bootc-managed Fedora workstation and a sovereign, offline-first agentic AI OS.

---

## Table of Contents

"""

    # Dynamic master README.md parts structure
    parts = [
        {"title": "Part I: Foundations & Philosophy", "range": range(1, 4)},
        {"title": "Part II: The Agentic AI Stack", "range": range(4, 8)},
        {"title": "Part III: Core OS Infrastructure", "range": range(8, 10)},
        {"title": "Part IV: Detailed Inference & Execution Layers", "range": range(10, 16)},
        {"title": "Part V: Deep Security, Cryptography & Hardware", "range": range(16, 23)},
        {"title": "Part VI: Storage, Network & Web Planes", "range": range(23, 30)},
        {"title": "Part VII: Build, Test & Upstream Maintenance", "range": range(30, 51)}
    ]

    for part in parts:
        aio_content += f"### {part['title']}\n"
        for ch in chapters:
            ch_num = int(ch["num"])
            if ch_num in part["range"]:
                aio_content += f"* **Chapter {ch['num']}: {ch['display']}**\n"
                for page_file, page_info in ch["pages"].items():
                    page_anchor = f"{ch['num']}_{page_info['title'].lower().replace(' ', '_').replace('/', '_').replace('-', '_')}"
                    aio_content += f"  * [{page_info['title']}](#{page_anchor}): {page_info['desc']}\n"
        aio_content += "\n"

    aio_content += "---\n\n"

    for part in parts:
        aio_content += f"# {part['title']}\n\n"
        for ch in chapters:
            ch_num = int(ch["num"])
            if ch_num in part["range"]:
                aio_content += f"## Chapter {ch['num']}: {ch['display']}\n\n"
                aio_content += f"This chapter covers the documentation for **{ch['display']}** under MiOS.\n\n"
                
                for page_file, page_info in ch["pages"].items():
                    page_anchor = f"{ch['num']}_{page_info['title'].lower().replace(' ', '_').replace('/', '_').replace('-', '_')}"
                    aio_content += f"### <a name=\"{page_anchor}\"></a>{ch['num']}.{page_file.replace('.md', '').replace('_', ' ')}: {page_info['title']}\n\n"
                    aio_content += f"> Path Reference: `/usr/share/doc/mios/manual.md#{page_anchor}`\n\n"
                    aio_content += "#### Overview\n\n"
                    aio_content += f"{page_info['content']}\n\n"
                    
                    if "citations" in page_info:
                        aio_content += "#### Citation & Attribution References\n\n"
                        aio_content += "This section links back to the authoritative [Attribution Registry (credits.md)](file:///usr/share/doc/mios/reference/credits.md):\n"
                        for cit in page_info["citations"]:
                            row_name, row_link = credits_map[cit]
                            aio_content += f"- **Row {cit}** ({row_name}): [Attribution Reference]({row_link})\n"
                        aio_content += "\n"

                    aio_content += "#### System References\n\n"
                    aio_content += "- Relevant configurations: `mios.toml`\n"
                    aio_content += "- Runtime services: `http://localhost:8642/v1`\n\n"
                    aio_content += "#### Guidelines & Best Practices\n\n"
                    aio_content += "1. Adhere to the Seven Architectural Laws of MiOS at all times.\n"
                    aio_content += "2. All configurations should be resolved using the three-layer override structure.\n"
                    aio_content += "3. System state updates must be atomic and verified before reboot.\n\n"
                    aio_content += "---\n\n"

    with open(manual_path, "w", encoding="utf-8") as f:
        f.write(aio_content)

    print(f"Successfully generated master manual.md and cleaned up old directory: {manual_dir}")

if __name__ == "__main__":
    main()
