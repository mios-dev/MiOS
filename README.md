<!-- AI-hint: Repository entry point for the MiOS system FHS overlay, its SSOT, image build pipeline, local AI interface, deployment shapes, and documented scope. AI-related: /usr/share/mios/mios.toml, /usr/libexec/mios/mios-build-driver, /usr/share/mios/ai/system.md, mios-bootstrap, MiOS-DEV. -->
# MiOS

MiOS (pronounced **MyOS**, “My Operating System”) is an Apache-2.0 research project. Its deliverable is a rebuildable Linux operating system blueprint: a Fedora bootc/OCI image, a local agent runtime, and the source and checks needed to regenerate that image. The [architectural thesis](usr/share/doc/mios/manual/thesis.md) defines four linked pillars: an immutable image, one local AI front door, a repository that mirrors the target root filesystem, and configuration projected from one source of truth.

This is the **system repository**. Its `usr/`, `etc/`, `var/`, and other FHS paths describe the filesystem baked into the image. [mios-bootstrap](https://github.com/mios-dev/mios-bootstrap) owns the interactive installer and operator-editable layer. MiOS-DEV is the build environment; Windows provisioning hands the build to MiOS-DEV.

> MiOS is an active proof of concept. WSL2 and development VM runs are the observed environments described by the [thesis](usr/share/doc/mios/manual/thesis.md). Bare-metal, blade fleet, and edge mesh shapes are design targets under development, not claims of a completed deployment.

## System shape

```text
mios-bootstrap installer + operator selections
    -> Total Root Merge with this FHS overlay
    -> MiOS-DEV build pipeline
    -> bootc/OCI image
    -> WSL2, VM, disk, or installer artifact
    -> bootc upgrade / rollback on a bootc host
```

The image includes a desktop, virtualization and GPU support, and a local AI stack. The build uses [Containerfile](Containerfile) and numbered [automation](automation/) stages. The runtime image owns its static files in `/usr`; `/etc` holds host overrides, and `/var` persists across bootc upgrades. A bootc image is the unit of update and rollback.

The planned MiOS-Metal architecture separates a bare-metal Blade from the MiOS guest. Each Blade owns its boot chain, TPM, NICs, radios, mesh access point, and hardware routing; the MiOS image runs as a NIC-less guest. Fleet roles distinguish services on every Blade, singleton services across Blades, and guest-plane services. See the [MiOS-Metal architecture](usr/share/doc/mios/concepts/mios-metal-architecture.md) for design details and limits. Whole-device VFIO passthrough is the driver-free host GPU path; mediated GPU sharing requires a host driver and explicit opt-in.

## One configuration source

[**`usr/share/mios/mios.toml`**](usr/share/mios/mios.toml) is the singular vendor SSOT for packages, repositories, images, ports, services, identity, build resources, and the shared theme. Operator choices are made through the local [HTML configurator](usr/share/mios/configurator/mios.html) and layered above vendor values. Higher nonempty user values win over host and vendor defaults. Generated files must be projections of the resolved TOML rather than independent settings.

The Windows bootstrap reads `[bootstrap.dev_vm.host_reserve]` for MiOS-DEV resources. Its current default reserves half of physical RAM for Windows, with an 8 GB minimum reserve; the generated WSL setting is recalculated during bootstrap. Terminal colors, fonts, geometry, and application launch behavior likewise derive from the theme and terminal sections of the same TOML.

The root [`.mios` guide](.mios/README.md) explains workflow dotfolders. They stage sources and generated work; they are not alternate runtime FHS locations.

## Local AI contract

Every OpenAI-compatible client resolves through `MIOS_AI_ENDPOINT`, `MIOS_AI_MODEL`, and `MIOS_AI_KEY`. The supported public shapes include `/v1/chat/completions`, `/v1/responses`, `/v1/embeddings`, and `/v1/models`, with function calls and MCP tools. The [agent contract](usr/share/mios/ai/INDEX.md) and [API reference](usr/share/doc/mios/reference/api.md) describe the local interface.

- `mios-llm-light` is the primary local inference and embeddings lane, with model selection in [`llama-swap.yaml`](usr/share/mios/llamacpp/llama-swap.yaml).
- Heavy GPU inference lanes are gated by the resolved configuration.
- Agent routing and tool work run through agent-pipe and the local gateway; PostgreSQL with pgvector holds durable agent memory.
- MCP exposes tools, while A2A connects agents. Service ports and enablement come from `mios.toml`.

No hosted model account is required for the local runtime. Actual acceleration and enabled services depend on the host hardware and operator selections.

## Build and installation

### Windows entry

The documented bootstrap entry is:

```text
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1 | iex"
```

The installer performs Windows provisioning, fetches the current repositories and full system TOML, and hands the build to MiOS-DEV. It is an interactive system installer that can repartition the selected data disk. Read the [bootstrap installation guide](https://github.com/mios-dev/mios-bootstrap/blob/main/usr/share/doc/mios-bootstrap/guides/bootstrap_install.md) for the current phase model, acknowledgement gate, TOML edit and import flow, monitor, and deployment artifacts.

The bootstrap repository's `field/` component owns live and USB media staging through `MiOS-Field`. Its shared staging implementation validates real OCI manifests, blobs, and filesystem layers before marking large media ready. The retired `cat/` launcher paths are no longer an installation entry.

### Linux development build

From a checkout on a suitable Linux builder:

```bash
git clone https://github.com/mios-dev/MiOS.git
cd MiOS
just preflight
just build
```

[`Justfile`](Justfile) also defines `iso`, `raw`, `qcow2`, `vhdx`, and `wsl2` artifact targets. MiOS-DEV is the canonical environment for build operations in the Windows bootstrap path. `just --list` shows the local targets; [self-build](usr/share/doc/mios/guides/self-build.md) describes their dependencies and outputs.

For an existing bootc-compatible installation, [deployment guidance](usr/share/doc/mios/guides/deploy.md) covers image selection, `bootc switch`, upgrades, and rollback. Do not treat a design target as a verified artifact: check the build log and postchecks for the selected image.

## Repository rules

The 16-law registry in [`mios.toml`](usr/share/mios/mios.toml) and its build gates govern contributions. The first six laws define the core image and runtime boundaries:

1. Static system configuration belongs under `/usr`; `/etc` is for overrides.
2. Persistent `/var` paths are declared through tmpfiles, not created during the image build.
3. Quadlet images are bound into the bootc image and units run without unnecessary privilege.
4. The final image must pass `bootc container lint`.
5. AI clients use the one local OpenAI-compatible endpoint.
6. Operator-tunable values originate in `mios.toml`; generated projections must stay in sync.

This repo owns the system overlay, `Containerfile`, automation, systemd and Quadlet units. The installer repo owns its interactive entry scripts and user-editable layer. Avoid tracking the same runtime file independently in both repositories.

## Documentation

| Start here | Purpose |
| --- | --- |
| [Thesis](usr/share/doc/mios/manual/thesis.md) | Four pillars and observed versus designed scope |
| [Architecture](usr/share/doc/mios/concepts/architecture.md) | System layout and component boundaries |
| [Installation guide](usr/share/doc/mios/manual/ch02-installation-and-deployment.md) | Day-0 and first-boot overview |
| [Engineering guide](usr/share/doc/mios/guides/engineering.md) | Build pipeline conventions |
| [Deploy guide](usr/share/doc/mios/guides/deploy.md) | Image lifecycle |
| [AI contract](usr/share/mios/ai/INDEX.md) | Local agent and endpoint rules |
| [Contributing](CONTRIBUTING.md) | Source and review conventions |
| [Agreements](AGREEMENTS.md) | Project acknowledgement and component attribution |

The version is recorded in [`VERSION`](VERSION). MiOS and its deployment shapes remain under active development. Component licenses and upstream credits are recorded in the [license catalog](usr/share/doc/mios/reference/licenses.md) and [credits](usr/share/doc/mios/reference/credits.md).
