<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines systemd tmpfiles for NFS state directories, ensuring /var/lib/nfs/sm and sm.bak exist to prevent sm-notify errors during WSL2 boots and manage RPC lock states.
'MiOS' -- NFS state directories
Required for NFS client status monitoring and lock management. sm-notify
requires /var/lib/nfs/sm and /var/lib/nfs/sm.bak; without them it logs
"Failed to open sm: No such file or directory" on every WSL2 boot.

<!-- mios-src:1c182aaf7f94 from usr/lib/tmpfiles.d/mios-nfs.conf:1-5 -->

