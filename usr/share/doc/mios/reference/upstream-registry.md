<!-- AI-hint: Comprehensive Upstream Project & Technology Registry for MiOS. -->
<!-- AI-related: usr/share/doc/mios/manual/ch70-upstream-technology-registry-and-ecosystem-advances.md, usr/share/mios/mios.toml -->
# MiOS Research Project \- Technology Accreditation & Upstream Registry

This document serves as the official technology accreditation registry for the **MiOS (MyOS)** research project. It compiles a comprehensive, categorized name list of all foundational layers, upstreams, projects, repositories, runtimes, libraries, and tools pulled from or utilized by the MiOS operating system and build pipeline.

---

## 1\. Foundational substrate

* **Linux kernel**

  * *Role in MiOS:* Bare-metal \+ virt \+ container kernel for every deployment shape
  * *Official Homepage/Repository:* [https://www.kernel.org/](https://www.kernel.org/)


* **systemd**

  * *Role in MiOS:* PID 1, units, sysusers.d, tmpfiles.d, generators, journal, logind, networkd, resolved
  * *Official Homepage/Repository:* [https://systemd.io/](https://systemd.io/) \-- [https://github.com/systemd/systemd](https://github.com/systemd/systemd)


* **dracut**

  * *Role in MiOS:* initramfs generation (with composefs root-prep hooks)
  * *Official Homepage/Repository:* [https://github.com/dracutdevs/dracut](https://github.com/dracutdevs/dracut)


* **FHS 3.0**

  * *Role in MiOS:* Filesystem layout convention \-- repo root **is** the deployed system root
  * *Official Homepage/Repository:* [https://refspecs.linuxfoundation.org/FHS\_3.0/](https://refspecs.linuxfoundation.org/FHS_3.0/)


* **Linux kernel parameters guide**

  * *Role in MiOS:* kargs reference (`usr/lib/bootc/kargs.d/*.toml`)
  * *Official Homepage/Repository:* [https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html](https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html)


* **Linux sysctl reference**

  * *Role in MiOS:* sysctl tuning (`usr/lib/sysctl.d/*mios*.conf`)
  * *Official Homepage/Repository:* [https://www.kernel.org/doc/Documentation/sysctl/](https://www.kernel.org/doc/Documentation/sysctl/)

## 2\. Image-mode / atomic substrate

* **bootc (CNCF Sandbox)**

  * *Role in MiOS:* OS-as-OCI-image lifecycle: install, upgrade, switch, kargs, container lint
  * *Official Homepage/Repository:* [https://github.com/bootc-dev/bootc](https://github.com/bootc-dev/bootc) \-- [https://bootc.dev/](https://bootc.dev/)


* **ostree / libostree**

  * *Role in MiOS:* Content-addressed object store (current bootc backend)
  * *Official Homepage/Repository:* [https://github.com/ostreedev/ostree](https://github.com/ostreedev/ostree) \-- [https://ostreedev.github.io/ostree/](https://ostreedev.github.io/ostree/)


* **composefs**

  * *Role in MiOS:* EROFS \+ overlayfs \+ fs-verity verifiable read-only root (bootc migration target)
  * *Official Homepage/Repository:* [https://github.com/containers/composefs](https://github.com/containers/composefs) \-- [https://github.com/composefs/composefs](https://github.com/composefs/composefs)


* **Fedora bootc base images**

  * *Role in MiOS:* Fedora-side base for `quay.io/fedora/fedora-bootc:*`
  * *Official Homepage/Repository:* [https://gitlab.com/fedora/bootc/base-images](https://gitlab.com/fedora/bootc/base-images)


* **RHEL image mode (sibling reference)**

  * *Role in MiOS:* bootc upstream consumer in enterprise context
  * *Official Homepage/Repository:* [https://docs.redhat.com/en/documentation/red\_hat\_enterprise\_linux/9/html-single/using\_image\_mode\_for\_rhel\_to\_build\_deploy\_and\_manage\_operating\_systems/index](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/using_image_mode_for_rhel_to_build_deploy_and_manage_operating_systems/index)

## 3\. Base image lineage

'MiOS' is built `FROM ghcr.io/ublue-os/ucore-hci:stable-nvidia` (overridable

via `MIOS_BASE_IMAGE`).

* **Fedora hardening guide**
  * *Role in MiOS:* Source for security-stack defaults
  * *Official Homepage/Repository:* [https://docs.fedoraproject.org/en-US/quick-docs/securing-fedora/](https://docs.fedoraproject.org/en-US/quick-docs/securing-fedora/)

## 4\. Build / packaging / signing pipeline

* **Podman**

  * *Role in MiOS:* Build runtime (machine on Windows; native on Linux)
  * *Official Homepage/Repository:* [https://github.com/containers/podman](https://github.com/containers/podman) \-- [https://docs.podman.io/](https://docs.podman.io/)


* **Buildah**

  * *Role in MiOS:* OCI image build primitive (Podman backend)
  * *Official Homepage/Repository:* [https://github.com/containers/buildah](https://github.com/containers/buildah)


* **Skopeo**

  * *Role in MiOS:* Image inspection and registry plumbing
  * *Official Homepage/Repository:* [https://github.com/containers/skopeo](https://github.com/containers/skopeo)


* **dnf5**

  * *Role in MiOS:* Package manager (`install_weak_deps=False` is the dnf5 spelling)
  * *Official Homepage/Repository:* [https://github.com/rpm-software-management/dnf5](https://github.com/rpm-software-management/dnf5) \-- [https://dnf5.readthedocs.io/](https://dnf5.readthedocs.io/)


* **bootc-image-builder (BIB)**

  * *Role in MiOS:* Renders OCI bootc image to `iso`, `qcow2`, `vhd`, `raw`, `wsl2`, etc.; configs in `config/artifacts/{bib,iso,qcow2,vhdx,wsl2}.toml`
  * *Official Homepage/Repository:* [https://github.com/osbuild/bootc-image-builder](https://github.com/osbuild/bootc-image-builder) \-- [https://osbuild.org/docs/bootc/](https://osbuild.org/docs/bootc/)


* **image-builder-cli (successor under evaluation)**

  * *Role in MiOS:* First-class SBOM \+ cross-arch successor to BIB
  * *Official Homepage/Repository:* [https://github.com/osbuild/image-builder-cli](https://github.com/osbuild/image-builder-cli)


* **rechunk (bootc-base-imagectl rechunk)**

  * *Role in MiOS:* Layer-restructuring for 5--10x smaller `bootc upgrade` deltas
  * *Official Homepage/Repository:* [https://github.com/hhd-dev/rechunk](https://github.com/hhd-dev/rechunk)


* **Anaconda (bootc kickstart)**

  * *Role in MiOS:* ISO installer codepath used by `just iso`
  * *Official Homepage/Repository:* [https://fedoramagazine.org/introducing-the-new-bootc-kickstart-command-in-anaconda/](https://fedoramagazine.org/introducing-the-new-bootc-kickstart-command-in-anaconda/)


* **Renovate**

  * *Role in MiOS:* Automated digest pinning for `image-versions.yml` and `Containerfile` ARGs
  * *Official Homepage/Repository:* [https://docs.renovatebot.com/](https://docs.renovatebot.com/)


* **GitHub Actions**

  * *Role in MiOS:* CI build/lint/sign/push pipeline
  * *Official Homepage/Repository:* [https://docs.github.com/en/actions](https://docs.github.com/en/actions)


* **GitHub Container Registry (GHCR)**

  * *Role in MiOS:* Image distribution at `ghcr.io/mios-dev/mios`
  * *Official Homepage/Repository:* [https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-container-registry](https://docs.github.com/packages/working-with-a-github-packages-registry/working-with-the-container-registry)


* **Sigstore / cosign**

  * *Role in MiOS:* Keyless OCI image signing \+ transparency log \+ attestation predicates
  * *Official Homepage/Repository:* [https://github.com/sigstore/cosign](https://github.com/sigstore/cosign)


* **syft**

  * *Role in MiOS:* CycloneDX / SPDX SBOM generation (`automation/90-generate-sbom.sh`)
  * *Official Homepage/Repository:* [https://github.com/anchore/syft](https://github.com/anchore/syft)


* **shellcheck**

  * *Role in MiOS:* Shell linter (CI gate; SC2038 fatal)
  * *Official Homepage/Repository:* [https://github.com/koalaman/shellcheck](https://github.com/koalaman/shellcheck)


* **hadolint**

  * *Role in MiOS:* Containerfile linter (CI gate)
  * *Official Homepage/Repository:* [https://github.com/hadolint/hadolint](https://github.com/hadolint/hadolint)


* **openssl (passwd \-6)**

  * *Role in MiOS:* yescrypt password hashes for BIB-injected accounts
  * *Official Homepage/Repository:* [https://www.openssl.org/](https://www.openssl.org/)

## 5\. Container runtime \+ Quadlet

* **Podman Quadlet**

  * *Role in MiOS:* systemd-native container units (`*.container`, `*.image`, `*.network`, `*.volume`) \-- the integration model for every `mios-*` service
  * *Official Homepage/Repository:* [https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)


* **Container Device Interface (CDI)**

  * *Role in MiOS:* Universal device passthrough spec (NVIDIA, AMD, Intel)
  * *Official Homepage/Repository:* [https://github.com/cncf-tags/container-device-interface](https://github.com/cncf-tags/container-device-interface)


* **containers.conf / storage.conf**

  * *Role in MiOS:* Podman client-side defaults (`usr/share/containers/`)
  * *Official Homepage/Repository:* [https://github.com/containers/common](https://github.com/containers/common)


* **containers/storage**

  * *Role in MiOS:* Podman/Buildah storage backend
  * *Official Homepage/Repository:* [https://github.com/containers/storage](https://github.com/containers/storage)


* **containers/image**

  * *Role in MiOS:* Image transport library
  * *Official Homepage/Repository:* [https://github.com/containers/image](https://github.com/containers/image)

## 6\. Local AI runtime (the canonical 'MiOS' AI endpoint)

`MIOS_AI_ENDPOINT` is served by the MiOS inference Quadlet

at `etc/containers/systemd/mios-ai.container`. All other engines below are

listed as **Day-0 portability targets**: 'MiOS' agents resolve through

`MIOS_AI_ENDPOINT` so any of these can be slotted in.

## 7\. OpenAI public API spec & standards (the surface 'MiOS' targets)

CLAUDE.md is a thin pointer to these documents; `usr/share/doc/mios/reference/api.md` tracks the served

subset. Every URL below is the source-of-truth for the named surface.

* **Structured outputs**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://platform.openai.com/docs/guides/structured-outputs](https://platform.openai.com/docs/guides/structured-outputs)


* **Embeddings**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://platform.openai.com/docs/guides/embeddings](https://platform.openai.com/docs/guides/embeddings)


* **Batch API**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://platform.openai.com/docs/guides/batch](https://platform.openai.com/docs/guides/batch)


* **Evals API**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://developers.openai.com/api/docs/guides/evals](https://developers.openai.com/api/docs/guides/evals)


* **Fine-tuning (SFT)**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://platform.openai.com/docs/guides/fine-tuning](https://platform.openai.com/docs/guides/fine-tuning)


* **Direct Preference Optimization**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://platform.openai.com/docs/guides/direct-preference-optimization](https://platform.openai.com/docs/guides/direct-preference-optimization)


* **Realtime / streaming**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://platform.openai.com/docs/guides/realtime](https://platform.openai.com/docs/guides/realtime)


* **Audio (TTS / STT)**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://platform.openai.com/docs/guides/audio](https://platform.openai.com/docs/guides/audio)


* **Images**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://platform.openai.com/docs/api-reference/images](https://platform.openai.com/docs/api-reference/images)


* **Moderation**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://platform.openai.com/docs/guides/moderation](https://platform.openai.com/docs/guides/moderation)


* **OpenAI Cookbook**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://cookbook.openai.com/](https://cookbook.openai.com/)


* **OpenAI Python SDK**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://github.com/openai/openai-python](https://github.com/openai/openai-python)


* **OpenAI Node SDK**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://github.com/openai/openai-node](https://github.com/openai/openai-node)


* **tiktoken (tokenizers)**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://github.com/openai/tiktoken](https://github.com/openai/tiktoken)


* **Migration guide (Chat Completions \-\> Responses)**

  * *Role in MiOS:*
  * *Official Homepage/Repository:* [https://developers.openai.com/api/docs/guides/migrate-to-responses](https://developers.openai.com/api/docs/guides/migrate-to-responses)

## 8\. AI / LLM tooling (referenced for KB ingestion \+ tools)

* **Model Context Protocol (MCP)**

  * *Role in MiOS:* Tool/server protocol used by Responses API and `mios-mcp.service`
  * *Official Homepage/Repository:* [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/) \-- [https://github.com/modelcontextprotocol](https://github.com/modelcontextprotocol)


* **LangChain**

  * *Role in MiOS:* Higher-level orchestration with OpenAI-compatible client
  * *Official Homepage/Repository:* [https://github.com/langchain-ai/langchain](https://github.com/langchain-ai/langchain)


* **LlamaIndex**

  * *Role in MiOS:* RAG framework
  * *Official Homepage/Repository:* [https://github.com/run-llama/llama\_index](https://github.com/run-llama/llama_index)


* **DSPy**

  * *Role in MiOS:* Programmatic prompting / compiler
  * *Official Homepage/Repository:* [https://github.com/stanfordnlp/dspy](https://github.com/stanfordnlp/dspy)


* **Outlines**

  * *Role in MiOS:* Constrained generation
  * *Official Homepage/Repository:* [https://github.com/outlines-dev/outlines](https://github.com/outlines-dev/outlines)


* **xgrammar**

  * *Role in MiOS:* vLLM grammar engine
  * *Official Homepage/Repository:* [https://github.com/mlc-ai/xgrammar](https://github.com/mlc-ai/xgrammar)


* **axolotl**

  * *Role in MiOS:* Fine-tuning trainer (consumes JSONL 'MiOS' ships)
  * *Official Homepage/Repository:* [https://github.com/OpenAccess-AI-Collective/axolotl](https://github.com/OpenAccess-AI-Collective/axolotl)


* **trl (Hugging Face)**

  * *Role in MiOS:* RLHF / DPO trainer
  * *Official Homepage/Repository:* [https://github.com/huggingface/trl](https://github.com/huggingface/trl)


* **llama-factory**

  * *Role in MiOS:* Fine-tuning toolkit
  * *Official Homepage/Repository:* [https://github.com/hiyouga/LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory)


* **MLX-LM**

  * *Role in MiOS:* Apple Silicon trainer/server
  * *Official Homepage/Repository:* [https://github.com/ml-explore/mlx-examples](https://github.com/ml-explore/mlx-examples)


* **unsloth**

  * *Role in MiOS:* Memory-efficient fine-tuning
  * *Official Homepage/Repository:* [https://github.com/unslothai/unsloth](https://github.com/unslothai/unsloth)

## 9\. Vector / RAG datastores

## 10\. Network / system services

* **NetworkManager**

  * *Role in MiOS:* Network state daemon \+ `nm-connection-editor`
  * *Official Homepage/Repository:* [https://networkmanager.dev/](https://networkmanager.dev/)


* **OpenSSH**

  * *Role in MiOS:* sshd \+ ssh client (postcheck enforces version \>= 9.6)
  * *Official Homepage/Repository:* [https://www.openssh.com/](https://www.openssh.com/)


* **chrony**

  * *Role in MiOS:* Time sync
  * *Official Homepage/Repository:* [https://chrony-project.org/](https://chrony-project.org/)


* **firewalld**

  * *Role in MiOS:* Zone-based firewall
  * *Official Homepage/Repository:* [https://firewalld.org/](https://firewalld.org/)


* **nftables**

  * *Role in MiOS:* In-kernel packet filtering
  * *Official Homepage/Repository:* [https://www.netfilter.org/projects/nftables/](https://www.netfilter.org/projects/nftables/)


* **Avahi / nss-mdns**

  * *Role in MiOS:* mDNS / `.local` resolution
  * *Official Homepage/Repository:* [https://avahi.org/](https://avahi.org/)


* **pipewire**

  * *Role in MiOS:* Audio/video routing
  * *Official Homepage/Repository:* [https://pipewire.org/](https://pipewire.org/)


* **WirePlumber**

  * *Role in MiOS:* pipewire session manager
  * *Official Homepage/Repository:* [https://gitlab.freedesktop.org/pipewire/wireplumber](https://gitlab.freedesktop.org/pipewire/wireplumber)


* **tuned**

  * *Role in MiOS:* System tunable profiles
  * *Official Homepage/Repository:* [https://github.com/redhat-performance/tuned](https://github.com/redhat-performance/tuned)


* **greenboot**

  * *Role in MiOS:* Health-checked boot rollback
  * *Official Homepage/Repository:* [https://github.com/fedora-iot/greenboot](https://github.com/fedora-iot/greenboot)


* **uupd**

  * *Role in MiOS:* Unified updater (replaces `bootc-fetch-apply-updates.timer`)
  * *Official Homepage/Repository:* [https://github.com/ublue-os/uupd](https://github.com/ublue-os/uupd)


* **bootupd**

  * *Role in MiOS:* Unified bootloader updater
  * *Official Homepage/Repository:* [https://github.com/coreos/bootupd](https://github.com/coreos/bootupd)

## 11\. Storage / cluster / source-control forge

* **Ceph (cephadm)**

  * *Role in MiOS:* Distributed storage; admin via `cephadm shell` (containerized)
  * *Official Homepage/Repository:* [https://ceph.io/](https://ceph.io/) \-- [https://docs.ceph.com/en/latest/cephadm/](https://docs.ceph.com/en/latest/cephadm/)


* **K3s**

  * *Role in MiOS:* Lightweight Kubernetes distribution
  * *Official Homepage/Repository:* [https://k3s.io/](https://k3s.io/) \-- [https://github.com/k3s-io/k3s](https://github.com/k3s-io/k3s)


* **k3s-selinux**

  * *Role in MiOS:* SELinux policy compiled in-image (`automation/19-k3s-selinux.sh`)
  * *Official Homepage/Repository:* [https://github.com/k3s-io/k3s-selinux](https://github.com/k3s-io/k3s-selinux)


* **Helm**

  * *Role in MiOS:* K8s package manager
  * *Official Homepage/Repository:* [https://helm.sh/](https://helm.sh/)


* **kubectl**

  * *Role in MiOS:* K8s CLI (symlinked from k3s binary)
  * *Official Homepage/Repository:* [https://kubernetes.io/docs/reference/kubectl/](https://kubernetes.io/docs/reference/kubectl/)


* **Pacemaker / Corosync**

  * *Role in MiOS:* HA cluster resource manager
  * *Official Homepage/Repository:* [https://clusterlabs.org/pacemaker/](https://clusterlabs.org/pacemaker/)


* **libvirt**

  * *Role in MiOS:* VM lifecycle daemon
  * *Official Homepage/Repository:* [https://libvirt.org/](https://libvirt.org/)


* **QEMU**

  * *Role in MiOS:* Machine emulator \+ KVM frontend
  * *Official Homepage/Repository:* [https://www.qemu.org/](https://www.qemu.org/)


* **KVM**

  * *Role in MiOS:* Linux kernel hypervisor
  * *Official Homepage/Repository:* [https://www.linux-kvm.org/](https://www.linux-kvm.org/)


* **virtiofs / virtio-net / virtio-blk**

  * *Role in MiOS:* Paravirt host\<-\>guest IO
  * *Official Homepage/Repository:* [https://virtio-fs.gitlab.io/](https://virtio-fs.gitlab.io/) \-- [https://wiki.libvirt.org/Virtio.html](https://wiki.libvirt.org/Virtio.html)


* **virtio-win**

  * *Role in MiOS:* Windows-guest paravirt drivers
  * *Official Homepage/Repository:* [https://github.com/virtio-win/virtio-win-pkg-automation](https://github.com/virtio-win/virtio-win-pkg-automation)


* **virt-viewer / virt-manager**

  * *Role in MiOS:* VM consoles \+ GUI
  * *Official Homepage/Repository:* [https://gitlab.com/virt-viewer/virt-viewer](https://gitlab.com/virt-viewer/virt-viewer) \-- [https://virt-manager.org/](https://virt-manager.org/)


* **FreeRDP**

  * *Role in MiOS:* RDP client used for `mios-guacamole` integration
  * *Official Homepage/Repository:* [https://www.freerdp.com/](https://www.freerdp.com/)


* **Forgejo**

  * *Role in MiOS:* Self-hosted Git forge served by `mios-forge.container` (HTTP 3000, git+ssh 2222); SQLite-default; matches MiOS-DEV's resource budget without a separate PostgreSQL
  * *Official Homepage/Repository:* [https://forgejo.org/](https://forgejo.org/) \-- [https://codeberg.org/forgejo/forgejo](https://codeberg.org/forgejo/forgejo)


* **Forgejo Runner**

  * *Role in MiOS:* GitHub-Actions-compatible CI runner that authenticates against `mios-forge` and executes `.github/workflows/` / `.forgejo/workflows/` jobs in ephemeral Podman containers
  * *Official Homepage/Repository:* [https://code.forgejo.org/forgejo/runner](https://code.forgejo.org/forgejo/runner) \-- [https://forgejo.org/docs/latest/admin/actions/](https://forgejo.org/docs/latest/admin/actions/)


* **ActivityPub / ForgeFed**

  * *Role in MiOS:* Federation protocol for Forgejo: cross-instance issue, PR, and star without surrendering source-code custody
  * *Official Homepage/Repository:* [https://www.w3.org/TR/activitypub/](https://www.w3.org/TR/activitypub/) \-- [https://forgefed.org/](https://forgefed.org/)

## 12\. Desktop / graphics

* **GNOME (Mutter, GTK, libadwaita)**

  * *Role in MiOS:* Default Wayland session
  * *Official Homepage/Repository:* [https://www.gnome.org/](https://www.gnome.org/)


* **GDM**

  * *Role in MiOS:* GNOME Display Manager
  * *Official Homepage/Repository:* [https://gitlab.gnome.org/GNOME/gdm](https://gitlab.gnome.org/GNOME/gdm)


* **Cockpit**

  * *Role in MiOS:* Web admin panel (postcheck enforces `LoginTo = false` and version \>= 361\)
  * *Official Homepage/Repository:* [https://cockpit-project.org/](https://cockpit-project.org/)


* **Mesa**

  * *Role in MiOS:* OpenGL / Vulkan / EGL userspace
  * *Official Homepage/Repository:* [https://www.mesa3d.org/](https://www.mesa3d.org/)


* **Wayland**

  * *Role in MiOS:* Display server protocol
  * *Official Homepage/Repository:* [https://wayland.freedesktop.org/](https://wayland.freedesktop.org/)


* **Phosh (optional)**

  * *Role in MiOS:* Mobile/touch shell
  * *Official Homepage/Repository:* [https://phosh.mobi/](https://phosh.mobi/)


* **Flatpak**

  * *Role in MiOS:* App sandboxing \+ Flathub apps
  * *Official Homepage/Repository:* [https://flatpak.org/](https://flatpak.org/) \-- [https://flathub.org/](https://flathub.org/)


* **Geist Font**

  * *Role in MiOS:* UI typography
  * *Official Homepage/Repository:* [https://github.com/vercel/geist-font](https://github.com/vercel/geist-font)


* **Bazaar (Flatpak)**

  * *Role in MiOS:* App store front-end
  * *Official Homepage/Repository:* [https://github.com/kolunmi/bazaar](https://github.com/kolunmi/bazaar)


* **Flatseal (Flatpak)**

  * *Role in MiOS:* Per-app permission editor
  * *Official Homepage/Repository:* [https://github.com/tchx84/Flatseal](https://github.com/tchx84/Flatseal)


* **Extension Manager (Flatpak)**

  * *Role in MiOS:* GNOME Shell extensions UI
  * *Official Homepage/Repository:* [https://github.com/mjakeman/extension-manager](https://github.com/mjakeman/extension-manager)


* **GNOME Epiphany**

  * *Role in MiOS:* GNOME Web (Flatpak default)
  * *Official Homepage/Repository:* [https://gitlab.gnome.org/GNOME/epiphany](https://gitlab.gnome.org/GNOME/epiphany)

## 13\. Security stack

* **SELinux**

  * *Role in MiOS:* Mandatory access control
  * *Official Homepage/Repository:* [https://github.com/SELinuxProject/selinux](https://github.com/SELinuxProject/selinux)


* **selinux-policy-targeted**

  * *Role in MiOS:* Active policy module
  * *Official Homepage/Repository:* [https://github.com/fedora-selinux/selinux-policy](https://github.com/fedora-selinux/selinux-policy)


* **fapolicyd**

  * *Role in MiOS:* Application allowlisting
  * *Official Homepage/Repository:* [https://github.com/linux-application-whitelisting/fapolicyd](https://github.com/linux-application-whitelisting/fapolicyd)


* **USBGuard**

  * *Role in MiOS:* USB device authorization
  * *Official Homepage/Repository:* [https://usbguard.github.io/](https://usbguard.github.io/)


* **CrowdSec**

  * *Role in MiOS:* Behavioral IDS / collaborative blocklists
  * *Official Homepage/Repository:* [https://www.crowdsec.net/](https://www.crowdsec.net/) \-- [https://github.com/crowdsecurity/crowdsec](https://github.com/crowdsecurity/crowdsec)


* **AIDE**

  * *Role in MiOS:* File integrity monitor
  * *Official Homepage/Repository:* [https://aide.github.io/](https://aide.github.io/)


* **OpenSCAP / scap-security-guide**

  * *Role in MiOS:* Compliance scanning
  * *Official Homepage/Repository:* [https://www.open-scap.org/](https://www.open-scap.org/) \-- [https://github.com/ComplianceAsCode/content](https://github.com/ComplianceAsCode/content)


* **audit (Linux Audit)**

  * *Role in MiOS:* auditd / ausearch / aureport
  * *Official Homepage/Repository:* [https://github.com/linux-audit/audit-userspace](https://github.com/linux-audit/audit-userspace)


* **libpwquality**

  * *Role in MiOS:* Password policy enforcement
  * *Official Homepage/Repository:* [https://github.com/libpwquality/libpwquality](https://github.com/libpwquality/libpwquality)


* **SecureBlue**

  * *Role in MiOS:* Hardening reference profile \+ auditing
  * *Official Homepage/Repository:* [https://github.com/secureblue/secureblue](https://github.com/secureblue/secureblue)

## 14\. GPU stacks

* **NVIDIA**

  * *Role in MiOS:* open kernel modules (Turing+) on `:stable-nvidia`; LTS proprietary 580 on `:stable-nvidia-lts`; `nvidia-container-toolkit`, `nvidia-persistenced`, `nvidia-settings`, CUDA, akmods
  * *Official Homepage/Repository:* [https://www.nvidia.com/](https://www.nvidia.com/) \-- [https://github.com/NVIDIA/nvidia-container-toolkit](https://github.com/NVIDIA/nvidia-container-toolkit) \-- [https://rpmfusion.org/Packaging/KernelModules/Akmods](https://rpmfusion.org/Packaging/KernelModules/Akmods)


* **Intel**

  * *Role in MiOS:* Xe / i915 kernel \+ mesa-vulkan-drivers \+ `intel-compute-runtime` (oneAPI)
  * *Official Homepage/Repository:* [https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html](https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html)


* **AMD**

  * *Role in MiOS:* amdgpu kernel \+ Mesa RADV \+ ROCm/HIP runtime
  * *Official Homepage/Repository:* [https://rocm.docs.amd.com/](https://rocm.docs.amd.com/)


* **Looking Glass**

  * *Role in MiOS:* Low-latency VFIO display via shared memory
  * *Official Homepage/Repository:* [https://looking-glass.io/](https://looking-glass.io/)


* **KVMFR**

  * *Role in MiOS:* Looking Glass kernel module (built in-image via `automation/52-bake-kvmfr.sh`)
  * *Official Homepage/Repository:* [https://looking-glass.io/docs/B7/install\_kvmfr/](https://looking-glass.io/docs/B7/install_kvmfr/)

## 15\. Virtualization / VFIO

* **VFIO-PCI**

  * *Role in MiOS:* PCI passthrough in-kernel
  * *Official Homepage/Repository:* [https://docs.kernel.org/driver-api/vfio.html](https://docs.kernel.org/driver-api/vfio.html)


* **qemu-device-display-virtio-gpu**

  * *Role in MiOS:* virtio-gpu accelerated display
  * *Official Homepage/Repository:* [https://wiki.qemu.org/Features/VirtIO](https://wiki.qemu.org/Features/VirtIO)


* **Waydroid**

  * *Role in MiOS:* Android-in-LXC for Wayland
  * *Official Homepage/Repository:* [https://waydro.id/](https://waydro.id/) \-- [https://github.com/waydroid](https://github.com/waydroid)

## 16\. Gaming / Windows compatibility

* **Steam**

  * *Role in MiOS:* Game launcher (user-installed via flatpak/repo per profile)
  * *Official Homepage/Repository:* [https://store.steampowered.com/about/](https://store.steampowered.com/about/)


* **Wine**

  * *Role in MiOS:* Windows API translation layer
  * *Official Homepage/Repository:* [https://www.winehq.org/](https://www.winehq.org/)


* **DXVK**

  * *Role in MiOS:* Direct3D \-\> Vulkan translation
  * *Official Homepage/Repository:* [https://github.com/doitsujin/dxvk](https://github.com/doitsujin/dxvk)


* **Gamescope**

  * *Role in MiOS:* Micro-compositor for game scaling
  * *Official Homepage/Repository:* [https://github.com/ValveSoftware/gamescope](https://github.com/ValveSoftware/gamescope)


* **MangoHud**

  * *Role in MiOS:* In-game performance overlay
  * *Official Homepage/Repository:* [https://github.com/flightlessmango/MangoHud](https://github.com/flightlessmango/MangoHud)


* **steam-devices**

  * *Role in MiOS:* udev rules for controllers
  * *Official Homepage/Repository:* [https://gitlab.com/evlaV/steam-devices](https://gitlab.com/evlaV/steam-devices)

## 17\. Knowledge / agent ingestion conventions

* **agents.md standard**

  * *Role in MiOS:* `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` follow this convention
  * *Official Homepage/Repository:* [https://agents.md/](https://agents.md/)


* **llms.txt standard**

  * *Role in MiOS:* `llms.txt` and `llms-full.txt` at repo root
  * *Official Homepage/Repository:* [https://llmstxt.org/](https://llmstxt.org/)


* **Renovate customManager regex**

  * *Role in MiOS:* `image-versions.yml` digest pinning
  * *Official Homepage/Repository:* [https://docs.renovatebot.com/modules/manager/regex/](https://docs.renovatebot.com/modules/manager/regex/)

## 18\. Reference / inspiration distros (for design decisions)

* **Universal Blue (umbrella)**

  * *Role in MiOS:* Direct upstream of the base image; Quadlet-first patterns
  * *Official Homepage/Repository:* [https://github.com/ublue-os](https://github.com/ublue-os)


* **Bluefin / Aurora / Bazzite**

  * *Role in MiOS:* Same family, different desktop targets
  * *Official Homepage/Repository:* [https://github.com/ublue-os/bluefin](https://github.com/ublue-os/bluefin) \-- [https://github.com/ublue-os/aurora](https://github.com/ublue-os/aurora) \-- [https://github.com/ublue-os/bazzite](https://github.com/ublue-os/bazzite)


* **Fedora Silverblue / Kinoite**

  * *Role in MiOS:* Original immutable Fedora workstations (rpm-ostree)
  * *Official Homepage/Repository:* [https://fedoraproject.org/silverblue/](https://fedoraproject.org/silverblue/) \-- [https://fedoraproject.org/kinoite/](https://fedoraproject.org/kinoite/)


* **CoreOS Layering / rpm-ostree**

  * *Role in MiOS:* Substrate for ostree-based atomic upgrades
  * *Official Homepage/Repository:* [https://github.com/coreos/rpm-ostree](https://github.com/coreos/rpm-ostree)


* **SecureBlue**

  * *Role in MiOS:* Hardening profile reference
  * *Official Homepage/Repository:* [https://github.com/secureblue/secureblue](https://github.com/secureblue/secureblue)


* **Talos**

  * *Role in MiOS:* API-driven Kubernetes-only OS (alt path, not chosen)
  * *Official Homepage/Repository:* [https://www.talos.dev/](https://www.talos.dev/)


* **Flatcar**

  * *Role in MiOS:* Container Linux successor (alt path, not chosen)
  * *Official Homepage/Repository:* [https://www.flatcar.org/](https://www.flatcar.org/)


* **NixOS**

  * *Role in MiOS:* Declarative comparison (different paradigm)
  * *Official Homepage/Repository:* [https://nixos.org/](https://nixos.org/)


* **Vanilla OS**

  * *Role in MiOS:* Image-based Ubuntu derivative (sibling concept)
  * *Official Homepage/Repository:* [https://vanillaos.org/](https://vanillaos.org/)

## 20\. Internal repo files referenced as canonical sources

These are 'MiOS'-internal files that other documents and code refer to as

the source of truth for a given concern. When in doubt, these win:

* **usr/share/mios/ai/INDEX.md**

  * *Role in MiOS:* Architectural laws \+ API surface index
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/INDEX.md](https://github.com/mios-dev/MiOS/blob/main/INDEX.md)


* **usr/share/doc/mios/concepts/architecture.md**

  * *Role in MiOS:* FHS layout \+ hardware model
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/ARCHITECTURE.md](https://github.com/mios-dev/MiOS/blob/main/ARCHITECTURE.md)


* **usr/share/doc/mios/guides/engineering.md**

  * *Role in MiOS:* Build \+ lint \+ shell conventions
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/ENGINEERING.md](https://github.com/mios-dev/MiOS/blob/main/ENGINEERING.md)


* **usr/share/doc/mios/guides/self-build.md**

  * *Role in MiOS:* Build modes (just / Windows orchestrator / BIB)
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/SELF-BUILD.md](https://github.com/mios-dev/MiOS/blob/main/SELF-BUILD.md)


* **usr/share/doc/mios/guides/deploy.md**

  * *Role in MiOS:* Day-2 lifecycle
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/DEPLOY.md](https://github.com/mios-dev/MiOS/blob/main/DEPLOY.md)


* **SECURITY.md**

  * *Role in MiOS:* Security posture and hardening kargs
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/SECURITY.md](https://github.com/mios-dev/MiOS/blob/main/SECURITY.md)


* **CONTRIBUTING.md**

  * *Role in MiOS:* Contributor conventions
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/CONTRIBUTING.md](https://github.com/mios-dev/MiOS/blob/main/CONTRIBUTING.md)


* **usr/share/doc/mios/reference/licenses.md**

  * *Role in MiOS:* Component license inventory
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/LICENSES.md](https://github.com/mios-dev/MiOS/blob/main/LICENSES.md)


* **usr/share/doc/mios/reference/sources.md**

  * *Role in MiOS:* KB-grade citation tracking
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/SOURCES.md](https://github.com/mios-dev/MiOS/blob/main/SOURCES.md)


* **usr/share/doc/mios/reference/api.md**

  * *Role in MiOS:* OpenAI surface trace \+ Build/Architecture appendix
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/API.md](https://github.com/mios-dev/MiOS/blob/main/API.md)


* **CLAUDE.md**

  * *Role in MiOS:* Agent-identity pointer to OpenAI docs \+ standards
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/CLAUDE.md](https://github.com/mios-dev/MiOS/blob/main/CLAUDE.md)


* **AGENTS.md / GEMINI.md**

  * *Role in MiOS:* Sibling agent-identity pointers
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/AGENTS.md](https://github.com/mios-dev/MiOS/blob/main/AGENTS.md) \-- [https://github.com/mios-dev/MiOS/blob/main/GEMINI.md](https://github.com/mios-dev/MiOS/blob/main/GEMINI.md)


* **usr/share/mios/mios.toml**

  * *Role in MiOS:* Single source of truth for every RPM (`[packages.<section>].pkgs`)
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/usr/share/mios/mios.toml](https://github.com/mios-dev/MiOS/blob/main/usr/share/mios/mios.toml)


* **usr/share/doc/mios/reference/PACKAGES.md**

  * *Role in MiOS:* Human-readable companion documentation for the package surface
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/usr/share/doc/mios/reference/PACKAGES.md](https://github.com/mios-dev/MiOS/blob/main/usr/share/doc/mios/reference/PACKAGES.md)


* **usr/share/mios/ai/system.md**

  * *Role in MiOS:* Canonical agent system prompt (image-baked)
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/usr/share/mios/ai/system.md](https://github.com/mios-dev/MiOS/blob/main/usr/share/mios/ai/system.md)


* **usr/share/mios/ai/v1/models.json**

  * *Role in MiOS:* Local `/v1/models` catalog
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/usr/share/mios/ai/v1/models.json](https://github.com/mios-dev/MiOS/blob/main/usr/share/mios/ai/v1/models.json)


* **usr/share/mios/ai/v1/mcp.json**

  * *Role in MiOS:* MCP server registry
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/usr/share/mios/ai/v1/mcp.json](https://github.com/mios-dev/MiOS/blob/main/usr/share/mios/ai/v1/mcp.json)


* **image-versions.yml**

  * *Role in MiOS:* Renovate-tracked base-image digests
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/image-versions.yml](https://github.com/mios-dev/MiOS/blob/main/image-versions.yml)


* **renovate.json**

  * *Role in MiOS:* Renovate config
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/renovate.json](https://github.com/mios-dev/MiOS/blob/main/renovate.json)


* **.github/workflows/mios-ci.yml**

  * *Role in MiOS:* CI pipeline
  * *Official Homepage/Repository:* [https://github.com/mios-dev/MiOS/blob/main/.github/workflows/mios-ci.yml](https://github.com/mios-dev/MiOS/blob/main/.github/workflows/mios-ci.yml)

## 21\. Bootstrap repo

* **mios-bootstrap (repo)**

  * *Role in MiOS:* Phase-0 preflight \+ identity, Phase-1 Total Root Merge, Phase-4 reboot
  * *Official Homepage/Repository:* [https://github.com/mios-dev/mios-bootstrap](https://github.com/mios-dev/mios-bootstrap)


* **install.sh / install.ps1**

  * *Role in MiOS:* Cross-platform installers
  * *Official Homepage/Repository:* [https://github.com/mios-dev/mios-bootstrap/blob/main/install.sh](https://github.com/mios-dev/mios-bootstrap/blob/main/install.sh) \-- [https://github.com/mios-dev/mios-bootstrap/blob/main/install.ps1](https://github.com/mios-dev/mios-bootstrap/blob/main/install.ps1)


* **bootstrap.sh / bootstrap.ps1**

  * *Role in MiOS:* First-run bootstrappers
  * *Official Homepage/Repository:* [https://github.com/mios-dev/mios-bootstrap/blob/main/bootstrap.sh](https://github.com/mios-dev/mios-bootstrap/blob/main/bootstrap.sh) \-- [https://github.com/mios-dev/mios-bootstrap/blob/main/bootstrap.ps1](https://github.com/mios-dev/mios-bootstrap/blob/main/bootstrap.ps1)


* **.env.mios**

  * *Role in MiOS:* User-runtime env defaults (mirrored into MiOS root)
  * *Official Homepage/Repository:* [https://github.com/mios-dev/mios-bootstrap/blob/main/.env.mios](https://github.com/mios-dev/mios-bootstrap/blob/main/.env.mios)


* **etc/skel/.config/mios/**

  * *Role in MiOS:* User dotfile templates seeded on `useradd -m`
  * *Official Homepage/Repository:* [https://github.com/mios-dev/mios-bootstrap/tree/main/etc/skel](https://github.com/mios-dev/mios-bootstrap/tree/main/etc/skel)


* **image-versions.yml**

  * *Role in MiOS:* Mirror of base-image digest pins
  * *Official Homepage/Repository:* [https://github.com/mios-dev/mios-bootstrap/blob/main/image-versions.yml](https://github.com/mios-dev/mios-bootstrap/blob/main/image-versions.yml)

## 22\. AI agents used in this project (un-labeled, OpenAI-API-shaped)

'MiOS' treats every editor/CLI agent as an *OpenAI-API-compatible client*

rather than as a vendor brand. The agent-identity files in this repo

(`CLAUDE.md`, `GEMINI.md`, `AGENTS.md`, `.clinerules`, `.cursorrules`,

`.github/ai-instructions.md`) exist for tooling discovery only \-- their

filenames are conventions the upstream tools look for; their contents

are vendor-neutral pointers to the same canonical prompt.

**Architectural Law 5 \-- UNIFIED-AI-REDIRECTS.** Every client below

resolves through `MIOS_AI_ENDPOINT`, an

OpenAI-public-API-compatible surface served by

`etc/containers/systemd/mios-ai.container`. Vendor-native URLs

(`api.openai.com`, `api.anthropic.com`,

`generativelanguage.googleapis.com`, `api.cline.bot`, `api.cursor.com`,

`api.githubcopilot.com`, etc.) are forbidden in the deployed image and

fail audit. Differences between clients are presentation-layer only.

**OpenAI patterns adopted across every client:**

Chat Completions (`POST /v1/chat/completions`), Responses

(`POST /v1/responses`), function calling / tool-use schema, structured

outputs (`response_format: json_schema`, `strict: true`), embeddings

(`POST /v1/embeddings`), MCP tool invocation, model discovery

(`GET /v1/models`), JSONL training format, and `Authorization: Bearer ...`

auth. Each surface is anchored in section 7 above.

The discovery files below are listed by **filename convention** (what the

tool looks for) and **client wiring** (how it resolves to the OpenAI-shaped

endpoint). Vendor names appear only as the upstream link target so a

reader can reach the tool's docs; they are not load-bearing in any

configuration in this repo.

* **CLAUDE.md, .claude/settings.local.json**

  * *Role in MiOS:* A CLI agent that auto-loads `CLAUDE.md` from cwd
  * *Official Homepage/Repository:* N/A


* **.github/ai-instructions.md**

  * *Role in MiOS:* Editor assistants that read `.github/` instruction files
  * *Official Homepage/Repository:* N/A


* **.clinerules**

  * *Role in MiOS:* A VS Code agent that reads `.clinerules` from project root
  * *Official Homepage/Repository:* N/A


* **.cursorrules**

  * *Role in MiOS:* An editor that reads `.cursorrules` from project root
  * *Official Homepage/Repository:* N/A


* **GEMINI.md**

  * *Role in MiOS:* A CLI that auto-loads `GEMINI.md` from cwd
  * *Official Homepage/Repository:* N/A


* **AGENTS.md (agents.md standard)**

  * *Role in MiOS:* Any agents.md-aware client (Codex CLI, etc.)
  * *Official Homepage/Repository:* N/A

Aliasing files that all point to the same canonical prompt:

### 'MiOS'-internal agent surfaces (runtime, not editor-time)

### `USER` variable resolution at build entry

Every `USER` token in this codebase is a *placeholder*, not a hardcoded

identity. Resolution happens at install/build entry:

The only other user-related identifiers permitted in the codebase are

the `MiOS` brand and the `mios` default account name; both are project

conventions, not personal identities.
