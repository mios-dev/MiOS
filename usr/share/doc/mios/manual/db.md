<!-- AI-hint: Manual pages distilled from the source comments of db, sanitized, each passage anchored to the comment it came from. -->

# db

### Repairs a corrupted SQLite database. MANDATORY INVARIANT...

Repairs a corrupted SQLite database.
        MANDATORY INVARIANT: Do NOT run destructive .dump recovery over healthy databases.
        Attempts non-destructive REINDEX and VACUUM first before table dump recovery.

<!-- mios-src:568bc9e403e0 from usr/libexec/mios/db/mios-db-doctor.py:157-161 -->

### Executes a single migration wrapped in an explicit...

Executes a single migration wrapped in an explicit transaction block (BEGIN ... COMMIT).
        MANDATORY INVARIANT: Records version ID and SHA-256 checksum in schema_version ledger.
        If an error occurs, executes ROLLBACK immediately.

<!-- mios-src:662d53f2e754 from usr/libexec/mios/db/mios-db-migrate.py:231-235 -->

### Promotes the standby replica to become the active primary....

Promotes the standby replica to become the active primary.
        MANDATORY INVARIANT: Must verify primary is fenced before promotion
        to eliminate split-brain writes.

<!-- mios-src:05237335accc from usr/libexec/mios/db/mios-pg-replica.py:272-276 -->
