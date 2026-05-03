# greenboot -- Operational Health Checks

> Mentioned in `llms.txt` as part of MiOS's operational stack.

## Project

- Repo: <https://github.com/fedora-iot/greenboot>
- Fedora docs: <https://docs.fedoraproject.org/en-US/iot/greenboot/>

## What it does

greenboot runs a series of health-check scripts immediately after each
boot. If a configurable threshold of checks fails (default: 3
consecutive failed boots), the bootloader rolls back to the previous
deployment automatically. This is the safety net for `bootc upgrade`:
even an image that boots far enough to run health checks but fails them
will get reverted without operator intervention.

## How 'MiOS' uses it

| Check | Purpose | Path |
| --- | --- | --- |
| `mios-ai-health` | Verify LocalAI Quadlet is responding on `/v1/models` | `etc/greenboot/check/required.d/` |
| `mios-network` | Default route + DNS resolve | (inherited from ucore) |
| `mios-firewalld` | Firewalld active and zone=drop | `etc/greenboot/check/required.d/` |
| `mios-selinux` | `getenforce` returns `Enforcing` | `etc/greenboot/check/required.d/` |

Failed boot count is tracked by `greenboot-rollback.service` and
surfaced via `journalctl -u greenboot-healthcheck`.

## Bootc + greenboot interaction

Order of events on `bootc upgrade && systemctl reboot`:

```
1. bootc stages new deployment in /sysroot/ostree/deploy/<csum>.<n+1>
2. systemd reboots
3. bootloader picks the new deployment as default
4. greenboot-healthcheck.service runs after multi-user.target
5a. all required checks pass → greenboot marks deployment "good"
5b. checks fail → greenboot-rollback.service flips bootloader default to <csum>.<n>
6. on next boot, system runs the previous deployment
```

The user sees a notification in Cockpit if a rollback occurred.

## Cross-refs

- `usr/share/doc/mios/upstream/bootc.md`
- `usr/share/doc/mios/80-security.md`
