<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Overrides the mios-gpu-nvidia.service unit to ensure it runs during the early sysinit.target phase, bypassing standard dependency delays to ensure GPU drivers are initialized early in the boot sequence.
AI-related: mios-gpu-nvidia, mios-gpu-nvidia.service, sysinit.target

<!-- mios-src:0ef213e56eeb from usr/lib/systemd/system/mios-gpu-nvidia.service.d/10-cycle-fix.conf:1-2 -->

