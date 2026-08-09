<!-- AI-hint: DB-Driven Cross-Platform Account Architecture for MiOS ("PostgresOS").
     AI-related: usr/share/mios/mios.toml, docs/adr/, AGY-TASKS.md -->
# DB-Driven Cross-Platform Account Architecture for MiOS ("PostgresOS")

## 1. Direct answer: what is "PostgresOS"?

**"PostgresOS" is not a real product. It is the operator's own coinage** — a north-star label for MiOS's design goal of one PostgreSQL instance as the single source of truth for accounts/identity, projected to every platform. Targeted web/GitHub searches for the literal string return only generic PostgreSQL ecosystem hits (postgres.org related-projects, Bucardo, Postgres-XC/XL forks) and unrelated "Postgres project" tooling — **there is no OS, distro, framework, or FOSS package whose accounts/identity natively live in Postgres** [postgresql.org/developer/related-projects]. Confirmed absent as of 2026-07.

**Implication for MiOS:** Do not hunt for a turnkey upstream by this name — the `MIOS_ACCOUNTS_DB_BACKED` flag ships *inert precisely because* there is no single "PostgresOS" package to install; the concept must be **assembled** from the confirmed FOSS bricks below. Any ADR should state plainly that "PostgresOS" is a MiOS concept name mapped to a concrete component stack, so future contributors don't chase a nonexistent repo.

**Closest real building blocks** (the honest decomposition of the concept):
- **Linux identity/auth:** systemd userdb (adopt) / libnss-pgsql + pam-pgsql (legacy reference) / SSSD (consumer)
- **Cross-platform projection:** an LDAP or SCIM front over Postgres (lldap = adopt; OpenLDAP back-sql / FreeIPA = reference; Keycloak+SCIM = watch)
- **Windows local accounts:** autounattend/SetupComplete generation from the DB (build-time) and/or a pGina-style credential provider (runtime)

---

## 2. The building blocks

| Layer | FOSS mechanism | How a Postgres row becomes an account | License | MiOS fit |
|---|---|---|---|---|
| **Linux — identity (NSS)** | **systemd userdb** (systemd-userdbd + nss-systemd + Varlink providers) [systemd.io/USER_RECORD] | Row → JSON User Record, served either live by a MiOS Varlink provider or projected into a static `/usr/lib/userdb/<name>.user` drop-in; nss-systemd synthesizes `struct passwd`/`shadow`/`group` for full `getpwnam` compat | LGPL-2.1-or-later | **adopt_now** — modern, maintained, matches MiOS SSOT-projection + drift-gate model exactly (same shape as mios-theme-render / dotfiles registry). Linux-only. |
| **Linux — identity (NSS)** | **libnss-pgsql** [github.com/jandd/libnss-pgsql] | `passwd: files pgsql` in nsswitch.conf → `getpwnam` queries Postgres directly; dbschema.sql maps columns to passwd/shadow/group | GPL-2.0 | **reference** — the most literal "row IS the account" pattern, but archived (~2004, Debian removed libnss-pgsql2 in 2024, known to hang on DB outage). Mine for schema, don't ship. |
| **Linux — auth (PAM)** | **pam-pgsql** [github.com/pam-pgsql/pam-pgsql] | `auth_query` pulls password hash from a Postgres column, compares to supplied credential; account/pwd/session queries handle expiry & changes | GPL-2.0 | **watch/reference** — the auth half only (user must already *exist* via NSS/userdb). Low velocity; puts DB in the login critical path. |
| **Linux — consumer daemon** | **nss-pam-ldapd (nslcd)** [github.com/arthurdejong/nss-pam-ldapd] | Resolves NSS + PAM against an LDAP directory via caching daemon; RFC2307 posixAccount → real login | LGPL-2.1 | **adopt_now** — lightweight glue when MiOS just needs Postgres-SSOT → NSS/PAM without Kerberos. LDAP-only (needs an LDAP server in front of Postgres). |
| **Linux — consumer daemon** | **SSSD + FreeIPA (389-DS)** [sssd.io] | Directory entry → login via SSSD ipa/ldap provider with offline caching | GPL-3.0+ | **reference** — canonical enterprise stack, already partially in-tree. Store is 389-DS LDAP, **not Postgres** — one-Postgres-SSOT would need an ETL hop into the directory (second source of truth = drift risk MiOS wants to avoid). |
| **Cross-platform SSOT/projection** | **lldap (Light LDAP)** [github.com/lldap/lldap] | Users/groups stored in SQL (**Postgres supported**), fronted as RFC2307 LDAP; Linux consumes via SSSD/nslcd | GPL-3.0 | **adopt_now** — strongest modern fit: Postgres stays SSOT, lldap gives a standards LDAP face without resurrecting dead NSS modules. Actively maintained (v0.6.3, 2026-04). Windows/Samba integration is explicitly WIP. |
| **Cross-platform SSOT/projection** | **OpenLDAP back-sql** [openldap.org/doc/admin24/backends.html] | Meta-tables map existing SQL rows/columns → LDAP entries over ODBC; presents Postgres as a live read LDAP subtree with no schema change | OpenLDAP Public License | **reference** — clean "project SSOT to one wire protocol both OSes consume," but explicitly **EXPERIMENTAL**, ODBC work required. |
| **Cross-platform SSOT/projection** | **Keycloak (+ native SCIM)** [keycloak.org] | Postgres-native IdP; LDAP/AD federation in, SCIM 2.0 out to downstream stores | Apache-2.0 | **watch** — mature IdP (v26.7, 2026-07) but **owns its own Postgres schema** (route writes *through* its API, don't dual-write raw rows). Native SCIM still experimental/flag-gated. Heavy stateful service. |
| **Cross-platform provisioning protocol** | **SCIM 2.0 (RFC 7643/7644)** [datatracker.ietf.org/doc/html/rfc7644] | Standard REST/JSON push: `POST /Users` etc. → SCIM server translates to create/update/deactivate on the target's native account store; idempotent | IETF open standard | **adopt_now (as pattern)** — the clean "row fans out to every platform" contract matching `MIOS_ACCOUNTS_DB_BACKED` intent. But it's a protocol, not a product: **MiOS must write the per-platform handlers** (`useradd` / `net user` / OIDC). No native Windows-local SCIM endpoint. |
| **Windows — provisioning (runtime)** | **pGina** (fork mutonufoai/pgina) [github.com/pgina/pgina] | Replaces the Windows credential provider; auth plugin validates against external backend, LocalMachine gateway **auto-creates the matching local Windows account** on login | BSD-3-Clause | **watch** — the Windows analog of NSS+PAM and the closest thing to *runtime* db-driven Windows accounts. But: shipped DB plugin targets **MySQL not Postgres** (need a custom Npgsql .NET plugin), unmaintained since 2018, credential-provider = max-trust component, must be code-signed. |
| **Windows — provisioning (build-time)** | **autounattend / SetupComplete + `New-LocalUser`** (MiOS current approach) | Provisioning script reads the DB-generated account manifest and calls `New-LocalUser` / RID-500 rename during specialize/OOBE | N/A (native Windows) | Windows has **no NSS/PAM** — generation-time projection is the honest baseline. SCIM/Keycloak can standardize the *feed*, but the New-LocalUser step is always yours to write. |

---

## 3. Recommended MiOS architecture

**Core principle:** keep Postgres as the accounts SSOT (itself projected from `mios.toml [accounts]`), but **do not bind glibc/Windows directly to raw Postgres on every endpoint.** Every "adopt-now" source and every "reference" gotcha points the same direction: put a *standard interface* (LDAP and/or generated drop-ins) between the DB and each platform's account machinery. This is the same "project SSOT to a surface, drift-gate it" move MiOS already uses for theme-render and the dotfiles registry.

### (a) bootc Linux host — **projection, not live DB in the login path**
Preferred: **project each `[accounts]` row from Postgres into a generated `/usr/lib/userdb/<name>.user` JSON drop-in** at build/sync time (systemd userdb) [systemd.io/USER_RECORD]. This is Linux-only, maintained (LGPL-2.1), needs no `/etc/passwd` editing, carries extensible MiOS-specific fields, and fits the existing SSOT-projection + drift-gate pattern precisely. Pair with PAM for password verification (pam-pgsql for the direct-DB variant, or SSSD/Kerberos long-term).

Alternative when live central identity is wanted: run **lldap pointed at the same Postgres** and consume it with **SSSD or nslcd** (NSS+PAM) [github.com/lldap/lldap; github.com/arthurdejong/nss-pam-ldapd]. Avoids resurrecting the archived libnss-pgsql/pam-pgsql pair while keeping Postgres as SSOT.

**Do not** ship libnss-pgsql as the primary engine (archived, Debian-removed, locks the box on DB outage) — mine it only for the passwd/shadow/group column schema. Always keep a break-glass local root account in `/etc/passwd` regardless of engine.

### (b) Windows / Xbox guest — **generation-time projection, optional runtime layer**
Because Windows has no NSS/PAM, the baseline stays **generation-time**: a SetupComplete/autounattend PowerShell step reads the account set (from a DB-generated manifest or a SCIM/LDAP read of the SSOT) and calls `New-LocalUser` with correct group membership. This is exactly what MiOS already does — the DB-driven design *standardizes the feed*, it doesn't remove the New-LocalUser step.

Optional runtime upgrade: a **pGina-style credential provider** (custom Npgsql plugin, pointed at an LDAP/SCIM projection of Postgres, **not** raw DB creds on every endpoint) so accounts added to Postgres *after* install auto-materialize on next login [github.com/pgina/pgina]. Treat as a later phase — it's an unmaintained, code-signed, max-trust logon component.

### (c) AI / container plane — **OIDC/LDAP off the same SSOT**
The container/AI plane should authenticate via **OIDC tokens or LDAP bind** against the same projection layer (lldap or, if the IdP path is chosen, Keycloak on the same Postgres) rather than its own account list. This aligns with MiOS's existing endpoint-canonical / container-runtime posture and gives token issuance for the /v1 plane for free.

### Reconcile-loop vs bake-at-build
- **Linux host & container plane → bake-at-build (projection), with a lightweight sync verb.** Generate userdb drop-ins / lldap seed at build or `mios-sync` time and **drift-gate** them (new check in the 25–41 family), exactly as theme/dotfiles surfaces are gated. This keeps offline/air-gapped bootc hosts working and keeps Postgres *out* of the boot/login critical path — directly answering the libnss-pgsql "DB outage locks you out" gotcha.
- **Windows guest → bake-at-provision (SetupComplete), optionally + runtime reconcile agent** (see §4).
- Reserve a true **live reconcile loop / SCIM push** only for the case where accounts must change *between* image builds without a re-sync. SCIM is online/push, so air-gapped hosts need store-and-forward or a build-time snapshot anyway [datatracker.ietf.org/doc/html/rfc7644].

### How this replaces/complements the current autounattend approach
It **complements, does not replace**, the autounattend RID-500-rename/LocalAccounts work. The RID-500 rename and initial LocalAccounts block stay as the **break-glass / first-account bootstrap** (you always need one account before any DB reconcile can run). What changes: the *set* of accounts and their attributes stops being hand-authored in the XML and instead is **generated from Postgres** — the autounattend becomes a projected surface, not a maintained one. `MIOS_ACCOUNTS_DB_BACKED` gates *which projection runs* (userdb drop-ins on Linux, DB-generated New-LocalUser manifest on Windows), consistent with it being a MiOS-owned switch rather than a reference to any external package.

---

## 4. Bearing on the Windows-install failure

**Should Windows account work move OUT of the autounattend specialize/OOBE pass into a first-boot DB-reconcile agent?** — **Partially, and deliberately, not wholesale.** Keep a minimal bootstrap account in the specialize/OOBE pass; move the *bulk* DB-driven account set to a first-boot reconcile agent.

**Pros of moving account creation to a first-boot DB-reconcile agent:**
- **Decouples a fragile, one-shot XML pass from account logic.** specialize/OOBE failures are hard to debug and non-idempotent; a first-boot agent (running `New-LocalUser` from a DB read) is re-runnable and loggable, isolating account failures from the OS-install critical path.
- **Single source of truth actually honored** — accounts derive from Postgres at boot instead of being frozen into the image XML, matching the db_backed intent and eliminating the divergent hand-maintained LocalAccounts block MiOS wants to avoid.
- **Later accounts work without re-imaging** — a row added to Postgres reconciles on next boot (or via a pGina layer, next login), which the pure autounattend model cannot do.
- **Standard feed** — the agent can consume a SCIM/LDAP projection, the same interface the Linux and AI planes use, instead of a Windows-only XML dialect.

**Cons / risks:**
- **Chicken-and-egg:** OOBE requires *at least one* local account to complete; you cannot remove the bootstrap account from the unattended pass or first boot may never reach the agent. Keep the RID-500 rename + one bootstrap account in specialize.
- **DB reachability at first boot:** the Xbox/standalone image may be offline. The agent needs a **build-time snapshot / store-and-forward** fallback (SCIM is push/online) so a missing Postgres doesn't leave the machine account-less.
- **New trust surface:** a first-boot agent holding DB/LDAP creds, or a pGina credential provider, is a high-privilege logon-path component — must be code-signed and audited; prefer pointing it at an LDAP/SCIM projection rather than raw DB creds on the endpoint.
- **Two-phase timing:** group membership, profile creation, and the RID-500 admin rename have ordering constraints; splitting across specialize (bootstrap) and first-boot (reconcile) needs careful sequencing or you get half-provisioned profiles.

**Recommendation:** two-phase. Phase 1 (specialize/OOBE): RID-500 rename + one break-glass bootstrap account, hardcoded-minimal, from the DB-generated manifest. Phase 2 (first-boot idempotent reconcile agent): create/update the full account set from the Postgres SSOT (via a snapshot or SCIM/LDAP read), drift-checkable and re-runnable. This keeps install robust while making the account set genuinely DB-driven — and mirrors the bake-bootstrap-then-reconcile split used on the Linux side.

---

*Sources: postgresql.org/developer/related-projects; systemd.io/USER_RECORD; github.com/jandd/libnss-pgsql; github.com/pam-pgsql/pam-pgsql; github.com/lldap/lldap; github.com/arthurdejong/nss-pam-ldapd; sssd.io; freeipa.org; openldap.org/doc/admin24/backends.html; keycloak.org and keycloak.org/2026/04/scim-as-experimental-feature; github.com/pgina/pgina; datatracker.ietf.org/doc/html/rfc7644. All disposition/status/gotcha claims trace to the correspondingly-named deep-read items. "PostgresOS" flagged throughout as an operator coinage, not a real project.*