<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_embed_backfill -- embedding-version hygiene for the...

mios_embed_backfill -- embedding-version hygiene for the MiOS agent-pipe
(WS-A2, the AIOS Memory-Manager embedding-identity layer).

Pure stdlib so it unit-tests in isolation, in the sibling-module style of
mios_sched / mios_pdp. server.py (or a maintenance CLI) owns the DB I/O and the
embedding call; this module owns only the DECISIONS: is a row's vector stale,
which rows are candidates, and how to batch the work so a backfill never
stampedes the embedder or the DB.

Why versioning
==============
Every embedded row carries emb_model + emb_version. The embedding space is only
comparable WITHIN one identity: if the model (or its dimensionality) changes,
old vectors are meaningless under the new model, so cosine recall silently
returns garbage neighbours. Tagging each row lets a backfill find + re-embed the
stale rows off the hot path, and lets recall optionally restrict to the current
identity until the backfill catches up.

<!-- mios-src:fd01946b3519 from usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py:3-20 -->
