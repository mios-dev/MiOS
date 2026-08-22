<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines static system users and groups for Cockpit components to resolve service startup failures caused by the removal of DynamicUser=yes in WSL2-compatible environments.
AI-related: mios-cockpit, mios-container, cockpit-wsinstance-socket-user.service, cockpit.service, cockpit.socket, cockpit-wsinstance-http.service, cockpit-wsinstance-https.service, localhost:9090
/usr/lib/sysusers.d/50-mios-cockpit.conf
'MiOS' static users for cockpit's dynamic-user references.

Newer cockpit-ws (300+) ships several units that use DynamicUser=yes
to create transient users at start time. Our drop-ins at
/usr/lib/systemd/system/cockpit*.service.d/10-mios-container.conf
neutralize DynamicUser=yes (along with PrivateTmp / ProtectSystem /
RestrictNamespaces / etc.) so the units can boot under WSL2's
unprivileged-namespace constraints. Without DynamicUser= the User= /
Group= refs are looked up STATICALLY in /etc/passwd and /etc/group,
and on a fresh image those entries are empty -- yielding the per-boot
failure chain:

  cockpit-wsinstance-socket-user.service: Failed to determine
      credentials for user 'cockpit-wsinstance-socket': Unknown user
  cockpit-wsinstance-socket-user.service: Failed at step USER
      spawning /bin/true: Invalid argument (status=217/USER)
  cockpit.service: Dependency failed (recursive cascade)
  cockpit.socket: Trigger limit hit, refusing further activation.

Operator-flagged 2026-05-10: cockpit web at https://localhost:9090
was supposed to "just work" out of the box but every boot left the
socket in failed/trigger-limit-hit state.

Pinning all the dynamic-user names here closes the gap. UIDs/GIDs
are in the system range (<1000) and chosen to NOT collide with:
  - MiOS service slots (810-829)
  - Fedora reservations (<200, 81 dbus, 999 polkitd, 990 systemd-resolve)
  - existing cockpit-systemd-service (977 - pre-existing entry below)

All users have /sbin/nologin and /var/empty so they cannot be used
for interactive login. Idempotent: systemd-sysusers skips users that
already exist with the same UID.

<!-- mios-src:c105c512d1e3 from usr/lib/sysusers.d/50-mios-cockpit.conf:1-35 -->

