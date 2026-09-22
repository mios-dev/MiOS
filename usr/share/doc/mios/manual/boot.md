<!-- AI-hint: Manual pages distilled from the source comments of boot, sanitized, each passage anchored to the comment it came from. -->

# boot

### Zero-timeout systemd-boot silent fastboot configurator and...

Zero-timeout systemd-boot silent fastboot configurator and baked UKI kargs manager for MiOS.

Configures systemd-boot loader.conf with timeout 0 for instant sub-300ms firmware handoff,
enforces UKI baked kargs immutability (Invariant 2), and provides Space/Esc emergency rescue menu fallback.

<!-- mios-src:f1f72a2e4193 from usr/libexec/mios/boot/fastboot_mgr.py:4-8 -->
