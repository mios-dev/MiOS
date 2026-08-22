<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures the usbguard daemon to manage USB device authorization, defining policy enforcement for existing/new devices, rule file paths, and audit logging for the MiOS security subsystem.
'MiOS' USBGuard configuration
PresentDevicePolicy=allow ensures all already-connected USB keeps working at boot
InsertedDevicePolicy=apply-policy means new insertions go through rules.conf
(empty rules.conf means new devices are blocked pending user approval)

<!-- mios-src:6fa1b1989b09 from usr/lib/usbguard/usbguard-daemon.conf:1-5 -->

