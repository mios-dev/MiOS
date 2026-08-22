<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures /run/podman permissions to 0750 (root:mios) to allow the mios operator group to traverse the directory and access the Podman API socket for container management.
AI-related: mios-podman-sock, mios-operator-access, podman.socket
/usr/lib/tmpfiles.d/mios-podman-sock.conf
Make the ROOTFUL podman runtime dir group-traversable so the operator (group
mios) can reach the API socket inside it. podman ships /run/podman 0700
root:root, which blocks the 0660 root:mios socket grant (podman.socket.d/
10-mios-operator-access.conf) -- the documented reason MiOS used a read-only
snapshot instead. 0750 root:mios lets the operator traverse + connect (for
Serverbox / SSH container managers) WITHOUT opening the dir to the world; the
agent user (not in group mios) still can't reach it and uses the snapshot.
Operator 2026-05-23.

<!-- mios-src:2da19918e95b from usr/lib/tmpfiles.d/mios-podman-sock.conf:1-11 -->

