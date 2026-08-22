<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures the allowed syscall architectures for the systemd-udevd service to ensure compatibility with multi-arch binaries and prevent SIGSYS failures during hardware device discovery.
We can't really control what helper programs are run from other udev
rules. E.g. running i386 binaries under amd64 is a valid use case and
should not trigger a SIGSYS failure.
https://bugs.debian.org/869719

<!-- mios-src:2a7b97fefacb from usr/lib/systemd/system/systemd-udevd.service.d/syscall-architecture.conf:1-5 -->

