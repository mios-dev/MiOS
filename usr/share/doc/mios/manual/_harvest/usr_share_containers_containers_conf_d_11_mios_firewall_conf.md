<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures the netavark network backend to use nftables as the mandatory firewall driver to ensure rootless podman container networking functions correctly in MiOS.
AI-related: mios-firewall
/usr/share/containers/containers.conf.d/11-mios-firewall.conf

Pin netavark's firewall backend to nftables. Required for podman 6.0+
(visible regression in podman 102:6.0.0~dev shipped 2026-05-05): netavark
6.0 dropped iptables as the default backend and now requires the operator
to declare the backend explicitly. Without this drop-in, every rootless
podman build / run that needs a network namespace fails with:

    error running container: did not get container start message from
        parent: EOF
    setup network: netavark: Must provide a valid firewall backend,
        got iptables

`nftables` is the modern, kernel-supported netfilter frontend; iptables-
nft was the transitional shim. MiOS's [packages.security] already pulls
in nftables.x86_64, so the kernel + userspace are both present -- this
drop-in just tells netavark to use them.

<!-- mios-src:a0de76e13d28 from usr/share/containers/containers.conf.d/11-mios-firewall.conf:1-19 -->

