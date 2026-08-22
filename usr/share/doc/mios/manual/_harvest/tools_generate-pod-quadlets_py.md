<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Generate MiOS .pod Quadlets from the [pods.*] SSOT (WS-7)....

Generate MiOS .pod Quadlets from the [pods.*] SSOT (WS-7).

A co-resident group -- a set of containers that must share a podman pod (one
network namespace + lifecycle) -- was previously a hand-authored .pod Quadlet
(only mios-webtools). That is drift-prone: the pod's [Unit]/[Pod]/[Install] and
its member list lived only in the file. This projects each [pods.<name>] in
mios.toml to a deterministic <name>.pod under usr/share/containers/systemd/, so:

  * the co-resident group is declared ONCE (SSOT), and
  * tools/generate-k3s-manifests.sh -- which reads the LIVE pods -- projects the
    same workloads to k3s, so the cluster path is one faithful bridge from SSOT.

Each member .container still declares `Pod=<name>.pod` (Quadlet wires the
Wants/After on the pod service); the member list here is the documented SSOT +
fuels a drift check that every declared member exists as a .container.

Pure renderer (render_pod_quadlet) so it unit-tests offline (--selftest), in the
sibling style of the other tools/ generators. Same SSOT -> byte-identical output.

<!-- mios-src:11f8e1c5b95e from tools/generate-pod-quadlets.py:3-21 -->

### [image.sidecars] -- the digest-pinned image SSOT. Consulted...

[image.sidecars] -- the digest-pinned image SSOT. Consulted by
    _sidecar_image() so bare (no-userenv) regeneration renders the committed
    @sha256 instead of the digestless inline fallback (Quadlet digest drift).

<!-- mios-src:a9bc76e9406e from tools/generate-pod-quadlets.py:210-212 -->
