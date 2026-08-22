<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Ensures world-readable permissions on /usr/lib/containers/storage via a systemd oneshot to prevent permission denied errors for unprivileged podman, flatpak, and GUI tools accessing the baked-in OCI image store.
AI-related: podman-restart.service, hermes-agent.service, local-fs.target, multi-user.target

<!-- mios-src:c88c827e98b9 from usr/lib/systemd/system/mios-additionalimagestores-perms.service:1-2 -->

