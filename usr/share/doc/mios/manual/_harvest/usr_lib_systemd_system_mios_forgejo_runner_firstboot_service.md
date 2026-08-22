<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: One-shot systemd service that executes the initial registration of the Forgejo runner using the local token if the runner is not yet configured, ensuring the runner is registered before the main service starts.
AI-related: /etc/mios/forge/runner-token, /usr/libexec/mios/mios-forgejo-runner-firstboot.sh, mios-forgejo-runner-firstboot, mios-forge, mios-forge-firstboot, mios-forgejo-runner, mios-forge.service, mios-forge-firstboot.service, mios-forgejo-runner.service, multi-user.target

<!-- mios-src:2b16938d5e7d from usr/lib/systemd/system/mios-forgejo-runner-firstboot.service:1-2 -->

