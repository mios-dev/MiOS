<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Overrides cockpit-wsinstance-socket-user.service to disable namespace-requiring security features when running inside a container, ensuring the Cockpit dashboard remains accessible in MiOS-DEV/podman environments.
AI-related: mios-container, cockpit-wsinstance-socket-user.service, socket-user.service, cockpit-wsinstance-http.socket, cockpit.service, cockpit.socket, localhost:9090
/usr/lib/systemd/system/cockpit-wsinstance-socket-user.service.d/10-mios-container.conf

Cockpit's wsinstance-socket-user service uses DynamicUser=yes which
pulls in PrivateTmp / PrivateMounts / mount-namespacing -- those
require kernel privileges (CAP_SYS_ADMIN + namespaces) that are not
available inside a container or a podman-machine WSL distro. The
stock unit then fails with:

    Failed to set up mount namespacing: Operation not supported
    Failed at step NAMESPACE spawning /bin/true: Operation not supported
    status=226/NAMESPACE

The systemd start-rate-limiter then trips on cockpit-wsinstance-
socket-user.service after a handful of retries, which cascades:
cockpit-wsinstance-http.socket fails -> cockpit.service fails ->
cockpit.socket trigger-limit-hit -> the operator's dashboard shows
'Cockpit https://localhost:9090/  (open circle = inactive)'.

This drop-in is gated to ConditionVirtualization=container so it
applies inside MiOS-DEV (podman-machine) but a NO-OP on bare-metal
/ Hyper-V / QEMU MiOS deployments where the namespacing works
correctly.

<!-- mios-src:e614dd800539 from usr/lib/systemd/system/cockpit-wsinstance-socket-user.service.d/10-mios-container.conf:1-24 -->

