<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Boot from NVMe over TCP (NBFT) For NVMe/TCP connections...

Boot from NVMe over TCP (NBFT)

For NVMe/TCP connections that provide namespaces containing rootfs
it is crucial to react on carrier events and reconnect any missing
NVMe/TCP connections as defined in the ACPI NBFT table. A custom
/usr/lib/NetworkManager/dispatcher.d/99-nvme-nbft-connect.sh hook
will respawn nvmf-connect-nbft.service on such occasion.

<!-- mios-src:9fd0b9654d48 from usr/lib/NetworkManager/conf.d/99-nvme-nbft-no-ignore-carrier.conf:1-7 -->
