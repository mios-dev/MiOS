<!-- AI-hint: DESIGN.
     AI-related: usr/share/mios/mios.toml, docs/adr/, AGY-TASKS.md -->
# DESIGN

## schema_sql
-- File: usr/share/mios/postgres/accounts-schema.sql  (include from schema-init.sql, or append verbatim).
-- Validated by review against PG14+ (matches the CREATE-OR-REPLACE-TRIGGER / GENERATED-IDENTITY
-- idioms already used in schema-init.sql). No live engine was reachable in-session (podman machine
-- down), so every construct was chosen to match features the existing schema-init.sql already relies on.

-- AI-hint: MiOS database-managed accounts SSOT (WS-ACCT / ACCT-03). The normalized,
--   Postgres-standards accounts schema that IS the accounts source-of-truth (itself
--   projected from mios.toml [accounts]) and is projected OUT to systemd userdb JSON
--   (Linux, nss-systemd) and Windows New-LocalUser (autounattend/SetupComplete +
--   first-boot reconcile). Parameterized callers ONLY (mios-pg-query --exec-json);
--   this file is DDL. Idempotent + migration-safe -- runs at every schema-init.
-- AI-related: usr/share/mios/postgres/schema-init.sql, usr/libexec/mios/seed-db-config.py,
--   usr/lib/mios/mios_accounts.py, usr/libexec/mios/mios-accounts-projector,
--   usr/libexec/mios/mios-account-sync, usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py,
--   mios.toml [accounts] / [[autounattend.accounts]] / [identity]
--
-- SUPERSEDES the flat, ALTER-grown `public.account` table (uid/gid/groups CSV/
-- is_admin/os_targets/password_hash) and the mios_identity.canonical_users/aliases
-- pair as the accounts modelling surface. Those legacy tables remain in place for
-- the owner_user/RLS linkage and are back-filled ONE-WAY from these tables by the
-- projector during migration (see §Migration at foot); no legacy row is rewritten
-- by this file.

-- citext: case-insensitive UNIQUE for username / group name. POSIX names are
-- case-sensitive, but the Windows SAM is case-insensitive, so MiOS treats
-- "Mios" == "mios" to keep a single row projecting safely to BOTH platforms.
CREATE EXTENSION IF NOT EXISTS citext;

-- ── POSIX id allocators ───────────────────────────────────────────────────────
-- Regular (login) accounts/groups get ids >= 1000; the system range (< 1000) is
-- reserved and never auto-allocated here. uid and gid are SEPARATE Linux
-- namespaces (their numeric ranges may overlap) -> two sequences, not one. The
-- setval reconcilers at the foot keep each sequence ahead of the max id already
-- present, so a re-run (or a migration that pre-loads higher ids) never collides.
CREATE SEQUENCE IF NOT EXISTS mios_uid_seq AS integer START WITH 1000 MINVALUE 1000;
CREATE SEQUENCE IF NOT EXISTS mios_gid_seq AS integer START WITH 1000 MINVALUE 1000;

-- ── updated_at touch trigger (shared) ─────────────────────────────────────────
-- BEFORE UPDATE: stamp updated_at = now() on every mutation, regardless of what
-- the caller sent, so updated_at is authoritative (callers never set it).
CREATE OR REPLACE FUNCTION mios_accounts_touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;
COMMENT ON FUNCTION mios_accounts_touch_updated_at() IS
    'BEFORE UPDATE trigger: forces updated_at = now() on mios_account / mios_group.';

-- ══════════════════════════════════════════════════════════════════════════════
-- mios_group -- POSIX groups (Linux) / local groups (Windows).
-- ══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS mios_group (
    id          bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        citext      NOT NULL UNIQUE
                    CONSTRAINT mios_group_name_format
                    CHECK ((name)::text ~ '^[a-z_][a-z0-9_-]{0,31}$'),
    gid         integer     NOT NULL UNIQUE DEFAULT nextval('mios_gid_seq')
                    CONSTRAINT mios_group_gid_nonneg CHECK (gid >= 0),
    description text,
    is_system   boolean     NOT NULL DEFAULT false,   -- true = pre-seeded/system group (not operator-managed)
    meta        jsonb       NOT NULL DEFAULT '{}'::jsonb,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
-- Forward-compat: bring an older mios_group up to the current column set (no-op
-- once the CREATE above has run on a fresh DB).
ALTER TABLE mios_group ADD COLUMN IF NOT EXISTS is_system  boolean     NOT NULL DEFAULT false;
ALTER TABLE mios_group ADD COLUMN IF NOT EXISTS meta       jsonb       NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE mios_group ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

COMMENT ON TABLE  mios_group             IS 'MiOS-managed groups (POSIX group on Linux, local group on Windows). SSOT projected from mios.toml [accounts].';
COMMENT ON COLUMN mios_group.id          IS 'Surface primary key (opaque). Stable across gid renumbering.';
COMMENT ON COLUMN mios_group.name        IS 'Group name, case-insensitive-unique. Projects to the POSIX group name and the Windows local-group name.';
COMMENT ON COLUMN mios_group.gid         IS 'Numeric POSIX GID (unique). Auto-allocated from mios_gid_seq (>=1000) when not supplied.';
COMMENT ON COLUMN mios_group.description IS 'Human description / GECOS for the group.';
COMMENT ON COLUMN mios_group.is_system   IS 'true = seeded/system group managed by MiOS, hidden from the operator applet''s default list.';
COMMENT ON COLUMN mios_group.meta        IS 'Extensible JSONB (Windows well-known-SID hints, projection overrides, etc.).';
COMMENT ON COLUMN mios_group.created_at  IS 'Row creation timestamp.';
COMMENT ON COLUMN mios_group.updated_at  IS 'Last-mutation timestamp (maintained by the touch trigger).';

CREATE OR REPLACE TRIGGER mios_group_touch_updated_at
    BEFORE UPDATE ON mios_group
    FOR EACH ROW EXECUTE FUNCTION mios_accounts_touch_updated_at();

-- Seed the default primary/login group so every account has a valid primary_gid
-- FK target on a fresh DB. Explicit gid 1000; the setval reconciler at the foot
-- pushes mios_gid_seq past it so no auto group collides. Idempotent (untargeted
-- ON CONFLICT covers both the name and gid unique constraints).
INSERT INTO mios_group (name, gid, description, is_system)
VALUES ('mios', 1000, 'Default MiOS primary/login group', true)
ON CONFLICT DO NOTHING;

-- ══════════════════════════════════════════════════════════════════════════════
-- mios_account -- one row per MiOS-managed OS account (human user or service).
-- ══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS mios_account (
    id             bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username       citext      NOT NULL UNIQUE
                       CONSTRAINT mios_account_username_format
                       CHECK ((username)::text ~ '^[a-z_][a-z0-9_-]{0,31}$'),
    uid            integer     NOT NULL UNIQUE DEFAULT nextval('mios_uid_seq')
                       CONSTRAINT mios_account_uid_nonneg CHECK (uid >= 0),
    primary_gid    integer     NOT NULL DEFAULT 1000
                       REFERENCES mios_group(gid) ON UPDATE CASCADE ON DELETE RESTRICT,
    display_name   text,                              -- GECOS / full name
    description    text,
    home_dir       text,                              -- NULL -> projector derives ('/var/home/<username>' | 'C:\Users\<username>')
    shell          text        NOT NULL DEFAULT '/bin/bash',
    enabled        boolean     NOT NULL DEFAULT true, -- false = account disabled (locked), NOT deleted
    is_admin       boolean     NOT NULL DEFAULT false,-- true -> wheel/sudo (Linux) + Administrators (Windows)
    is_service     boolean     NOT NULL DEFAULT false,-- service / RID-500-renamed system account (no interactive profile churn)
    password_hash  text,                              -- HASHED ONLY, never plaintext (crypt $6$/$y$; NULL = no password set)
    must_change_pw boolean     NOT NULL DEFAULT false,-- force credential change at next logon
    on_linux       boolean     NOT NULL DEFAULT true, -- project this account to the Linux/userdb surface
    on_windows     boolean     NOT NULL DEFAULT true, -- project this account to the Windows/New-LocalUser surface
    meta           jsonb       NOT NULL DEFAULT '{}'::jsonb,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    -- At least one platform must be in scope, else the row projects nowhere.
    CONSTRAINT mios_account_platform_scope CHECK (on_linux OR on_windows)
);
-- Forward-compat migrations for an older mios_account (each is a no-op on a fresh DB).
ALTER TABLE mios_account ADD COLUMN IF NOT EXISTS is_service     boolean     NOT NULL DEFAULT false;
ALTER TABLE mios_account ADD COLUMN IF NOT EXISTS must_change_pw boolean     NOT NULL DEFAULT false;
ALTER TABLE mios_account ADD COLUMN IF NOT EXISTS on_linux       boolean     NOT NULL DEFAULT true;
ALTER TABLE mios_account ADD COLUMN IF NOT EXISTS on_windows     boolean     NOT NULL DEFAULT true;
ALTER TABLE mios_account ADD COLUMN IF NOT EXISTS meta           jsonb       NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE mios_account ADD COLUMN IF NOT EXISTS updated_at     timestamptz NOT NULL DEFAULT now();

COMMENT ON TABLE  mios_account                IS 'MiOS-managed OS accounts (SSOT). Projected to systemd userdb JSON (Linux) and New-LocalUser (Windows). Passwords stored HASHED only.';
COMMENT ON COLUMN mios_account.id             IS 'Surface primary key (opaque). Stable across uid/username changes; FK target for mios_account_group.';
COMMENT ON COLUMN mios_account.username       IS 'Login name, case-insensitive-unique. Projects to the POSIX user name and the Windows local-account name.';
COMMENT ON COLUMN mios_account.uid            IS 'Numeric POSIX UID (unique). Auto-allocated from mios_uid_seq (>=1000) when not supplied. Windows uses it only as a stable numeric handle.';
COMMENT ON COLUMN mios_account.primary_gid    IS 'Primary group GID (FK -> mios_group.gid). Defaults to the seeded ''mios'' group (1000).';
COMMENT ON COLUMN mios_account.display_name   IS 'GECOS / full display name (Linux GECOS field; Windows -FullName).';
COMMENT ON COLUMN mios_account.description    IS 'Free-text account description (Windows -Description; userdb realName/description).';
COMMENT ON COLUMN mios_account.home_dir       IS 'Home directory. NULL -> projector derives per platform (/var/home/<u> | C:\Users\<u>).';
COMMENT ON COLUMN mios_account.shell          IS 'Login shell (Linux). Ignored on Windows. Default /bin/bash.';
COMMENT ON COLUMN mios_account.enabled        IS 'false disables/locks the account (userdb ''locked''; New-LocalUser -Disabled) WITHOUT deleting the row.';
COMMENT ON COLUMN mios_account.is_admin       IS 'true adds the account to the admin set: wheel/sudo on Linux, Administrators on Windows.';
COMMENT ON COLUMN mios_account.is_service     IS 'true = service / RID-500-renamed system account; projector suppresses interactive-profile side effects.';
COMMENT ON COLUMN mios_account.password_hash  IS 'HASHED password ONLY (never plaintext). crypt $6$/$y$ for Linux shadow; the Windows leg re-hashes at set time. NULL = no password.';
COMMENT ON COLUMN mios_account.must_change_pw IS 'true forces a credential change at next logon (chage -d 0 / -ChangePasswordAtLogon).';
COMMENT ON COLUMN mios_account.on_linux       IS 'Include this account in the Linux (userdb) projection.';
COMMENT ON COLUMN mios_account.on_windows     IS 'Include this account in the Windows (New-LocalUser) projection.';
COMMENT ON COLUMN mios_account.meta           IS 'Extensible JSONB (SSH keys, SID overrides, per-account projection hints).';
COMMENT ON COLUMN mios_account.created_at     IS 'Row creation timestamp.';
COMMENT ON COLUMN mios_account.updated_at     IS 'Last-mutation timestamp (maintained by the touch trigger); the projector/sync high-water mark.';

CREATE OR REPLACE TRIGGER mios_account_touch_updated_at
    BEFORE UPDATE ON mios_account
    FOR EACH ROW EXECUTE FUNCTION mios_accounts_touch_updated_at();

-- ══════════════════════════════════════════════════════════════════════════════
-- mios_account_group -- supplementary group membership (M:N). Composite PK.
-- Primary-group membership is NOT stored here (it lives in mios_account.primary_gid);
-- this table is the SUPPLEMENTARY set only.
-- ══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS mios_account_group (
    account_id bigint      NOT NULL REFERENCES mios_account(id) ON DELETE CASCADE,
    group_id   bigint      NOT NULL REFERENCES mios_group(id)   ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (account_id, group_id)
);
COMMENT ON TABLE  mios_account_group            IS 'Supplementary group membership (M:N). Primary group is mios_account.primary_gid, not stored here.';
COMMENT ON COLUMN mios_account_group.account_id IS 'FK -> mios_account.id (ON DELETE CASCADE).';
COMMENT ON COLUMN mios_account_group.group_id   IS 'FK -> mios_group.id (ON DELETE CASCADE).';
COMMENT ON COLUMN mios_account_group.created_at IS 'Membership grant timestamp.';

-- ── Indexes ───────────────────────────────────────────────────────────────────
-- Reverse-lookup index for "who is in this group" (the PK covers account->group).
CREATE INDEX IF NOT EXISTS mios_account_group_group_idx ON mios_account_group (group_id);
-- Partial indexes for the two projector scans (only the in-scope rows).
CREATE INDEX IF NOT EXISTS mios_account_linux_idx   ON mios_account (username) WHERE on_linux;
CREATE INDEX IF NOT EXISTS mios_account_windows_idx ON mios_account (username) WHERE on_windows;
-- High-water-mark scan for incremental projector/sync runs.
CREATE INDEX IF NOT EXISTS mios_account_updated_idx ON mios_account (updated_at);
-- FK-support index (primary_gid is not otherwise indexed; speeds group deletes/renumbers).
CREATE INDEX IF NOT EXISTS mios_account_primary_gid_idx ON mios_account (primary_gid);

-- ══════════════════════════════════════════════════════════════════════════════
-- mios_account_export -- the ONE read surface the projectors consume. Pre-joins
-- the primary group name and aggregates the supplementary group name/gid arrays,
-- so a projector query is parameter-free and platform-filtered (WHERE on_linux).
-- ══════════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW mios_account_export AS
SELECT
    a.id,
    a.username,
    a.uid,
    a.primary_gid,
    pg.name                              AS primary_group,
    a.display_name,
    a.description,
    a.home_dir,
    a.shell,
    a.enabled,
    a.is_admin,
    a.is_service,
    a.password_hash,
    a.must_change_pw,
    a.on_linux,
    a.on_windows,
    COALESCE(
        (SELECT array_agg(g.name ORDER BY g.name)
           FROM mios_account_group m JOIN mios_group g ON g.id = m.group_id
          WHERE m.account_id = a.id),
        ARRAY[]::citext[]
    )                                    AS member_groups,
    COALESCE(
        (SELECT array_agg(g.gid ORDER BY g.gid)
           FROM mios_account_group m JOIN mios_group g ON g.id = m.group_id
          WHERE m.account_id = a.id),
        ARRAY[]::integer[]
    )                                    AS member_gids,
    a.meta,
    a.updated_at
FROM mios_account a
JOIN mios_group pg ON pg.gid = a.primary_gid;
COMMENT ON VIEW mios_account_export IS
    'Denormalized projector read surface: primary group + supplementary group name/gid arrays per account. Filter by on_linux / on_windows.';

-- ══════════════════════════════════════════════════════════════════════════════
-- Change notification -- LISTEN/NOTIFY seam for the live reconcile agent
-- (mios-account-sync). Channel: mios_account_sync. Payloads are compact JSON
-- (identity + which side changed); the listener re-reads mios_account_export for
-- the authoritative record, so the payload need not carry every column.
-- ══════════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION mios_account_notify()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_notify('mios_account_sync', json_build_object(
        'entity',   'account',
        'action',   TG_OP,
        'id',       COALESCE(NEW.id, OLD.id),
        'username', COALESCE(NEW.username, OLD.username)::text
    )::text);
    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE OR REPLACE FUNCTION mios_group_notify()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_notify('mios_account_sync', json_build_object(
        'entity', 'group',
        'action', TG_OP,
        'id',     COALESCE(NEW.id, OLD.id),
        'name',   COALESCE(NEW.name, OLD.name)::text,
        'gid',    COALESCE(NEW.gid, OLD.gid)
    )::text);
    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE OR REPLACE FUNCTION mios_account_group_notify()
RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_username citext;
    v_group    citext;
BEGIN
    SELECT username INTO v_username FROM mios_account WHERE id = COALESCE(NEW.account_id, OLD.account_id);
    SELECT name     INTO v_group    FROM mios_group   WHERE id = COALESCE(NEW.group_id,   OLD.group_id);
    PERFORM pg_notify('mios_account_sync', json_build_object(
        'entity',   'membership',
        'action',   TG_OP,
        'username', v_username::text,
        'group',    v_group::text
    )::text);
    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE OR REPLACE TRIGGER mios_account_notify_trigger
    AFTER INSERT OR UPDATE OR DELETE ON mios_account
    FOR EACH ROW EXECUTE FUNCTION mios_account_notify();
CREATE OR REPLACE TRIGGER mios_group_notify_trigger
    AFTER INSERT OR UPDATE OR DELETE ON mios_group
    FOR EACH ROW EXECUTE FUNCTION mios_group_notify();
CREATE OR REPLACE TRIGGER mios_account_group_notify_trigger
    AFTER INSERT OR UPDATE OR DELETE ON mios_account_group
    FOR EACH ROW EXECUTE FUNCTION mios_account_group_notify();

-- ══════════════════════════════════════════════════════════════════════════════
-- Least-privilege roles. Group (NOLOGIN) roles the app's LOGIN role is granted
-- membership in. CREATE ROLE is not itself idempotent, so guard on pg_roles.
--   mios_accounts_ro : SELECT on tables + the export view (projector / sync read,
--                      applet read, drift-gate). NO write.
--   mios_accounts_rw : ro + INSERT/UPDATE/DELETE on the three tables + sequence
--                      USAGE (CLI / applet write path). NO DDL, NO TRUNCATE.
-- ══════════════════════════════════════════════════════════════════════════════
DO $roles$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mios_accounts_ro') THEN
        CREATE ROLE mios_accounts_ro NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mios_accounts_rw') THEN
        CREATE ROLE mios_accounts_rw NOLOGIN;
    END IF;
END
$roles$;

-- Read grants (idempotent).
GRANT USAGE ON SCHEMA public TO mios_accounts_ro;
GRANT SELECT ON mios_account, mios_group, mios_account_group, mios_account_export
    TO mios_accounts_ro;

-- Write grants: rw inherits ro, adds DML + sequence advance. No TRUNCATE/DDL.
GRANT mios_accounts_ro TO mios_accounts_rw;
GRANT INSERT, UPDATE, DELETE ON mios_account, mios_group, mios_account_group
    TO mios_accounts_rw;
GRANT USAGE, SELECT ON SEQUENCE mios_uid_seq, mios_gid_seq TO mios_accounts_rw;

-- Bridge to the actual login role MiOS connects as (MIOS_PG_USER, default 'mios').
-- Grant membership so existing connections keep working under least privilege;
-- guarded so a non-standard deployment role name never aborts schema-init.
DO $bridge$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mios') THEN
        GRANT mios_accounts_rw TO mios;
    END IF;
END
$bridge$;

-- ══════════════════════════════════════════════════════════════════════════════
-- Sequence reconcilers -- keep the allocators ahead of the max id present. Safe
-- on every re-run and after a migration that pre-loads higher ids (idempotent;
-- the false 3rd arg makes the NEXT nextval return the set value on an empty table).
-- ══════════════════════════════════════════════════════════════════════════════
SELECT setval('mios_uid_seq',
    GREATEST((SELECT COALESCE(max(uid), 999) FROM mios_account), 999), true);
SELECT setval('mios_gid_seq',
    GREATEST((SELECT COALESCE(max(gid), 999) FROM mios_group),   999), true);

## contracts
COMPONENT CONTRACTS -- how each consumer calls the data layer. All roads go through ONE data-access module; no consumer emits raw/interpolated SQL.

== 0. Data layer: usr/lib/mios/mios_accounts.py  (NEW; the single choke point) ==
The only module that talks to the accounts tables. Every function builds a parameterized envelope and executes it via the existing injection-safe transport `mios-pg-query --exec-json` (extended protocol Parse/Bind/Execute; envelope {"sql","params"} for one statement, {"statements":[{sql,params},...]} for an atomic BEGIN/COMMIT transaction). Reads may alternatively use psycopg with bound params. Connection config comes from mios_db_config.get_pg_config(). NEVER f-string/%-interpolate a value into SQL -- values are always in `params`.

Public API (typed; hashing happens here, never in a caller):
  list_accounts(platform=None, include_disabled=True) -> list[dict]   # SELECT * FROM mios_account_export [WHERE on_linux/on_windows]
  get_account(username) -> dict|None                                   # WHERE username = $1
  create_account(username, *, display_name=None, description=None, uid=None, primary_gid=1000, shell='/bin/bash', is_admin=False, is_service=False, on_linux=True, on_windows=True, password=None, must_change_pw=False, groups=()) -> dict
        # one {"statements":[...]} txn: INSERT INTO mios_account (...) VALUES ($1..) RETURNING id; then per group INSERT INTO mios_account_group SELECT $acct,id FROM mios_group WHERE name=$g. Password hashed here -> password_hash param.
  update_account(username, **fields) -> dict                           # UPDATE mios_account SET <col>=$n,... WHERE username=$k  (whitelisted columns only; updated_at handled by trigger)
  set_password(username, plaintext, must_change_pw=False) -> None      # hash -> UPDATE mios_account SET password_hash=$1, must_change_pw=$2 WHERE username=$3
  set_enabled(username, enabled) -> None
  delete_account(username) -> None                                     # DELETE FROM mios_account WHERE username=$1 (CASCADE clears memberships)
  list_groups() / create_group(name, gid=None, description=None) / delete_group(name)
  set_members(username, group_names) / add_member(username, group) / remove_member(username, group)
        # membership writes resolve names->ids in-SQL: INSERT ... SELECT a.id,g.id FROM mios_account a, mios_group g WHERE a.username=$1 AND g.name=$2 ON CONFLICT DO NOTHING
  export(platform) -> list[dict]                                       # thin alias over the view for the projector
Errors surface as typed exceptions (DuplicateUsername on 23505, UnknownGroup on 23503, FormatError on 23514) mapped from SQLSTATE.

== 1. CLI: `mios accounts` (verb -> usr/libexec/mios/mios-accounts, dispatched by the verb catalog) ==
Subcommands: list | show <u> | add <u> [--admin --service --display --shell --groups a,b --linux/--no-linux --windows/--no-windows --password-stdin] | mod <u> [same flags] | passwd <u> [--stdin --must-change] | enable/disable <u> | del <u> | group list|add|del | sync (invoke projector+reconcile). Each subcommand is a thin argparse wrapper that calls exactly one mios_accounts.py function and prints a table/JSON. Read subcommands connect ro; mutating ones rw. No SQL in this file.

== 2. Projector: usr/libexec/mios/mios-accounts-projector (SSOT -> surfaces; bake/sync-time) ==
`mios-accounts-projector [--platform linux|windows] [--check]`.
  - Linux: mios_accounts.export('linux') -> writes /usr/lib/userdb/<username>.user + <group>.group JSON drop-ins (0644; privileged sub-object 0600), atomically (temp+rename), removing drop-ins whose username is no longer present/on_linux. Field mapping per the field_mapping deliverable.
  - Windows: mios_accounts.export('windows') -> writes the account manifest JSON the autounattend SetupComplete / first-boot reconcile PowerShell reads (New-LocalUser feed).
  - `--check` = drift-gate mode: byte/normalize-compare the on-disk artifacts against a fresh projection, exit non-zero on drift (new check in the 25-41 drift-gate family), NEVER writes. Read-only (ro role). Mirrors mios-theme-render/dotfiles-render.
Runs at build (bake), on `mios sync`, and on demand.

== 3. Admin applet: accounts panel in the Portal (:8640) ==
New routes co-located on portal_router in portal.py (same pattern as /portal/config): all gated by `_portal_authed(request)` (401 JSON otherwise); blocking DB calls run off the event loop via `await asyncio.to_thread(...)`.
  GET  /portal/accounts                 -> JSONResponse(mios_accounts.list_accounts())          [ro]
  GET  /portal/accounts/{username}      -> get_account                                          [ro]
  POST /portal/accounts                 -> create_account(**json_body)                          [rw]
  PUT  /portal/accounts/{username}      -> update_account                                       [rw]
  POST /portal/accounts/{username}/password -> set_password (plaintext accepted here, hashed in data layer; response never echoes it)  [rw]
  POST /portal/accounts/{username}/enabled  -> set_enabled                                      [rw]
  DELETE /portal/accounts/{username}    -> delete_account                                       [rw]
  GET/POST/DELETE /portal/groups[...]   -> group + membership functions                         [rw]
  POST /portal/accounts/sync            -> background_tasks.add_task(run projector+reconcile)    (degrade-open, like run_db_reseed_bg)
Handlers call ONLY mios_accounts.py -- no SQL, no direct psycopg -- and return typed errors as 400/409/422. The panel is a sub-view of the existing Portal shell (served by portal_page_logic), consistent with the /configure configurator surface.

== 4. Sync agent: usr/libexec/mios/mios-account-sync (DB -> live OS; runtime reconcile) ==
Supersedes the legacy account/aliases reads with the normalized tables. LISTEN on channel `mios_account_sync` (the notify triggers in the schema) for low-latency reaction, PLUS a periodic full reconcile (idempotent) as the store-and-forward / offline safety net. On wake it re-reads `mios_account_export` (authoritative; payload is only a hint) and:
  - Linux: reconciles /etc/passwd,/etc/shadow,/etc/group via useradd/usermod/gpasswd (or by re-invoking the projector to refresh userdb drop-ins). Password write-BACK (a locally-rotated hash flowing to the SSOT) uses mios_accounts.set_password-equivalent parameterized UPDATE (rw).
  - Windows: drives New-LocalUser/Set-LocalUser/Add-LocalGroupMember from the manifest.
Keeps a /var/lib/mios state file for high-water/idempotency. Always leaves the break-glass local admin untouched.

SEEDING (mios.toml [accounts]/[[autounattend.accounts]] -> rows): seed-db-config.py gains an accounts pass that UPSERTs each [accounts]/[[autounattend.accounts]] entry via parameterized INSERT ... ON CONFLICT (username) DO UPDATE, resolving [identity] defaults (shell, default_password->hash, groups). This makes Postgres the accounts SSOT that is itself projected from mios.toml, closing the SSOT loop.

MIGRATION (one-way, additive): a step copies legacy public.account rows (name/uid/gid/is_admin/os_targets/password_hash/home_dir/shell) and mios_identity.canonical_users into mios_account/mios_group (INSERT ... ON CONFLICT DO NOTHING), then the projector back-fills the legacy owner_user linkage. No legacy row is rewritten by the schema; the legacy tables stay for RLS owner linkage until a later hard-FK cutover.

## field_mapping
USER-RECORD FIELD MAPPING  (mios_account/mios_group column -> systemd userdb JSON [systemd.io/USER_RECORD] -> Windows New-LocalUser / Local* cmdlet)

Read the row via the `mios_account_export` view (primary_group + member_groups[]/member_gids[] already aggregated). "userdb JSON" = the object written to /usr/lib/userdb/<username>.user (0644) that nss-systemd serves. "Windows" = the projected account-manifest entry the SetupComplete/first-boot reconcile PowerShell consumes.

| DB column (mios_account_export) | systemd userdb JSON | Windows (New-LocalUser / Local* cmdlet) | Notes |
|---|---|---|---|
| username           | "userName": <str>                     | -Name <str>                                             | Identity key on both. citext-unique. |
| uid                | "uid": <int>                          | (stable numeric handle in meta; Windows assigns its own RID) | userdb also needs matching gid; Windows has no uid. |
| primary_gid        | "gid": <int>                          | primary group not set at create; enforced via Add-LocalGroupMember(primary_group) | userdb primary group = gid. |
| primary_group      | (name resolved into the group's own <gid>.group record) | -                                                      | Emit a companion /usr/lib/userdb/<group>.group record. |
| display_name       | "realName": <str>                     | -FullName <str>                                         | GECOS. Omit key when NULL. |
| description        | "description": <str>                  | -Description <str>                                      | Free text. |
| home_dir (NULL)    | "homeDirectory": "/var/home/<u>"      | profile path C:\Users\<u> (implicit; not a New-LocalUser arg) | NULL -> projector derives per-platform default. |
| shell              | "shell": <str>                        | (n/a on Windows)                                        | Default /bin/bash. |
| enabled=false      | "locked": true                        | Disable-LocalUser -Name <u>  (create with -Disabled)    | enabled=true -> omit "locked"/Enable-LocalUser. Never deletes. |
| is_admin=true      | "memberOf": [... "wheel"]  (+ sudo drop-in) | Add-LocalGroupMember -Group "Administrators" -Member <u> | Linux admin = wheel membership. |
| is_service=true    | "disposition": "system"               | account created but interactive-profile steps skipped   | is_service=false -> "disposition":"regular". |
| password_hash      | "privileged": { "hashedPassword": [<crypt $6$/$y$>] } | -Password <SecureString>  (reconcile re-hashes to NTLM at set time; hash is NOT reused verbatim) | HASHED only. The privileged sub-object is chmod-0600 / served only to root by userdbd. NULL -> no password. |
| must_change_pw     | (no native userdb field) -> emit sidecar so first-boot runs `chage -d 0 <u>` | net user <u> /logonpasswordchg:yes  (or -ChangePasswordAtLogon via WMI) | Carried in the projector sidecar / meta, applied by the reconcile step. |
| on_linux           | row emitted to /usr/lib/userdb only when true | -                                                | Platform scope filter (WHERE on_linux). |
| on_windows         | -                                     | row emitted to the Windows manifest only when true      | Platform scope filter (WHERE on_windows). |
| member_groups[]    | "memberOf": [<names>]                 | foreach g: Add-LocalGroupMember -Group g -Member <u>    | Supplementary groups (excludes primary). |
| member_gids[]      | (companion <gid>.group records)       | -                                                       | Ensures each supplementary group exists as a group record. |
| meta.ssh_authorized_keys (opt) | "sshAuthorizedKeys": [...]  | (n/a)                                                   | Optional, pulled from meta JSONB. |
| updated_at         | (not projected; drift/high-water only)| (same)                                                  | Projector compares against on-disk artifact mtime/hash. |

mios_group -> systemd <name>.group JSON: name->"groupName", gid->"gid", description->"description". Windows: New-LocalGroup -Name <name> -Description <description>.

BREAK-GLASS: a local root/Administrator account always remains in /etc/passwd (Linux) and the autounattend RID-500 bootstrap (Windows) independent of this table -- never gated by on_linux/on_windows -- so a DB outage can never lock the box out (per doc-postgresos-accounts.md §3a/§4).

## roles
DB ROLE / PERMISSION MODEL

Two NOLOGIN group roles (created idempotently in the schema, guarded on pg_roles):

- mios_accounts_ro  -- USAGE on schema public; SELECT on mios_account, mios_group, mios_account_group, and the mios_account_export view. NO INSERT/UPDATE/DELETE, NO sequence access, NO DDL.
- mios_accounts_rw  -- granted mios_accounts_ro (inherits all reads) PLUS INSERT/UPDATE/DELETE on the three base tables and USAGE,SELECT on mios_uid_seq / mios_gid_seq. NO TRUNCATE, NO DDL, NO role management, NO access to unrelated agent-plane tables.

Login roles connect as MIOS_PG_USER (default 'mios', the existing connection identity used by get_pg_config() in mios_db_config.py / seed-db-config.py / mios-pg-query). The schema GRANTs mios_accounts_rw to 'mios' (guarded) so current connection strings keep working while gaining exactly these privileges and nothing table-specific beyond them. Deployments that want privilege separation point read-only consumers at a login role granted only mios_accounts_ro.

Component -> role:
- mios accounts CLI (read subcommands: list/show/export)        -> mios_accounts_ro
- mios accounts CLI (write subcommands: add/mod/del/passwd/group)-> mios_accounts_rw
- Portal Admin applet GET routes  (/portal/accounts, .../{u})    -> mios_accounts_ro
- Portal Admin applet POST/PUT/DELETE routes                     -> mios_accounts_rw
- mios-accounts-projector (reads mios_account_export -> drop-ins) -> mios_accounts_ro
- Drift-gate (checks projected artifacts vs SSOT)                -> mios_accounts_ro
- mios-account-sync (reads export; writes back rotated pw hash)  -> mios_accounts_rw (needs the UPDATE password_hash write-back path; otherwise read-only)
- seed-db-config.py (projects mios.toml [accounts] -> rows)      -> mios_accounts_rw

RLS: these three tables are federation-global identity data and are deliberately OUTSIDE the WS-5 owner_user RLS set (same posture as peer_reputation / the legacy `account` table). No mios.owner_user GUC scoping applies. Row visibility is governed purely by the ro/rw grants above.

SECRET HYGIENE: password_hash holds crypt hashes only. The Portal applet and CLI MUST refuse a plaintext password field and hash before insert (openssl passwd -6 / crypt). The existing config_kv/config_event redaction denylist already masks password/secret keys; account writes go through the tables (not config_kv) so they never enter the config audit trail verbatim.

PARAMETERIZATION MANDATE (enforced by the data layer, not the DB grants): every write is a bound-parameter statement ($1..$n) via mios-pg-query --exec-json or psycopg parameters. No component builds SQL by string interpolation. Group roles cannot compensate for injection, so this is a hard code-review gate for all build agents.


# COMPONENT: Linux systemd-userdb projector: mios-account-project (Phase 2) + its oneshot .service, reconcile .timer, and the install/enable wiring in automation/17-accounts-db.sh


## new usr/libexec/mios/mios-account-project

```
#!/usr/bin/env python3
# AI-hint: The Linux systemd-userdb projector (WS-ACCT / ACCT-03, Phase 2). Projects the
#   Postgres accounts SSOT (mios_account_export, itself projected from mios.toml [accounts])
#   OUT to systemd userdb JSON User/Group records under /usr/lib/userdb (bake) or /etc/userdb
#   (runtime) that nss-systemd serves -- the SSOT-projection twin of mios-dotfiles-render, but
#   sourced from Postgres instead of [colors]. Idempotent (atomic temp+rename), prunes drop-ins
#   for accounts/groups no longer present, and drift-gateable (--check, read-only). All DB reads
#   go through mios_accounts.py (parameterized, ro role); this file emits NO SQL.
# AI-related: usr/lib/mios/mios_accounts.py, usr/share/mios/postgres/accounts-schema.sql,
#   usr/libexec/mios/mios-account-sync, usr/libexec/mios/mios-dotfiles-render,
#   usr/lib/mios/mios_db_config.py, mios-account-project.service, mios-account-project.timer,
#   mios.toml [accounts] / [identity], /usr/lib/userdb, nss-systemd
# AI-functions: _root, _userdb_dir, _state_path, _derive_home, _user_record, _group_record,
#   _canon, _project, _load_state, _save_state, cmd_render, cmd_check, main
"""Linux systemd-userdb projector: render/prune/check MiOS accounts as userdb drop-ins.

The Postgres accounts tables are the SSOT (projected from mios.toml [accounts]). This
tool projects the Linux-scoped rows (WHERE on_linux) to systemd User Record + Group
Record JSON drop-ins that nss-systemd serves, so `getent passwd`/`id`/PAM resolve
DB-managed accounts with no NSS module of our own.

Modes:
  mios-account-project                 render + prune (default; bake / sync / on-demand)
  mios-account-project --check         drift-gate: compare on-disk vs a fresh projection,
                                       exit 1 on drift, NEVER writes (read-only, ro role)
  mios-account-project --platform linux    explicit platform select (linux is the only leg
                                            this tool implements; the Windows manifest leg
                                            lives in the broader mios-accounts-projector)

Target directory precedence (systemd searches /etc/userdb, /run/userdb, /usr/lib/userdb):
  * bake time  -> /usr/lib/userdb (the image default; /usr is writable during the build)
  * runtime    -> /etc/userdb     (the .service passes MIOS_USERDB_DIR; /usr is read-only
                                   on a booted bootc host, /etc persists)
Override with MIOS_USERDB_DIR. A per-directory state manifest under /var/lib/mios records
which basenames this projector owns, so pruning only ever removes MiOS-managed drop-ins and
never touches foreign userdb records or the break-glass local root in /etc/passwd.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Repo/system root: two dirs up from usr/libexec/mios/, overridable (mirrors
# mios-dotfiles-render so the same layout resolves at bake and at runtime).
_SELF = os.path.abspath(__file__)


def _root() -> str:
    return os.environ.get("MIOS_ROOT") or os.path.abspath(
        os.path.join(os.path.dirname(_SELF), "..", "..", "..")
    )


# The data layer (the ONLY module that talks to the accounts tables; parameterized,
# ro/rw roles). Imported from usr/lib/mios like every other MiOS python consumer.
sys.path.insert(0, os.path.join(_root(), "usr/lib/mios"))
sys.path.insert(0, "/usr/lib/mios")
try:
    import mios_accounts  # noqa: E402
except Exception as _e:  # pragma: no cover - surfaced at runtime, degrade-open
    mios_accounts = None
    _IMPORT_ERR = _e
else:
    _IMPORT_ERR = None


def _log(msg: str) -> None:
    sys.stderr.write(f"[mios-account-project] {msg}\n")


def _userdb_dir() -> str:
    """Target userdb drop-in directory. Default /usr/lib/userdb (bake); the runtime
    .service overrides to /etc/userdb via MIOS_USERDB_DIR (/usr is read-only when booted)."""
    return os.environ.get("MIOS_USERDB_DIR") or "/usr/lib/userdb"


def _state_path(userdb_dir: str) -> str:
    """Per-directory ownership manifest (which basenames we manage -> safe prune).
    Keyed by the target dir so a bake run (/usr/lib/userdb) and a runtime run
    (/etc/userdb) keep independent ownership sets."""
    key = userdb_dir.strip("/").replace("/", "-") or "root"
    base = os.environ.get("MIOS_STATE_DIR") or "/var/lib/mios"
    return os.path.join(base, f"account-project.{key}.json")


# ── record derivation ─────────────────────────────────────────────────────

def _derive_home(row: dict) -> str:
    """NULL home_dir -> the per-platform Linux default (/var/home/<u>, the
    Silverblue/bootc home location)."""
    return row.get("home_dir") or f"/var/home/{row['username']}"


def _as_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("t", "true", "y", "yes", "1")
    return bool(v)


def _as_list(v) -> list:
    """member_groups / member_gids arrive as a python list (psycopg) or a Postgres
    array literal string ('{a,b}') depending on the transport. Normalize to a list."""
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return list(v)
    s = str(v).strip()
    if s in ("", "{}", "None"):
        return []
    if s.startswith("{") and s.endswith("}"):
        inner = s[1:-1]
        return [p.strip().strip('"') for p in inner.split(",") if p.strip()]
    return [s]


def _user_record(row: dict) -> dict:
    """One mios_account_export row -> a systemd User Record (JSON User Record,
    systemd.io/USER_RECORD). Only the documented fields are emitted; unset optional
    fields are OMITTED so the artifact is stable and minimal. Password hashes go in
    the `privileged` sub-object -> the whole file is written 0600 (see _project)."""
    username = row["username"]
    rec: dict = {
        "userName": username,
        "disposition": "system" if _as_bool(row.get("is_service")) else "regular",
        "uid": int(row["uid"]),
        "gid": int(row["primary_gid"]),
        "homeDirectory": _derive_home(row),
        "shell": row.get("shell") or "/bin/bash",
    }
    real = row.get("display_name") or row.get("description")
    if real:
        rec["realName"] = real

    # Supplementary groups + the admin (wheel) grant. Primary group is `gid`, never
    # repeated here. Sorted -> deterministic artifact.
    member_of = set(str(g) for g in _as_list(row.get("member_groups")))
    if _as_bool(row.get("is_admin")):
        member_of.add("wheel")
    if member_of:
        rec["memberOf"] = sorted(member_of)

    # enabled=false -> locked (disable/lock WITHOUT deleting). Omit when enabled.
    if not _as_bool(row.get("enabled", True)):
        rec["locked"] = True

    # Optional SSH keys carried in meta JSONB.
    meta = row.get("meta")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta or "{}")
        except Exception:
            meta = {}
    if isinstance(meta, dict):
        keys = meta.get("ssh_authorized_keys") or meta.get("sshAuthorizedKeys")
        if isinstance(keys, list) and keys:
            rec["sshAuthorizedKeys"] = list(keys)

    # HASHED password ONLY, in the privileged sub-object. NULL -> no password field
    # (the file stays 0644). Present -> the record is sensitive -> 0600 whole-file.
    pw = row.get("password_hash")
    if pw:
        rec["privileged"] = {"hashedPassword": [pw]}
    return rec


def _group_record(grp: dict) -> dict:
    """One mios_group row -> a systemd Group Record. Membership is NOT listed here;
    nss-systemd derives it from each user record's memberOf."""
    rec: dict = {
        "groupName": str(grp["name"]),
        "disposition": "system" if _as_bool(grp.get("is_system")) else "regular",
        "gid": int(grp["gid"]),
    }
    if grp.get("description"):
        rec["description"] = grp["description"]
    return rec


def _canon(rec: dict) -> str:
    """Canonical on-disk bytes for a record -> deterministic render + byte-stable
    drift compare (sorted keys, 2-space indent, trailing newline)."""
    return json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _project() -> tuple[dict[str, tuple[str, bool]], list[str]]:
    """Build the full desired file set for the Linux userdb surface.

    Returns (desired, warnings):
      desired: basename -> (canonical_text, privileged) where basename is
               '<user>.user' / '<group>.group' and privileged marks 0600 files.
      warnings: non-fatal notes (never abort a render).
    Raises RuntimeError only when the accounts data layer is unreachable, so the
    caller can degrade-open (skip pruning) rather than delete live accounts.
    """
    if mios_accounts is None:
        raise RuntimeError(f"mios_accounts unavailable: {_IMPORT_ERR}")

    warnings: list[str] = []
    accounts = mios_accounts.export("linux")   # WHERE on_linux; ro role, parameterized
    groups = mios_accounts.list_groups()       # every managed group (SSOT gid consistency)

    desired: dict[str, tuple[str, bool]] = {}

    # Every managed group projects a group record so primary/supplementary gids stay
    # consistent even for a group with no current members.
    for grp in groups:
        rec = _group_record(grp)
        desired[f"{rec['groupName']}.group"] = (_canon(rec), False)

    for row in accounts:
        rec = _user_record(row)
        priv = "privileged" in rec
        desired[f"{rec['userName']}.user"] = (_canon(rec), priv)
        # A supplementary/primary group that references a name we did NOT emit as a
        # managed group record (e.g. the system `wheel` group from /etc/group) is left
        # to NSS; only note it so a genuinely missing DB group is visible.
        for g in rec.get("memberOf", []):
            if g != "wheel" and f"{g}.group" not in desired:
                warnings.append(f"account {rec['userName']}: memberOf '{g}' has no managed group record")

    return desired, warnings


# ── state (ownership) ──────────────────────────────────────────────────────

def _load_state(userdb_dir: str) -> list[str]:
    path = _state_path(userdb_dir)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            managed = data.get("managed")
            if isinstance(managed, list):
                return [str(x) for x in managed]
        except Exception as e:
            _log(f"WARN: unreadable state {path}: {e}")
    return []


def _save_state(userdb_dir: str, managed: list[str]) -> None:
    path = _state_path(userdb_dir)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"userdb_dir": userdb_dir, "managed": sorted(managed)}, fh, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        _log(f"WARN: could not persist state {path}: {e}")


def _atomic_write(dst: str, text: str, mode: int) -> None:
    """Write text to dst atomically (temp in the same dir + rename) at `mode`."""
    d = os.path.dirname(dst)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, f".{os.path.basename(dst)}.tmp.{os.getpid()}")
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
        try:
            os.write(fd, text.encode("utf-8"))
        finally:
            os.close(fd)
        os.chmod(tmp, mode)   # honor mode even if umask clipped the O_CREAT bits
        os.replace(tmp, dst)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ── commands ───────────────────────────────────────────────────────────

def cmd_render() -> int:
    userdb_dir = _userdb_dir()
    try:
        desired, warnings = _project()
    except RuntimeError as e:
        # Degrade-open: DB/data-layer unreachable. Do NOT prune (that would remove
        # live accounts); leave the existing drop-ins in place and succeed so a
        # transient DB outage never wedges boot. Break-glass root is unaffected.
        _log(f"WARN: {e} -- leaving existing userdb drop-ins untouched (degrade-open)")
        return 0

    for w in warnings:
        _log(f"note: {w}")

    prev = set(_load_state(userdb_dir))
    now = set(desired.keys())
    written = 0
    for name, (text, priv) in sorted(desired.items()):
        dst = os.path.join(userdb_dir, name)
        mode = 0o600 if priv else 0o644
        cur = None
        if os.path.isfile(dst):
            try:
                with open(dst, "r", encoding="utf-8") as fh:
                    cur = fh.read()
            except Exception:
                cur = None
        cur_mode = None
        try:
            cur_mode = os.stat(dst).st_mode & 0o777
        except OSError:
            pass
        if cur == text and cur_mode == mode:
            continue  # idempotent: unchanged content + perms -> no write
        _atomic_write(dst, text, mode)
        written += 1

    # Prune drop-ins we previously owned that are no longer desired. Only files in
    # the ownership manifest are ever removed -> foreign userdb records are safe.
    pruned = 0
    for stale in sorted(prev - now):
        victim = os.path.join(userdb_dir, stale)
        if os.path.isfile(victim):
            try:
                os.unlink(victim)
                pruned += 1
            except Exception as e:
                _log(f"WARN: could not prune {victim}: {e}")

    _save_state(userdb_dir, sorted(now))
    _log(f"rendered {len(desired)} record(s) -> {userdb_dir} "
         f"({written} written/updated, {pruned} pruned)")
    return 0


def cmd_check() -> int:
    """Drift-gate: a fresh projection must equal the on-disk drop-ins (content, mode,
    and no stale managed files). Read-only; exit 1 on drift. New member of the
    25-41 drift-gate family, same shape as mios-dotfiles-render --check."""
    userdb_dir = _userdb_dir()
    try:
        desired, _warnings = _project()
    except RuntimeError as e:
        _log(f"FAIL: cannot project accounts for drift-check: {e}")
        return 1

    drift: list[str] = []
    for name, (text, priv) in sorted(desired.items()):
        dst = os.path.join(userdb_dir, name)
        want_mode = 0o600 if priv else 0o644
        if not os.path.isfile(dst):
            drift.append(f"{name}: missing drop-in ({dst})")
            continue
        try:
            with open(dst, "r", encoding="utf-8") as fh:
                got = fh.read()
        except Exception as e:
            drift.append(f"{name}: unreadable ({e})")
            continue
        if got != text:
            drift.append(f"{name}: content drifted from SSOT projection")
        got_mode = os.stat(dst).st_mode & 0o777
        if got_mode != want_mode:
            drift.append(f"{name}: mode {got_mode:04o} != expected {want_mode:04o}")

    # Stale managed drop-ins that a render would prune.
    for stale in sorted(set(_load_state(userdb_dir)) - set(desired.keys())):
        if os.path.isfile(os.path.join(userdb_dir, stale)):
            drift.append(f"{stale}: stale managed drop-in (would be pruned on render)")

    for d in drift:
        _log(f"    {d}")
    if drift:
        _log(f"FAIL: {len(drift)} userdb drop-in(s) drifted from the accounts SSOT -- "
             f"re-run `mios-account-project` (or `mios accounts sync`) to re-project")
        return 1
    _log(f"PASS: {len(desired)} userdb drop-in(s) match the accounts SSOT projection")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="mios-account-project",
        description="Project the Postgres accounts SSOT to systemd userdb drop-ins (Linux).",
    )
    ap.add_argument("--platform", choices=("linux",), default="linux",
                    help="platform leg to project (linux is the only leg this tool implements)")
    ap.add_argument("--check", action="store_true",
                    help="drift-gate: compare on-disk drop-ins vs a fresh projection, never write")
    args = ap.parse_args(argv)

    if args.check:
        return cmd_check()
    return cmd_render()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

```


## new usr/lib/systemd/system/mios-account-project.service

```
# AI-hint: Oneshot unit that projects the Postgres accounts SSOT to systemd userdb drop-ins via /usr/libexec/mios/mios-account-project. Runs on boot (and on the paired .timer) so nss-systemd resolves DB-managed Linux accounts; degrade-open so a DB outage never wedges boot and never touches the break-glass local root.
# AI-related: /usr/libexec/mios/mios-account-project, mios-account-project.timer, mios-account-sync.service, mios-pgvector.service, /etc/userdb, nss-systemd, multi-user.target

[Unit]
Description='MiOS' accounts -> systemd userdb projector (Linux SSOT projection)
Documentation=file:///usr/libexec/mios/mios-account-project
# Needs the pgvector container (the accounts SSOT) reachable. Wants, never Requires:
# the projector degrades open (leaves existing drop-ins untouched) when the DB is
# down, so a transient outage must not fail this unit or block the boot.
After=mios-pgvector.service network-online.target
Wants=mios-pgvector.service
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=oneshot
EnvironmentFile=-/etc/mios/install.env
# Runtime target: /etc/userdb (writable + persistent). /usr/lib/userdb is baked into
# the image and is read-only on a booted bootc host, so runtime projection lands in
# /etc/userdb, which systemd searches ahead of /usr/lib/userdb.
Environment=MIOS_USERDB_DIR=/etc/userdb
# Best-effort readiness probe; degrade-open, so a miss does not fail the unit.
ExecStartPre=-/usr/bin/podman exec mios-pgvector pg_isready -q -h 127.0.0.1 -p 8432 -U mios -d mios
ExecStart=/usr/libexec/mios/mios-account-project --platform linux
# Config projection, never a workload: the tool already returns 0 on a DB miss, but
# accept 1 defensively so a degrade-open path never marks the unit failed.
SuccessExitStatus=0 1
RemainAfterExit=no

[Install]
WantedBy=multi-user.target

```


## new usr/lib/systemd/system/mios-account-project.timer

```
# AI-hint: Timer that re-runs mios-account-project.service shortly after boot and periodically so the systemd userdb drop-ins track the Postgres accounts SSOT even when the low-latency LISTEN/NOTIFY path (mios-account-sync) missed an event. The store-and-forward safety net for the Linux userdb projection.
# AI-related: mios-account-project.service, /usr/libexec/mios/mios-account-project, mios-account-sync.service, timers.target

[Unit]
Description=Periodic MiOS accounts -> userdb re-projection (SSOT reconcile safety net)

[Timer]
# 90s after boot (pgvector container up by then), then every 15 min so the userdb
# drop-ins reconcile against the accounts SSOT independent of the NOTIFY listener.
OnBootSec=90s
OnUnitActiveSec=15min
Persistent=true

[Install]
WantedBy=timers.target

```


## edit automation/17-accounts-db.sh

```
#!/usr/bin/env bash
# AI-hint: Configures the dynamic PostgreSQL-to-OS user account sync service, enabling live account mappings without the packaging-restricted NSS/PAM pgsql modules. Also installs + enables the systemd-userdb projector (mios-account-project) so nss-systemd resolves DB-managed accounts from userdb drop-ins.
# AI-related: 31-user.sh, schema-init.sql, mios-account-sync.service, mios-account-project.service, mios-account-project.timer, /usr/libexec/mios/mios-account-project
# 'MiOS' - 17-accounts-db: PostgreSQL account synchronization setup
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

log "Configuring PostgreSQL host account sync service"

# Install account-sync executable to system path
install -d -m 0755 /usr/libexec/mios/
install -m 0755 "$(dirname "$0")/../usr/libexec/mios/mios-account-sync" /usr/libexec/mios/mios-account-sync

# Install systemd service unit
install -d -m 0755 /usr/lib/systemd/system/
install -m 0644 "$(dirname "$0")/../usr/lib/systemd/system/mios-account-sync.service" /usr/lib/systemd/system/mios-account-sync.service

# Install the systemd-userdb projector (Linux SSOT projection) + its service/timer.
# The projector renders /etc/userdb/<name>.user|.group drop-ins from the Postgres
# accounts SSOT (via mios_accounts.py) so nss-systemd resolves DB-managed accounts.
install -m 0755 "$(dirname "$0")/../usr/libexec/mios/mios-account-project" /usr/libexec/mios/mios-account-project
install -m 0644 "$(dirname "$0")/../usr/lib/systemd/system/mios-account-project.service" /usr/lib/systemd/system/mios-account-project.service
install -m 0644 "$(dirname "$0")/../usr/lib/systemd/system/mios-account-project.timer" /usr/lib/systemd/system/mios-account-project.timer

# Clean up legacy libnss-pgsql and pam_pgsql configs if they exist
rm -f /etc/nss-pgsql.conf /etc/nss-pgsql-root.conf /etc/pam_pgsql.conf

# Revert nsswitch.conf changes if they were previously written
if [ -f /etc/nsswitch.conf ]; then
    sed -i 's/ pgsql//g' /etc/nsswitch.conf
fi

# Revert PAM system-auth/password-auth pgsql inserts if previously written
for f in /etc/pam.d/system-auth /etc/pam.d/password-auth; do
    if [ -f "$f" ]; then
        sed -i '/pam_pgsql.so/d' "$f"
    fi
done

if [[ "${MIOS_ACCOUNTS_DB_BACKED:-false}" =~ ^(true|1|yes)$ ]]; then
    log "Enabling live PostgreSQL database account synchronization daemon"
    systemctl enable mios-account-sync.service || true

    # nss-systemd must be on the NSS passwd/group stack for the userdb drop-ins the
    # projector writes to resolve via getent/id/PAM. Idempotent: append ' systemd'
    # to the passwd:/group: lines only when absent (Fedora usually ships it already).
    if [ -f /etc/nsswitch.conf ]; then
        for _db in passwd group; do
            if grep -qE "^${_db}:" /etc/nsswitch.conf \
               && ! grep -E "^${_db}:" /etc/nsswitch.conf | grep -qw systemd; then
                sed -i -E "s/^(${_db}:.*)$/\\1 systemd/" /etc/nsswitch.conf
                log "nsswitch.conf: added nss-systemd to ${_db} database"
            fi
        done
    fi

    log "Enabling systemd-userdb accounts projector (boot + periodic reconcile)"
    systemctl enable mios-account-project.timer || true
    systemctl enable mios-account-project.service || true
else
    log "PostgreSQL account synchronization is flag-gated off (db_backed = false)"
    systemctl disable mios-account-sync.service || true
    systemctl disable mios-account-project.timer || true
    systemctl disable mios-account-project.service || true
fi

```


**wiring:** DEPENDENCY: the projector reads ONLY through usr/lib/mios/mios_accounts.py (the data-layer choke point in the contract), calling mios_accounts.export('linux') and mios_accounts.list_groups(). That module is a sibling deliverable (built by another agent per the CONTRACTS spec); this projector emits NO SQL itself, so the parameterized-SQL mandate and ro-role posture are satisfied upstream. It also depends on the accounts-schema.sql view mios_account_export (columns username, uid, primary_gid, primary_group, display_name, description, home_dir, shell, enabled, is_admin, is_service, password_hash, must_change_pw, member_groups[], member_gids[], meta, on_linux/on_windows). member_groups[] and member_gids[] are NOT positionally aligned (sorted by name vs by gid), so the projector deliberately uses member_groups[] for memberOf and derives gids from list_groups() instead of zipping them.\n\nVERIFIED IN-SESSION: py_compile clean; a render against a stub mios_accounts produced byte-correct records -- admin -> memberOf includes wheel; is_service -> disposition:system; enabled=false -> locked:true; NULL home_dir -> /var/home/<u>; password_hash -> privileged.hashedPassword (file 0600); ssh keys pulled from meta; a group record per managed group. Only Windows-host filesystem artifacts appeared (chmod maps to 0666; the drive-letter colon breaks the state filename) -- both vanish on Linux where /etc/userdb yields the clean state key 'etc-userdb' and real Unix modes.\n\nNAMING: Phase 2 mandates the filename usr/libexec/mios/mios-account-project; the CONTRACTS section references a broader mios-accounts-projector with a Windows leg. This file IS the Linux leg. It accepts --platform linux for forward-compat; the Windows-manifest leg is a separate deliverable. If the two are later unified, this can become mios-accounts-projector's linux branch or be symlinked -- no code change needed.\n\nRUNTIME PATH: at bake the default target is /usr/lib/userdb (writable during build; but the pgvector container is not up at build so no bake-time projection is wired -- deliberately). At runtime the .service passes MIOS_USERDB_DIR=/etc/userdb because /usr is read-only on a booted bootc host; systemd searches /etc/userdb ahead of /usr/lib/userdb, and /etc persists. Ownership manifest lives at /var/lib/mios/account-project.<dirkey>.json so pruning only ever removes MiOS-managed drop-ins -- the break-glass local root in /etc/passwd is never touched.\n\nWIRING TO SIBLINGS: mios-account-sync's LISTEN on channel mios_account_sync should call `mios-account-project` on each NOTIFY for low-latency reaction; this timer is the periodic safety net. The `mios accounts sync` CLI subcommand should invoke this projector (+ the reconcile). The drift-gate family (checks 25-41) gains a new check that runs `mios-account-project --check` (read-only, ro role, exit 1 on drift) -- same shape as mios-dotfiles-render --check. Enable/install is gated on MIOS_ACCOUNTS_DB_BACKED (mirrors mios.toml [accounts].db_backed), the same flag the existing account-sync daemon uses. The nss-systemd nsswitch ensure was added because without `systemd` on the passwd:/group: lines the drop-ins are inert.\n\nASSUMPTIONS: mios-pgvector runs the pgvector container reachable at 127.0.0.1:8432 as user/db 'mios' (matches mios-account-sync.service's ExecStartPre and mios_db_config.get_pg_config defaults). memberOf 'wheel' resolves from /etc/group (a system group), so the projector does not emit a wheel.group record and only warns on non-wheel referenced groups that lack a managed group record.


# COMPONENT: mios accounts CLI


## new usr/libexec/mios/mios-accounts

```
#!/usr/bin/env python3
# AI-hint: The operator-facing `mios accounts` verb backend (WS-ACCT / ACCT-03) -- the CLI face of the MiOS database-managed accounts SSOT. A THIN argparse dispatcher over usr/lib/mios/mios_accounts.py (the single parameterized data-access choke point); it emits NO SQL of its own and NEVER interpolates a value into a query (per the parameterization mandate + TD-1 eval-safety: argparse only, no eval/shell=True, values flow as $-bound params inside the data layer). Reads (list/show) use the ro path, mutations (add/modify/remove/enable/disable/passwd) the rw path -- role selection is owned by mios_accounts.py, not here. Passwords are read on stdin ONLY (never argv/env), passed as plaintext to the data layer which hashes them (crypt $6$/$y$); this CLI never echoes, logs, or stores a credential. Rows are read via the mios_account_export view (primary group + supplementary group arrays pre-aggregated) and projected OUT to systemd userdb JSON (Linux) / New-LocalUser (Windows) by mios-accounts-projector.
# AI-related: usr/lib/mios/mios_accounts.py, usr/libexec/mios/mios-pg-query, usr/lib/mios/mios_db_config.py, usr/libexec/mios/mios-accounts-projector, usr/libexec/mios/mios-account-sync, usr/libexec/mios/seed-db-config.py, usr/share/mios/postgres/accounts-schema.sql, usr/bin/mios, etc/profile.d/mios-verbs.sh, usr/share/mios/mios.toml [verbs]/[accounts]/[[autounattend.accounts]]
# AI-functions: _fail, _load_data_layer, _dispatch_error, _split_csv, _read_password_stdin, _emit, _cellstr, _fmt_table, _fmt_record, _account_kwargs_from_args, cmd_list, cmd_show, cmd_add, cmd_modify, cmd_remove, _set_enabled, cmd_enable, cmd_disable, cmd_passwd, _add_common_account_flags, build_parser, main
"""mios accounts -- manage MiOS database-backed OS accounts (the accounts SSOT).

Subcommands:
  list                          list managed accounts (--platform linux|windows,
                                --all/--enabled-only, --json)
  show <user>                   show one account (all fields + group membership)
  add  <user>  [flags]          create an account (INSERT ... one txn)
  modify <user> [flags]         mutate an existing account (whitelisted columns)
  remove <user>                 delete an account (CASCADE clears memberships)
  enable  <user>                un-lock an account (never deletes)
  disable <user>                lock an account (never deletes)
  passwd  <user> [--stdin]      set the account password (hashed in the data layer)

Every subcommand calls exactly ONE mios_accounts.py function. No SQL lives in
this file; the data layer builds parameterized ($1..$n) statements and executes
them via mios-pg-query --exec-json (or bound psycopg params). Output is a plain
aligned table by default, or machine JSON with --json.

Exit codes:
  0   success
  1   generic / data-layer error
  2   usage error (argparse)
  3   duplicate username / group already exists   (SQLSTATE 23505)
  4   no such account / group                     (not found)
  5   unknown group referenced                    (SQLSTATE 23503)
  6   invalid name / value format                 (SQLSTATE 23514)
  127 data layer unavailable (mios_accounts.py / psycopg / pg unreachable)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

PROG = "mios accounts"

# Exit codes (documented in the module docstring).
EX_OK, EX_ERR, EX_USAGE = 0, 1, 2
EX_DUP, EX_NOTFOUND, EX_UNKNOWN_GROUP, EX_FORMAT = 3, 4, 5, 6
EX_UNAVAILABLE = 127

# The single choke point: usr/lib/mios/mios_accounts.py. Import is deferred into
# a helper so `mios accounts --help` works even where the data layer / psycopg /
# Postgres is not present (mirrors usr/bin/mios's degrade-open openai import).
_LIBDIR = os.environ.get("MIOS_LIB_DIR") or "/usr/lib/mios"


def _fail(msg: str, code: int = EX_ERR) -> "NoReturn":  # type: ignore[name-defined]
    """Print a clean one-line error to stderr and exit with `code`. No stack
    traces leak to the operator; the data layer already carries the detail."""
    sys.stderr.write(f"{PROG}: {msg}\n")
    raise SystemExit(code)


def _load_data_layer():
    """Import mios_accounts (the parameterized data layer). Degrade-open with a
    clear 127 when it -- or its Postgres transport -- is unavailable, rather than
    dumping an ImportError traceback."""
    if _LIBDIR not in sys.path:
        sys.path.insert(0, _LIBDIR)
    try:
        import mios_accounts  # noqa: E402  (deferred on purpose)
    except ImportError as exc:
        _fail(
            "the accounts data layer (mios_accounts) is unavailable "
            f"({exc}). Ensure {_LIBDIR}/mios_accounts.py and its Postgres "
            "transport (mios-pg-query / psycopg) are installed and the AI-plane "
            "database is reachable.",
            EX_UNAVAILABLE,
        )
    return mios_accounts


def _dispatch_error(acct, exc: Exception) -> "NoReturn":  # type: ignore[name-defined]
    """Map a typed data-layer exception to a stable exit code + terse message.
    Exception classes are resolved defensively by name (getattr) so a rename in
    the data layer degrades to the generic path instead of crashing the CLI."""
    for name, code in (
        ("DuplicateUsername", EX_DUP),
        ("UnknownGroup", EX_UNKNOWN_GROUP),
        ("FormatError", EX_FORMAT),
        ("NotFound", EX_NOTFOUND),
    ):
        klass = getattr(acct, name, None)
        if klass is not None and isinstance(exc, klass):
            _fail(str(exc) or name, code)
    base = getattr(acct, "AccountsError", None)
    if base is not None and isinstance(exc, base):
        _fail(str(exc) or "accounts error", EX_ERR)
    raise  # unknown -> re-raise for the top-level guard


# ── small helpers (pure) ──────────────────────────────────────────
def _split_csv(value):
    """'a,b , ,c' -> ['a','b','c']. Empty/None -> []. eval-safe: pure string
    splitting, never eval/shell."""
    if not value:
        return []
    return [tok.strip() for tok in value.split(",") if tok.strip()]


def _read_password_stdin() -> str:
    """Read a plaintext password from stdin (single line, trailing newline
    stripped). Passwords NEVER come from argv or the environment -- only stdin --
    so they cannot leak via `ps`, shell history, or the process table."""
    data = sys.stdin.readline()
    if not data:
        _fail("no password on stdin (expected the password piped in)", EX_USAGE)
    return data.rstrip("\n").rstrip("\r")


def _emit(obj, as_json: bool) -> None:
    """Render a result. --json -> compact JSON; else a human table/record."""
    if as_json:
        sys.stdout.write(json.dumps(obj, default=str, indent=2) + "\n")
        return
    if isinstance(obj, list):
        _fmt_table(obj)
    elif isinstance(obj, dict):
        _fmt_record(obj)
    elif obj is not None:
        sys.stdout.write(f"{obj}\n")


# Columns shown in the default `list` table (a readable subset of the export view).
_LIST_COLS = ("username", "uid", "primary_group", "is_admin", "enabled",
              "on_linux", "on_windows", "member_groups")


def _cellstr(val) -> str:
    if val is None:
        return ""
    if isinstance(val, bool):
        return "yes" if val else "no"
    if isinstance(val, (list, tuple)):
        return ",".join(str(v) for v in val)
    return str(val)


def _fmt_table(rows) -> None:
    if not rows:
        sys.stdout.write("(no accounts)\n")
        return
    cols = [c for c in _LIST_COLS if any(c in r for r in rows)]
    if not cols:  # unexpected shape -> fall back to JSON so nothing is hidden
        sys.stdout.write(json.dumps(rows, default=str, indent=2) + "\n")
        return
    widths = {c: len(c) for c in cols}
    table = []
    for r in rows:
        cells = {c: _cellstr(r.get(c)) for c in cols}
        for c in cols:
            widths[c] = max(widths[c], len(cells[c]))
        table.append(cells)
    header = "  ".join(c.upper().ljust(widths[c]) for c in cols)
    sys.stdout.write(header.rstrip() + "\n")
    sys.stdout.write("  ".join("-" * widths[c] for c in cols) + "\n")
    for cells in table:
        sys.stdout.write("  ".join(cells[c].ljust(widths[c]) for c in cols).rstrip() + "\n")


def _fmt_record(rec) -> None:
    # Never surface the hash in the human view; --json still carries whatever the
    # data layer returns (the API contract already withholds plaintext).
    order = ("username", "uid", "primary_gid", "primary_group", "display_name",
             "description", "home_dir", "shell", "enabled", "is_admin",
             "is_service", "must_change_pw", "on_linux", "on_windows",
             "member_groups", "member_gids", "meta", "updated_at")
    keys = [k for k in order if k in rec] + [k for k in rec if k not in order]
    width = max((len(k) for k in keys), default=0)
    for k in keys:
        if k == "password_hash":
            val = "(set)" if rec.get(k) else "(none)"
        else:
            val = _cellstr(rec.get(k))
        sys.stdout.write(f"{k.ljust(width)} : {val}\n")


def _account_kwargs_from_args(args, *, for_create: bool) -> dict:
    """Collect the account attributes the operator actually supplied.

    Boolean flags use argparse.BooleanOptionalAction with default=None, so an
    unspecified flag is None (=> left to the data-layer/DB default on create, or
    left unchanged on modify). Only non-None values are forwarded, which is why
    the same collector serves both add (unset -> create_account defaults) and
    modify (unset -> untouched)."""
    kwargs: dict = {}

    def put(key, val):
        if val is not None:
            kwargs[key] = val

    put("display_name", args.display)
    put("description", args.description)
    put("shell", args.shell)
    put("home_dir", args.home)
    put("primary_gid", args.primary_gid)
    put("is_admin", args.admin)
    put("is_service", args.service)
    put("on_linux", args.linux)
    put("on_windows", args.windows)
    if for_create:
        put("uid", args.uid)
    return kwargs


# ── subcommand handlers ────────────────────────────────────────
def cmd_list(acct, args) -> int:
    rows = acct.list_accounts(
        platform=args.platform,
        include_disabled=not args.enabled_only,
    )
    _emit(rows, args.json)
    return EX_OK


def cmd_show(acct, args) -> int:
    rec = acct.get_account(args.username)
    if rec is None:
        _fail(f"no such account: {args.username}", EX_NOTFOUND)
    _emit(rec, args.json)
    return EX_OK


def cmd_add(acct, args) -> int:
    kwargs = _account_kwargs_from_args(args, for_create=True)
    kwargs["groups"] = _split_csv(args.groups)
    if args.must_change:
        kwargs["must_change_pw"] = True
    if args.password_stdin:
        kwargs["password"] = _read_password_stdin()
    rec = acct.create_account(args.username, **kwargs)
    if not args.json:
        sys.stderr.write(f"{PROG}: created account '{args.username}'\n")
    _emit(rec, args.json)
    return EX_OK


def cmd_modify(acct, args) -> int:
    # Confirm existence first for a clean 4 (instead of a 0-row UPDATE no-op).
    if acct.get_account(args.username) is None:
        _fail(f"no such account: {args.username}", EX_NOTFOUND)

    fields = _account_kwargs_from_args(args, for_create=False)
    if args.must_change:
        fields["must_change_pw"] = True

    touched = False
    if fields:
        acct.update_account(args.username, **fields)
        touched = True
    if args.groups is not None:                      # explicit (even empty) -> set
        acct.set_members(args.username, _split_csv(args.groups))
        touched = True
    if args.password_stdin:
        acct.set_password(args.username, _read_password_stdin(),
                          must_change_pw=bool(args.must_change))
        touched = True
    if not touched:
        _fail("nothing to modify (no fields given)", EX_USAGE)

    rec = acct.get_account(args.username)
    if not args.json:
        sys.stderr.write(f"{PROG}: modified account '{args.username}'\n")
    _emit(rec, args.json)
    return EX_OK


def cmd_remove(acct, args) -> int:
    if acct.get_account(args.username) is None:
        _fail(f"no such account: {args.username}", EX_NOTFOUND)
    acct.delete_account(args.username)
    if not args.json:
        sys.stderr.write(f"{PROG}: removed account '{args.username}'\n")
    else:
        _emit({"removed": args.username}, True)
    return EX_OK


def _set_enabled(acct, args, enabled: bool, word: str) -> int:
    if acct.get_account(args.username) is None:
        _fail(f"no such account: {args.username}", EX_NOTFOUND)
    acct.set_enabled(args.username, enabled)
    if not args.json:
        sys.stderr.write(f"{PROG}: {word} account '{args.username}'\n")
    else:
        _emit({"username": args.username, "enabled": enabled}, True)
    return EX_OK


def cmd_enable(acct, args) -> int:
    return _set_enabled(acct, args, True, "enabled")


def cmd_disable(acct, args) -> int:
    return _set_enabled(acct, args, False, "disabled")


def cmd_passwd(acct, args) -> int:
    if acct.get_account(args.username) is None:
        _fail(f"no such account: {args.username}", EX_NOTFOUND)
    if args.stdin:
        plaintext = _read_password_stdin()
    else:
        import getpass
        try:
            plaintext = getpass.getpass("New password: ")
            confirm = getpass.getpass("Retype password: ")
        except (EOFError, KeyboardInterrupt):
            _fail("password entry aborted", EX_USAGE)
        if plaintext != confirm:
            _fail("passwords do not match", EX_USAGE)
    if not plaintext:
        _fail("refusing to set an empty password", EX_USAGE)
    acct.set_password(args.username, plaintext, must_change_pw=bool(args.must_change))
    # Never echo the credential; a terse confirmation only.
    sys.stderr.write(f"{PROG}: password updated for '{args.username}'\n")
    return EX_OK


# ── argument parser ────────────────────────────────────────────
def _add_common_account_flags(p: argparse.ArgumentParser, *, create: bool) -> None:
    """Shared attribute flags for add/modify. BooleanOptionalAction(default=None)
    yields tri-state (--flag / --no-flag / unset) so `add` falls back to the data
    layer's create defaults and `modify` leaves unspecified fields untouched."""
    p.add_argument("--display", metavar="NAME", help="full/display name (GECOS / -FullName)")
    p.add_argument("--description", metavar="TEXT", help="free-text account description")
    p.add_argument("--shell", metavar="PATH", help="login shell (Linux; default /bin/bash on create)")
    p.add_argument("--home", metavar="PATH", help="home directory (NULL -> projector derives per platform)")
    p.add_argument("--primary-gid", type=int, metavar="GID", dest="primary_gid",
                   help="primary group GID (FK -> mios_group.gid; default 1000)")
    p.add_argument("--groups", metavar="a,b,c",
                   help="supplementary groups (CSV). On modify this REPLACES the set.")
    p.add_argument("--admin", action=argparse.BooleanOptionalAction, default=None,
                   help="member of the admin set (wheel/sudo + Administrators)")
    p.add_argument("--service", action=argparse.BooleanOptionalAction, default=None,
                   help="service / system account (suppress interactive-profile steps)")
    p.add_argument("--linux", action=argparse.BooleanOptionalAction, default=None,
                   help="project to the Linux (userdb) surface")
    p.add_argument("--windows", action=argparse.BooleanOptionalAction, default=None,
                   help="project to the Windows (New-LocalUser) surface")
    p.add_argument("--must-change", action="store_true", dest="must_change",
                   help="force a credential change at next logon")
    p.add_argument("--password-stdin", action="store_true", dest="password_stdin",
                   help="read the initial password from stdin (hashed by the data layer)")
    if create:
        p.add_argument("--uid", type=int, metavar="UID",
                       help="explicit POSIX UID (default: auto-allocated >=1000)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Manage MiOS database-backed OS accounts (the accounts SSOT).",
    )
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON instead of a table")
    sub = parser.add_subparsers(dest="cmd", metavar="<subcommand>")

    p = sub.add_parser("list", help="list managed accounts")
    p.add_argument("--platform", choices=("linux", "windows"), default=None,
                   help="only accounts projected to this platform")
    p.add_argument("--enabled-only", action="store_true", dest="enabled_only",
                   help="hide disabled/locked accounts")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="show one account")
    p.add_argument("username")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("add", help="create an account")
    p.add_argument("username")
    _add_common_account_flags(p, create=True)
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("modify", aliases=["mod"], help="modify an existing account")
    p.add_argument("username")
    _add_common_account_flags(p, create=False)
    p.set_defaults(func=cmd_modify)

    p = sub.add_parser("remove", aliases=["del", "rm"], help="delete an account")
    p.add_argument("username")
    p.set_defaults(func=cmd_remove)

    p = sub.add_parser("enable", help="un-lock an account (never deletes)")
    p.add_argument("username")
    p.set_defaults(func=cmd_enable)

    p = sub.add_parser("disable", help="lock an account (never deletes)")
    p.add_argument("username")
    p.set_defaults(func=cmd_disable)

    p = sub.add_parser("passwd", help="set an account password (hashed in the data layer)")
    p.add_argument("username")
    p.add_argument("--stdin", action="store_true",
                   help="read the password from stdin (else prompt interactively)")
    p.add_argument("--must-change", action="store_true", dest="must_change",
                   help="force a credential change at next logon")
    p.set_defaults(func=cmd_passwd)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help(sys.stderr)
        return EX_USAGE

    acct = _load_data_layer()
    try:
        return args.func(acct, args)
    except SystemExit:
        raise
    except BrokenPipeError:
        # A closed pager/pipe is not an error worth a traceback.
        try:
            sys.stdout.close()
        except Exception:
            pass
        return EX_OK
    except Exception as exc:  # typed data-layer errors -> stable exit codes
        _dispatch_error(acct, exc)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.stderr.write("\n")
        sys.exit(130)

```


## edit usr/share/mios/mios.toml

```
help   = { description = "List every verb",                                                       surface = "windows" }
accounts = { description = "Manage MiOS DB-backed OS accounts (list/show/add/modify/passwd/enable/disable/remove; SSOT -> userdb / New-LocalUser)", surface = "dev_vm" }
```


## edit usr/bin/mios

```
    "user":   ["/usr/libexec/mios/user-setup.sh"],
    "accounts": ["/usr/libexec/mios/mios-accounts"],
```


## edit etc/profile.d/mios-verbs.sh

```
        accounts)
            shift
            # `mios accounts <verb>` -- manage the DB-backed OS accounts SSOT
            # via the mios-accounts CLI (thin wrapper over the parameterized
            # mios_accounts data layer). Reads (list/show) are ro; mutating
            # verbs (add/modify/remove/enable/disable/passwd) rw.
            if [[ -x /usr/libexec/mios/mios-accounts ]]; then
                /usr/libexec/mios/mios-accounts "$@"
            elif [[ -x /mnt/m/usr/libexec/mios/mios-accounts ]]; then
                /mnt/m/usr/libexec/mios/mios-accounts "$@"
            else
                echo "mios accounts: mios-accounts not found" >&2
                return 127
            fi
            ;;
        help|"-h"|"--help"|"")
```


**wiring:** DEPENDENCY: the CLI imports usr/lib/mios/mios_accounts.py (Phase 1's data layer -- the single parameterized choke point). That module is NOT yet in the live tree; the CLI degrades open (exit 127 + clear message) if it, psycopg, or the Postgres transport is missing, so it is safe to land before Phase 1. Import path: sys.path.insert(0, MIOS_LIB_DIR or /usr/lib/mios), matching the agent-pipe convention.

DATA-LAYER API CONSUMED (exactly per the CONTRACTS spec, no SQL in the CLI): list_accounts(platform, include_disabled) / get_account(username) / create_account(username, **kwargs incl. groups=, password=) / update_account(username, **fields) / set_password(username, plaintext, must_change_pw=) / set_enabled(username, bool) / delete_account(username) / set_members(username, group_names). Typed exceptions mapped to exit codes: DuplicateUsername->3, UnknownGroup->5, FormatError->6, NotFound->4, AccountsError->1 (resolved via getattr so a rename degrades to the generic path, never a crash).

PARAMETERIZATION / TD-1 EVAL-SAFETY: the CLI contains zero SQL and never eval/exec/shell=True's operator input -- it is pure argparse and forwards values as Python kwargs; the data layer binds them as $1..$n. This satisfies the hard code-review gate.

SECRET HYGIENE: passwords are accepted ONLY on stdin (--password-stdin on add/modify, --stdin or interactive getpass on passwd) -- never argv/env, so they cannot appear in `ps`/history. Plaintext is handed to the data layer which hashes (crypt $6$/$y$); the CLI never echoes/logs it, and the human `show` view renders password_hash as (set)/(none).

ROLE SELECTION: the CLI does not itself pick ro vs rw -- mios_accounts.py owns the connection identity (get_pg_config()); read verbs (list/show) map to the ro read path, mutating verbs to rw, per the ROLES spec.

WIRES TO SIBLINGS: `mios accounts sync` is intentionally NOT implemented here (Phase 2 scope = add/list/show/modify/remove/enable/disable/passwd); the projector (mios-accounts-projector) and reconcile agent (mios-account-sync) own projection, and the Portal :8640 applet + a future `group`/`sync` subcommand call the same mios_accounts.py functions. Aliases provided for contract-grammar parity: modify=mod, remove=del/rm.

VERIFICATION: syntax-checked (py_compile, Python 3.14) and exercised end-to-end against a stub mios_accounts module -- table + --json rendering, add/modify(groups replace + --no-admin)/remove/enable/disable/passwd, password withheld from human view, empty-password refusal (exit 2), duplicate (exit 3), not-found (exit 4), and no-op modify (exit 2) all confirmed.

ASSUMPTION: the operator-facing [verbs] table lives only in usr/share/mios/mios.toml (the root ./mios.toml has no [verbs] table); if a build step projects the root SSOT -> share copy, add the same `accounts` line to whichever file is authoritative in that pipeline. The two dispatch edits (KNOWN_VERBS + mios-verbs.sh) are the actual Linux routing and MUST both land for `mios accounts` to resolve inside MiOS-DEV (the file header of mios-verbs.sh explicitly requires the KNOWN_VERBS mirror).


# COMPONENT: MiOS Admin accounts applet — Portal (:8640) accounts panel + JSON API


## new usr/share/mios/accounts/mios-accounts.html

```
<!-- AI-hint: MiOS Admin accounts applet -- the operator-facing accounts-management
     web panel (WS-ACCT). Self-contained, dependency-free HTML+CSS+JS served raw
     from /usr/share/mios/accounts/mios-accounts.html by the Portal (:8640) route
     /portal/accounts-panel (auth-gated, SSOT-palette-injected) and mounted as an
     in-app iframe view by the Portal shell (same pattern as the configurator).
     Every mutation is a parameterized-SQL write behind mios_accounts.py -- this
     page only speaks the /portal/accounts + /portal/groups JSON API; it never
     sees a password hash (the API scrubs password_hash -> has_password) and it
     posts plaintext passwords ONLY to the reset route, which hashes server-side.
     AI-related: /usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py,
     /usr/lib/mios/mios_accounts.py, /usr/share/mios/postgres/accounts-schema.sql,
     /usr/libexec/mios/mios-accounts-projector, /usr/libexec/mios/mios-account-sync
     AI-functions: api, loadAccounts, renderAccounts, loadGroups, openForm,
     submitForm, openPw, submitPw, toggleEnabled, delAccount, addGroup, delGroup,
     syncNow, toast -->
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MiOS Admin &middot; Accounts</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
/* MiOS palette. The static :root here is the documented fallback; the Portal
   injects a :root override from mios.toml [colors] just before </head> so this
   panel re-skins with the operator's theme (same var names as the dashboard). */
:root{
--bg:#282262;--panel:#1A407F;--fg:#E7DFD3;--mut:#B7C9D7;--accent:#F35C15;
--ok:#3E7765;--bad:#DC271B;--warn:#FF8540;--info:#3D6BA8;--silver:#E0E0E0;
--card:color-mix(in srgb,var(--panel) 24%,var(--bg));
--card2:color-mix(in srgb,var(--panel) 42%,var(--bg));
--line:color-mix(in srgb,var(--mut) 24%,transparent);
--rad:12px;
--mono:ui-monospace,"Cascadia Code","Source Code Pro",Consolas,monospace;
--sans:-apple-system,"Segoe UI",system-ui,Roboto,sans-serif}
*{box-sizing:border-box}
body{margin:0;color:var(--fg);font:14px/1.5 var(--sans);min-height:100vh;
background:radial-gradient(1100px 520px at 12% -12%,
  color-mix(in srgb,var(--accent) 13%,transparent),transparent 60%),
  radial-gradient(900px 500px at 100% 0%,
  color-mix(in srgb,var(--panel) 30%,transparent),transparent 55%),var(--bg)}
a{color:var(--accent);text-decoration:none}
.bar{display:flex;align-items:center;gap:14px;padding:14px 22px;
border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20;
background:var(--bg)}
h1{margin:0;font-size:20px;letter-spacing:.4px}h1 b{color:var(--accent)}
.sub{color:var(--mut);font-size:12px;margin-left:4px}
.spacer{flex:1}
.btn{background:var(--card2);border:1px solid var(--line);color:var(--fg);
border-radius:9px;padding:7px 13px;font:inherit;font-size:13px;cursor:pointer;
transition:.15s}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#1a1230;font-weight:700}
.btn.primary:hover{background:color-mix(in srgb,var(--accent) 84%,#fff);color:#1a1230}
.btn.danger:hover{border-color:var(--bad);color:var(--bad)}
.btn.sm{padding:4px 9px;font-size:12px;border-radius:7px}
section{padding:18px 22px;max-width:1180px;margin:0 auto}
.h{display:flex;align-items:center;gap:10px;margin:6px 0 14px}
.h h2{font-size:14px;letter-spacing:.4px;text-transform:uppercase;color:var(--silver);
margin:0;border-left:4px solid var(--accent);padding-left:9px}
.h .n{color:var(--ok);font-size:12px;font-weight:600}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:var(--rad);
background:var(--card)}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:820px}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);
white-space:nowrap}
th{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.4px;
position:sticky;top:0;background:var(--card2)}
tr:last-child td{border-bottom:0}
tr:hover td{background:color-mix(in srgb,var(--accent) 6%,transparent)}
td.u{font-weight:600}
.uid{font-family:var(--mono);color:var(--mut);font-size:12px}
.tag{display:inline-block;font-size:10.5px;padding:1px 7px;border-radius:20px;
border:1px solid var(--line);color:var(--mut);margin-right:4px}
.tag.admin{color:var(--warn);border-color:color-mix(in srgb,var(--warn) 45%,transparent)}
.tag.svc{color:var(--info);border-color:color-mix(in srgb,var(--info) 45%,transparent)}
.tag.plat{color:var(--silver)}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--mut);
margin-right:6px;vertical-align:middle}
.dot.ok{background:var(--ok)}.dot.bad{background:var(--bad)}
.acts{display:flex;gap:6px;flex-wrap:wrap}
.grpwrap{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.chip{display:inline-flex;align-items:center;gap:7px;background:var(--card2);
border:1px solid var(--line);border-radius:20px;padding:4px 6px 4px 12px;font-size:12.5px}
.chip .gid{color:var(--mut);font-family:var(--mono);font-size:11px}
.chip .x{background:transparent;border:0;color:var(--mut);cursor:pointer;font-size:15px;
line-height:1;padding:0 4px;border-radius:50%}
.chip .x:hover{color:var(--bad)}
.chip.sys{opacity:.7}
.empty{padding:26px;text-align:center;color:var(--mut)}
/* modal */
.modal{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;z-index:50;
align-items:flex-start;justify-content:center;padding:40px 16px;overflow:auto}
.modal.open{display:flex}
.sheet{background:var(--card);border:1px solid var(--line);border-radius:14px;
width:min(560px,100%);padding:20px 22px}
.sheet h3{margin:0 0 14px;font-size:18px}
.sheet h3 .x{float:right;background:transparent;border:0;color:var(--mut);
font-size:22px;cursor:pointer;line-height:1}
label{display:block;margin:12px 0 5px;color:var(--mut);font-size:12px}
input[type=text],input[type=number],input[type=password],select{
width:100%;background:var(--bg);color:var(--fg);border:1px solid var(--line);
border-radius:7px;padding:8px 10px;font:13px var(--mono)}
input:focus,select:focus{outline:none;border-color:var(--accent)}
input[readonly]{opacity:.7;cursor:not-allowed}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.checks{display:flex;flex-wrap:wrap;gap:14px;margin:12px 0 2px}
.chk{display:flex;align-items:center;gap:7px;font-size:13px;color:var(--fg);cursor:pointer}
.chk input{width:auto;cursor:pointer}
.hint{color:var(--mut);font-size:11px;margin-top:5px}
.foot{display:flex;justify-content:flex-end;gap:10px;margin-top:20px}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);
background:var(--card2);border:1px solid var(--line);border-radius:9px;
padding:10px 18px;font-size:13px;display:none;z-index:60;max-width:90vw}
.toast.err{border-color:var(--bad);color:var(--bad)}
.toast.ok{border-color:var(--ok);color:var(--fg)}
@media(max-width:600px){.row2{grid-template-columns:1fr}}
</style></head>
<body>
<div class="bar">
  <a href="/" style="color:inherit"><h1>Mi<b>OS</b> Admin</h1></a>
  <span class="sub">&middot; Accounts</span>
  <div class="spacer"></div>
  <button class="btn" id="syncBtn" title="Project the SSOT to the OS + reconcile">&#8635; Sync</button>
  <button class="btn" id="refreshBtn" title="Reload">&#10227; Refresh</button>
  <button class="btn primary" id="addBtn">&#43; Add account</button>
</div>

<section>
  <div class="h"><h2>Accounts</h2><span class="n" id="acctN"></span></div>
  <div class="tablewrap">
    <table id="acctTable">
      <thead><tr>
        <th>User</th><th>UID</th><th>Primary group</th><th>Flags</th>
        <th>Platforms</th><th>Groups</th><th>Status</th><th>Actions</th>
      </tr></thead>
      <tbody id="acctBody"><tr><td class="empty" colspan="8">loading&hellip;</td></tr></tbody>
    </table>
  </div>
</section>

<section>
  <div class="h"><h2>Groups</h2><span class="n" id="grpN"></span>
    <div class="spacer"></div>
    <button class="btn sm" id="addGrpBtn">&#43; Add group</button></div>
  <div class="grpwrap" id="grpWrap"><span class="empty">loading&hellip;</span></div>
</section>

<!-- account add/edit modal -->
<div class="modal" id="acctModal"><div class="sheet">
  <h3 id="acctTitle">Add account<button class="x" data-close>&times;</button></h3>
  <form id="acctForm">
    <div class="row2">
      <div><label>Username</label><input type="text" id="f_username" autocomplete="off"
        pattern="[a-z_][a-z0-9_-]{0,31}" required></div>
      <div><label>Primary group</label>
        <select id="f_primary_group"></select></div>
    </div>
    <div class="row2">
      <div><label>Display name</label><input type="text" id="f_display_name" autocomplete="off"></div>
      <div><label>Login shell</label><input type="text" id="f_shell" value="/bin/bash" autocomplete="off"></div>
    </div>
    <label>Description</label><input type="text" id="f_description" autocomplete="off">
    <label>Supplementary groups (comma-separated names)</label>
    <input type="text" id="f_groups" autocomplete="off" placeholder="wheel, developers">
    <div class="checks">
      <label class="chk"><input type="checkbox" id="f_is_admin"> Administrator</label>
      <label class="chk"><input type="checkbox" id="f_is_service"> Service account</label>
      <label class="chk"><input type="checkbox" id="f_on_linux" checked> Linux</label>
      <label class="chk"><input type="checkbox" id="f_on_windows" checked> Windows</label>
      <label class="chk"><input type="checkbox" id="f_must_change_pw"> Must change password</label>
    </div>
    <div id="pwBlock">
      <label>Initial password <span class="hint">(hashed server-side; leave blank for none)</span></label>
      <input type="password" id="f_password" autocomplete="new-password">
    </div>
    <div class="foot">
      <button type="button" class="btn" data-close>Cancel</button>
      <button type="submit" class="btn primary" id="acctSave">Create</button>
    </div>
  </form>
</div></div>

<!-- password reset modal -->
<div class="modal" id="pwModal"><div class="sheet">
  <h3 id="pwTitle">Reset password<button class="x" data-close>&times;</button></h3>
  <form id="pwForm">
    <label>New password</label>
    <input type="password" id="pw_password" autocomplete="new-password" required>
    <div class="hint">Sent over the same-origin session and hashed by the data layer;
      the plaintext is never stored or echoed.</div>
    <label class="chk" style="margin-top:12px"><input type="checkbox" id="pw_must_change">
      Force change at next logon</label>
    <div class="foot">
      <button type="button" class="btn" data-close>Cancel</button>
      <button type="submit" class="btn primary">Set password</button>
    </div>
  </form>
</div></div>

<div class="toast" id="toast"></div>

<script>
"use strict";
function $(id){return document.getElementById(id);}
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function toast(msg,kind){var e=$("toast");e.className="toast "+(kind||"")+" ";
  e.textContent=msg;e.style.display="block";
  clearTimeout(e._t);e._t=setTimeout(function(){e.style.display="none";},2600);}

// Single fetch helper: same-origin (carries the portal session cookie), JSON in
// and out. A 401 means the session expired -> bounce the TOP window to /login
// (this panel runs inside the portal iframe). Any non-2xx throws the API's error
// message so the caller surfaces it in a toast.
function api(method,path,body){
  var opt={method:method,cache:"no-store",headers:{},credentials:"same-origin"};
  if(body!==undefined){opt.headers["Content-Type"]="application/json";
    opt.body=JSON.stringify(body);}
  return fetch(path,opt).then(function(r){
    if(r.status===401){ (window.top||window).location.href="/login";
      throw new Error("session expired"); }
    return r.text().then(function(t){
      var j={}; try{ j=t?JSON.parse(t):{}; }catch(e){ j={error:t}; }
      if(!r.ok) throw new Error(j.error||("HTTP "+r.status));
      return j; });
  });
}

var ACCOUNTS=[],GROUPS=[];

function flags(a){
  var s="";
  if(a.is_admin)s+='<span class="tag admin">admin</span>';
  if(a.is_service)s+='<span class="tag svc">service</span>';
  if(a.must_change_pw)s+='<span class="tag">chg-pw</span>';
  if(a.has_password===false)s+='<span class="tag">no-pw</span>';
  return s||'<span class="tag" style="opacity:.5">&mdash;</span>';
}
function platforms(a){
  var s="";
  if(a.on_linux)s+='<span class="tag plat">linux</span>';
  if(a.on_windows)s+='<span class="tag plat">win</span>';
  return s||'<span class="tag" style="opacity:.5">none</span>';
}
function groupList(a){
  var g=a.member_groups||[];
  if(!g.length)return '<span style="color:var(--mut)">&mdash;</span>';
  return g.map(function(n){return '<span class="tag">'+esc(n)+'</span>';}).join("");
}

function renderAccounts(){
  var b=$("acctBody");
  if(!ACCOUNTS.length){
    b.innerHTML='<tr><td class="empty" colspan="8">No managed accounts yet. '+
      'Click <b>Add account</b> to create one.</td></tr>';
    $("acctN").textContent="0 accounts";return;}
  b.innerHTML=ACCOUNTS.map(function(a){
    var en=a.enabled!==false;
    return '<tr data-u="'+esc(a.username)+'">'+
      '<td class="u">'+esc(a.username)+
        (a.display_name?'<div class="uid">'+esc(a.display_name)+'</div>':'')+'</td>'+
      '<td class="uid">'+esc(a.uid)+'</td>'+
      '<td>'+esc(a.primary_group||a.primary_gid)+'</td>'+
      '<td>'+flags(a)+'</td>'+
      '<td>'+platforms(a)+'</td>'+
      '<td>'+groupList(a)+'</td>'+
      '<td><span class="dot '+(en?"ok":"bad")+'"></span>'+(en?"enabled":"disabled")+'</td>'+
      '<td><div class="acts">'+
        '<button class="btn sm" data-act="edit">Edit</button>'+
        '<button class="btn sm" data-act="pw">Password</button>'+
        '<button class="btn sm" data-act="toggle">'+(en?"Disable":"Enable")+'</button>'+
        '<button class="btn sm danger" data-act="del">Delete</button>'+
      '</div></td></tr>';
  }).join("");
  $("acctN").textContent=ACCOUNTS.length+" account"+(ACCOUNTS.length===1?"":"s");
}

function loadAccounts(){
  return api("GET","/portal/accounts").then(function(j){
    ACCOUNTS=j.accounts||[];renderAccounts();
  }).catch(function(e){
    $("acctBody").innerHTML='<tr><td class="empty" colspan="8">accounts unavailable: '+
      esc(e.message)+'</td></tr>';});
}

function renderGroups(){
  var w=$("grpWrap");
  if(!GROUPS.length){w.innerHTML='<span class="empty">no groups</span>';}
  else{
    w.innerHTML=GROUPS.map(function(g){
      var sys=g.is_system;
      return '<span class="chip'+(sys?" sys":"")+'" data-g="'+esc(g.name)+'">'+
        esc(g.name)+' <span class="gid">'+esc(g.gid)+'</span>'+
        (sys?'':'<button class="x" data-delg="'+esc(g.name)+'" title="Delete group">&times;</button>')+
        '</span>';
    }).join("");
  }
  $("grpN").textContent=GROUPS.length+" group"+(GROUPS.length===1?"":"s");
  // keep the primary-group <select> in the account form in sync
  var sel=$("f_primary_group"),cur=sel.value;
  sel.innerHTML=GROUPS.map(function(g){
    return '<option value="'+esc(g.name)+'" data-gid="'+esc(g.gid)+'">'+
      esc(g.name)+' ('+esc(g.gid)+')</option>';}).join("");
  if(cur)sel.value=cur;
}
function loadGroups(){
  return api("GET","/portal/groups").then(function(j){
    GROUPS=j.groups||[];renderGroups();
  }).catch(function(e){
    $("grpWrap").innerHTML='<span class="empty">groups unavailable: '+esc(e.message)+'</span>';});
}

// account add/edit modal
var EDIT_USER=null;
function openForm(user){
  EDIT_USER=user;
  var a=user?ACCOUNTS.filter(function(x){return x.username===user;})[0]:null;
  $("acctTitle").firstChild.nodeValue=a?("Edit "+a.username):"Add account";
  $("acctSave").textContent=a?"Save changes":"Create";
  $("f_username").value=a?a.username:"";
  $("f_username").readOnly=!!a;
  $("f_display_name").value=a?(a.display_name||""):"";
  $("f_description").value=a?(a.description||""):"";
  $("f_shell").value=a?(a.shell||"/bin/bash"):"/bin/bash";
  $("f_groups").value=a?((a.member_groups||[]).join(", ")):"";
  $("f_is_admin").checked=a?!!a.is_admin:false;
  $("f_is_service").checked=a?!!a.is_service:false;
  $("f_on_linux").checked=a?a.on_linux!==false:true;
  $("f_on_windows").checked=a?a.on_windows!==false:true;
  $("f_must_change_pw").checked=a?!!a.must_change_pw:false;
  $("pwBlock").style.display=a?"none":"block";   // password set via its own route on edit
  $("f_password").value="";
  // primary group select -> default to the row's primary_group, else 'mios'
  var want=a?(a.primary_group||"mios"):"mios";
  var sel=$("f_primary_group");
  if(!sel.querySelector('option[value="'+want+'"]')&&sel.options.length)want=sel.options[0].value;
  sel.value=want;
  $("acctModal").classList.add("open");
  if(!a)$("f_username").focus();
}

function submitForm(e){
  e.preventDefault();
  var groups=$("f_groups").value.split(",").map(function(s){return s.trim();})
    .filter(function(s){return s;});
  var sel=$("f_primary_group").selectedOptions[0];
  var primary_gid=sel?parseInt(sel.getAttribute("data-gid"),10):undefined;
  var common={
    display_name:$("f_display_name").value.trim()||null,
    description:$("f_description").value.trim()||null,
    shell:$("f_shell").value.trim()||"/bin/bash",
    is_admin:$("f_is_admin").checked,
    is_service:$("f_is_service").checked,
    on_linux:$("f_on_linux").checked,
    on_windows:$("f_on_windows").checked,
    must_change_pw:$("f_must_change_pw").checked};
  if(primary_gid!=null&&!isNaN(primary_gid))common.primary_gid=primary_gid;

  if(EDIT_USER){
    var u=EDIT_USER;
    api("PUT","/portal/accounts/"+encodeURIComponent(u),common)
      .then(function(){return api("POST","/portal/accounts/"+encodeURIComponent(u)+"/groups",{groups:groups});})
      .then(function(){closeModals();toast("Saved "+u,"ok");return refresh();})
      .catch(function(err){toast(err.message,"err");});
  }else{
    var username=$("f_username").value.trim();
    var body=Object.assign({username:username,groups:groups},common);
    var pw=$("f_password").value;
    if(pw)body.password=pw;
    api("POST","/portal/accounts",body)
      .then(function(){closeModals();toast("Created "+username,"ok");return refresh();})
      .catch(function(err){toast(err.message,"err");});
  }
}

// password reset modal
var PW_USER=null;
function openPw(user){
  PW_USER=user;
  $("pwTitle").firstChild.nodeValue="Reset password — "+user;
  $("pw_password").value="";$("pw_must_change").checked=false;
  $("pwModal").classList.add("open");$("pw_password").focus();
}
function submitPw(e){
  e.preventDefault();
  var pw=$("pw_password").value;
  if(!pw){toast("password required","err");return;}
  api("POST","/portal/accounts/"+encodeURIComponent(PW_USER)+"/password",
      {password:pw,must_change_pw:$("pw_must_change").checked})
    .then(function(){closeModals();toast("Password set for "+PW_USER,"ok");return loadAccounts();})
    .catch(function(err){toast(err.message,"err");});
}

function toggleEnabled(user){
  var a=ACCOUNTS.filter(function(x){return x.username===user;})[0];
  if(!a)return;
  var next=a.enabled===false;   // currently disabled -> enable, and vice-versa
  api("POST","/portal/accounts/"+encodeURIComponent(user)+"/enabled",{enabled:next})
    .then(function(){toast((next?"Enabled ":"Disabled ")+user,"ok");return loadAccounts();})
    .catch(function(err){toast(err.message,"err");});
}
function delAccount(user){
  if(!confirm("Delete account \""+user+"\"? Group memberships are removed. "+
    "The account row is deleted; the break-glass local admin is unaffected."))return;
  api("DELETE","/portal/accounts/"+encodeURIComponent(user))
    .then(function(){toast("Deleted "+user,"ok");return refresh();})
    .catch(function(err){toast(err.message,"err");});
}

function addGroup(){
  var name=prompt("New group name (a-z, _, -, 1-32 chars):","");
  if(!name)return;name=name.trim();if(!name)return;
  var gidStr=prompt("GID (blank = auto-allocate >=1000):","");
  var body={name:name};
  if(gidStr&&gidStr.trim()){var g=parseInt(gidStr.trim(),10);if(!isNaN(g))body.gid=g;}
  api("POST","/portal/groups",body)
    .then(function(){toast("Created group "+name,"ok");return loadGroups();})
    .catch(function(err){toast(err.message,"err");});
}
function delGroup(name){
  if(!confirm("Delete group \""+name+"\"? Members lose this supplementary group."))return;
  api("DELETE","/portal/groups/"+encodeURIComponent(name))
    .then(function(){toast("Deleted group "+name,"ok");return refresh();})
    .catch(function(err){toast(err.message,"err");});
}

function syncNow(){
  api("POST","/portal/accounts/sync",{})
    .then(function(){toast("Sync scheduled — projecting SSOT to the OS","ok");})
    .catch(function(err){toast(err.message,"err");});
}

function closeModals(){
  $("acctModal").classList.remove("open");
  $("pwModal").classList.remove("open");
}
function refresh(){return Promise.all([loadAccounts(),loadGroups()]);}

// events
$("addBtn").onclick=function(){openForm(null);};
$("refreshBtn").onclick=function(){refresh();toast("refreshed");};
$("syncBtn").onclick=syncNow;
$("addGrpBtn").onclick=addGroup;
$("acctForm").addEventListener("submit",submitForm);
$("pwForm").addEventListener("submit",submitPw);

$("acctBody").addEventListener("click",function(e){
  var btn=e.target.closest("[data-act]");if(!btn)return;
  var u=btn.closest("tr").getAttribute("data-u"),act=btn.getAttribute("data-act");
  if(act==="edit")openForm(u);
  else if(act==="pw")openPw(u);
  else if(act==="toggle")toggleEnabled(u);
  else if(act==="del")delAccount(u);
});
$("grpWrap").addEventListener("click",function(e){
  var x=e.target.closest("[data-delg]");if(x)delGroup(x.getAttribute("data-delg"));
});
document.addEventListener("click",function(e){
  if(e.target.closest("[data-close]"))closeModals();
  if(e.target.classList.contains("modal"))closeModals();
});
document.addEventListener("keydown",function(e){if(e.key==="Escape")closeModals();});

refresh();
</script>
</body></html>

```


## edit usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py

```
=== EDIT 1 of 4 — INSERT the accounts applet routes ===
Location: immediately AFTER the get_portal_config_status handler and BEFORE the `@portal_router.get("/configure"...)` route (~line 1814).

OLD (anchor — leave unchanged, insert the new block between these two):
----------------------------------------------------------------------
        return JSONResponse({"error": "unavailable"})


@portal_router.get("/configure", response_class=HTMLResponse)
----------------------------------------------------------------------

NEW (anchor + inserted block):
----------------------------------------------------------------------
        return JSONResponse({"error": "unavailable"})


# ══════════════════════════════════════════════════════════════════════════════════════════
# MiOS Admin — accounts applet (WS-ACCT). The operator-facing accounts-management
# surface: a parameterized-SQL CRUD API over the mios_account / mios_group SSOT
# (all writes go through usr/lib/mios/mios_accounts.py -- the single data-access
# choke point; NO raw/interpolated SQL here) plus the self-contained web panel
# served at /portal/accounts-panel and mounted as an in-app iframe view by the
# Portal shell (same pattern as /portal/configurator). Every route is auth-gated
# by _portal_authed (401 JSON otherwise); every blocking DB call runs off the
# event loop via asyncio.to_thread. Reads use the ro role, mutations rw (the data
# layer chooses the connection). Passwords are accepted as plaintext ONLY to be
# hashed INSIDE the data layer -- never stored raw, never echoed, and
# password_hash is scrubbed to a has_password boolean on every read response.
# ══════════════════════════════════════════════════════════════════════════════════════════
_ACCOUNTS_HTML_PATH = os.environ.get(
    "MIOS_ACCOUNTS_HTML", "/usr/share/mios/accounts/mios-accounts.html")

# create_account accepts exactly these keys from a JSON body; anything else is
# dropped so a hostile/typo'd field can never reach the data layer as a kwarg.
_ACCOUNT_CREATE_KEYS = (
    "display_name", "description", "uid", "primary_gid", "shell",
    "is_admin", "is_service", "on_linux", "on_windows", "password",
    "must_change_pw", "groups")
# update_account whitelist (the data layer re-whitelists at the SQL layer; this
# is the API-surface guard). username/uid identity + password are mutated via
# their own dedicated routes, never the generic PUT.
_ACCOUNT_UPDATE_KEYS = (
    "display_name", "description", "primary_gid", "shell", "is_admin",
    "is_service", "on_linux", "on_windows", "must_change_pw", "home_dir")


def _accounts_mod():
    """Lazy-import the accounts data layer (usr/lib/mios/mios_accounts.py) at
    request time -- not module load -- so the portal keeps importing on a host
    without psycopg / the accounts schema, and a DB/schema outage surfaces as a
    handled 5xx rather than an import error."""
    import sys
    if "/usr/lib/mios" not in sys.path:
        sys.path.insert(0, "/usr/lib/mios")
    import mios_accounts
    return mios_accounts


def _accounts_scrub(row: Optional[dict]) -> Optional[dict]:
    """Never let a hash leave the box: drop password_hash from a read row and
    replace it with a boolean has_password so the UI shows whether a credential
    is set without ever seeing it."""
    if not isinstance(row, dict):
        return row
    out = dict(row)
    has_pw = bool(out.pop("password_hash", None))
    out["has_password"] = has_pw
    return out


def _accounts_error(exc: Exception) -> JSONResponse:
    """Map the data layer's typed exceptions (and raw SQLSTATEs) to HTTP status.
    DuplicateUsername/DuplicateGroup (23505) -> 409, UnknownGroup (23503) -> 400,
    FormatError (23514) -> 422, unknown account -> 404, other value errors ->
    400, anything else -> 500 (logged). Messages are operator-readable (the data
    layer raises clean messages, never raw driver dumps)."""
    name = type(exc).__name__
    status = {"DuplicateUsername": 409, "DuplicateGroup": 409,
              "UnknownGroup": 400, "UnknownAccount": 404,
              "AccountNotFound": 404, "FormatError": 422}.get(name)
    if status is None:
        code = str(getattr(exc, "sqlstate", "") or getattr(exc, "pgcode", ""))
        status = {"23505": 409, "23503": 400, "23514": 422}.get(code)
    if status is None:
        status = 400 if isinstance(exc, (ValueError, KeyError)) else 500
    if status >= 500:
        log.error("accounts applet: unhandled data-layer error: %s", exc)
    return JSONResponse({"error": str(exc), "type": name}, status_code=status)


async def _accounts_body(request: Request) -> dict:
    """Parse a JSON request body into a dict (empty dict for an empty body)."""
    raw = await request.body()
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("request body must be a JSON object")
    return data


def run_accounts_sync_bg() -> None:
    """Background task: project the SSOT to the live OS surfaces + reconcile. Runs
    the projector (SSOT -> userdb / Windows manifest) then the sync agent
    (surfaces -> live accounts). Degrade-open -- a missing binary or non-zero exit
    is logged, never raised (mirrors run_db_reseed_bg)."""
    import subprocess
    for bin_env, default in (
            ("MIOS_ACCOUNTS_PROJECTOR", "/usr/libexec/mios/mios-accounts-projector"),
            ("MIOS_ACCOUNT_SYNC", "/usr/libexec/mios/mios-account-sync")):
        path = os.environ.get(bin_env, default)
        try:
            subprocess.run([path], check=True, timeout=120)
        except Exception as e:  # noqa: BLE001 -- degrade-open, never block the request
            log.warning("accounts sync: %s failed: %s", path, e)


async def portal_accounts_panel_logic(request: Request):
    """Serve the self-contained accounts-management panel HTML (auth-gated). Read
    from disk at request time so live edits show without a restart; the SSOT
    palette is injected so the panel tracks the operator's theme like the
    dashboard + configurator do."""
    if not _portal_authed(request):
        return RedirectResponse("/login", status_code=303)
    try:
        with open(_ACCOUNTS_HTML_PATH, "r", encoding="utf-8") as fh:
            html = fh.read()
    except OSError:
        log.warning("portal accounts: panel not found at %s", _ACCOUNTS_HTML_PATH)
        return HTMLResponse(
            "<h1 style='font-family:sans-serif;padding:40px'>Accounts panel not found</h1>",
            status_code=404)
    html = html.replace("</head>", _portal_theme_css() + "</head>", 1)
    return HTMLResponse(html, headers={"Cache-Control": "no-store, must-revalidate"})


@portal_router.get("/portal/accounts-panel", response_class=HTMLResponse)
async def portal_accounts_panel(request: Request):
    """The accounts applet's web panel (iframe target for the Portal shell + a
    standalone deep link)."""
    return await portal_accounts_panel_logic(request)


@portal_router.get("/portal/accounts")
async def portal_accounts_list(request: Request) -> JSONResponse:
    """List MiOS-managed accounts (ro). ?platform=linux|windows filters to the
    in-scope projection; ?include_disabled=0 hides locked accounts. password_hash
    is scrubbed to a has_password boolean."""
    if not _portal_authed(request):
        return JSONResponse({"error": "auth required"}, status_code=401)
    platform = request.query_params.get("platform") or None
    include_disabled = (request.query_params.get("include_disabled", "1")
                        .strip().lower() not in ("0", "false", "no", "off"))
    try:
        rows = await asyncio.to_thread(
            lambda: _accounts_mod().list_accounts(
                platform=platform, include_disabled=include_disabled))
        return JSONResponse({"accounts": [_accounts_scrub(r) for r in rows]})
    except Exception as e:  # noqa: BLE001
        return _accounts_error(e)


@portal_router.get("/portal/accounts/{username}")
async def portal_account_get(username: str, request: Request) -> JSONResponse:
    if not _portal_authed(request):
        return JSONResponse({"error": "auth required"}, status_code=401)
    try:
        row = await asyncio.to_thread(lambda: _accounts_mod().get_account(username))
        if row is None:
            return JSONResponse({"error": "no such account", "username": username},
                                status_code=404)
        return JSONResponse(_accounts_scrub(row))
    except Exception as e:  # noqa: BLE001
        return _accounts_error(e)


@portal_router.post("/portal/accounts")
async def portal_account_create(request: Request) -> JSONResponse:
    """Create an account (rw). Body: {username, display_name?, description?, uid?,
    primary_gid?, shell?, is_admin?, is_service?, on_linux?, on_windows?,
    password?, must_change_pw?, groups?[]}. Plaintext password (if any) is hashed
    INSIDE the data layer and never echoed."""
    if not _portal_authed(request):
        return JSONResponse({"error": "auth required"}, status_code=401)
    try:
        body = await _accounts_body(request)
    except (ValueError, json.JSONDecodeError) as e:
        return JSONResponse({"error": f"invalid JSON body: {e}"}, status_code=400)
    username = (body.get("username") or "").strip()
    if not username:
        return JSONResponse({"error": "username is required"}, status_code=422)
    kwargs = {k: body[k] for k in _ACCOUNT_CREATE_KEYS if k in body}
    if "groups" in kwargs and kwargs["groups"] is None:
        kwargs["groups"] = ()
    try:
        row = await asyncio.to_thread(
            lambda: _accounts_mod().create_account(username, **kwargs))
        return JSONResponse(_accounts_scrub(row), status_code=201)
    except Exception as e:  # noqa: BLE001
        return _accounts_error(e)


@portal_router.put("/portal/accounts/{username}")
async def portal_account_update(username: str, request: Request) -> JSONResponse:
    """Update mutable account fields (rw). Identity (username/uid) + password are
    changed via their own routes, not here."""
    if not _portal_authed(request):
        return JSONResponse({"error": "auth required"}, status_code=401)
    try:
        body = await _accounts_body(request)
    except (ValueError, json.JSONDecodeError) as e:
        return JSONResponse({"error": f"invalid JSON body: {e}"}, status_code=400)
    fields = {k: body[k] for k in _ACCOUNT_UPDATE_KEYS if k in body}
    if not fields:
        return JSONResponse({"error": "no updatable fields supplied"}, status_code=422)
    try:
        row = await asyncio.to_thread(
            lambda: _accounts_mod().update_account(username, **fields))
        return JSONResponse(_accounts_scrub(row))
    except Exception as e:  # noqa: BLE001
        return _accounts_error(e)


@portal_router.post("/portal/accounts/{username}/password")
async def portal_account_password(username: str, request: Request) -> JSONResponse:
    """Set/reset an account password (rw). Body: {password, must_change_pw?}. The
    plaintext is hashed inside the data layer; the response NEVER echoes it."""
    if not _portal_authed(request):
        return JSONResponse({"error": "auth required"}, status_code=401)
    try:
        body = await _accounts_body(request)
    except (ValueError, json.JSONDecodeError) as e:
        return JSONResponse({"error": f"invalid JSON body: {e}"}, status_code=400)
    password = body.get("password")
    if not password:
        return JSONResponse({"error": "password is required"}, status_code=422)
    must_change = bool(body.get("must_change_pw", False))
    try:
        await asyncio.to_thread(
            lambda: _accounts_mod().set_password(
                username, password, must_change_pw=must_change))
        return JSONResponse({"status": "ok", "username": username})
    except Exception as e:  # noqa: BLE001
        return _accounts_error(e)


@portal_router.post("/portal/accounts/{username}/enabled")
async def portal_account_enabled(username: str, request: Request) -> JSONResponse:
    """Enable/disable (lock) an account WITHOUT deleting it (rw). Body:
    {enabled: bool}."""
    if not _portal_authed(request):
        return JSONResponse({"error": "auth required"}, status_code=401)
    try:
        body = await _accounts_body(request)
    except (ValueError, json.JSONDecodeError) as e:
        return JSONResponse({"error": f"invalid JSON body: {e}"}, status_code=400)
    if "enabled" not in body:
        return JSONResponse({"error": "enabled (bool) is required"}, status_code=422)
    enabled = bool(body.get("enabled"))
    try:
        await asyncio.to_thread(lambda: _accounts_mod().set_enabled(username, enabled))
        return JSONResponse({"status": "ok", "username": username, "enabled": enabled})
    except Exception as e:  # noqa: BLE001
        return _accounts_error(e)


@portal_router.post("/portal/accounts/{username}/groups")
async def portal_account_groups(username: str, request: Request) -> JSONResponse:
    """Replace an account's supplementary group set (rw). Body: {groups:[names]}."""
    if not _portal_authed(request):
        return JSONResponse({"error": "auth required"}, status_code=401)
    try:
        body = await _accounts_body(request)
    except (ValueError, json.JSONDecodeError) as e:
        return JSONResponse({"error": f"invalid JSON body: {e}"}, status_code=400)
    groups = body.get("groups")
    if not isinstance(groups, list):
        return JSONResponse({"error": "groups (list) is required"}, status_code=422)
    try:
        await asyncio.to_thread(
            lambda: _accounts_mod().set_members(username, [str(g) for g in groups]))
        return JSONResponse({"status": "ok", "username": username, "groups": groups})
    except Exception as e:  # noqa: BLE001
        return _accounts_error(e)


@portal_router.delete("/portal/accounts/{username}")
async def portal_account_delete(username: str, request: Request) -> JSONResponse:
    """Delete an account (rw). Memberships cascade; the break-glass local admin is
    outside this table and unaffected."""
    if not _portal_authed(request):
        return JSONResponse({"error": "auth required"}, status_code=401)
    try:
        await asyncio.to_thread(lambda: _accounts_mod().delete_account(username))
        return JSONResponse({"status": "ok", "username": username})
    except Exception as e:  # noqa: BLE001
        return _accounts_error(e)


@portal_router.get("/portal/groups")
async def portal_groups_list(request: Request) -> JSONResponse:
    if not _portal_authed(request):
        return JSONResponse({"error": "auth required"}, status_code=401)
    try:
        rows = await asyncio.to_thread(lambda: _accounts_mod().list_groups())
        return JSONResponse({"groups": rows})
    except Exception as e:  # noqa: BLE001
        return _accounts_error(e)


@portal_router.post("/portal/groups")
async def portal_group_create(request: Request) -> JSONResponse:
    """Create a group (rw). Body: {name, gid?, description?}."""
    if not _portal_authed(request):
        return JSONResponse({"error": "auth required"}, status_code=401)
    try:
        body = await _accounts_body(request)
    except (ValueError, json.JSONDecodeError) as e:
        return JSONResponse({"error": f"invalid JSON body: {e}"}, status_code=400)
    name = (body.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "name is required"}, status_code=422)
    try:
        row = await asyncio.to_thread(
            lambda: _accounts_mod().create_group(
                name, gid=body.get("gid"), description=body.get("description")))
        return JSONResponse(row, status_code=201)
    except Exception as e:  # noqa: BLE001
        return _accounts_error(e)


@portal_router.delete("/portal/groups/{name}")
async def portal_group_delete(name: str, request: Request) -> JSONResponse:
    if not _portal_authed(request):
        return JSONResponse({"error": "auth required"}, status_code=401)
    try:
        await asyncio.to_thread(lambda: _accounts_mod().delete_group(name))
        return JSONResponse({"status": "ok", "name": name})
    except Exception as e:  # noqa: BLE001
        return _accounts_error(e)


@portal_router.post("/portal/accounts/sync")
async def portal_accounts_sync(request: Request,
                               background_tasks: BackgroundTasks) -> JSONResponse:
    """Kick the projector + reconcile agent in the background (rw side effects).
    Returns immediately (degrade-open, like the config re-seed)."""
    if not _portal_authed(request):
        return JSONResponse({"error": "auth required"}, status_code=401)
    background_tasks.add_task(run_accounts_sync_bg)
    return JSONResponse({"status": "scheduled"})


@portal_router.get("/accounts", response_class=HTMLResponse)
async def portal_accounts_page(request: Request):
    """MiOS Admin -- the accounts applet as a unified portal sub-page. Serves the
    Portal shell HTML so it boots into the accounts view client-side (mirrors the
    /configure deep link)."""
    return await portal_page_logic(request)


@portal_router.get("/configure", response_class=HTMLResponse)
----------------------------------------------------------------------


=== EDIT 2 of 4 — add the 'Accounts' header button (inside _PORTAL_HTML, ~line 610) ===
OLD:
----------------------------------------------------------------------
  <button class="btn primary" id="installBtn">&#11015; Install</button>
  <button class="btn" id="chatToggle">&#128172; Chat</button>
  <button class="btn" id="settingsToggle">&#9881;&#65039; Settings</button>
----------------------------------------------------------------------
NEW:
----------------------------------------------------------------------
  <button class="btn primary" id="installBtn">&#11015; Install</button>
  <button class="btn" id="chatToggle">&#128172; Chat</button>
  <button class="btn" id="accountsToggle">&#128100; Accounts</button>
  <button class="btn" id="settingsToggle">&#9881;&#65039; Settings</button>
----------------------------------------------------------------------


=== EDIT 3 of 4 — add the accounts iframe view (inside _PORTAL_HTML, ~line 676) ===
OLD:
----------------------------------------------------------------------
<div id="settings-view" style="display:none; width:100%; height:calc(100vh - 65px); margin:0; padding:0; overflow:hidden;">
  <iframe id="settings-iframe" style="width:100%; height:100%; border:0; background:transparent;" src="about:blank"></iframe>
</div>
----------------------------------------------------------------------
NEW:
----------------------------------------------------------------------
<div id="settings-view" style="display:none; width:100%; height:calc(100vh - 65px); margin:0; padding:0; overflow:hidden;">
  <iframe id="settings-iframe" style="width:100%; height:100%; border:0; background:transparent;" src="about:blank"></iframe>
</div>

<div id="accounts-view" style="display:none; width:100%; height:calc(100vh - 65px); margin:0; padding:0; overflow:hidden;">
  <iframe id="accounts-iframe" style="width:100%; height:100%; border:0; background:transparent;" src="about:blank"></iframe>
</div>
----------------------------------------------------------------------


=== EDIT 4 of 4 — make the shell view-switch 3-way (dashboard/settings/accounts) ===
Replace the whole showView() block + its wiring (inside _PORTAL_HTML, ~lines 926-969).
OLD:
----------------------------------------------------------------------
function showView(view, push) {
  if (view === "settings") {
    $("dashboard-view").style.display = "none";
    $("settings-view").style.display = "block";
    $("settingsToggle").classList.add("active");
    var iframe = $("settings-iframe");
    if (!iframe.dataset.loaded) {
      iframe.src = "/portal/configurator";
      iframe.dataset.loaded = "1";
    }
    if (push) history.pushState({view: "settings"}, "", "/configure");
  } else {
    $("settings-view").style.display = "none";
    $("dashboard-view").style.display = "block";
    $("settingsToggle").classList.remove("active");
    if (push) history.pushState({view: "dashboard"}, "", "/");
  }
}
$("settingsToggle").onclick = function(e) {
  e.preventDefault();
  var isSettings = $("settings-view").style.display === "block";
  showView(isSettings ? "dashboard" : "settings", true);
};
$("logoLink").onclick = function(e) {
  e.preventDefault();
  showView("dashboard", true);
};
// "Edit in Settings ->" opens the configurator via the same in-app view switch
// as the gear; falls back to a real /configure navigation if JS is unavailable.
var _cfgEdit=$("cfgedit");
if(_cfgEdit)_cfgEdit.onclick=function(e){e.preventDefault();showView("settings",true);};
window.onpopstate = function(e) {
  if (location.pathname === "/configure") {
    showView("settings", false);
  } else {
    showView("dashboard", false);
  }
};
var initPath = location.pathname;
if (initPath === "/configure") {
  showView("settings", false);
} else {
  showView("dashboard", false);
}
----------------------------------------------------------------------
NEW:
----------------------------------------------------------------------
function hideAllViews() {
  $("dashboard-view").style.display = "none";
  $("settings-view").style.display = "none";
  $("accounts-view").style.display = "none";
  $("settingsToggle").classList.remove("active");
  $("accountsToggle").classList.remove("active");
}
function showView(view, push) {
  hideAllViews();
  if (view === "settings") {
    $("settings-view").style.display = "block";
    $("settingsToggle").classList.add("active");
    var f = $("settings-iframe");
    if (!f.dataset.loaded) { f.src = "/portal/configurator"; f.dataset.loaded = "1"; }
    if (push) history.pushState({view: "settings"}, "", "/configure");
  } else if (view === "accounts") {
    $("accounts-view").style.display = "block";
    $("accountsToggle").classList.add("active");
    var a = $("accounts-iframe");
    if (!a.dataset.loaded) { a.src = "/portal/accounts-panel"; a.dataset.loaded = "1"; }
    if (push) history.pushState({view: "accounts"}, "", "/accounts");
  } else {
    $("dashboard-view").style.display = "block";
    if (push) history.pushState({view: "dashboard"}, "", "/");
  }
}
$("settingsToggle").onclick = function(e) {
  e.preventDefault();
  showView($("settings-view").style.display === "block" ? "dashboard" : "settings", true);
};
$("accountsToggle").onclick = function(e) {
  e.preventDefault();
  showView($("accounts-view").style.display === "block" ? "dashboard" : "accounts", true);
};
$("logoLink").onclick = function(e) {
  e.preventDefault();
  showView("dashboard", true);
};
// "Edit in Settings ->" opens the configurator via the same in-app view switch
// as the gear; falls back to a real /configure navigation if JS is unavailable.
var _cfgEdit=$("cfgedit");
if(_cfgEdit)_cfgEdit.onclick=function(e){e.preventDefault();showView("settings",true);};
window.onpopstate = function(e) {
  if (location.pathname === "/configure") showView("settings", false);
  else if (location.pathname === "/accounts") showView("accounts", false);
  else showView("dashboard", false);
};
var initPath = location.pathname;
if (initPath === "/configure") showView("settings", false);
else if (initPath === "/accounts") showView("accounts", false);
else showView("dashboard", false);
----------------------------------------------------------------------

```


**wiring:** HOW IT WIRES

Data layer (sibling deliverable, hard dependency): every route calls ONLY usr/lib/mios/mios_accounts.py via the lazy `_accounts_mod()` import (adds /usr/lib/mios to sys.path at request time, like get_portal_config does). The applet emits NO SQL. It relies on this exact public API from the CONTRACTS spec: list_accounts(platform=, include_disabled=), get_account(username), create_account(username, **kwargs), update_account(username, **fields), set_password(username, plaintext, must_change_pw=), set_enabled(username, enabled), delete_account(username), list_groups(), create_group(name, gid=, description=), delete_group(name), set_members(username, group_names). Typed exceptions are mapped to HTTP by class name (DuplicateUsername/DuplicateGroup->409, UnknownGroup->400, FormatError->422, *NotFound/UnknownAccount->404) with a SQLSTATE fallback (23505/23503/23514) so the mapping still holds if the data layer surfaces a raw driver error carrying .sqlstate/.pgcode.

Mount: no server.py edit is required. New routes bind through the already-present `app.include_router(portal_router)` in server.py (~line 7798) and the surface gate composes them cross-file by reading portal_router directly (mios_surface.project_package). This matches the existing get_portal_config / get_portal_config_status routes, which live on portal_router and are NOT re-imported in server.py. OPTIONAL parity nicety (not needed to run): add the handler names (portal_accounts_list, portal_account_get, portal_account_create, portal_account_update, portal_account_password, portal_account_enabled, portal_account_groups, portal_account_delete, portal_groups_list, portal_group_create, portal_group_delete, portal_accounts_sync, portal_accounts_panel, portal_accounts_page) to server.py's `from mios_portal import (...)` list to keep them in server's importable `provided` surface, as the R13 comment convention prefers.

Auth: every route is gated by the existing _portal_authed(request) (cookie OR Bearer) and returns 401 JSON otherwise — same posture as /portal/config. The panel-serving routes (portal_accounts_panel_logic, /accounts) redirect to /login instead, matching portal_configure_page_logic / portal_page_logic. All blocking DB calls run off the event loop via asyncio.to_thread.

Panel serving + shell integration: the panel HTML ships at /usr/share/mios/accounts/mios-accounts.html (env override MIOS_ACCOUNTS_HTML) and is served raw + theme-injected by /portal/accounts-panel exactly like /portal/configurator. The four _PORTAL_HTML edits add an "Accounts" header button and an in-app iframe view (view key "accounts", deep-link /accounts served by the new shell route), reusing the Settings/configurator view-switch mechanism verbatim.

Secret hygiene: mios_account_export exposes password_hash; _accounts_scrub() strips it from EVERY read response (list/get/create/update) and replaces it with has_password:bool, so a hash never crosses the wire. Passwords are accepted as plaintext only on POST create + the dedicated /password route and are hashed INSIDE the data layer (hashing never happens in the caller per the contract); responses never echo them.

Route-ordering: POST /portal/accounts/sync is a static sub-path and never collides with GET/PUT/DELETE /portal/accounts/{username} (different methods) or POST /portal/accounts (different path). Verified.

Sync: POST /portal/accounts/sync schedules run_accounts_sync_bg (FastAPI BackgroundTasks), which shells mios-accounts-projector then mios-account-sync (env-overridable), degrade-open like run_db_reseed_bg.

Assumption: mios_accounts.py returns JSON-native dicts (it goes through mios-pg-query --exec-json), so timestamps arrive as strings and member_groups/member_gids as plain arrays — FastAPI's JSONResponse serializes them directly. If a future variant returns raw psycopg datetime objects, the data layer (not the applet) should normalize them, keeping the applet a pure pass-through.

Packaging: add usr/share/mios/accounts/mios-accounts.html to the file manifest/RPM %files so the asset is baked into the image (peer of usr/share/mios/configurator/mios.html).

Validation done in-session: the inserted route block compiles and imports cleanly against FastAPI-shaped stubs (py import OK); the panel HTML is self-contained (no external hosts, inline CSS/JS only) and uses the same CSS var names the Portal injects from mios.toml [colors].


# COMPONENT: Windows AccountSync (DB -> Windows local accounts) — MiOS-AccountSync.ps1


## edit mios-bootstrap/cat/autounattend/MiOS-AccountSync.ps1

```
# AI-hint: Windows DB->SAM account reconciler. Single-pass payload of the MiOS-AccountSync MINUTE task (schtasks /sc MINUTE /mo 1 -File C:\ProgramData\MiOS\MiOS-AccountSync.ps1). Reads the Windows-scoped desired account state from the MiOS Postgres accounts SSOT via the mios_account_export view -- queried over the WSL loopback-trust bridge (wsl.exe -> python3 /usr/libexec/mios/mios-pg-query --exec-json), the same injection-safe parameterized transport the agent plane uses -- then reconciles Windows LOCAL accounts idempotently: New-LocalUser / Set-LocalUser / Enable/Disable-LocalUser / Add|Remove-LocalGroupMember / Remove-LocalUser for accounts whose on_windows scope was withdrawn. Degrade-open (a DB outage NEVER mutates or deletes local accounts) and break-glass-safe (the RID-500 Administrator + built-ins are never touched).
# AI-related: MiOS-Host.ps1, MiOS-Provision.lib.ps1, New-MiOSISO.ps1, usr/libexec/mios/mios-pg-query, usr/libexec/mios/mios-accounts-projector, usr/libexec/mios/mios-account-sync (Linux peer), usr/lib/mios/mios_accounts.py, usr/share/mios/postgres/accounts-schema.sql, mios.toml [[autounattend.accounts]]
# 'MiOS' -- Windows DB->SAM live account-sync service (single-pass, task-driven)
#Requires -Version 5.1
<#
.SYNOPSIS
    Reconcile Windows local accounts from the MiOS Postgres accounts SSOT.
    Single-pass: the MiOS-AccountSync MINUTE scheduled task re-invokes it every
    minute, so this script runs ONE reconcile and exits (no internal loop).
.DESCRIPTION
    Desired state is read from the mios_account_export view (WHERE on_windows) --
    the same denormalized projector surface the Linux projector consumes. The read
    goes through the WSL loopback-trust bridge: wsl.exe -d <distro> runs
    `python3 /usr/libexec/mios/mios-pg-query --exec-json` inside the MiOS distro,
    which speaks the PG v3 extended (parameterized) protocol to pgvector. NO DB
    credential lives on the Windows side -- auth is pg_hba loopback `trust` inside
    the guest, reached only via the WSL user's registered distro. This is chosen
    over the AI-plane HTTP API because the HTTP path would require minting/holding
    a Portal auth token on disk; the WSL bridge reuses the existing credential-free
    transport and matches every other MiOS DB consumer.
.PARAMETER StateDir     Root for logs + the managed-account state file.
.PARAMETER Distro       Exact WSL distro name; empty -> auto-resolve (as MiOS-Host).
.PARAMETER PgPort       Override pgvector port inside the distro (else mios-pg-query
                        env defaults apply, matching the rest of the plane).
.NOTES
    WinPS 5.1 compatible: no '&&' / '||' pipeline chain operators, no ternary.
    Must run in a context that can see the MiOS WSL distro (the distro is
    registered per-user, like the MiOS-Host mios-sudo identity); when it cannot,
    the script degrades open (logs + exits 0) and mutates nothing.
#>
[CmdletBinding()]
param(
    [string]$StateDir = 'C:\ProgramData\MiOS',
    [string]$Distro   = '',
    [int]$PgPort      = 0
)

$ErrorActionPreference = 'Continue'

# -- paths + logging -----------------------------------------------------------
$logDir    = Join-Path $StateDir 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log       = Join-Path $logDir 'mios-accountsync.log'
$marker    = Join-Path $StateDir 'accountsync.marker'          # heartbeat: last run + status
$stateFile = Join-Path $StateDir 'accountsync-managed.json'    # accounts THIS tool created/manages
$queryFile = Join-Path $StateDir 'MiOS-AccountSync.query.json' # the --exec-json envelope (fed via /mnt/c)

function Write-Log {
    param([string]$Msg)
    $ts   = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$ts] $Msg"
    Write-Output $line
    try { $line | Out-File -FilePath $log -Append -Encoding utf8 } catch {}
}

function Write-Marker {
    param([string]$Status)
    try {
        $obj = @{ ran = (Get-Date).ToString('o'); status = $Status; host = $env:COMPUTERNAME }
        ($obj | ConvertTo-Json -Compress) | Set-Content -Path $marker -Encoding utf8
    } catch {}
}

# Break-glass + Windows built-ins that this tool must NEVER create, modify, or
# delete -- the RID-500 local Administrator stays reachable independent of the DB
# (per doc-postgresos-accounts.md break-glass), and the MiOS-Host WSL identity
# (mios-sudo) must not be disturbed by an accounts churn.
$ProtectedUsers = @(
    'Administrator', 'DefaultAccount', 'Guest', 'WDAGUtilityAccount',
    'mios-sudo', 'SYSTEM', 'LocalService', 'NetworkService'
)
function Test-ProtectedUser {
    param([string]$Name)
    foreach ($p in $ProtectedUsers) {
        if ($Name -and $p -and ($Name -eq $p)) { return $true }
    }
    return $false
}

# -- WSL distro resolution (mirror MiOS-Host: exact-name match, real distro) ----
$env:WSL_UTF8 = '1'   # force UTF-8 from wsl.exe (else UTF-16LE mojibake under PS 5.1)
$wsl = if (Test-Path "$env:ProgramFiles\WSL\wsl.exe") { "$env:ProgramFiles\WSL\wsl.exe" } else { 'wsl.exe' }

function Resolve-MiOSDistro {
    param([string]$Preferred)
    $candidates = @($Preferred, 'MiOS', 'podman-MiOS-DEV', 'MiOS-DEV') |
                  Where-Object { $_ } | Select-Object -Unique
    $names = @()
    try {
        $names = (((& $wsl --list --quiet 2>$null) -join "`n") -replace "`0", '') -split "`r?`n" |
                 ForEach-Object { $_.Trim() } | Where-Object { $_ }
    } catch { return $null }
    foreach ($c in $candidates) { if ($names -contains $c) { return $c } }
    return $null
}

# -- PG helpers ----------------------------------------------------------------
function ConvertFrom-PgBool {
    param([string]$V)
    return ($V -eq 't')
}

# array_to_string(member_groups, ',') -> "a,b,c" (empty -> ''). Group names are
# constrained to ^[a-z_][a-z0-9_-]{0,31}$ so a plain comma split is exact.
function Split-Groups {
    param([string]$V)
    if (-not $V) { return @() }
    $v = $V.Trim()
    if (-not $v) { return @() }
    return @($v -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

# Read the Windows-scoped desired state from mios_account_export. Returns a
# hashtable: @{ ok = <bool query succeeded>; rows = @( per-account hashtables ) }.
# Parameterized envelope (no interpolated values); free-text columns are stripped
# of tab/CR/LF in-SQL so the tab-separated wire shape can never be corrupted.
function Get-DesiredAccounts {
    param([string]$DistroName)

    $sql = @'
SELECT username,
       translate(COALESCE(display_name,''), E'\t\n\r', '   '),
       translate(COALESCE(description,''),  E'\t\n\r', '   '),
       enabled,
       is_admin,
       is_service,
       must_change_pw,
       primary_group,
       array_to_string(member_groups, ',')
FROM mios_account_export
WHERE on_windows
ORDER BY username
'@

    # Single-statement parameterized envelope ({"sql","params"}); params empty --
    # this is a fixed projection read, no caller-supplied values are ever spliced.
    $envelope = @{ sql = $sql; params = @() } | ConvertTo-Json -Compress

    # Write WITHOUT a BOM: mios-pg-query does json.loads(sys.stdin.read()); a
    # UTF-8 BOM would make that raise. PS 5.1 Out-File -Encoding utf8 emits a BOM,
    # so use the .NET writer with a BOM-less UTF8Encoding.
    try {
        [System.IO.File]::WriteAllText($queryFile, $envelope, (New-Object System.Text.UTF8Encoding($false)))
    } catch {
        Write-Log "ERROR: could not stage query envelope: $($_.Exception.Message)"
        return @{ ok = $false; rows = @() }
    }

    # Feed the envelope over /mnt/c (WSL2 auto-mount) as stdin -- avoids all
    # shell-quoting/escaping of the JSON. Optional port override is exported inline.
    $wslQueryPath = '/mnt/c/ProgramData/MiOS/MiOS-AccountSync.query.json'
    $portPrefix   = ''
    if ($PgPort -gt 0) { $portPrefix = "MIOS_PORT_PGVECTOR=$PgPort MIOS_PG_PORT=$PgPort " }
    $bashCmd = "$portPrefix" + "python3 /usr/libexec/mios/mios-pg-query --exec-json < '$wslQueryPath'"

    $out = & $wsl -d $DistroName -- /bin/bash -c $bashCmd 2>$null
    $code = $LASTEXITCODE

    if ($code -ne 0) {
        Write-Log "DB query failed (wsl/mios-pg-query exit=$code) -- degrade-open, no reconcile"
        return @{ ok = $false; rows = @() }
    }

    $rows = @()
    $lines = @($out) -split "`r?`n" | ForEach-Object { ($_ -replace "`0", '').TrimEnd() } |
             Where-Object { $_ -ne '' }
    foreach ($line in $lines) {
        $f = $line -split "`t"
        if ($f.Count -lt 9) {
            Write-Log "skip malformed row ($($f.Count) cols): $line"
            continue
        }
        $rows += @{
            Username     = $f[0].Trim()
            DisplayName  = $f[1]
            Description  = $f[2]
            Enabled      = (ConvertFrom-PgBool $f[3])
            IsAdmin      = (ConvertFrom-PgBool $f[4])
            IsService    = (ConvertFrom-PgBool $f[5])
            MustChangePw = (ConvertFrom-PgBool $f[6])
            PrimaryGroup = $f[7].Trim()
            Groups       = (Split-Groups $f[8])
        }
    }
    return @{ ok = $true; rows = $rows }
}

# -- managed-state persistence (which accounts + supplementary groups WE own) --
function Read-ManagedState {
    $managed = @{}
    if (Test-Path $stateFile) {
        try {
            $j = Get-Content $stateFile -Raw -ErrorAction Stop | ConvertFrom-Json
            if ($j -and $j.users) {
                foreach ($p in $j.users.PSObject.Properties) {
                    $groups = @()
                    if ($p.Value -and $p.Value.groups) { $groups = @($p.Value.groups) }
                    $managed[$p.Name] = @{ groups = $groups }
                }
            }
        } catch { Write-Log "warn: could not parse state file, treating as empty: $($_.Exception.Message)" }
    }
    return $managed
}

function Write-ManagedState {
    param([hashtable]$Managed)
    $state = @{ version = 1; updated = (Get-Date).ToString('o'); users = @{} }
    foreach ($u in $Managed.Keys) {
        $state.users[$u] = @{ groups = @($Managed[$u].groups) }
    }
    try {
        ($state | ConvertTo-Json -Depth 6) | Set-Content -Path $stateFile -Encoding utf8
    } catch { Write-Log "warn: could not write state file: $($_.Exception.Message)" }
}

# -- local-account primitives (idempotent) -------------------------------------
function New-RandomSecurePassword {
    # Windows leg cannot reuse the Linux crypt $6$/$y$ hash (different algo); create
    # with a strong random secret. Real credential provisioning is out-of-band
    # (must_change_pw drives the change-at-logon flow); we never reset an existing
    # user's password here (no churn / no lockout of a working credential).
    $chars = [char[]](33..126)
    $pw = -join (1..24 | ForEach-Object { $chars | Get-Random })
    return (ConvertTo-SecureString $pw -AsPlainText -Force)
}

function Set-ChangePasswordAtLogon {
    param([string]$Name, [bool]$Value)
    try {
        if ($Value) { & net.exe user $Name /logonpasswordchg:yes | Out-Null }
        else        { & net.exe user $Name /logonpasswordchg:no  | Out-Null }
    } catch { Write-Log "warn: logonpasswordchg for '$Name' failed: $($_.Exception.Message)" }
}

function Ensure-LocalGroup {
    param([string]$Name)
    $g = Get-LocalGroup -Name $Name -ErrorAction SilentlyContinue
    if (-not $g) {
        try {
            New-LocalGroup -Name $Name -Description 'MiOS-managed group' -ErrorAction Stop | Out-Null
            Write-Log "created local group '$Name'"
            return $true
        } catch {
            Write-Log "warn: could not create group '$Name': $($_.Exception.Message)"
            return $false
        }
    }
    return $true
}

function Test-GroupMember {
    param([string]$Group, [string]$Member)
    try {
        $m = Get-LocalGroupMember -Group $Group -ErrorAction Stop
        foreach ($x in $m) {
            # .Name is DOMAIN\user or COMPUTER\user; match the leaf.
            $leaf = ($x.Name -split '\\')[-1]
            if ($leaf -eq $Member) { return $true }
        }
    } catch {}
    return $false
}

function Add-GroupMemberIfMissing {
    param([string]$Group, [string]$Member)
    if (Test-GroupMember -Group $Group -Member $Member) { return }
    try {
        Add-LocalGroupMember -Group $Group -Member $Member -ErrorAction Stop
        Write-Log "added '$Member' to group '$Group'"
    } catch { Write-Log "warn: add '$Member' to '$Group' failed: $($_.Exception.Message)" }
}

function Remove-GroupMemberIfPresent {
    param([string]$Group, [string]$Member)
    if (-not (Test-GroupMember -Group $Group -Member $Member)) { return }
    try {
        Remove-LocalGroupMember -Group $Group -Member $Member -ErrorAction Stop
        Write-Log "removed '$Member' from group '$Group'"
    } catch { Write-Log "warn: remove '$Member' from '$Group' failed: $($_.Exception.Message)" }
}

# Reconcile ONE desired account into the local SAM. Returns the supplementary
# group set actually managed for this user (for state persistence).
function Sync-Account {
    param([hashtable]$Acct)

    $name = $Acct.Username
    if (Test-ProtectedUser $name) {
        Write-Log "skip protected/break-glass account '$name'"
        return $null
    }

    $existing = Get-LocalUser -Name $name -ErrorAction SilentlyContinue

    if (-not $existing) {
        try {
            $params = @{
                Name                 = $name
                Password             = (New-RandomSecurePassword)
                FullName             = $Acct.DisplayName
                Description          = $Acct.Description
                AccountNeverExpires  = $true
                ErrorAction          = 'Stop'
            }
            if (-not $Acct.MustChangePw) { $params['PasswordNeverExpires'] = $true }
            New-LocalUser @params | Out-Null
            Write-Log "created local user '$name'"
            $existing = Get-LocalUser -Name $name -ErrorAction SilentlyContinue
        } catch {
            Write-Log "ERROR: create user '$name' failed: $($_.Exception.Message)"
            return $null
        }
    } else {
        # Update FullName/Description only on drift (avoid needless SAM writes).
        $needFull = ($existing.FullName -ne $Acct.DisplayName)
        $needDesc = ($existing.Description -ne $Acct.Description)
        if ($needFull -or $needDesc) {
            try {
                Set-LocalUser -Name $name -FullName $Acct.DisplayName -Description $Acct.Description -ErrorAction Stop
                Write-Log "updated FullName/Description for '$name'"
            } catch { Write-Log "warn: Set-LocalUser '$name' failed: $($_.Exception.Message)" }
        }
    }

    if (-not $existing) { return $null }

    # enabled -> Enable/Disable (locks, never deletes).
    try {
        if ($Acct.Enabled -and -not $existing.Enabled) {
            Enable-LocalUser -Name $name -ErrorAction Stop; Write-Log "enabled '$name'"
        } elseif (-not $Acct.Enabled -and $existing.Enabled) {
            Disable-LocalUser -Name $name -ErrorAction Stop; Write-Log "disabled '$name'"
        }
    } catch { Write-Log "warn: enable/disable '$name' failed: $($_.Exception.Message)" }

    # must_change_pw -> change-at-logon (only meaningful on real credential set;
    # applied idempotently regardless).
    if ($Acct.MustChangePw) { Set-ChangePasswordAtLogon -Name $name -Value $true }

    # Administrators membership is authoritative from is_admin (both directions).
    if ($Acct.IsAdmin) { Add-GroupMemberIfMissing   -Group 'Administrators' -Member $name }
    else               { Remove-GroupMemberIfPresent -Group 'Administrators' -Member $name }

    # Supplementary groups (excludes primary + Administrators). Ensure each exists,
    # then add. Removal from groups WE previously managed is handled by the caller
    # via the returned set diffed against prior managed state.
    $managedGroups = @()
    foreach ($g in $Acct.Groups) {
        if (-not $g) { continue }
        if ($g -eq 'Administrators') { continue }   # handled above via is_admin
        if (Ensure-LocalGroup -Name $g) {
            Add-GroupMemberIfMissing -Group $g -Member $name
            $managedGroups += $g
        }
    }

    if ($Acct.IsService) {
        Write-Log "note: '$name' is a service account (interactive-profile steps skipped)"
    }

    return @($managedGroups)
}

# ==============================================================================
# MAIN -- one reconcile pass.
# ==============================================================================
Write-Log 'MiOS-AccountSync: reconcile pass start'

$distro = Resolve-MiOSDistro -Preferred $Distro
if (-not $distro) {
    Write-Log 'no MiOS WSL distro visible in this context -- degrade-open, nothing changed'
    Write-Marker 'no-distro'
    return
}
Write-Log "using distro '$distro'"

$desired = Get-DesiredAccounts -DistroName $distro
$priorManaged = Read-ManagedState
$newManaged   = @{}

if (-not $desired.ok) {
    # DB unreachable / query error: DO NOT reconcile removals or mutate anything.
    # Preserve prior managed state untouched so a transient outage never deletes
    # local accounts. (Degrade-open is the whole point of the break-glass posture.)
    Write-Log 'desired-state read failed -- preserving state, no mutations this pass'
    Write-Marker 'db-unreachable'
    return
}

Write-Log "desired Windows-scoped accounts: $($desired.rows.Count)"

# 1) Create / update each desired account + its group memberships.
foreach ($acct in $desired.rows) {
    try {
        $grp = Sync-Account -Acct $acct
        if ($null -ne $grp) { $newManaged[$acct.Username] = @{ groups = @($grp) } }
    } catch {
        Write-Log "ERROR reconciling '$($acct.Username)': $($_.Exception.Message)"
        # keep prior record so we don't orphan/remove on a per-user hiccup
        if ($priorManaged.ContainsKey($acct.Username)) { $newManaged[$acct.Username] = $priorManaged[$acct.Username] }
    }
}

# 2) Supplementary-group removals: for accounts still present, pull them out of
#    any group WE previously added that is no longer desired (only groups we own).
foreach ($u in $newManaged.Keys) {
    if (-not $priorManaged.ContainsKey($u)) { continue }
    $prev = @($priorManaged[$u].groups)
    $now  = @($newManaged[$u].groups)
    foreach ($g in $prev) {
        if ($now -notcontains $g) { Remove-GroupMemberIfPresent -Group $g -Member $u }
    }
}

# 3) Account removals: any account WE previously managed that is no longer
#    on_windows (dropped from the query result) is deleted. Query succeeded
#    (checked above) so an empty/short result is authoritative, not an outage.
foreach ($u in $priorManaged.Keys) {
    if ($newManaged.ContainsKey($u)) { continue }
    if (Test-ProtectedUser $u) { continue }
    $lu = Get-LocalUser -Name $u -ErrorAction SilentlyContinue
    if ($lu) {
        try {
            Remove-LocalUser -Name $u -ErrorAction Stop
            Write-Log "removed local user '$u' (no longer Windows-scoped in SSOT)"
        } catch { Write-Log "warn: Remove-LocalUser '$u' failed: $($_.Exception.Message)" }
    }
}

Write-ManagedState -Managed $newManaged
Write-Marker 'ok'
Write-Log "MiOS-AccountSync: reconcile pass complete (managed=$($newManaged.Count))"

```


**wiring:** WHAT THIS IS: Phase-2 Windows AccountSync. Full replacement of mios-bootstrap/cat/autounattend/MiOS-AccountSync.ps1 (staged verbatim to C:\ProgramData\MiOS\MiOS-AccountSync.ps1 by New-MiOSISO.ps1). Validated: passes the PowerShell AST parser (2160 tokens, 0 errors); the ConvertTo-Json -> BOM-less file -> Python json.loads round-trip was exercised and confirmed (params=[], SQL E'\\t\\n\\r' escapes survive intact).

DB ACCESS / AUTH (the requested "pick the robust one + note it"): the WSL loopback-trust bridge, NOT the HTTP API. wsl.exe -d <distro> -- /bin/bash -c "python3 /usr/libexec/mios/mios-pg-query --exec-json < /mnt/c/.../MiOS-AccountSync.query.json". No credential is stored on Windows: mios-pg-query connects over 127.0.0.1 inside the guest where pg_hba is `trust`, and the guest is reachable only through the WSL user's own registered distro. The HTTP-API alternative was rejected because it would require minting and storing a Portal (:8640) auth token on the Windows box. The envelope is the parameterized {"sql","params"} shape mios-pg-query already supports (params empty here — fixed projection read, zero interpolation), fed as stdin via the WSL2 /mnt/c auto-mount to sidestep JSON shell-quoting entirely. Free-text columns are translate()-scrubbed of tab/CR/LF in-SQL so the tab-separated wire output can't be corrupted.

READS FROM SCHEMA: the mios_account_export view (the single projector read surface from accounts-schema.sql), filtered WHERE on_windows. Consumes exactly: username, display_name, description, enabled, is_admin, is_service, must_change_pw, primary_group, member_groups. Field mapping honored: enabled->Enable/Disable-LocalUser, is_admin->Administrators membership (both directions, authoritative), is_service->skip interactive-profile steps, must_change_pw->net user /logonpasswordchg:yes, member_groups->New-LocalGroup+Add-LocalGroupMember. password_hash is intentionally NOT selected/used: the Linux crypt hash can't be reused on Windows, so New-LocalUser gets a random SecureString and existing users' passwords are never touched (out-of-band credential provisioning).

DESIGN CORRECTION vs the old file: the MiOS-AccountSync task is `schtasks /sc MINUTE /mo 1` (confirmed in the autounattend RunSynchronousCommand), i.e. re-invoked every minute — so this is SINGLE-PASS (runs one reconcile, exits), replacing the old infinite `while($true){Start-Sleep}` loop that would have blocked all subsequent task launches. It also targets the NEW normalized view instead of the legacy flat `account` table + mios_identity.aliases.

SAFETY: (1) Degrade-open — if the distro isn't visible or the query fails (exit!=0), it logs, writes a marker, and returns WITHOUT mutating/deleting anything; removals only run when the query provably succeeded. (2) Break-glass — Administrator/DefaultAccount/Guest/WDAGUtilityAccount/mios-sudo/SYSTEM/LocalService/NetworkService are never created, modified, or deleted. (3) Removal is bounded to accounts THIS tool created: it persists C:\ProgramData\MiOS\accountsync-managed.json (usernames + the supplementary groups it added); only entries in that state file that vanish from the on_windows result are Remove-LocalUser'd, and per-user group removals only touch groups the tool itself added. Heartbeat/status in accountsync.marker; log in logs\mios-accountsync.log (matches MiOS-Host's StateDir\logs convention).

ASSUMPTIONS: (a) The distro is registered per-user (like MiOS-Host's mios-sudo identity); the task must run in a context that can see it. The autounattend currently sets /ru SYSTEM — as SYSTEM the per-user distro may be invisible, in which case the script degrades open (mutates nothing). RECOMMENDATION to the orchestrator/Phase-that-owns-autounattend: change the MiOS-AccountSync task's /ru to the same .\mios-sudo identity MiOS-Host runs under (or whichever account owns the WSL distro) so the DB read actually resolves. (b) WSL2 /mnt/c auto-mount is enabled (default). (c) pgvector is reachable on mios-pg-query's env-resolved port inside the distro (matching every other in-distro consumer); a -PgPort override param is provided if a deployment needs to force MIOS_PORT_PGVECTOR/MIOS_PG_PORT. (d) Distro auto-resolution mirrors MiOS-Host's candidate list (MiOS, podman-MiOS-DEV, MiOS-DEV) with exact-name match; -Distro overrides. WinPS 5.1 clean (no &&/||, no ternary; splatting + BOM-less .NET file write used deliberately).


# COMPONENT: MIOS_ACCOUNTS_DB_BACKED wiring (userenv.sh twin) + drift-gate check (59, WS-ACCT) in automation/38-drift-checks.sh


## edit tools/lib/userenv.sh

```
See note: three old->new hunks for tools/lib/userenv.sh (apply identically to the usr/lib/mios/userenv.sh twin).
```


## edit usr/lib/mios/userenv.sh

```
Identical edits to the tools/lib/userenv.sh hunks above -- see that file's note for the full old->new text.
```


## edit automation/38-drift-checks.sh

```
See note: two old->new hunks -- (A) the check_accounts_db function inserted before `main() {`, and (B) its registration between check_nut_projection and check_version_ssot in the main() run list.
```


**wiring:** HOW IT WIRES / KEY FINDINGS:\n\n1. ROOT CAUSE of the inert flag: I empirically sourced the CURRENT tools/lib/userenv.sh against usr/share/mios/mios.toml and it DOES emit MIOS_ACCOUNTS_DB_BACKED=true (via the generic section walk, since `accounts` is in neither EXCLUDED_SECTIONS nor WALK_MOSTLY_DEAD). So the derivation is not broken in the canonical vendor config -- it is IMPLICIT and fragile: (a) it silently produces nothing if [accounts] is absent from all layers (e.g. the ROOT /c/MiOS/mios.toml has NO [accounts] section; usr/share/mios/mios.toml lines 92-94 does: db_backed=true, db_render_prefs=false), leaving 17-accounts-db.sh line 35 to fall back to its own `${MIOS_ACCOUNTS_DB_BACKED:-false}` and always `systemctl disable`; and (b) it would vanish if anyone reclassified `accounts` into WALK_MOSTLY_DEAD/EXCLUDED. My HUNK 2 (explicit get_aliases branch, emitted by the UNCONDITIONAL alias loop at userenv.sh lines ~563-564) + HUNK 3 (post-load canonicalization with a guaranteed strict-true/false export, mirroring the existing MIOS_PG_BIND_ADDR block at lines 602-605) make the flag explicit AND non-inert in every layering.\n\n2. TWIN PARITY: tools/lib/userenv.sh and usr/lib/mios/userenv.sh are currently byte-identical (verified via diff -q). Drift-check 27 (check_userenv_parity, line ~1563) fails the build on any divergence, so the three hunks MUST be applied identically to both. 36-tools.sh (lines 66-74) installs the tools/lib copy to /usr/lib/mios/userenv.sh at build.\n\n3. CONSUMER: automation/17-accounts-db.sh line 35 already reads `${MIOS_ACCOUNTS_DB_BACKED:-false}` (via lib/common.sh -> _mios_locate_userenv -> source userenv.sh). No edit needed there; my new check's sub-assertion (d) anti-regresses that it keeps gating on the flag.\n\n4. NEW DRIFT-CHECK numbering: labelled (59, WS-ACCT) -- verified free (used numbers run through 58; 59-63 unused). Registered in main() between check_nut_projection and check_version_ssot; also individually runnable via `automation/38-drift-checks.sh check_accounts_db` (main()'s single-arg dispatch at lines 3520-3531).\n\n5. DEGRADE-OPEN on partial merge: the sibling Phase-1/3/4 artifacts do NOT exist yet in the tree (confirmed: only usr/libexec/mios/mios-account-sync is present; accounts-schema.sql, mios_accounts.py, mios-accounts, mios-accounts-projector are absent). The check follows repo convention (absent -> WARN/skip, present-but-broken -> FAIL). Sub-assertion (a) MIOS_ACCOUNTS_DB_BACKED derivation and the 17-accounts-db gate anti-regression are ALWAYS enforced, so this Phase-2 deliverable is green on its own and tightens automatically as the other phases land.\n\n6. Assumptions: schema file lands at usr/share/mios/postgres/accounts-schema.sql (per the design's schema deliverable path, alongside the existing schema-init.sql); data layer at usr/lib/mios/mios_accounts.py; CLI dispatcher at usr/libexec/mios/mios-accounts; projector at usr/libexec/mios/mios-accounts-projector -- all matching the CONTRACTS section paths. The token-grep coverage list in sub-assertion (b) matches the exact column names in the SCHEMA deliverable (mios_account/mios_group/mios_account_export/mios_account_group + username,uid,primary_gid,enabled,is_admin,is_service,on_linux,on_windows,password_hash,must_change_pw).