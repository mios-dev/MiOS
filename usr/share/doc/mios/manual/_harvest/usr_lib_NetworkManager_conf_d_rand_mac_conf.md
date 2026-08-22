<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures NetworkManager MAC address randomization policies to prevent WiFi tracking by enforcing random scan MACs and stable, per-connection identifiers for both wireless and ethernet interfaces.
'MiOS' MAC address randomization (secureblue upstream pattern)
Prevents passive WiFi tracking via persistent hardware MACs.

wifi.scan-rand-mac-address=yes  -- use a random MAC during scanning (not associated)
wifi.cloned-mac-address=stable  -- per-connection stable MAC (not random per-boot;
  consistent within the same network, different across networks)
ethernet.cloned-mac-address=stable -- same stable-per-connection policy for wired
connection.stable-id=${CONNECTION}/${BOOT} -- seed changes each boot for connections
  that don't have a fixed stable-id, adding another layer of rotation

<!-- mios-src:a94699926129 from usr/lib/NetworkManager/conf.d/rand_mac.conf:1-10 -->

