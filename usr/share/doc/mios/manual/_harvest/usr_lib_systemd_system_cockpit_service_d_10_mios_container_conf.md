<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Disables systemd namespace isolation hardening for the cockpit.service unit to allow the service to start successfully within unprivileged environments like WSL2, Podman containers, or Distrobox.
AI-related: mios-container, cockpit.service, cockpit.socket
/usr/lib/systemd/system/cockpit.service.d/10-mios-container.conf

Relax cockpit's namespace-isolation hardening so the unit comes up inside
containers and WSL2. Cockpit's upstream unit (in cockpit-ws) configures
cockpit-certificate-ensure with the full systemd hardening surface --
PrivateNetwork, PrivateIPC, PrivateMounts, PrivateTmp, ProtectSystem,
ProtectHome, ProtectKernelTunables, ProtectKernelModules, ProtectClock,
RestrictNamespaces, NoNewPrivileges, plus a SystemCallFilter -- none of
which the kernel allows when systemd is running without CAP_SYS_ADMIN
over its parent namespaces. That is the normal case when MiOS runs as
a podman-machine, distrobox, WSL2 distro, or nested container.

Symptom on the 2026-05-05 / 2026-05-06 WSL2 boot:

    cockpit.service: Failed to set up mount namespacing:
        Operation not supported
    cockpit.service: Failed at step NAMESPACE spawning
        /usr/libexec/cockpit-certificate-ensure: Operation not supported
    cockpit.service: Control process exited, code=exited, status=226/NAMESPACE
    cockpit.service: Failed with result 'exit-code'.
    cockpit.socket: Failed with result 'service-start-limit-hit'.

Even with PrivateMounts=no set, ANY of {PrivateTmp, ProtectSystem,
ProtectHome, ProtectKernelTunables, ProtectControlGroups,
RestrictNamespaces, ProtectKernelModules, ProtectClock, ProtectKernelLogs,
ReadWritePaths, ReadOnlyPaths, InaccessiblePaths} causes systemd to clone
a mount namespace at exec time, and that clone fails with EOPNOTSUPP on
any host where the parent namespace is unprivileged. Below we explicitly
neutralize ALL of them so cockpit-certificate-ensure can exec without any
CLONE_NEWNS attempt at all.

The relaxation cost is negligible. cockpit-certificate-ensure is a tiny
binary whose only job is to ensure a TLS cert exists under
/etc/cockpit/ws-certs.d/ -- it doesn't touch the kernel surface.
Cockpit's actual long-lived runtime privsep happens later, via
cockpit-bridge -> cockpit-session inside cockpit-ws's own user namespace,
which is unaffected by this drop-in. Bluefin / Aurora / Universal Blue
ship the equivalent drop-in unconditionally for the same reason.

<!-- mios-src:c04be09f93c5 from usr/lib/systemd/system/cockpit.service.d/10-mios-container.conf:1-40 -->

