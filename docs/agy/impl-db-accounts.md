<!-- AI-hint: DESIGN.
     AI-related: usr/share/mios/mios.toml, docs/adr/, AGY-TASKS.md -->
# DESIGN: Database-Managed Accounts SSOT (WS-ACCT / ACCT-03)

## Architecture Overview
The database-managed accounts subsystem implements a normalized PostgreSQL accounts schema that serves as the dynamic source-of-truth for user and group identities across Linux and Windows targets. It projects accounts outward to:
1. Linux: `systemd-userdb` JSON user/group records under `/usr/lib/userdb` (bake) or `/etc/userdb` (runtime) served via `nss-systemd`.
2. Windows: Local user and group state reconciled via `MiOS-AccountSync.ps1` calling `mios-pg-query --exec-json`.

## Schema Specification
- `mios_group`: Normalized POSIX/Windows groups (`id`, `name citext`, `gid`, `description`, `is_system`, `meta jsonb`, `created_at`, `updated_at`).
- `mios_account`: Primary account registry (`id`, `username citext`, `uid`, `primary_gid`, `display_name`, `description`, `home_dir`, `shell`, `enabled`, `is_admin`, `is_service`, `password_hash`, `must_change_pw`, `on_linux`, `on_windows`, `meta jsonb`, `created_at`, `updated_at`).
- `mios_account_group`: Join table for supplementary group memberships (`account_id`, `group_id`, `created_at`).
- `mios_account_export`: Unified projection view aggregating primary groups and supplementary group membership arrays.

## Interface Contracts
- `list_accounts(platform=None, include_disabled=True) -> list[dict]`: Query export view.
- `get_account(username: str) -> dict | None`: Query single account by case-insensitive username.
- `create_account(username: str, ...) -> dict`: Insert account and associate default/supplementary groups.
- `update_account(username: str, **fields) -> dict`: Update whitelisted account columns.
- `set_password(username: str, plaintext: str, must_change_pw: bool = False) -> None`: Hash password and update hash.
- `delete_account(username: str) -> None`: Cascade delete account row and memberships.
- `export(platform: str) -> list[dict]`: Projection adapter for systemd-userdb and Windows synchronizers.

## Field Mappings
| Database Field | Linux systemd-userdb Mapping | Windows SAM / LocalUser Mapping |
| :--- | :--- | :--- |
| `username` | `userName` | `Name` |
| `uid` | `uid` | Derived handle / ignored |
| `primary_gid` | `gid` | Primary group SID |
| `display_name` | `realName` / GECOS | `FullName` |
| `description` | `description` | `Description` |
| `home_dir` | `homeDirectory` (`/var/home/<user>`) | `C:\Users\<user>` |
| `shell` | `shell` (`/bin/bash`) | Ignored |
| `enabled` | `locked: false` | `Enabled: true` |
| `is_admin` | Supplementary `wheel` membership | `Administrators` group membership |
| `password_hash` | `privileged.hashedPassword` ($6$ / $y$) | Re-hashed / unmanaged locally |

## Security & Safety Guardrails
1. **Break-Glass Protection**: Core system accounts (`root`, `mios`, `Administrator`, `DefaultAccount`, `Guest`, `WDAGUtilityAccount`, `mios-sudo`, `SYSTEM`) are never modified or deleted by automated synchronization.
2. **Degrade-Open Reliability**: If PostgreSQL is unreachable, synchronization daemons log telemetry, touch error markers, and preserve existing local user/group state without destructive pruning.
3. **Bounded Pruning**: Deletion actions only prune entities explicitly tracked in the projection state file (`/var/lib/mios/accounts-state.json` on Linux, `C:\ProgramData\MiOS\accountsync-managed.json` on Windows).
4. **Credential Isolation**: Plaintext credentials are never written to disk or logged; only cryptographically hashed values ($6$ / $y$) are persisted.

## Synchronization Lifecycles
- Linux: `mios-account-project.service` (oneshot on boot) and `mios-account-project.timer` (periodic 15m reconciliation).
- Windows: Scheduled task executing `MiOS-AccountSync.ps1` single-pass loopback query via WSL2.