<!-- AI-hint: Windows build guide for MiOS — how to compile the MiOS OCI image on Windows with Docker Desktop (WSL2 backend) and convert it to a bootable VHDX (Hyper-V), qcow2, raw, or WSL2 artifact via bootc-image-builder. Entry point is tools/windows/Build-MiOS.ps1; output of the build is the same immutable image consumed by the bootc lifecycle.
     AI-related: mios-dev, mios-bib, Build-MiOS.ps1, Containerfile, mios.toml -->
# MiOS — Windows Build Guide

## Purpose

MiOS is one system built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image — boot it,
`bootc upgrade` it like a `git pull`, `bootc rollback` it like a Ctrl-Z) that is
*also* a **local, self-replicating, agentic AI operating system**. The same image
ships GNOME/Wayland, GPU via CDI, KVM/libvirt, and a one-node k3s+Ceph cluster
path *and* a full local agent stack behind one OpenAI-compatible endpoint
(`mios-agent-pipe` orchestration → MiOS-Hermes gateway → pgvector memory →
MCP/A2A federation, fed by the local inference lanes).

This guide covers **one slice of the whole: producing that image on a Windows
host.** The build pipeline assembles the OCI image; this script wraps it for
Windows (Docker Desktop + WSL2) and then cuts a bootable disk artifact from it
with bootc-image-builder. Whatever artifact you produce here — VHDX, qcow2, raw,
or WSL2 — is the *same single image* the bootc lifecycle later carries forward on
the running host. Build it once; the host upgrades and rolls it back atomically.

**Audience:** anyone building MiOS locally on Windows. **Outcome:** a bootable
MiOS image you can import into Hyper-V (or run under WSL2).

The entry point is [`tools/windows/Build-MiOS.ps1`](Build-MiOS.ps1).

---

## Prerequisites

| Tool | Where to get |
|------|-------------|
| Docker Desktop (WSL2 backend) | <https://www.docker.com/products/docker-desktop/> |
| Git for Windows | <https://git-scm.com/download/win> |
| PowerShell 5.1+ | Built-in on Windows 10/11 |
| (Optional) Hyper-V | Windows 10/11 Pro — enable in "Turn Windows features on or off" |

The script runs a preflight that fails fast if `docker` is missing or the daemon
is down, and warns if Docker Desktop is not on the WSL2 backend (builds are
slower without it).

---

## 1. Clone the repo

The repo root **is** the deployed system root: `usr/`, `etc/`, `srv/`, `var/`
mirror exactly where files land on a booted host, and the `Containerfile` bakes
them into the image. Cloning the repo is cloning the OS source.

```powershell
git clone https://github.com/mios-dev/MiOS.git
cd MiOS
```

If you need to authenticate with a token:

```powershell
git clone https://mios-dev:<YOUR_GITHUB_TOKEN>@github.com/mios-dev/MiOS.git
cd MiOS
```

---

## 2. Set up environment variables

Everything operator-tunable — packages, ports, AI lanes, services, account and
hostname baked into the image — flows from one config file, `mios.toml`. On the
Windows side the build reads `~\.config\mios\mios.toml` automatically (with a
fallback to a legacy `env.toml`). The vendor schema lives at
`usr/share/mios/mios.toml`.

```toml
# Flat MIOS_* keys are read directly by Build-MiOS.ps1; sectioned keys ([user],
# [image], …) are read by tools/lib/userenv.sh on the Linux side.
MIOS_USER_PASSWORD_HASH = "$6$..."   # openssl passwd -6 yourpassword
MIOS_SSH_PUBKEY         = "ssh-ed25519 AAAA..."

[user]
name     = "mios"
hostname = "mios"
```

`MIOS_USER_PASSWORD_HASH` is required for any disk-image build (qcow2/vhdx/raw);
the script prompts for it if unset. `MIOS_SSH_PUBKEY` is optional (Enter to skip).

Or export them in your PowerShell session:

```powershell
$env:MIOS_USER_PASSWORD_HASH = (openssl passwd -6 yourpassword)
$env:MIOS_SSH_PUBKEY         = Get-Content "$HOME\.ssh\id_ed25519.pub"
```

---

## 3. Build

The build does two things: (1) `docker build` assembles the MiOS OCI image from
the `Containerfile` (whose final step is `bootc container lint` — Architectural
Law 4, fail = fail the build); (2) bootc-image-builder converts that image into a
bootable disk artifact.

```powershell
# Full build → VHDX (default output format)
.\tools\windows\Build-MiOS.ps1

# Build only the OCI image (no disk conversion)
.\tools\windows\Build-MiOS.ps1 -SkipBib

# Other output formats
.\tools\windows\Build-MiOS.ps1 -OutputFormat qcow2   # QEMU/KVM
.\tools\windows\Build-MiOS.ps1 -OutputFormat wsl2    # WSL2 tarball
.\tools\windows\Build-MiOS.ps1 -OutputFormat raw     # Raw disk image

# Override the local image tag (default: mios:local)
.\tools\windows\Build-MiOS.ps1 -Tag mios:dev
```

Disk artifacts land in `.\output\` (for VHDX, `.\output\disk.vhdx`). The
OutputFormat maps to a bootc-image-builder `--type`: `vhdx` → `vhd` (renamed to
`.vhdx` afterward), `raw` → `raw`, `qcow2` → `qcow2`, `wsl2` → `wsl2`.

> The image you produce here is the deliverable. What it *contains* — the inference
> lanes (`mios-llm-light` on `:11450` as the primary llama.cpp engine behind the
> upstream llama-swap proxy,
> serving everyday models, the `mios-opencode` coder model, and embeddings via
> `nomic-embed-text`; the gated heavy lanes `mios-llm-heavy` SGLang `:11441` and
> `mios-llm-heavy-alt` vLLM), the agent stack (`mios-agent-pipe` `:8640`,
> MiOS-Hermes `:8642`, OWUI `:3030`), and the PostgreSQL+pgvector datastore
> (`mios-pgvector` `:5432`) — is all baked in as bound images. You don't configure
> any of that here; you build the image and the running host stands it up.

---

## 4. Import into Hyper-V

```powershell
New-VM `
  -Name 'MiOS' `
  -BootDevice VHD `
  -VHDPath ".\output\disk.vhdx" `
  -Generation 2 `
  -MemoryStartupBytes 4GB

# Enable Secure Boot with Microsoft UEFI CA (required for bootc/GRUB)
Set-VMFirmware -VMName 'MiOS' -SecureBootTemplate MicrosoftUEFICertificateAuthority

# Optional: Enable Enhanced Session (clipboard/audio/USB redirect)
Set-VMHost -EnableEnhancedSessionMode $true
Set-VM -VMName 'MiOS' -EnhancedSessionTransportType HvSocket

Start-VM -Name 'MiOS'
```

Once booted, the host carries the image forward with the bootc lifecycle:
`bootc upgrade` to take a new release, `bootc rollback` to revert — no in-place
package mutation, every change atomic.

---

## 5. WSL2 install (alternative to Hyper-V)

Useful for fast iteration on the agent/inference plane without a full VM.

```powershell
.\tools\windows\Build-MiOS.ps1 -OutputFormat wsl2

wsl --import 'MiOS' "$HOME\AppData\Local\MiOS" ".\output\disk.wsl2"
wsl -d 'MiOS'
```

> Some services are bare-metal- or VM-only and stay inert under WSL2 (they carry
> `ConditionVirtualization=!wsl`). The heavy GPU lanes are also gated off by
> default in `mios.toml` until enabled and reachable. The core agent stack runs
> fine for development.

---

## Troubleshooting

**"Docker daemon not running"** — Open Docker Desktop and wait for the whale icon
to stop animating.

**"Containerfile not found"** — Run the script from the repo root (`cd MiOS`
first). The repo root is the system root; the build needs it as the build context.

**BIB fails with "permission denied"** — bootc-image-builder runs privileged.
Docker Desktop needs privileged containers enabled:
Docker Desktop → Settings → Docker Engine → add `"privileged": true`.

**VHDX won't boot in Hyper-V** — Ensure a Generation 2 VM and that the Secure
Boot template is `MicrosoftUEFICertificateAuthority` (not the default Windows
one), which is required for bootc/GRUB.

**`bootc container lint` failure during build** — This is Architectural Law 4
working as intended (the final `RUN` of the `Containerfile`). Fix the lint
finding in the image content; the build is meant to fail rather than ship a
non-compliant image.
