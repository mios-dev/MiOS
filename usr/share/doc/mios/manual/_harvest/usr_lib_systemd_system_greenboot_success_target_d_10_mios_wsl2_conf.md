<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Masks the greenboot-success.target failure on WSL systems by skipping the target when ConditionVirtualization is detected, preventing boot-loop logic from failing due to missing block devices.
AI-related: mios-wsl2, greenboot-success.target, greenboot-healthcheck.service, boot-complete.target, boot.mount
Skip greenboot-success.target on WSL.

greenboot-success.target chains into greenboot-healthcheck.service
which depends on boot-complete.target which depends on boot.mount
which requires /dev/disk/by-label/boot -- a block device WSL doesn't
have. The cascade leaves greenboot-success.target stuck in 'failed
(dependency)' on every WSL boot. greenboot's purpose (auto-rollback
after 3 failed boots) is also moot in WSL: there's no bootloader to
count against.

Mirrors the existing greenboot-healthcheck.service.d/10-mios-wsl2.conf
skip; this target sibling was missed in the original cascade pass.

<!-- mios-src:8961c1936f84 from usr/lib/systemd/system/greenboot-success.target.d/10-mios-wsl2.conf:1-14 -->

