<!-- AI-hint: Chapter 54: Agent-Pipe Importability. Records the defect class that let agent-pipe's server module reference names nothing defines, the three undefined module-scope names that made it unimportable, the four further undefined names found once a real checker ran, the two gates that were silently vacuous because of it, and the knowledge-memory consolidation loop restored in the process. Covers what each gate now enforces and why an ImportError from repo code must fail rather than skip. -->

# <a name="54_agent_pipe_importability"></a>Chapter 54: Agent-Pipe Importability

> Part VI: The Local AI Plane of the [MiOS manual](../manual.md).

> Path Reference: `/usr/share/doc/mios/manual.md#54_agent_pipe_importability`

#### Overview

`usr/lib/mios/agent-pipe/server.py` is the router and dispatch gateway every
front-end talks to. It parsed cleanly, passed every syntax check, and could not
be imported: three module-scope names it referenced were defined nowhere in the
repository. This chapter records what went wrong, because the interesting part
is not the three names — it is that two separate gates were positioned to catch
this and both reported success.

#### <a name="54_the_three_undefined_names"></a>54.The Three Undefined Names: The Three Undefined Names

| Name | Symptom | Resolution |
|---|---|---|
| `_consolidate_memory_loop` | `from mios_daemons import ...` for a function that existed nowhere | implemented in `mios_pipe/kernel/daemons.py` (below) |
| `_match_user_cfg`, `_user_rbac_filter` | injected into the a2a and http_caps configure calls, never imported | imported from `mios_policy`, where they live |
| `_PG_PRIMARY`, `_PG_ENABLED`, `_PERMISSION_TIERS` | referenced bare at six sites | resolved in the config layer from `[pgvector]`, and imported from `mios_policy` |

`_PG_PRIMARY` is worth a note. Two early call sites read it as
`globals().get("_PG_PRIMARY", False)` — someone had already met its absence and
worked around it locally rather than defining it. The later sites read it bare
and raised. It now resolves from SSOT: Postgres is the agent plane's sole
datastore since the WS-A3 cutover, so `[pgvector].enable` plus
`db_backend = "postgres"` *is* "primary".

#### <a name="54_why_the_gates_missed_it"></a>54.Why the Gates Missed It: Why the Gates Missed It

Two gates should have caught this.

**`lint-python.sh`** ran `ast.parse` over every Python file. That proves a file
*parses*; it says nothing about whether the names it uses exist. All three
undefined names sat behind a clean parse.

**`test_mios_approutes.py`**, the live-app route-parity gate, imported the real
FastAPI app and compared its served routes against the committed golden. It
wrapped that import in `except ImportError: raise unittest.SkipTest(...)`,
reasoning that a bare checkout may lack fastapi. But an `ImportError` naming a
*symbol* is not an absent dependency — it is a code defect. The gate skipped,
reported OK, and the golden went unverified for as long as the defect existed.

Both are now closed:

* `lint-python.sh` gained an **undefined-name pass** over every Python file,
  backed by pyflakes and failing closed under `MIOS_DRIFT_REQUIRE_TOOLS=1`.
* The route-parity gate distinguishes causes. A `ModuleNotFoundError` naming a
  third-party package still skips; one naming a module *this repo ships* fails,
  as does any `ImportError`, `NameError` or `AttributeError` — those mean
  server.py references something the repo does not define.

The general rule the episode argues for: **a gate may skip on the environment,
never on the artifact.** A skip that can be triggered by the code under test is
not a gate.

#### <a name="54_the_four_further_defects"></a>54.The Four Further Defects: The Four Further Defects

The undefined-name pass found four more files on its first run, all real:

| File | Name | Consequence |
|---|---|---|
| `mios_pipe/memory/knowledge.py` | `os` at six sites | see below |
| `mios_pipe/memory/memory.py` | `Optional` in a signature | unresolvable annotation |
| `mios_pipe/access/hitlflow.py` | `AsyncGenerator` in a return annotation | unresolvable annotation |
| `mios_pipe/routing/turn.py` | `re` in a parameter annotation | unresolvable annotation |

The `knowledge.py` one was not cosmetic. `_evict_knowledge` calls
`os.environ.get` as its third statement, and `os` was never imported — so every
eviction sweep raised `NameError` immediately and the function's trailing
`except Exception` swallowed it, returning `{"deleted": 0, "dry_run": True}`.
The K-LRU + TTL knowledge eviction loop had been reporting a clean no-op sweep
while never reaching its own logic. A blanket `except Exception` around a whole
function body will convert a missing import into a plausible-looking result;
that is the reason the undefined-name pass has to exist upstream of it.

#### <a name="54_memory_consolidation"></a>54.Memory Consolidation: Memory Consolidation

`_consolidate_memory_loop` was imported and spawned as a background task under
`AGENT_MEMORY_RECALL_ENABLED`, but never written. It is now implemented in
`mios_pipe/kernel/daemons.py` as a periodic sweep over the `knowledge` table:

* Rows answering the **same normalized question** (`lower(btrim(q))`) collapse
  into the newest.
* The losers' `access_count` and `recall_hits` are **folded into the survivor**,
  and its `last_access` takes the group maximum. Consolidation must not look
  like a reset to the K-LRU tiering that reads those counters — a merge that
  zeroed usage history would make hot rows evictable.
* A group containing **any pinned row is skipped entirely**: pinned means an
  operator asked for that exact entry to survive, and a merge could delete it.
* Each group is merged in its own statement, so one bad row cannot roll back the
  whole sweep, and `consolidate_max_groups` bounds one pass's work.

It is Postgres-only; on the legacy seam it reports a no-op rather than a partial
merge. Tunables live in `[memory]`: `consolidate`, `consolidate_interval_s`,
`consolidate_max_groups`.
