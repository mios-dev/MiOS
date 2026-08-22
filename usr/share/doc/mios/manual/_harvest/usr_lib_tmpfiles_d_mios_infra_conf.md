<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines systemd-tmpfiles directory permissions and initial content for core infrastructure components including Cockpit, Libvirt, K3s, Ceph, and MiOS-specific configuration skeletons.
AI-related: /etc/mios/ai, /etc/mios/env.d, /etc/mios/role.conf, /usr/share/mios/role.conf.example, /usr/lib/mios/hostname.default, mios-k3s, mios-ceph, mios-init, mios-XXXXX, mios-ai
'MiOS' -- Infrastructure & Virtualization runtime skeletons
Ensures services starting before persistent /var is ready have necessary dirs.

<!-- mios-src:2b3b431e8792 from usr/lib/tmpfiles.d/mios-infra.conf:1-4 -->

