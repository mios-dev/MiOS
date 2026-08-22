<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines the default container storage configuration for MiOS, enforcing kernel-native overlayfs with metacopy/userxattr to ensure rootless container compatibility in restricted environments like WSL2.
/usr/share/containers/storage.conf

Vendor-default storage config for MiOS -- shipped at the lowest precedence
layer so the host (/etc/containers/storage.conf) and the user
(~/.config/containers/storage.conf) can override.

Why this file: the upstream containers/storage default uses fuse-overlayfs
for rootless mode. Inside WSL2 distros and nested containers, /dev/fuse
may not be exposed, and rootless containers fail with:

    fuse-overlayfs: cannot mount: No such file or directory
    Error: mounting storage for container ...: creating overlay mount to
        /var/lib/containers/storage/overlay/.../merged ...

The kernel-native overlayfs DOES work in unprivileged user namespaces
since Linux 5.11 (CONFIG_OVERLAY_FS_USE_USER_NS=y). Empty mount_program
tells containers/storage to skip fuse-overlayfs and use the kernel
directly. metacopy=on and userxattr keep the rootless overlay semantics
correct (preserves uid/gid mappings without copy-up).

vfs is a universal-compatibility fallback -- works everywhere but slow
and disk-hungry. Operators on non-WSL hosts where fuse is fine can swap
back to fuse-overlayfs via /etc/containers/storage.conf or the user
layer.

<!-- mios-src:714ffc8583a2 from usr/share/containers/storage.conf:1-25 -->

