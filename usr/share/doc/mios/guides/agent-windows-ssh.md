# Agent → Windows host control via Tailscale SSH

The MiOS agent runs inside the WSL2 distro `podman-MiOS-DEV`. Some
operations are **Windows-side** and the agent can't reach them
directly:

- `Restart-Service vmcompute` (when WSL itself wedges)
- `New-NetFirewallRule` (LAN port exposure)
- `Restart-Computer` (after Windows updates)
- Inspecting Windows-side process / network state
- Mounting / unmounting Windows partitions
- Hyper-V VM management

The supported escape hatch is **Tailscale SSH from WSL → the Windows
host's tailnet IP**, fronted by `/usr/libexec/mios/mios-windows`. No
SSH keys to manage, no port-22 hole on the LAN.

## One-time operator setup

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

The default Tailscale ACL grants you SSH to your own nodes. If you've
customised your ACL to restrict SSH, ensure a rule like this exists in
your tailnet's ACL JSON:

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

In `/etc/mios/mios.toml`:

```toml
[identity]
username = "mios"            # the Linux operator (already set)
windows_user = "Corey"       # the Windows-side username for SSH
```

If `windows_user` is unset, `mios-windows` falls back to `[identity].username`.

### 4. (Optional) Pin the Windows tailnet IP

`mios-hermes-firstboot` writes the Windows tailscale IP to
`/etc/mios/windows-host` automatically when it detects Tailscale on the
host. To pin manually:

```bash
echo "100.122.197.2" | sudo tee /etc/mios/windows-host
```

## Usage from the agent

```bash
# Read-only, non-elevated:
mios-windows 'Get-Service vmcompute | Format-List Name,Status,StartType'
mios-windows 'Get-NetIPAddress -AddressFamily IPv4'
mios-windows 'Get-Process | Where-Object Name -match "vmwp|vmmem" | Format-Table Id,Name'

# Elevated (NOT YET WIRED -- placeholder):
mios-windows -e 'Restart-Service vmcompute -Force'
```

## Elevation caveat

Tailscale SSH executes commands with the Windows user's **filtered
(non-elevated) token** — even when the user is in the Administrators
group. UAC's split-token model strips admin privileges from the
non-elevated token by default. So `Restart-Service vmcompute` over
Tailscale SSH will fail with "Access denied" unless one of:

1. **UAC is set to "Elevate without prompting" for admins**
   (Group Policy: `Computer Configuration → Windows Settings →
   Security Settings → Local Policies → Security Options → User
   Account Control: Behavior of the elevation prompt for administrators
   in Admin Approval Mode → Elevate without prompting`).
2. **A SYSTEM-level scheduled task** watches a queue directory the agent
   writes to (the `-e` flag will eventually wire this; not yet
   shipped).
3. **Operator runs the command manually** in elevated PowerShell when
   the agent reports it needs elevation.

For 90% of read-only investigation (state queries, service status,
process listing), non-elevated is enough.

## Security model

- **Auth**: Tailscale's SSO/OAuth identity. No SSH keys on disk.
- **Network**: only over the tailnet (encrypted, peer-to-peer); no
  port 22 exposed on LAN.
- **Authorisation**: gated by your tailnet ACL — you can scope which
  agent identity can SSH to which nodes from the Tailscale admin
  panel.
- **Audit**: Tailscale logs every SSH session in the admin console.
- **Revocation**: `tailscale set --ssh=false` on the Windows host kills
  the entire path instantly.

## When to use vs. when NOT to use

**USE for:**
- Diagnostic queries the agent can't answer from inside WSL
- Recovery commands when WSL itself is wedged
- Windows Firewall / portproxy / scheduled task management

**DO NOT USE for:**
- Anything you'd want to do via a friendly UI (Settings, Task Manager) —
  those still belong to the operator
- Continuous loops or polling — Tailscale SSH is meant for one-shot
  commands, not long-running sessions
- Untrusted operator inputs — the command is interpolated into a
  PowerShell string; sanitise inputs at the agent level before calling
  `mios-windows`
