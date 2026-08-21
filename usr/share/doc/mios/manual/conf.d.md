<!-- AI-hint: Manual pages distilled from the source comments of conf.d, sanitized, each passage anchored to the comment it came from. -->

# conf.d

### This sets defaults for Wi-Fi profiles to set a generated...

This sets defaults for Wi-Fi profiles to set a generated, stable MAC address.

Do not modify this file. You can hide/overwrite this file by placing a file
to "/etc/NetworkManager/conf.d/22-wifi-mac-addr.conf". You can also add
configuration snippets with higher priority that override this setting (see
`man 5 NetworkManager.conf`). Most importantly, this snippet only sets
default values for the profile. You can explicitly set the value for each
profile, so that this default value is not used.

For example, on a particular profile/network set

  $ nmcli connection modify "$PROFILE" wifi.cloned-mac-address permanent

to use the hardware MAC address. This prevents the default from this file
to take effect.

Or

  $ nmcli connection modify "$PROFILE" wifi.cloned-mac-address stable connection.stable-id '${NETWORK_SSID}/${BOOT}'

to get a generated MAC address that changes on each boot. Note how setting
"connection.stable-id" also affects other aspects of the profile.

See `man 5 nm-settings` for "wifi.cloned-mac-address" and "connection.stable-id".

<!-- mios-src:70cd7488ae33 from usr/lib/NetworkManager/conf.d/22-wifi-mac-addr.conf:1-24 -->

### Boot from NVMe over TCP (NBFT) For NVMe/TCP connections...

Boot from NVMe over TCP (NBFT)

For NVMe/TCP connections that provide namespaces containing rootfs
it is crucial to react on carrier events and reconnect any missing
NVMe/TCP connections as defined in the ACPI NBFT table. A custom
/usr/lib/NetworkManager/dispatcher.d/99-nvme-nbft-connect.sh hook
will respawn nvmf-connect-nbft.service on such occasion.

<!-- mios-src:9fd0b9654d48 from usr/lib/NetworkManager/conf.d/99-nvme-nbft-no-ignore-carrier.conf:1-7 -->
