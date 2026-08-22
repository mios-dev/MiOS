<!-- AI-hint: Chapter 61: Run-Template Replay. Records why the capture half of the run-template feature was write-only for so long: templates were keyed by a hash of the PLAN's shape, which can only be computed after planning and so can never answer "should I plan?". Covers the intent key derived from the turn instead, why the matcher is deliberately model-free, why two empty token sets must score zero rather than a perfect match, why a merely partial overlap re-plans rather than replaying a near-miss, and the one-line stamp without which every stored template is unreplayable. -->

# <a name="61_run_template_replay"></a>Chapter 61: Run-Template Replay

> Part VI: The Local AI Plane of the [MiOS manual](../manual.md).

> Path Reference: `/usr/share/doc/mios/manual.md#61_run_template_replay`

#### Overview

Every planned DAG was already captured to `run_template`, and `GET
/v1/run-templates` listed them. Nothing ever read one back. Each identical
request paid full planning latency and tokens again, and the same intent could
plan differently from run to run.

#### <a name="61_the_wrong_key"></a>61.The Wrong Key: Why Capture Could Not Feed Reuse

Templates were keyed by `_run_template_class` — a hash of the plan's sorted
tool names and edge count. It is a good key for "have we seen this plan
*shape*?", and useless for the question reuse actually asks, because you can
only compute it **after** the planner has run. A key derived from the plan
cannot decide whether to plan.

So the replay path keys on the **turn**: the normalized, sorted, unique
significant tokens of the user's text. Word order stops mattering, so "search
the web for X and summarise it" and "summarise it, searching the web for X" key
identically. Both keys are now stored; they answer different questions and
neither replaces the other.

#### <a name="61_model_free"></a>61.Model-Free On Purpose

The obvious upgrade is to embed the turn and match by cosine similarity. It is
the wrong upgrade here. The entire value of this feature is *not spending a
model call*, and an embedding call is a model call — it would buy better
matching with the very resource the feature exists to conserve.

So matching is lexical: exact key first, bounded Jaccard overlap second. That
is deliberately conservative, and the conservatism is the point.

#### <a name="61_refuse_the_near_miss"></a>61.Refuse the Near Miss

Two rules make a wrong replay unlikely:

* A **partial overlap re-plans.** "search the web for kernel CVEs" scores 0.56
  against "search the web for the latest linux kernel CVEs and summarise the
  top three". That is clearly related and clearly not the same request, and it
  falls below the 0.85 default, so it plans. Replaying a near-miss returns a
  confident answer to a question nobody asked; re-planning merely costs tokens.
* **Two empty token sets score 0.0, not 1.0.** A turn made entirely of
  stopwords keys to nothing and must match nothing. Letting "no tokens" equal
  "no tokens" as a perfect match would make the emptiest possible input the
  most confident one.

The score is returned on a miss as well as a hit, so "why did this plan?" is
answerable from the log rather than inferred.

#### <a name="61_the_stamp"></a>61.The Stamp: One Line the Whole Feature Rests On

The capture path reads the intent off the DAG it is given. Nothing put it
there. Until `decompose_intent` stamps `parsed["intent"]` with the turn that
produced the plan, every stored row has an empty intent key, every lookup
misses, and the feature is silently dead while looking completely wired — the
same shape of defect as an imported-but-uncalled module.

The test suite guards that line directly: removing it must turn the suite red,
and it does. A round-trip assertion that *passes the intent in itself* would
not have caught it, and did not until it was rewritten to plan a DAG and check
what came back.
