<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Disables WINE binfmt_misc handlers for windows/windowsPE to ensure WSL's WSLInterop handles .exe files, preventing Windows binaries from being incorrectly launched via WINE instead of the host OS.
AI-related: mios-dev, mios-wsl-interop-priority, systemd-binfmt.service, multi-user.target, default.target

<!-- mios-src:53cdd8466e85 from usr/lib/systemd/system/mios-wsl-interop-priority.service:1-2 -->

