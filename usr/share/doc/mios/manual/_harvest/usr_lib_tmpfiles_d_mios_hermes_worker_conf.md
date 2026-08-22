<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Declares the Hermes WORKER (:8643) runtime directory and its dedicated CDP browser profile, owned by the mios-ai service user, so the second isolated gateway instance has its own HERMES_HOME (separate pid/lock/state/DBs/config) and its own browser profile (separate cookies) without sharing the primary :8642 tree.
AI-related: /var/lib/mios/hermes-worker, /var/lib/mios/hermes-browser/profile-w2, hermes-worker.service, mios-hermes-browser-worker.service, mios-ai
/usr/lib/tmpfiles.d/mios-hermes-worker.conf
'MiOS' Hermes-WORKER runtime directories (P1, operator 2026-06-19).

SEPARATE HERMES_HOME from the :8642 gateway -- its own gateway.pid /
gateway.lock / gateway_state.json / state.db / kanban.db / config.yaml /
auth.json. NO-MKDIR-IN-VAR (Law 2): declare here, never mkdir at build time.

<!-- mios-src:476b9fecae3c from usr/lib/tmpfiles.d/mios-hermes-worker.conf:1-8 -->

