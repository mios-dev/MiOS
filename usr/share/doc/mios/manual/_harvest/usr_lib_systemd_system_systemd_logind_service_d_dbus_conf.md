<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures a startup condition for systemd-logind to prevent service failure in minimal environments by requiring the presence of either dbus-daemon or dbus-broker binaries.
logind fails to start in minimal environments without dbus, such as LXC
containers or servers. Add a startup condition to avoid the very noisy
startup failure.
Consider both dbus-daemon (the reference implementation) and dbus-broker.
See https://bugs.debian.org/772700

<!-- mios-src:85a7a37c9d69 from usr/lib/systemd/system/systemd-logind.service.d/dbus.conf:1-6 -->

