# MiOS — Windows Build Guide

Build MiOS locally on Windows using **Docker Desktop** (WSL2 backend) and produce a VHDX for Hyper-V.

---

## Prerequisites

| Tool | Where to get |
|------|-------------|
| Docker Desktop (WSL2 backend) | <https://www.docker.com/products/docker-desktop/> |
| Git for Windows | <https://git-scm.com/download/win> |
| PowerShell 5.1+ | Built-in on Windows 10/11 |
| (Optional) Hyper-V | Windows 10/11 Pro — enable in "Turn Windows features on or off" |

---

## 1. Clone the repo

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

Create `~\.config\mios\env.toml` (loaded automatically by the build script):

```toml
MIOS_USER_PASSWORD_HASH = "$6$..."   # openssl passwd -6 yourpassword
MIOS_SSH_PUBKEY = "ssh-ed25519 AAAA..."
```

Or export them in your PowerShell session:

```powershell
$env:MIOS_USER_PASSWORD_HASH = (openssl passwd -6 yourpassword)
$env:MIOS_SSH_PUBKEY         = Get-Content "$HOME\.ssh\id_ed25519.pub"
```

---

## 3. Build

```powershell
# Full build → VHDX (default)
.\tools\windows\Build-MiOS.ps1

# Build only the OCI image (no disk conversion)
.\tools\windows\Build-MiOS.ps1 -SkipBib

# Other output formats
.\tools\windows\Build-MiOS.ps1 -OutputFormat qcow2   # QEMU/KVM
.\tools\windows\Build-MiOS.ps1 -OutputFormat wsl2    # WSL2 tarball
.\tools\windows\Build-MiOS.ps1 -OutputFormat raw     # Raw disk image
```

Artifacts land in `.\output\`.

---

## 4. Import into Hyper-V

```powershell
New-VM `
  -Name MiOS `
  -BootDevice VHD `
  -VHDPath ".\output\disk.vhdx" `
  -Generation 2 `
  -MemoryStartupBytes 4GB

# Enable Secure Boot with Microsoft UEFI CA (required for bootc/GRUB)
Set-VMFirmware -VMName MiOS -SecureBootTemplate MicrosoftUEFICertificateAuthority

# Optional: Enable Enhanced Session (clipboard/audio/USB redirect)
Set-VMHost -EnableEnhancedSessionMode $true
Set-VM -VMName MiOS -EnhancedSessionTransportType HvSocket

Start-VM -Name MiOS
```

---

## 5. WSL2 install (alternative to Hyper-V)

```powershell
.\tools\windows\Build-MiOS.ps1 -OutputFormat wsl2

wsl --import MiOS "$HOME\AppData\Local\MiOS" ".\output\disk.wsl2"
wsl -d MiOS
```

---

## Troubleshooting

**"Docker daemon not running"** — Open Docker Desktop and wait for the whale icon to stop animating.

**"Containerfile not found"** — Run the script from the repo root (`cd MiOS` first).

**BIB fails with "permission denied"** — Docker Desktop needs privileged containers enabled:
Docker Desktop → Settings → Docker Engine → add `"privileged": true`.

**VHDX won't boot in Hyper-V** — Ensure Generation 2 VM and Secure Boot template is set to
`MicrosoftUEFICertificateAuthority` (not the default Windows one).
