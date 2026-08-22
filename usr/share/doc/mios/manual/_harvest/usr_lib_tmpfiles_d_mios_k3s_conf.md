<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines the persistent directory structure and initial manifest copy operations for the K3s cluster in /var/lib/rancher, ensuring the container runtime and storage drivers are correctly initialized at boot.
AI-related: /usr/share/mios/k3s-manifests/, /usr/share/mios/k3s-manifests/ceph-csi-cephfs.yaml, k3s.service
'MiOS' v0.2.4: Create K3s directory structure at boot
These directories live in /var (persistent state). Manifests are shipped
in /usr/share/mios/k3s-manifests/ and copied on first boot by k3s.service.

<!-- mios-src:a5d89a9dfe22 from usr/lib/tmpfiles.d/mios-k3s.conf:1-5 -->

