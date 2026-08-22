<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that launches a ttyd-wrapped PowerShell session via WSL interop, providing a browser-accessible interactive pwsh.exe terminal on port 7682 for the operator.
AI-related: /usr/libexec/mios/mios-ttyd-launch, /etc/mios/userenv.sh, mios-ttyd-launch, mios-ttyd-powershell, mios-powershell, mios-ttyd-bash, mios-as-operator, mios-ttyd-bash.service, network-online.target, multi-user.target
/usr/lib/systemd/system/mios-ttyd-powershell.service
Phase D.2 of the AgentOS roadmap: browser-accessible Windows-
side PowerShell terminal. Operator hits http://localhost:7682
and gets an interactive pwsh.exe session through WSL interop.

Operator directive 2026-05-18: "add ttyd to the stack so we can
access PowerShell from a local browser(s)".

How it works:
  mios-ttyd-launch powershell  ->  ttyd <flags> mios-powershell --shell
  mios-powershell --shell      ->  exec pwsh.exe -NoProfile
                                   (falls back to powershell.exe 5.1)
WSL interop bridges the pty so the agent's pty + the Windows-
side stdout/stderr/stdin pipes round-trip cleanly. From the
browser it feels exactly like a Windows Terminal pwsh tab,
minus tab completion that requires real-time keystrokes the
WebSocket layer occasionally hiccups on. Operator-confirmed
trade-off accepted in the directive.

<!-- mios-src:c4ed8ebaec06 from usr/lib/systemd/system/mios-ttyd-powershell.service:1-20 -->

