<!-- AI-hint: Chapter 60: Durable Quota. Records why a per-principal budget that lives only in memory is not a budget at all -- every restart, including a bootc upgrade, hands an exhausted account a fresh allowance -- and what the quota_ledger does and deliberately does NOT persist. Covers why the sliding RPM window is thrown away while the spend window is kept, why a rolled-over row must be refused rather than replayed, how a synchronous gate writes to an async store without blocking, and why every failure path degrades open. -->

# <a name="60_durable_quota"></a>Chapter 60: Durable Quota

> Part V: Security & Identity of the [MiOS manual](../manual.md).

> Path Reference: `/usr/share/doc/mios/manual.md#60_durable_quota`

#### Overview

`mios_quota` tracked a per-principal request rate and spend budget, and the
dispatch gate keyed it on the verified principal. Both halves worked. Neither
survived a restart, so the hard stop was not hard: any restart — a crash, a
service reload, a `bootc` upgrade — handed an exhausted account a clean ledger.

#### <a name="60_what_persists"></a>60.What Persists: And What Must Not

`quota_ledger` stores exactly three things per principal: the budget window's
start, the spend inside it, and when it was last written.

The sliding **RPM window is deliberately thrown away**. A request-per-minute
limiter is a statement about load *right now*; a minute of timestamps recorded
before the process existed describes nothing about the process that is running.
Replaying them would deny a caller for traffic the current server never
received — a limiter that punishes you for the past. The spend budget is the
opposite case: a daily budget whose entire purpose is to outlive any one
process, so it is the thing worth writing down.

#### <a name="60_stale_rows"></a>60.Stale Rows: Refuse, Don't Replay

`restore()` returns False and seats nothing when the persisted window has
already rolled over. Without that check a row written just before a long
outage would come back as live spend, charging a principal for a budget period
that has since expired — the ledger would leak spend forward forever instead of
resetting each window. A stale row is not a smaller balance; it is *no*
balance, and the tracker starts the principal clean.

#### <a name="60_sync_gate_async_store"></a>60.A Synchronous Gate Over an Async Store

The quota gate runs inside the dispatch chokepoint, which is synchronous. The
store is `psycopg` behind an async client. Rather than block the event loop or
make the gate async, the two are decoupled at the ends:

* **Reads happen once, at startup.** `quota_preload()` pulls every row before
  the first dispatch into an in-process map, so the hot path never touches the
  database to *decide* anything.
* **Writes are fire-and-forget.** The in-process map is updated first — so a
  lost database write cannot make the running process forget — then a row
  upsert is scheduled on the running loop. With no loop running (a CLI, a sync
  test) the write simply does not happen, which is correct: there is no server
  whose restart it would need to survive.

#### <a name="60_degrade_open"></a>60.Degrade Open: A Budget Bug Never Blocks Work

Every failure path here returns control rather than raising. An unreachable
store preloads nothing, does not mark itself persistent, and lets work through;
a malformed row restores nothing; a failed write leaves the in-process balance
standing. The reasoning is that the alternative — a quota subsystem that can
refuse legitimate work because its ledger is unreachable — turns a cost control
into an availability risk. The enforcement that matters is the balance that is
*present*; a missing balance means the machine has no evidence against you.
