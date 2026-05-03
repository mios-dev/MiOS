# SELinux on 'MiOS'

> Mode: enforcing. Five custom modules in `usr/share/selinux/packages/mios/`,
> compiled and shipped, **not auto-loaded at build** — see
> `automation/19-k3s-selinux.sh:46-51`. Booleans and fcontexts declared
> via `semanage` in `automation/37-selinux.sh`.

## Project

- SELinux: <https://github.com/SELinuxProject/selinux>
- Reference policy: <https://github.com/SELinuxProject/refpolicy>
- Fedora SELinux user-space: <https://github.com/fedora-selinux>

## Custom modules

| Module | Purpose |
| --- | --- |
| `mios_portabled` | systemd-portabled D-Bus access for sysext/confext |
| `mios_kvmfr` | Looking Glass shared-memory device file labeling |
| `mios_cdi` | NVIDIA CDI spec generation fcontext (`/var/run/cdi`, `/etc/cdi`) |
| `mios_quadlet` | Podman Quadlet container management transitions |
| `mios_sysext` | systemd-sysext extension activation |

## Booleans

- `container_use_cephfs=on` — let containers read/write CephFS
- `virt_use_samba=on` — let libvirt VMs talk to host Samba shares

## Fcontexts

- `/var/home(/.*)?` → `user_home_dir_t` (so `/var/home/<user>`
  inherits the right context — `home_dirs` is a virtual link)

## Verification

```bash
getenforce                          # must print "Enforcing"
ausearch -m AVC -ts recent          # any recent denials
semodule -l | grep mios             # all five mios_* modules listed
```

## Why "compiled and shipped, not auto-loaded"

`automation/19-k3s-selinux.sh:46-51` builds the `.te` files into
`.pp` policy modules and stages them under
`/usr/share/selinux/packages/mios/`. Loading happens via
`automation/37-selinux.sh` which calls `semodule -i` for each `.pp`,
plus `semanage` for the booleans and fcontexts. Splitting compile from
load lets `bootc container lint` validate the artifacts without needing
a live policy load (which would require `/sys/fs/selinux` mounted in
the build container).

## Cross-refs

- `usr/share/doc/mios/80-security.md`
- `usr/share/doc/mios/upstream/looking-glass-kvmfr.md`
- `usr/share/doc/mios/upstream/cdi.md`
