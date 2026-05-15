<!-- FHS: /usr/share/mios/PACKAGES.md -->

# MiOS Package Manifest

All packages installed into the MiOS image flow through this file.
Phase scripts parse fenced ` ```packages-<category> ` blocks and feed
them to `dnf5 install --setopt=install_weak_deps=False`. Inline
`dnf install` is forbidden in the Containerfile and phase scripts.

```packages-core
bootc
ostree
composefs
podman
just
git-core
jq
yq
```

```packages-gpu-nvidia
akmod-nvidia
xorg-x11-drv-nvidia-cuda
nvidia-container-toolkit
```

```packages-rdp
xrdp
xorgxrdp
xorgxrdp-glamor
```

```packages-virt
qemu-kvm
libvirt
edk2-ovmf
swtpm
looking-glass-client
```

```packages-security
selinux-policy-targeted
fapolicyd
fapolicyd-selinux
usbguard
usbguard-selinux
firewalld
crowdsec
crowdsec-firewall-bouncer
```

```packages-ai
ollama
qdrant
litellm
```

```packages-dev-cockpit
cockpit
cockpit-podman
cockpit-machines
cockpit-storaged
cockpit-networkmanager
```

```packages-shell
bash-completion
zsh
fish
tmux
```

```packages-python
# Host python deps that MiOS scripts use (NOT inside the Hermes venv;
# those are pip-installed by automation/38-hermes-agent.sh).
#   * python3-passlib + python3-bcrypt -- bcrypt password hashing
#     for mios-owui-bootstrap-admin (creates the OWUI admin row
#     with a bcrypt $2b$ hash of either MIOS_OPERATOR_PASSWORD from
#     /etc/mios/secrets.env or a freshly-generated 24-char password
#     written to /etc/mios/owui-admin-password). Without bcrypt,
#     the helper falls back to `podman exec mios-open-webui python3`
#     -- works but slower + requires the OWUI container be up first.
#   * python3-cryptography -- transitive of passlib's bcrypt path,
#     declared explicitly so it isn't gated on weak deps.
python3-passlib
python3-bcrypt
python3-cryptography
```

```packages-cron
# Operator directive 2026-05-15: "make sure MiOS images and deployments
# also include the installations of all the cron related tools that
# are needed". Hermes-Agent has its own in-process cronjob_tool
# (croniter-backed, schedules re-fired prompts inside the gateway), but
# anything an agent or operator wants to schedule OUTSIDE the gateway
# -- shell scripts, system jobs, one-shot runs after an interval -- has
# always assumed the canonical Linux cron + at surface is present.
# These packages provide the standard daemons + binaries:
#   * cronie -- the modern Fedora cron daemon (vixie-cron successor);
#     ships /usr/sbin/crond + crontab + /etc/cron.d /etc/cron.{daily,
#     hourly,weekly,monthly}/.
#   * cronie-anacron -- catch-up runs after sleep/shutdown; essential
#     for workstations that don't run 24/7.
#   * at -- one-shot scheduling (`at now + 5 min`); also provides atd.
#   * dbus-daemon -- pulls in /usr/sbin/dbus-run-session, used by
#     mios-hermes-browser to spin a transient session bus for
#     flatpak's portal helper. Usually transitively present, but
#     declared here so a minimal-image deploy doesn't lose it.
cronie
cronie-anacron
at
dbus-daemon
```
