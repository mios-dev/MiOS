<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Registers a Windows Scheduled Task to run a hidden PowerShell process that maintains a persistent WSL session via `sleep infinity`, preventing the WSL VM and its internal services (systemd, pgvector, sglang) from shutting down.
AI-related: mios-wsl-keepalive
mios-wsl-keepalive.ps1

Registers the "MiOS-WSL-KeepAlive" scheduled task: hold a PERSISTENT session
open inside the WSL distro so WSL never tears the VM (and its systemd services)
down on last-session-detach.

WHY THIS EXISTS
---------------
WSL2 stops a distro's systemd services when the LAST attached session detaches
(default vmIdleTimeout ~60s). On MiOS this cycles the whole stack every ~30-60s:
agent-pipe / pgvector / searxng / sglang restart, every MCP server is re-probed
(Playwright stdio re-spawns), the 8B is swapped in/out of VRAM, and the P0
byte-stable RadixAttention prefix is destroyed -- which also makes any latency /
VRAM / offline-eval measurement non-reproducible. A single
long-lived `sleep infinity` process keeps a session attached, so WSL keeps the VM
+ all enabled services running continuously.

This task runs that holder at logon AND re-checks every minute: if the holder
died (a `wsl --shutdown`, a crash, a manual stop), the next tick restarts it
within ~60s. MultipleInstances=IgnoreNew means only ever ONE holder runs.

Idempotent: safe to re-run (-Force overwrites). Run as the operator (mios);
NO elevation needed to register a logon task for the current user.

Alternative / complementary OS-level fix (operator, one-time): add to
%USERPROFILE%\.wslconfig  ->  [wsl2]\nvmIdleTimeout=-1   then `wsl --shutdown`
once to reload it. The KeepAlive task is the robust default because it also
survives an explicit shutdown and needs no global WSL config change.

To remove:  Unregister-ScheduledTask -TaskName 'MiOS-WSL-KeepAlive' -Confirm:$false

<!-- mios-src:db49c1b9df0c from usr/share/mios/windows/mios-wsl-keepalive.ps1:1-32 -->

