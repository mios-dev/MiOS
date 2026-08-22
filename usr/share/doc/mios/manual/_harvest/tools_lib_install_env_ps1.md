<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Powershell helper for MiOS Windows installers that generates the /etc/mios/install.env file in a WSL2 distro to inject the operator's hostname and sha512crypt password hash into the wsl-firstboot sequence.
AI-related: /etc/mios/install.env, /usr/libexec/mios/wsl-firstboot, /usr/share/mios/env.defaults, /etc/mios/env.d/, /usr/libexec/mios/mios-dashboard.sh, /usr/libexec/mios/forge-firstboot.sh., mios-dashboard, wsl-firstboot.service
AI-functions: Write-MiosInstallEnv
tools/lib/install-env.ps1 -- shared helper for the 'MiOS' Windows installers.
Writes /etc/mios/install.env into a freshly-imported WSL2 distro so that
/usr/libexec/mios/wsl-firstboot can pick up the operator-supplied hostname
and password hash on first boot, instead of falling back to the literal
default password "mios".

Resolution chain documented in /usr/share/mios/env.defaults:
  ~/.config/mios/env -> /etc/mios/install.env -> /etc/mios/env.d/*.env -> /usr/share/mios/env.defaults
This file produces the third layer.

<!-- mios-src:cafe7aa72736 from tools/lib/install-env.ps1:1-12 -->

