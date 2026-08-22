<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines the core WSL2 environment configuration for MiOS, enabling systemd, setting the default 'mios' user, and configuring mount options and network behavior for the WSL subsystem.
AI-related: wsl-init.service
'MiOS' WSL2 configuration. Read by WSL2 from /etc/wsl.conf on every boot.
Reference copy lives at /usr/lib/wsl.conf; wsl-init.service restores
/etc/wsl.conf from that reference if drift is detected.
Format: ASCII only, LF endings, no blank lines between sections, single
trailing newline. Older WSL parsers reject blank-line separation and any
non-ASCII byte (multibyte chars throw off the line counter and surface as
"Expected ' ' or '\n' in /etc/wsl.conf:N").

<!-- mios-src:4b13e4d9f54c from usr/lib/wsl.conf:1-9 -->

