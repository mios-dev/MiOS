<!-- AI-hint: Chapter 53: Drift Monitoring. Explains the Jensen-Shannon Goodhart alarm that watches the agent plane's own verdict and intent distributions for a silent shift. Covers the bounded 0..1 divergence measure, the frozen baseline and how it self-seeds quiet, the thin-window guard that stops a handful of samples reading as drift, the drift_snapshot table, the GET /v1/drift surface and the drift_alert event. -->

# <a name="53_drift_monitoring"></a>Chapter 53: Drift Monitoring

> Part VI: The Local AI Plane of the [MiOS manual](../manual.md).

> Path Reference: `/usr/share/doc/mios/manual.md#53_drift_monitoring`

#### Overview

Self-improvement loops and multi-judge consensus both optimize against a
measure, and any system that optimizes against a measure can drift away from
what the measure was standing in for. If the share of turns judged "satisfied"
climbs from 60% to 95% over a month, that is either a genuine improvement or
Goodhart's law arriving quietly — and before CONS-02 nothing in MiOS could tell
you the shift had happened at all, let alone which of the two it was.

The drift monitor does not answer that question. It answers a smaller one
reliably: **has the distribution moved, and by how much.** A human or a
follow-up task decides what the movement means.

The pure math lives in
`usr/lib/mios/agent-pipe/mios_pipe/observability/drift_monitor.py`; the route
that feeds it is `GET /v1/drift` in `server.py`. The module holds no I/O and no
config import, so `test_mios_drift.py` exercises every branch directly.

#### <a name="53_the_divergence_measure"></a>53.The Divergence Measure: The Divergence Measure

`jensen_shannon(p, q)` returns the Jensen-Shannon divergence between two label
distributions, computed in log base 2 so the result is **bounded 0.0 to 1.0**:
0.0 for identical distributions, 1.0 for distributions with no shared support.
That bound is why JSD is used here rather than KL divergence — a threshold like
`0.2` means the same thing on every axis and never has to be re-tuned because
one axis happens to have more categories than another. JSD is also symmetric,
so "how far has live drifted from baseline" and the reverse are the same number.

Inputs are normalized before comparison, so raw counts and pre-normalized
fractions both work. Weights that are negative, non-numeric, `NaN` or infinite
are dropped rather than propagated, and an empty distribution on either side
returns 0.0 — an absent window is not evidence of drift.

#### <a name="53_the_frozen_baseline"></a>53.The Frozen Baseline: The Frozen Baseline

Divergence needs a reference. On the first poll of an axis the monitor freezes
the *current* live window as that axis's baseline and writes it to
`drift_snapshot` with `kind = 'baseline'`. A window compared against itself
scores exactly 0.0, so **the alarm starts quiet rather than firing on its own
bootstrap** — a monitor whose first act is a false alarm gets switched off.

Subsequent polls write the live window as `kind = 'sample'`. Divergence itself
is never stored: it is derived from a (baseline, sample) pair on read, so
changing the threshold later re-scores the whole history without a backfill.

#### <a name="53_the_thin_window_guard"></a>53.The Thin-Window Guard: The Thin-Window Guard

Three verdicts that happen to be unanimous will diverge wildly from a
representative baseline, and that is noise, not drift. Any axis whose live
window holds fewer than `min_samples` observations is reported with
`compared = false` and cannot alert, however extreme its divergence looks. The
same applies to an axis missing from either side of the comparison. The report
still shows what was and was not compared, so a permanently-uncompared axis is
visible rather than silently absent.

#### <a name="53_axes_and_extraction"></a>53.Axes and Extraction: Axes and Extraction

An axis is a named distribution. `_DRIFT_AXIS_LABELS` in `server.py` maps each
axis to a one-line extractor over the satisfaction-verdict rows the plane
already records, so the monitor needs no sampler of its own:

| Axis | Label |
|---|---|
| `verdict` | the event kind — `user_query_satisfied` / `user_query_unsatisfied` |
| `intent` | `payload.refine_intent` — the route the turn took |

Rows whose label comes out empty are skipped: an unset intent is missing data,
not a distinct category worth alarming on. An axis named in SSOT with no
extractor yields an empty distribution and is reported uncompared, never as
drift.

#### <a name="53_the_alert_and_the_surface"></a>53.The Alert and the Surface: The Alert and the Surface

`GET /v1/drift` returns the per-axis divergence, which axis is worst, the sample
counts behind each window, and which axes the monitor seeded on this call. When
any *compared* axis crosses the threshold the route emits a `drift_alert`
session event naming the axis and the divergence, so the shift lands in the
event log rather than only in whoever happened to poll.

With `[drift_monitor].enable = false` — the default — the route returns
`{"enabled": false}` immediately: no query, no divergence, no event. Every
other failure path degrades to an empty result rather than a 500; an
observe-only alarm must never be able to take down the plane it is watching.

#### <a name="53_drift_configuration"></a>53.Drift Configuration: Drift Configuration

The `[drift_monitor]` block in `usr/share/mios/mios.toml` carries every tunable,
each with a matching `MIOS_DRIFT_MONITOR_*` environment override and a
configurator card. It is deliberately a **separate table from `[drift]`**, which
registers agent-pipe module-wiring exceptions and has nothing to do with
distribution drift.

| Key | Default | Meaning |
|---|---|---|
| `enable` | `false` | compute divergence at all |
| `threshold` | `0.2` | JSD at or above which `drift_alert` fires |
| `window` | `200` | most recent verdicts forming the live window |
| `min_samples` | `30` | observations required before an axis may alert |
| `axes` | `["verdict", "intent"]` | which distributions to watch |
