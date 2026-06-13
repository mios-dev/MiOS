<!-- AI-hint: Guide for the agent's Windows-host control bridge `/usr/libexec/mios/mios-windows`, which reaches the Windows host the WSL2 VM lives inside via TWO backends — WSL interop (default, no setup) and Tailscale SSH (opt-in `ssh-ps` subcommand for elevated/remote cases). Covers subcommands, one-time Tailscale setup, the non-elevated-token caveat, and the security model. Part of MiOS's OS-control surface.
     AI-related: /usr/libexec/mios/mios-windows, /etc/mios/mios.toml, /usr/share/mios/mios.toml, /etc/mios/windows-host, mios-windows, mios-hermes-firstboot, mios-oscontrol-server, mios-pc-control -->
# Agent → Windows host control

## Why this exists (the whole-system view)

MiOS is one image built two ways at once: an immutable, bootc/OCI-shaped Fedora
workstation *and* a local, self-replicating agentic AI OS. The agent stack —
the agent-pipe orchestrator (`:8640`), the MiOS-Hermes gateway (`:8642`), the
local inference lanes (`mios-llm-light` on `:11450` plus the gated heavy lanes),
and PostgreSQL+pgvector memory (`:5432`) — is built to **operate the machine it
runs on**: launch apps, query state, fix problems.

When that image is deployed as a **WSL2 distro** (`MiOS-DEV`), the agent lives
*inside* the Linux VM, but some of the things it needs to act on are
**Windows-side**, outside the VM's reach:

- `Restart-Service vmcompute` (when WSL itself wedges)
- `New-NetFirewallRule` / `netsh portproxy` (LAN port exposure)
- `Restart-Computer` (after Windows updates)
- Inspecting Windows-side process / network / service state
- Mounting / unmounting Windows partitions
- Hyper-V VM management
- Launching Windows GUI apps onto the operator's interactive desktop

`/usr/libexec/mios/mios-windows` is the supported bridge across that boundary.
It is the WSL-specific complement to the rest of MiOS's OS-control surface
(`mios-oscontrol-server`, `mios-pc-control`, the `launch_*`/`pc_*` verbs):
*one* environment-adaptive verb set, with `mios-windows` the piece that reaches
the host the VM is nested inside. Everything still resolves through the unified
AI plane — the verbs that ultimately call this helper are dispatched by the same
agent-pipe/Hermes loop that targets `MIOS_AI_ENDPOINT` (Architectural Law 5).

This guide is for the **operator** setting up the bridge and for anyone reading
how the agent reaches Windows. It is not a launch surface the operator drives
by hand; it is the code path the agent uses.

## Two backends, one frontend

`mios-windows` fronts **two** ways to reach the Windows host. The frontend
(subcommands) is the same; the backend is chosen per-call:

| Backend | When | Setup |
|---|---|---|
| **WSL interop** (default) | The common case: launch an app, run a non-elevated `powershell.exe` / `cmd.exe` one-liner, query a service/process/network state. | **None.** `/init` (PID 1 in the WSL2 distro) transparently exec's `/mnt/c/.../*.exe` on the host and pipes stdout/stderr back. |
| **Tailscale SSH** (`ssh-ps`) | Opt-in: commands that must run AS the host's interactive operator account (not interop's SYSTEM-spawned context), or that need to reach a *different* machine on the tailnet. | Tailscale SSH enabled host-side (one-time; see below). |

The operator directive that shaped this (2026-05-15) was *"should be able to ssh
in to the host's shell environment via loopback (or similar)."* The **"or
similar"** turned out to be plain WSL interop — no SSH, no Tailscale, no keys for
the common case (launching Notepad, running `ipconfig`, querying a service). The
Tailscale-SSH path is preserved for the cases interop's window-station context
can't serve.

> **Note on Tailscale.** Tailscale is **OFF by MiOS policy by default**
> (it congests the operator's wider internet). Because WSL interop needs no
> Tailscale, the bridge works out of the box with Tailscale stopped. Only the
> `ssh-ps` backend requires it.

## Subcommands

```bash
mios-windows launch <app>       # Launch a Windows GUI app (interop, detached, centered)
mios-windows ps "<command>"     # Run a Windows PowerShell command (interop)
mios-windows cmd "<command>"    # Run a Windows cmd.exe command (interop)
mios-windows ssh-ps [-e] "<cmd>"# Run PowerShell via Tailscale SSH (elevated / remote tailnet)
mios-windows list               # Print short-name → .exe mappings (live App Paths registry)
mios-windows help               # Usage
```

### Read-only state queries (interop, no setup)

```bash
mios-windows ps 'Get-Service vmcompute | Format-List Name,Status,StartType'
mios-windows ps 'Get-NetIPAddress -AddressFamily IPv4'
mios-windows ps 'Get-Process | Where-Object Name -match "vmwp|vmmem" | Format-Table Id,Name'
mios-windows cmd 'tasklist /FI "IMAGENAME eq notepad.exe"'
```

`ps` defaults to Windows PowerShell 5.1
(`System32\WindowsPowerShell\v1.0\powershell.exe`); override with
`MIOS_WINDOWS_PWSH=<absolute path>` for pwsh 7.

### Launching apps (interop)

App-name resolution is **generative** — no hardcoded short-name → exe table.
A bare name is resolved at launch time from the live Windows **App Paths
registry**, then the Start-Menu `.lnk` tree, then `Get-StartApps` (for UWP/Store
apps), falling back to `mios-find`. Launches are routed through the in-session
executor / launcher broker so the window appears on the operator's **interactive
desktop** (session 1), not a non-interactive station, and is centered + focused.

```bash
mios-windows launch notepad
mios-windows launch "C:\Program Files\App\app.exe"
```

### Elevated / remote (Tailscale SSH)

```bash
mios-windows ssh-ps 'Get-Service Tailscale | Format-List Name,Status'

# Elevated (NOT YET WIRED — placeholder; falls back to non-elevated SSH):
mios-windows ssh-ps -e 'Restart-Service vmcompute -Force'
```

For backwards compatibility, a bare first argument that looks like a PowerShell
cmdlet (`Get-*`, `Set-*`, `Restart-*`, …) is routed to `ssh-ps` automatically,
preserving operator muscle memory.

## One-time operator setup (only for the `ssh-ps` backend)

WSL interop needs **no** setup. The steps below apply only if you want the
Tailscale-SSH path for elevated/remote commands.

### 1. Enable Tailscale SSH on the Windows host

Run once in **elevated PowerShell** on the Windows host:

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" set --ssh
```

Verify:

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" debug prefs | Select-String 'RunSSH'
# expected: "RunSSH": true,
```

### 2. Confirm your tailnet ACL allows the agent

The default Tailscale ACL grants you SSH to your own nodes. If you've customised
your ACL to restrict SSH, ensure a rule like this exists in your tailnet's ACL
JSON:

```json
{
  "ssh": [{
    "action": "accept",
    "src":    ["autogroup:owner"],
    "dst":    ["autogroup:self"],
    "users":  ["autogroup:nonroot", "your-windows-username"]
  }]
}
```

### 3. Tell the agent which user to SSH as

In `/etc/mios/mios.toml` (admin overlay; the vendor default at
`/usr/share/mios/mios.toml` ships `[identity].username = "mios"`):

```toml
[identity]
username     = "mios"               # the Linux operator (already set)
windows_user = "YourWindowsUser"    # the Windows-side username for SSH
```

If `windows_user` is unset, `mios-windows ssh-ps` falls back to
`[identity].username`, then to `$USER`.

### 4. (Optional) Pin the Windows tailnet IP

`mios-hermes-firstboot` writes the Windows Tailscale IPv4 to
`/etc/mios/windows-host` automatically on every firstboot when it detects
`tailscale.exe` on the host (idempotent; keeps the cached value if the probe
transiently fails). Without that file, `ssh-ps` falls back to the WSL default
gateway — which is the Hyper-V vSwitch, **not** the tailnet interface — so
pinning is what makes the SSH path reliable. To pin manually:

```bash
echo "100.122.197.2" | sudo tee /etc/mios/windows-host
```

## Elevation caveat (Tailscale SSH path)

Tailscale SSH executes commands with the Windows user's **filtered
(non-elevated) token** — even when the user is in the Administrators group. UAC's
split-token model strips admin privileges from the non-elevated token by default.
So `Restart-Service vmcompute` over Tailscale SSH will fail with "Access denied"
unless one of:

1. **UAC is set to "Elevate without prompting" for admins** (Group Policy:
   `Computer Configuration → Windows Settings → Security Settings → Local
   Policies → Security Options → User Account Control: Behavior of the elevation
   prompt for administrators in Admin Approval Mode → Elevate without
   prompting`).
2. **A SYSTEM-level scheduled task** watches a queue directory the agent writes
   to (the `-e` flag will eventually wire this; not yet shipped).
3. **Operator runs the command manually** in elevated PowerShell when the agent
   reports it needs elevation.

For 90% of read-only investigation (state queries, service status, process
listing), non-elevated is enough — and the **default WSL-interop backend** sidesteps
the SSH token model entirely for those.

## Security model

- **Auth (interop):** the WSL ↔ Windows interop bridge — no network, no keys;
  bounded by the Windows user the distro runs as.
- **Auth (ssh-ps):** Tailscale's SSO/OAuth identity. No SSH keys on disk.
- **Network (ssh-ps):** only over the tailnet (encrypted, peer-to-peer); no
  port 22 exposed on the LAN.
- **Authorisation (ssh-ps):** gated by your tailnet ACL — you can scope which
  agent identity can SSH to which nodes from the Tailscale admin panel.
- **Audit (ssh-ps):** Tailscale logs every SSH session in the admin console.
- **Revocation (ssh-ps):** `tailscale set --ssh=false` on the Windows host kills
  the SSH path instantly (interop is unaffected and stays available).
- **Least privilege:** consistent with Architectural Law 6 — the agent runs
  unprivileged; the only path to admin actions is the gated, not-yet-wired `-e`
  flow above.

## When to use vs. when NOT to use

**USE for:**
- Diagnostic queries the agent can't answer from inside WSL
- Recovery commands when WSL itself is wedged (`ssh-ps`, since interop dies with
  the VM)
- Windows Firewall / portproxy / scheduled-task management
- Launching Windows GUI apps onto the operator's desktop (`launch`)

**DO NOT USE for:**
- Anything better done via a friendly UI (Settings, Task Manager) — those still
  belong to the operator.
- Continuous loops or polling — this bridge is for one-shot commands, not
  long-running sessions.
- Untrusted operator inputs — the command is interpolated into a PowerShell
  string; sanitise inputs at the agent level before calling `mios-windows`.
