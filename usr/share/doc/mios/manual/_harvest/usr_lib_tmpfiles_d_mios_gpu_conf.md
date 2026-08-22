<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines systemd-tmpfiles for GPU runtime directories, CDI paths, and NVIDIA container toolkit configurations to ensure persistent mount points and environment files for GPU acceleration.
'MiOS' v0.2.4 -- GPU runtime directories. Declared per LAW 2 (NO-MKDIR-IN-VAR).
Format: Type Path Mode UID GID Age Argument
/var/run is a symlink to /run on bootc/Fedora; systemd-tmpfiles rejects the
legacy alias ("Line references path below /var/run") and wants /run direct.

<!-- mios-src:1a91b6a8f4f2 from usr/lib/tmpfiles.d/mios-gpu.conf:1-5 -->

