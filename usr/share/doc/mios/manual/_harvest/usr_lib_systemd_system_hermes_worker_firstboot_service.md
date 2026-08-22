<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Oneshot that seeds the non-thin Hermes WORKER config (/var/lib/mios/hermes-worker/config.yaml) from the vendor template before hermes-worker.service starts. Distinct from mios-hermes-firstboot (which owns and re-thins the primary `hermes` config); this one NEVER touches the primary path.
AI-related: /usr/libexec/mios/hermes-worker-firstboot, /usr/share/mios/hermes/config-worker.yaml, /var/lib/mios/hermes-worker/config.yaml, hermes-worker.service

<!-- mios-src:16bf9e6ae257 from usr/lib/systemd/system/hermes-worker-firstboot.service:1-2 -->

