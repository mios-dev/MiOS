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

# **Based on the detailed analysis of the MiOS architecture, here are suggested improvements focused on addressing current limitations, enhancing long-term maintainability, and extending capabilities:1. Address the `systemd-sysext` Kernel Stacking Depth Limitation**

# 

# The analysis explicitly notes the risk of the `overlayfs: maximum fs stacking depth exceeded` error during `systemd-sysext.service` initialization, as observed in a competing distribution.

* **Improvement:** Proactively develop and implement a kernel-level mitigation strategy before the full transition to `systemd-sysext`.  
  * **Action:** Open a dedicated upstream issue or submit a patch to the Fedora Rawhide kernel maintainers to increase the default `overlayfs` stacking depth (if technically feasible and safe) or, failing that, develop a robust workaround in the `mios-init.service` to dynamically repackage multiple small `.sysext` images into a single, larger one at runtime to reduce the perceived stacking depth. This ensures the strategic long-term vision for proprietary driver management is not crippled by an upstream kernel limitation.

2\. **Enhance the Network UPS Tools (NUT) Remediation Strategy**

# 

# The current plan for NUT integration relies on crafting universal, immutable configuration files for common UPS models in the `/sys_files/usr/` blueprint. This approach is brittle and non-scalable.

* **Improvement:** Implement a dynamic configuration layer for hardware-specific settings within the immutable environment.  
  * **Action:** Instead of hardcoding all UPS configurations, utilize a **Distrobox pattern** for persistent system daemons. Package the full NUT suite (server and client) into a lightweight, specialized read/write **Distrobox container**. This container can manage the mutable configurations (e.g., `/etc/udev/rules.d`, socket files, and `nut.conf`) within its own writeable root filesystem, while the necessary USB device nodes (`/dev/bus/usb`) are seamlessly mapped inside via `podman` volume mounts. This decouples a mutable, hardware-specific daemon from the immutable host.

3\. **Implement Granular OCI Update Differentials for Bandwidth Reduction**

# 

# The analysis points out that delivering updates as comprehensive OCI image layers results in "significantly larger" data payloads, necessitating internal pull-through caches to mitigate "severe localized network congestion."

* **Improvement:** Research and integrate OSTree's native differential update capabilities at the registry level.  
  * **Action:** While the current model relies on monolithic image swaps, the underlying OSTree technology is designed to only transmit the file and block-level differences between the old and new image commits. Configure the CI/CD pipeline and the GitHub Container Registry (GHCR) integration to fully leverage OSTree's delta generation. This will reduce the on-the-wire payload size dramatically, potentially eliminating the need for expensive, localized pull-through caches for most deployments.

4\. **Formalize and Automate the Secure Boot MOK Enrollment Prompt**

# 

# The remediation for proprietary NVIDIA drivers requires the end-user to manually enroll a Machine Owner Key (MOK) into the UEFI firmware on first boot. This manual step introduces a point of failure and degrades the "zero-touch" deployment goal.

* **Improvement:** Automate the MOK enrollment process as much as possible and provide a failsafe.  
  * **Action:** Utilize the `mokutil` utility and systemd hooks to automatically stage the MOK key for the next reboot. Instead of a manual prompt, execute a **graphical `zenity` or `plymouth` script** that presents the user with a single, clear message *before* the graphical environment initializes, explaining that they must press a specific key (e.g., `Enter`) to confirm the enrollment. This turns a complex manual procedure into a near-automated, guided interactive process.

5\. **Strengthen Security by Applying SELinux to Sandboxes**

# 

# While the system enforces a strong "Zero-Trust" posture and utilizes `fapolicyd` and `CrowdSec` for host protection, the description of Distrobox sandboxes and K3s containers does not explicitly mention fine-grained mandatory access control (MAC).

* **Improvement:** Enforce a strict SELinux profile on all containerization and virtualization runtimes.  
  * **Action:** Configure the Podman and K3s daemons to run with a mandatory, non-default SELinux type (e.g., `container_t` or a custom `mios_sandbox_t`). Ensure that the Distrobox creation process strictly adheres to this, thereby using SELinux to confine any potential container escape or vulnerability within the mutable sandbox away from critical system resources, providing a multi-layered security defense.

# **Engineering the MiOS: Architectural Paradigms, Lifecycle Management, and Strategic Evolution of an Immutable Workstation**

## **Introduction to the MiOS Paradigm**

The landscape of operating system engineering is undergoing a foundational paradigm shift, moving definitively away from traditional, mutable, package-based distribution models toward unified, image-centric, and immutable architectures. At the vanguard of this transition is MiOS, an advanced, cloud-native workstation operating system currently engineered upon the bleeding-edge Fedora Rawhide (fc45) distribution framework. Designed from its inception to function simultaneously as a high-performance developer desktop and a Tier-1 hypervisor, MiOS fundamentally reimagines how an operating system is constructed, deployed, and maintained. By rigorously applying the Open Container Initiative (OCI) specification to the host itself, the project abstracts the hardware layer entirely, treating the Linux kernel, the bootloader, and the entire userspace ecosystem as a singular, cohesive container payload.  
Historically, operating systems have relied on local, on-device package managers (such as APT, DNF, or Pacman) to continuously mutate the state of the host filesystem over time. This approach inevitably leads to severe configuration drift, intricate dependency conflicts, and systemic fragility, often colloquially referred to as "dependency hell" or "system rot". MiOS resolves this systemic fragility by utilizing the bootc (bootable container) ecosystem. This framework ensures universal hardware compatibility across complex AMD, Intel, and NVIDIA silicon topologies, and seamlessly facilitates highly deterministic deployments across diverse environments, ranging from isolated bare-metal servers to local Hyper-V/WSL2 virtualization environments, and hyperscale cloud providers such as the Cloud Cloud Platform (GCP).  
The developmental trajectory of MiOS traces back to a highly optimized, monolithic foundation based on Fedora Bootc and MiOS. In its legacy iteration, the system relied on a massive suite of imperative shell scripts for hardware management, most notably the mios-build-assess.sh utility, which calculated a zero-to-ten compatibility score by rigorously evaluating virtualization support, IOMMU grouping quality, TPM 2.0 availability, and Secure Boot capabilities. This legacy toolkit also included system-assess.sh, a 2,629-line diagnostic utility, and the mios-full.sh monolithic management script, sprawling across 4,497 lines of code to orchestrate interactive installations. However, recognizing that imperative scripting cannot guarantee enterprise-grade immutability or facilitate atomic updates via the GitHub Container Registry (GHCR), the architectural foundation was systematically migrated to the Fedora Rawhide bootc ecosystem. This pivot introduces profound benefits in runtime stability, enabling updates to be delivered as transactional OCI image layer swaps that mathematically eliminate zero-day deployment breakages through automated fallback mechanisms.

## **Core Architecture and the Immutability Engine**

The cornerstone of MiOS is its immutability engine, an advanced filesystem architecture that securely binds the operating system's operational state to cryptographically verifiable container layers. Unlike standard container runtimes (such as Docker or Podman) that execute ephemeral applications within isolated kernel namespaces situated above an existing, mutable host operating system, the bootc architecture inverts this relationship. In this paradigm, the OCI image definitively maps the host's primary userspace, where systemd acts natively as Process ID (PID) 1\.

### **The OSTree and composefs Framework**

The deployment lifecycle is continuously managed by the bootc command-line client, which natively leverages embedded OSTree internals to orchestrate discrete system deployment nodes directly on the physical storage medium. This underlying architecture enforces rigorous, unyielding filesystem segregation. Specifically, the /usr directory, which houses all critical system binaries, shared libraries, and core execution environments, is mounted strictly as a read-only filesystem via composefs. The implementation of composefs provides the cryptographic deduplication equivalent to what OSTree provides to Flatpak environments, enabling highly efficient storage utilization. It ensures that the active system state is cryptographically sealed and identical to the verified OCI container image residing in the remote cloud registry, utilizing fs-verity to guarantee that the filesystem remains impervious to unauthorized modifications or malware injections.  
To accommodate the strict requirement for dynamic, persistent user data within an otherwise static and frozen system, MiOS dynamically isolates mutable state. The /home directory is fundamentally re-architected during the boot sequence as a symbolic link pointing to the /var/home directory, as the /var partition is explicitly designated for persistent, mutable data. This segregation ensures that during an atomic system update—where the root filesystem is replaced entirely out-of-place—all user configurations, cryptographic SSH keys, and personal engineering files remain entirely untouched and persistent across system reboots.

### **System State Management and the Verification Lifecycle**

To prevent configuration drift within the conventionally mutable /etc directory, MiOS relies heavily on the nss-altfiles and systemd-sysusers subsystems. Rather than relying on static, manual file modifications for the provisioning of user accounts, groups, and stateful daemon configurations, the system delegates these critical responsibilities to dynamic systemd generators executing during the early initialization phases.  
Security and operational stability are further reinforced during the early boot stage. If systemic tampering is detected by the fs-verity subsystem, or if a newly applied OCI update results in a catastrophic boot failure—such as a kernel panic or a fatal crash within the Wayland compositor—a dedicated diagnostic daemon, mios-verify.service, detects the anomaly. Upon detecting an unrecoverable state, this service triggers an automated, seamless rollback, pivoting the bootloader to boot from the previous, known-good OSTree commit. This advanced dual-deployment model ensures absolute zero interruption to end-user productivity, definitively resolving the traditional administrative fear of "bricking" a physical workstation through a faulty downstream driver update. Furthermore, upgrades are executed utilizing the systemd-soft-reboot framework. This technology pivots the root directory to a newly pulled image and restarts systemd entirely in memory, taking mere seconds and completely bypassing the lengthy UEFI and hardware initialization POST phases typically associated with kernel updates.

### **Memory Aggregation and Virtualization Tuning**

Given the heavy virtualization and containerization workloads inherent to a Tier-1 hypervisor designed for complex software engineering, physical memory management is aggressively optimized within the base image. Traditional, slow swap partitions located on physical disk drives are completely disabled at the architectural level. Instead, MiOS implements zram-generator, which dynamically and elastically provisions up to fifty percent of the available physical RAM (capped strictly at thirty-two gigabytes) as a highly compressed swap block utilizing the advanced zstd compression algorithm.  
The Linux kernel itself is explicitly tuned for maximum virtualization throughput and memory retention. The vm.swappiness sysctl parameter is pinned aggressively at a value of ten, forcing the kernel scheduler to keep virtual machine memory mapped inside high-speed physical RAM for as long as mathematically possible before resorting to compression. Furthermore, to support the dense, high-frequency orchestration of rootless Podman containers and localized Kubernetes (K3s) pods, the system increases its file-watching capabilities by setting inotify watches to an unprecedented maximum of 1,048,576. To maintain network stability within these dense microservice environments, aggressive Address Resolution Protocol (ARP) garbage collection thresholds are enforced via sysctl, preventing network flux and catastrophic routing table overflows in highly clustered environments.

## **Source Code Organization and the Build Ecosystem**

The structural design of the source code repository directly dictates the scalability, auditability, and maintainability of an image-based operating system. A pervasive anti-pattern frequently observed in early, experimental bootc projects is the heavy reliance on a monolithic Containerfile. Early iterations of container-based operating systems often consist of a single file heavily burdened with chained RUN commands, massive inline bash scripts, and convoluted sed and awk substitutions designed to manipulate configuration files directly during the build. This methodology becomes exponentially more difficult to maintain, audit, and debug as the complexity of the operating system scales.  
MiOS explicitly rejects this monolithic model in favor of a highly modular repository hierarchy modeled after mature, enterprise-grade bootable image blueprints, specifically mirroring the successful architecture pioneered by the Universal Blue project (which produces the Bazzite and Bluefin operating systems). The orchestrator script within MiOS was comprehensively redesigned from a monolithic structure into a declarative architecture utilizing a shared package parser.

### **Declarative Repositories and Structural Modularity**

A forensic analysis of optimal bootc blueprints mandates a rigorous separation of package management, sequential build scripts, system configurations, and Continuous Integration pipeline definitions. The repository structure aligns with the following functional delineations:

| Component Directory / File | Functional Purpose in the Ecosystem | Implementation Strategy within MiOS |
| :---- | :---- | :---- |
| Containerfile | The root orchestrator for the OCI image. | Acts purely as a high-level orchestrator. It defines the base OS layer (e.g., Fedora Rawhide 45\) and systematically invokes modular external scripts rather than housing complex inline execution logic. |
| /build\_files/ | Sequentially numbered execution shell scripts. | Houses heavily decoupled logic (e.g., 01-packages.sh, 02-k3s-setup.sh, 17-cleanup.sh), ensuring mathematical determinism and rapid isolation of errors during the OCI compilation phase. |
| /sys\_files/usr/ | A structural mirror of the final /usr immutable filesystem tree. | Utilized to securely inject default configurations, custom udev rules, and systemd unit files directly into the image layer via a standard COPY instruction, completely bypassing the need for complex, failure-prone echo or sed commands during compilation. |
| packages.json | A fully declarative RPM package JSON manifest. | Replaces inline, imperative dnf install loops. Parsing a JSON array during the build phase allows for automated dependency tracking and permits integration with automated bots (such as Renovate) to autonomously submit pull requests for upstream library updates. |
| Justfile | A standardized, cross-platform command runner configuration. | Abstracts complex multi-stage Podman builds, comprehensive linting pipelines, and advanced Secure Boot MOK enrollment commands into simplified, repeatable developer aliases. |

This rigorous compartmentalization vastly reduces the technical debt associated with operating system maintenance. By injecting system configurations via a static /sys\_files copy operation, the execution time, resource consumption, and potential failure points of the container build step are exponentially reduced.

### **Cloud-Based Compilation and the OCI Delivery Mechanism**

The delivery mechanism of MiOS fundamentally shifts the compilation burden entirely from the end-user's local hardware to centralized, cloud-based Continuous Integration and Continuous Deployment (CI/CD) pipelines. Utilizing infrastructure such as GitHub Actions, the pipeline fetches the specific kernel version embedded in the Fedora base, installs the requisite compilation toolchains, and executes the operating system build entirely inside a transient runner. The system utilizes a fleet management philosophy governed by lightweight systemd timers, specifically bootc-fetch.timer and bootc-apply.timer. These timers incorporate mathematical jitter to prevent network flooding and utilize machine-level certificates to authenticate against corporate registries.  
However, this paradigm shift introduces critical infrastructural dependencies. The deployment model relies heavily on the continuous availability, bandwidth, and uptime of external registries such as the GitHub Container Registry (GHCR). Because updates are delivered as comprehensive OCI image layers rather than highly isolated, granular RPM patches, the data payloads are significantly larger in size. To mitigate severe localized network congestion during fleet-wide rollouts, enterprise deployments of MiOS necessitate the implementation of internal pull-through cache registries to effectively manage the massive bandwidth required for these monolithic image updates.

## **Desktop Environment, Sandboxing, and the Prebake Engine**

Aligning strictly with modern cloud-native architectural philosophies, MiOS embraces a "Naked Core" approach. The foundational operating system contains only the absolute minimum RPM packages necessary to initialize the hardware, configure the network stack, and render the graphical interface. All subsequent end-user applications, complex development suites, and web browsers are aggressively delegated to fully sandboxed environments.

### **Wayland-Driven GNOME 50 and Typographic Rendering**

The primary user interface is powered by a heavily optimized, Wayland-only implementation of the GNOME 50 desktop environment, deeply integrated with the Mutter 50 compositor and the GTK 4.22 toolkit. Native X11 protocol support is explicitly deprecated and excluded from the core system, supported solely via the isolated Xwayland compatibility layer strictly for legacy application execution.  
Aesthetic consistency across disparate UI frameworks is managed through dynamic portal theming. By utilizing xdg-desktop-portal in conjunction with qgnomeplatform, the system instantly and perfectly synchronizes Dark Mode transitions across GTK3, GTK4, Qt5, Qt6, and Electron-based application frameworks. The entire visual environment is unified by the integration of Vercel’s open-source Geist typeface, ensuring a high-fidelity typographic experience. Core workflow enhancements are deeply integrated into the GNOME shell via pre-configured extensions, including Dash to Dock for dynamic transparency, native AppIndicator support, and the Tiling Assistant for advanced, multi-monitor quarter-snapping.

### **Mutable Sandboxes via Distrobox**

Because the /usr filesystem is strictly mounted as read-only, developers cannot utilize the dnf5 package manager to install arbitrary libraries, language compilers, or development headers directly onto the host filesystem. To provide an unimpeded, highly flexible development experience, MiOS utilizes Distrobox to create highly integrated, mutable development sandboxes. Underpinned by the daemonless Podman architecture, Distrobox allows engineers to rapidly instantiate lightweight, mutable containers (such as fully functional Ubuntu, Alpine, or Fedora Bootc environments) that seamlessly map to the user's persistent home directory, Wayland compositor socket, and D-Bus system bus. This profound integration allows graphical applications and CLI tools installed within the mutable sandbox to appear and function identically to native host applications.

### **The Flatpak Prebake Vault Mechanism**

A fundamental, unresolved architectural conflict exists between OSTree's deployment mechanics and the distribution of Flatpak applications. During the compilation of an OCI container image, OSTree meticulously captures the precise state of the /usr directory to form the cryptographic seal. However, because the /var directory is strictly designated for machine-local, mutable data, OSTree systematically and intentionally wipes the contents of the /var directory during the final image commit to prevent cross-device configuration drift. As system-wide Flatpak installations are inherently mapped to the /var/lib\[span\_5\](start\_span)\[span\_5\](end\_span)/flatpak hierarchy, this immutable mechanism effectively destroys all pre-installed applications during the CI build process.  
To engineer a solution around this limitation, MiOS developed a proprietary mechanism known as the "Prebake Vault". During the OCI build phase, core Flatpak applications—such as Epiphany (GNOME Web), VSCodium, and Podman Desktop—are fully downloaded, installed, and configured within the transient container environment. Immediately before the termination of the build step, the entire populated /var/lib/flatpak directory is securely captured into an uncompressed archive stored directly within the immutable /usr tree at the specific path /usr/share/mios-flatpak-prebake.tar. Crucially, this tarball is generated utilizing the strict \--selinux and \--xattrs execution flags to perfectly preserve highly complex security contexts.  
Upon the system's first initialization, a dedicated unit file, mios-init.service, detects the virgin state of the machine. It rapidly extracts the tar archive directly into the newly provisioned /var partition and executes a flatpak repair \--system command to systematically rebuild the application metadata. This methodology allows the GNOME dock to be instantly populated with functional applications on the first boot, completely bypassing the architectural limitations of the OSTree compilation wipe.

## **Centralized Management and Telemetry**

Centralized administrative control of the MiOS node is achieved through the integration of the Cockpit WebUI. Cockpit serves as the administrative nexus for managing the entire containerized stack, executing virtual machine controls, and monitoring system telemetry. Unlike traditional monitoring agents that require a localized proprietary database, Cockpit interacts directly and exclusively with the system's native D-Bus APIs and standard command-line utilities.  
From an efficiency standpoint, Cockpit is designed to operate strictly on-demand. It utilizes systemd socket activation (systemd-socket-active), ensuring that the web server components consume absolute zero memory or CPU resources when an administrator is not actively logged into the graphical interface. Furthermore, MiOS incorporates AI-assisted development workflows. Utilizing a telemetry-free compilation of the VSCodium IDE, engineers can leverage a proprietary extension interfacing directly with the Agent 1.5 Pro API for architectural reasoning and code generation. Security is maintained by strictly injecting the API keys into ephemeral .devcontainer environments, explicitly preventing the plaintext storage of access tokens on the persistent filesystem.

## **Hardware Acceleration and Virtualization Mechanics**

MiOS transcends the limitations of a standard client desktop; it is engineered from its inception to function as a highly performant Tier-1 hypervisor designed explicitly for intense parallel computing, hardware-accelerated virtualization, and microservice orchestration.

### **The Hypervisor Stack and Core Shielding**

The core hypervisor infrastructure relies on the KVM (Kernel-based Virtual Machine) and Libvirt stack, managed natively via qemu-kvm and virt-manager. To facilitate high-speed, mathematically zero-latency file sharing between the Linux host and virtualized guest operating systems, the architecture utilizes the virtiofsd daemon.  
Virtualization performance is radically augmented through deep system-level tuning. Borrowing heavily from its MiOS heritage, which is renowned for microarchitecture optimizations targeting x86-64-v3, v4, and znver4 instruction sets, the system utilizes specialized kernel configurations featuring the BORE (Burst-Oriented Response Enhancer) scheduler. This highly specialized CPU scheduler strictly prioritizes interactive desktop fluidity in the GNOME Wayland session, ensuring the user interface remains highly responsive even while the background system is utterly saturated with heavy KVM virtualization payloads. Furthermore, MiOS employs modular Libvirt daemons (such as virtqemud.socket and virtproxyd.socket) to achieve strict process fault isolation, and systematically executes CPU topology pinning—also known as core shielding—via systemd hooks to drastically reduce context-switching latency during complex parallel computing tasks.

### **GPU Passthrough, VFIO, and Looking Glass**

A defining architectural characteristic of MiOS is its ability to seamlessly manage multi-GPU hardware environments. It is explicitly engineered for asymmetric configurations, such as scenarios where an integrated AMD GPU drives the Linux host Wayland compositor while a discrete NVIDIA GPU (e.g., an RTX 4090\) is completely and securely isolated for an underlying Windows guest VM.  
Traditional GPU passthrough requires static kernel boot parameters and rigid IOMMU group isolations that lock the discrete GPU away permanently from the host. MiOS introduces dynamic rebinding capabilities via the advanced mios-vfio-toggle utility. Operating as a highly privileged wrapper for the driverctl framework, this script empowers users to instantaneously bind and unbind specific PCIe devices to the vfio-pci stub driver on the fly, entirely eliminating the need for disruptive host reboots. The foundational universal-vfio-configurator.sh script fully automates this complex process by evaluating IOMMU topologies and injecting hardware IDs directly into the bootramfs generation sequence. This configurator specifically includes advanced logic to address specialized hardware errata, successfully mitigating the initialization reset bug inherent to modern NVIDIA RTX 50-series hardware.  
For graphical output from the virtual machine, the architecture completely abandons physical monitor switching in favor of Looking Glass (B7). This capture technology leverages highly optimized shared memory via the /dev/shm/looking-glass block to intercept the frame buffer of the Windows guest's isolated GPU. It then streams this uncompressed video data directly into a native Wayland client window on the Linux host. Paired with the Mutter compositor's experimental support for High Dynamic Range (HDR) and Variable Refresh Rate (VRR) technologies like FreeSync and G-Sync, this pipeline allows for absolute zero-latency, 144Hz+ graphical performance inside a fully virtualized sandbox.

### **Mobile Application Subsystems**

Beyond traditional PC virtualization, the operating system natively integrates Waydroid, a highly advanced LXC-based Android container subsystem. Waydroid allows Android APK applications to execute directly upon the GNOME Wayland compositor. By utilizing the LXC framework to share the Linux host's kernel, Waydroid bypasses the massive overhead associated with traditional Android emulation, granting mobile applications direct, unmitigated access to the host's hardware acceleration and GPU rendering pipelines.

## **The Hardware Driver Conundrum: DKMS vs. System Extensions**

One of the most profound architectural conflicts in deploying an immutable, container-native operating system revolves around the integration of proprietary hardware drivers, specifically those provided by NVIDIA. In traditional Linux environments, Dynamic Kernel Module Support (DKMS) automatically compiles proprietary driver modules against the active kernel headers directly on the user's local machine during a system update. However, this process is fundamentally impossible on MiOS for two explicit reasons: the /usr filesystem is strictly cryptographically sealed as read-only, and the system completely lacks a local compiler toolchain due to its aggressive "Naked Core" minimalist philosophy.

### **Strategic Remediation via Cloud-Based Precompilation**

The primary short-term remediation for this capability delta requires shifting the heavy compilation payload entirely into the CI/CD pipeline. Proprietary NVIDIA drivers are precompiled into the OCI container layers during the GitHub Actions build sequence using prebuilt, highly optimized modules (linux-cachyos-nvidia-open). These compiled kernel modules (such as nvidia.ko) are then injected directly into the container's /usr/lib/modules hierarchy alongside standard open-source drivers.  
However, this precompilation strategy introduces severe friction with modern Unified Extensible Firmware Interface (UEFI) Secure Boot environments. Because the injected drivers are proprietary and not cryptographically signed by the upstream Linux kernel keys, the host machine's Secure Boot enforcement will refuse to load them into memory, invariably leading to catastrophic graphical failures. The remediation necessitates the rigorous engineering of custom cryptographic signing infrastructure. Infrastructure teams must successfully generate a unique Machine Owner Key (MOK) during the OCI build process, sign the proprietary drivers, and securely distribute the MOK. Crucially, developers must implement complex automation scripts designed to prompt the end-user to manually enroll this MOK into the physical machine's UEFI firmware during the very first boot sequence, strictly before the graphical environment is permitted to initialize.

### **Advanced Implementation via systemd-sysext**

While CI precompilation is functional, it tightly couples the base OS image to specific proprietary binary blob versions, severely inflating the container registry size and complicating deployment flexibility. The strategic, long-term horizon for MiOS—slated for implementation across a four-to-six-month roadmap—is the transition to System Extensions (systemd-sysext).  
The systemd-sysext framework provides an advanced mechanism to dynamically augment the immutable /usr and /opt directories without physically altering the base OSTree cryptographic hash. Proprietary NVIDIA drivers, complex CUDA toolkits, and heavy dependencies can be packaged independently as standalone SquashFS image files. During the operating system boot sequence, systemd-sysext utilizes an overlayfs mount to seamlessly merge these highly specialized extension images directly on top of the host filesystem in a transient state. This architectural decoupling allows the base MiOS image to remain entirely open-source,  and universally compatible, while hardware-specific proprietary overlays are loaded purely on-demand at runtime.  
The industry is rapidly pivoting toward this model, with competing distributions such as GNOME OS, Flatcar Container Linux, and uBlue exploring identical overlay paradigms. However, this technology introduces immense complexity regarding kernel versioning. As demonstrated by a recent critical failure in the uCore LTS distribution, a transition to the v0.1.1 LTS kernel entirely broke sysext functionality due to the overlayfs subsystem throwing an overlayfs: maximum fs stacking depth exceeded error during the systemd-sysext.service initialization. MiOS engineering must meticulously navigate these upstream kernel stacking depth limitations to ensure seamless extension merging.

## **Security Posture, Networking, and Cluster Operations**

To successfully sustain a workstation capable of interacting with highly sensitive enterprise networks and executing untrusted code within isolated development sandboxes, MiOS enforces a strict, uncompromising "Zero-Trust" local security philosophy.

### **Intrusion Prevention and Cryptographic Access Control**

At the network perimeter, the firewalld daemon is strictly configured with its default operational zone set to drop. Every single incoming network packet is systematically and instantly discarded by the kernel before it can interact with userspace, unless it originates from a whitelisted, explicitly trusted virtual interface. These trusted boundaries are strictly limited to podman0 for internal container traffic, virbr0 for hypervisor communication, waydroid0 for the Android emulation subsystem, or the local loopback interface.  
This rigid perimeter defense is aggressively augmented by the inclusion of CrowdSec IPS (Intrusion Prevention System). Configured specifically for sovereign, offline use, the CrowdSec engine continuously monitors system logs for malicious behavior and dynamically injects localized ban rules directly into the nftables firewall configuration, thwarting automated attacks and port scans.  
Internal access control and anti-malware enforcement are strictly governed by fapolicyd (File Access Policy Daemon). This utility is strictly enforced at the kernel level to prevent the execution of any unapproved, unknown, or dynamically downloaded binary payloads residing within the mutable /var/home user directory, effectively neutralizing a massive vector of user-space malware execution and ransomware. Physical security against localized hardware attacks is maintained via the USBGuard framework, a strict whitelist-based daemon that intercepts and blocks unauthorized rogue USB devices (such as malicious HID keyboard emulators or covert network interfaces) from initializing upon physical connection.

### **Orchestration and High Availability Clustering**

MiOS includes deeply embedded logic to function not merely as an isolated, standalone workstation, but as a robust, fully integrated node within an enterprise infrastructure cluster. Daemonless container execution is natively managed via Podman and Buildah, with standard Docker CLI aliases preconfigured to maintain developer muscle memory. Furthermore, a lightweight, highly optimized Kubernetes distribution, K3s, is baked directly into the immutable image and seamlessly orchestrated via the k3s.service daemon. This implementation allows the workstation to operate autonomously as a standalone control plane for local testing, or to immediately and securely join an existing bare-metal edge cluster without requiring complex external installation scripts.  
For data redundancy and sophisticated distributed operations, the system natively includes advanced enterprise High Availability (HA) primitives out-of-the-box, such as the Pacemaker cluster resource manager and the Corosync messaging layer. The underlying storage tier supports robust, multi-node distributed network file systems through the native inclusion of glusterfs, ceph-common, and iscsi-initiator-utils. This is further optimized by rigorous Multipath IO (multipath.conf) configurations designed specifically to handle automatic failovers for complex Storage Area Networks (SANs), ensuring enterprise-grade data persistence.

## **Artifact Generation and Hyperscale Cloud Provisioning**

The immense flexibility of the standard OCI format allows a single, unified source repository to be mathematically transformed into an expansive array of deployment artifacts. MiOS utilizes bootc-image-builder, a highly privileged, specialized containerization utility. Operating with elevated block-level permissions, the builder synthesizes a virtualized block device architecture, formats the necessary disk partitions (creating XFS or BTRFS for the primary tree and FAT32 for the EFI boot partition), installs the bootloader binaries, and maps the container's OSTree contents directly into the structured disk hierarchy.

### **Artifact Compilation Parameters and Deployment Matrices**

The generation of these diverse artifacts is strictly executed via tightly parameterized shell commands, capable of being run locally via command-line extensions or via GUI tools such as the dedicated extension-bootc plugin available within the Podman Desktop environment.  
A standard invocation matrix engineered to generate a QCOW2 image requires launching the podman engine with highly specific parameters, including \--privileged flags and explicit security context overriding (--security-opt label=type:unconfined\_t) to allow the manipulation of internal storage loops. The primary output targets generated by the overarching deploy-mios-targets.ps1 orchestrator include :

| Artifact Target Format | Technical Specification and Operational Use Case |
| :---- | :---- |
| **RAW Disk Images** | Bit-for-bit identical payloads used for immediate bare-metal dd flashing. Natively supports advanced LUKS2 full-disk encryption via the automated install.sh sequence. |
| **QCOW2 / VHDX Archives** | Hypervisor-optimized, copy-on-write virtual disks explicitly targeting Microsoft Hyper-V (Generation 2\) and generic generic QEMU/KVM infrastructure. |
| **WSL2 Tarballs** | A highly customized output format containing an injected wsl.conf manifest designed to force native systemd initialization and enable WSLg graphical forwarding within the Windows Subsystem for Linux environments. |
| **AMI / GCE Disks** | Cloud-native proprietary formats tailored explicitly for deployment within Amazon Web Services (AWS) and the Cloud Cloud Engine (GCE). |
| **Anaconda ISOs** | Traditional, unattended bootable installer images used for legacy network provisioning workflows and physical USB deployments. |

### **Cloud Cloud Platform (GCP) Rollout Strategies**

MiOS features dedicated, highly specialized integration for hyperscale deployment, specifically engineered for the Cloud Cloud Platform (GCP). When converting the raw OCI image into a proprietary GCE disk, the image generation pipeline strictly enforces the \--guest-os-features=UEFI\_COMPATIBLE system flag. This parameter is an absolute prerequisite to enable advanced cloud security features within GCP, including Secure Boot enforcement, Virtual Trusted Platform Modules (vTPM), and Cloud's internal low-level integrity monitoring.  
To operate seamlessly within the complex GCP ecosystem, the primary Containerfile explicitly embeds the Linux Guest Environment daemon set, specifically including Legacy-Cloud-guest-agent and Legacy-Cloud-compute-engine. This deep integration allows the immutable operating system to automatically process dynamic metadata scripts, execute dynamic block disk resizing upon boot, and natively ingest OSLogin SSH cryptographic keys via highly automated cloud-init parameters during critical "Day 0" deployments. Because the deployment pulls its atomic updates securely from the Cloud Artifact Registry (GAR), a customized pull secret is automatically provisioned via Terraform and securely symlinked to /usr/lib/container-auth.json to allow uninterrupted, authenticated background updates via the bootc-fetch.timer.  
For migrating existing cloud infrastructure, MiOS intelligently utilizes the "install-to-existing-root" methodology. An administrator can provision a standard, mutable CentOS or Fedora virtual machine on GCP, establish a secure SSH connection, and execute the privileged command bootc install to-existing-root /target. This command forcefully maps the entire MiOS OCI payload directly over the active root filesystem in place. It preserves all existing user data and inherited SSH keys, executing the complete transition to an immutable architecture in a single, rapid reboot sequence. Furthermore, proprietary Virtual Desktop Infrastructure (VDI) brokers (such as Citrix or VMware) are explicitly bypassed in favor of native HTML5 WebRTC rendering pipelines, allowing remote engineers to access the high-fidelity GNOME 50 Wayland session directly and securely through standard web browsers.

## **Quality Assurance and Automated Traceability Infrastructure**

A severe vulnerability inherent in many emerging, hobbyist image-based operating systems is the dangerous assumption that a successfully compiled OCI image automatically equates to a functional operating system. If an updated graphics driver, a broken udev rule, or a critical kernel regression is blindly committed to the public registry, client machines will obediently pull the update, potentially resulting in a devastating, fleet-wide graphical failure or unbootable state. To mathematically preempt this scenario, MiOS integrates rigorous, end-to-end automated testing utilizing the advanced Test Management Tool (tmt) and the Testing Farm framework.  
The tmt utility natively supports a dedicated bootable container plugin that fundamentally automates the entire OS validation lifecycle. Upon a successful GitHub Actions code merge, the CI pipeline ingests the newly generated container image and leverages bootc-image-builder to rapidly output a temporary QCOW2 virtual disk artifact. The testing pipeline then seamlessly triggers the virtual.testcloud plugin to autonomously spawn a headless virtual machine utilizing this exact disk artifact.  
Once the virtual machine successfully boots, tmt executes a massive, predefined suite of tests via Ansible playbooks and structured shell scripts. These tests programmatically verify that critical infrastructure layers—such as the complex formation of the K3s cluster, the operational status of the Libvirt daemons, the zram swap allocation, and the listening readiness of the WebRTC RDP ports—are functioning perfectly. This logic is highly aligned with the Testing Farm MVP (Minimum Viable Product) explicitly designed for testing RHEL Image Mode, bridging the gap between existing RPM package tests and new image-mode environments.  
Furthermore, traceability and safety-critical documentation are enforced through integrations with tools such as BASIL (part of the ELISA project). This integration ensures that every automated test executed via tmt can be directly linked to safety requirements, allowing the CI pipeline to export comprehensive, SPDX-based Software Bill of Materials (SBOMs). This guarantees complete traceability from architectural design down to final verification. Only after the system passes this incredibly comprehensive functional validation is the image cryptographically signed and tagged as a stable release in the public GHCR registry, ensuring unparalleled reliability for enterprise deployments.

## **Capability Gaps and the Network UPS Tools (NUT) Anomaly**

As of early 2026, the MiOS architecture is actively tracking several capability gaps managed through a structured, multi-phase Kanban workflow spanning 13 specific research workstreams. A specifically identified gap currently undergoing intensive research involves the total absence of native Uninterruptible Power Supply (UPS) management capabilities within the immutable core.  
In a traditional, mutable system, administrators rely heavily on the Network UPS Tools (NUT) suite to gracefully monitor power loss events and trigger safe, automated shutdowns before complete battery depletion. However, due to the strict read-only nature of the MiOS root filesystem and the rigid configuration of its systemd initializers, integrating NUT poses a distinct and complex architectural challenge. Standard implementations require deep, write-heavy hooks into /etc/udev/rules.d to correctly map the USB-HID interfaces of the UPS hardware to the nut user, coupled with the installation of nut-server and upsd binaries. When users attempt to run the upsdrvctl start daemon, it frequently fails because the systemd units cannot dynamically construct the required socket files in the locked filesystem.  
The remediation strategy for this specific gap involves a dedicated research phase to successfully integrate the networkupstools package set directly into the Containerfile via the declarative packages.json manifest. The engineering team must craft highly specialized, immutable configuration files within the /sys\_files/usr/ blueprint directory that can accurately and universally map standard consumer UPS hardware (such as CyberPower or APC devices) via USB without requiring post-installation manipulation by the end user. Furthermore, critical systemd timers and ordering dependencies must be strictly established within the OCI image to guarantee that the upsdrvctl shutdown processes execute sequentially only after the virtio daemons and podman containers have completely and safely spun down. This ordering is absolutely essential to preventing catastrophic data corruption within active virtual machines during an emergency, automated power-loss event.

## **Strategic Conclusions**

The MiOS project embodies the absolute bleeding edge of operating system design and cloud-native infrastructure engineering. By abstracting the highly complex host OS into a standardized, OCI-compliant container image, the architecture successfully eradicates decades-old issues of configuration drift, dependency hell, and deployment anxiety. Through the highly intelligent and rigorous application of composefs, OSTree, and fully automated rollback triggers, the system achieves a level of immutability previously reserved solely for lightweight, specialized IoT edge devices, and applies it directly to highly complex, hardware-accelerated developer workstations.  
The implementation of the Flatpak Prebake Vault brilliantly navigates the intense friction between static system snapshots and the requirement for mutable user applications, while the deep integration of Distrobox guarantees unimpeded, highly flexible developer productivity. Furthermore, the strategic, forward-looking roadmap addressing the severe limitations of proprietary drivers through systemd-sysext overlays signifies a maturing engineering foresight. This ensures that MiOS can dynamically and fluidly adapt to closed-source hardware requirements—such as NVIDIA driver stacks—without ever compromising the strict cryptographic integrity of its core. Coupled with incredibly robust enterprise security postures, comprehensive High Availability clustering, and deeply embedded hyperscale GCP deployment capabilities, MiOS establishes a definitive, verifiable blueprint for the future of immutable infrastructure.

#### **Works cited**

1\. uboot-images-armv8-2026.04-1.fc45 \- Fedora Packages, https://packages.fedoraproject.org/pkgs/uboot-tools/uboot-images-armv8/fedora-rawhide.html 2\. Bootc and OSTree: Modernizing Linux System Deployment \- A cup of coffee, https://a-cup-of.coffee/blog/ostree-bootc/ 3\. Announcing the Alpha release of KDE Linux, https://pointieststick.com/2025/09/06/announcing-the-alpha-release-of-kde-linux/ 4\. Shape the Future of Linux: Contribute to bootc Open Source Project | Red Hat Developer, https://developers.redhat.com/blog/2025/07/23/shape-future-linux-contribute-bootc-open-source-project 5\. MiOS-Blueprint.docx, https://drive.Legacy-Cloud.com/open?id=13wSnNlrXPUimOXmO2cnX4g1Lk\_hVfQsh 6\. The ultimate list of Linux terminal commands, https://www.linux.org/threads/the-ultimate-list-of-linux-terminal-commands.57914/ 7\. HELLO WORLD \- Sutton Grammar School, https://www.suttongrammar.sutton.sch.uk/wp-content/uploads/2024/11/HelloWorld-1.pdf 8\. Bootc Project Analysis and Recommendations, https://drive.Legacy-Cloud.com/open?id=1cwThZJ1PDFqa\_E4Hxeug3yAyRBIz-2Kwjw4OL7hJjgc 9\. CrowdStrike Update: Windows Bluescreen and Boot Loops | Hacker News \- Y Combinator, https://news.ycombinator.com/item?id=41002195 10\. Podman Desktop blog\! | Podman Desktop, https://podman-desktop.io/blog 11\. kvm-hypervisor · GitHub Topics, https://github.com/topics/kvm-hypervisor?l=shell\&o=desc\&s=stars 12\. Newbie: NVIDIA Drivers, apps slow to load. Fedora 43 Workstation, https://discussion.fedoraproject.org/t/newbie-nvidia-drivers-apps-slow-to-load-fedora-43-workstation/181380 13\. Using NVIDIA GPUs on Flatcar, https://www.flatcar.org/specs/latest/setup/customization/using-nvidia/ 14\. Bootc and OSTree: Modernizing Linux System Deployment | Hacker News, https://news.ycombinator.com/item?id=47189625 15\. Systemd-sysext | Flatcar Container Linux, https://www.flatcar.org/specs/latest/provisioning/sysext/ 16\. KDE Linux deep dive: package management is amazing, which is why we don't include it, https://www.reddit.com/r/linux/comments/1ogxv8t/kde\_linux\_deep\_dive\_package\_management\_is\_amazing/ 17\. GitHub \- ublue-os/ucore: An OCI base image of Fedora CoreOS with batteries included, https://github.com/ublue-os/ucore 18\. Analyzing MiOS GitHub Repository, https://drive.Legacy-Cloud.com/open?id=1j7v2QulE1OgkDXbQtiubexaBbWnvSVCbvv42wAqX\_sE 19\. Getting Started with Bootable Containers \- Fedora Docs, https://docs.fedoraproject.org/en-US/bootc/getting-started/ 20\. 58 posts tagged with "podman-desktop", https://podman-desktop.io/blog/tags/podman-desktop 21\. RFD5 \- Testing Farm support for Fedora, CentOS Stream and RHEL in Image Mode, https://docs.testing-farm.io/Testing%20Farm/0.1/rfd/rfd5-testing-image-mode.html 22\. DevConf.CZ \- Pretalx, https://pretalx.com/devconf-cz-2024/schedule/ 23\. DevConf.CZ 2025 :: pretalx, https://pretalx.devconf.info/devconf-cz-2025/schedule/ 24\. Critical Software Summit \- ELISA Project, https://elisa.tech/category/critical-software-summit/ 25\. user-manual.pdf \- Network UPS Tools, https://networkupstools.org/specs/user-manual.pdf 26\. Shutting down servers that are on a consumer UPS? : r/homelab \- Reddit, https://www.reddit.com/r/homelab/comments/18oesrs/shutting\_down\_servers\_that\_are\_on\_a\_consumer\_ups/ 27\. Network UPS Tools breakage : r/Fedora \- Reddit, https://www.reddit.com/r/Fedora/comments/zrv4x0/network\_ups\_tools\_breakage/ 28\. 5\. Installation instructions \- Network UPS Tools, [https://networkupstools.org/specs/user-manual.chunked/\_installation\_instructions.html](https://networkupstools.org/specs/user-manual.chunked/_installation_instructions.html)

Some endpoints for secrets, webhooks, and code scanning alerts are not supported within the current tools. However, here are alternative suggestions for checking those elements manually or enabling configurations to monitor them:

Recommendations:

1\. Actions Secrets:

• Navigate to Settings \> Secrets and variables \> Actions in the repository settings to review and manage secrets.

• Ensure sensitive data like API keys, tokens, or passwords are stored securely.

2\. Webhooks:

• Review existing webhooks in Settings \> Webhooks to ensure no unverified or outdated integrations exist. This avoids potential data leaks or unauthorized events.

3\. Code Scanning Alerts:

• Enable code scanning in Security \> Code scanning alerts to automatically detect issues in your codebase. Tools like GitHub Advanced Security or third-party scanning tools can help.

Would you like to focus on other areas, such as reviewing specific configurations, or dive deeper into any file/existing content concerns in the repository? Let me know\!**Specific Configurations for Deep Dive:**

* **Kernel Tuning Parameters:** Review the aggressive memory management settings, including `vm.swappiness` pinned at 10 and the increase of `inotify` watches to 1,048,576 for dense container environments.  
  * **Immutability and State Segregation:** Focus on the architecture where `/usr` is strictly read-only via `composefs` and mutable user data is linked from `/home` to `/var/home`.  
  * **Proprietary Driver Remediation:** Detailed review of the long-term plan to transition to **systemd-sysext** for dynamic augmentation of `/usr` and `/opt` to manage proprietary NVIDIA drivers.  
  * **Container Security:** Analyze the enforcement of a strict, mandatory, non-default SELinux profile (e.g., `mios_sandbox_t`) on all Podman/K3s sandboxes to prevent container escapes.  
  * **Artifact Generation:** Review the specific `bootc-image-builder` parameters and the deployment matrix for generating diverse targets (RAW, QCOW2, WSL2 Tarballs) and the `install-to-existing-root` methodology for GCP migration.  
* **File/Existing Content Concerns:**  
  * **NUT Configuration:** The brittleness of relying on universal, immutable configuration files in the `/sys_files/usr/` blueprint for Network UPS Tools (NUT).  
  * **Bandwidth Consumption:** The concern over "significantly larger" data payloads from comprehensive OCI image layers and the need to leverage OSTree's native differential updates to mitigate network congestion.  
  * **MOK Enrollment Automation:** The need for a failsafe graphical `zenity` or `plymouth` script to transform the manual Machine Owner Key (MOK) enrollment into a guided, near-automated interactive process.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
