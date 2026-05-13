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
