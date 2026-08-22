<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that executes /usr/libexec/mios/mios-adguard-firstboot to generate the AdGuardHome.yaml config from mios.toml, injecting Tailscale IPs before the AdGuard container starts.
AI-related: /usr/libexec/mios/mios-adguard-firstboot, /etc/mios/adguard/AdGuardHome.yaml, mios-adguard-firstboot, mios-adguard, mios-adguard.container, tailscaled.service, mios-adguard.service, network-online.target, multi-user.target
/usr/lib/systemd/system/mios-adguard-firstboot.service
Generates /etc/mios/adguard/AdGuardHome.yaml from mios.toml [adguard]/[ports]
+ the live Tailscale IP/MagicDNS suffix, BEFORE the AdGuard container starts.
Idempotent + non-destructive (skips if the config already exists), so it is
safe to leave enabled across boots. mios-adguard.container Requires= + After=
this unit, so it is pulled in automatically; it is also enabled directly for
fresh installs.

<!-- mios-src:f5c42f1452df from usr/lib/systemd/system/mios-adguard-firstboot.service:1-9 -->

