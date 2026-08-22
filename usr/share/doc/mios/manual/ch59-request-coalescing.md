<!-- AI-hint: Chapter 59: Request Coalescing. Explains why MiOS deliberately does NOT client-side batch its own inference lanes -- vLLM, SGLang and llama.cpp already run continuous batching, so a second layer only adds head-of-line latency -- and what the coalescer is actually for: bounding a burst against a rate-limited non-native endpoint. Covers why the chokepoint is an httpx request hook on the one shared AsyncClient rather than an edit at every call site, why a flushed group must be SEALED, and why the flag being off means the hook is never registered rather than merely inert. -->

# <a name="59_request_coalescing"></a>Chapter 59: Request Coalescing

> Part VI: The Local AI Plane of the [MiOS manual](../manual.md).

> Path Reference: `/usr/share/doc/mios/manual.md#59_request_coalescing`

#### Overview

`mios_batch` held the decision logic for batch coalescing — window keys, a
native-lane bypass, a flush rule — and `server.py` imported it. Nothing called
it. The module read as an active guardrail during review while nothing bounded
duplicate fan-out at all.

#### <a name="59_what_it_is_not_for"></a>59.What It Is Not For: Not the Local Lanes

The instinct is to batch everything. That is wrong here, and the module says so
at length: vLLM (PagedAttention), SGLang (RadixAttention) and llama.cpp all
implement **continuous batching** — the engine's own scheduler forms a rolling
batch from concurrent requests with no fixed timer or count. Client-side
grouping in front of that is strictly worse: it adds a head-of-line delay to
buy a batch the engine would have formed anyway.

So the coalescer **bypasses** every endpoint that self-batches, matched against
the local lane ports. What is left is the case it exists for: a rate-limited
remote endpoint, where collapsing a burst into one release window genuinely
reduces the request count.

#### <a name="59_one_chokepoint"></a>59.One Chokepoint: A Hook, Not an Edit Per Call Site

Upstream calls are issued from many places across the pipe, but they all obtain
their client from one function — `_get_client()`, which memoises a single
`httpx.AsyncClient`. That makes the client, not any call site, the real
chokepoint. The coalescer attaches as an httpx **request event hook**, so every
POST through the pipe passes it and no call site had to be touched.

The hook degrades open by construction: a streaming body it cannot read, a body
that is not JSON, a `GET` with no model — each falls straight through to
sending the request unheld. Nothing raised inside the hook may block a request.

#### <a name="59_sealing"></a>59.Sealing: Why a Flushed Group Must Close

The first caller for a `(endpoint, model)` key opens the window and arms a loop
timer; every caller then waits on that group's event. The subtle requirement is
what happens to a request that arrives *while* the group is being released. If
it could still join, a busy key would keep topping up a group that is already
on its way out, and callers could be held indefinitely — the window would stop
being a bound at all.

So a group is **sealed** the instant it flushes: it is dropped from the key
table before its event is set, and the next caller opens a fresh window. Every
path — interval expiry, `max_size`, a single sequential call — leaves the key
table empty, which the tests assert directly rather than inferring.

#### <a name="59_off_means_absent"></a>59.Off Means Absent: The Default Is Not Merely Inert

`[dispatch].batch_enable` defaults to false, and the guarantee is stronger than
"the hook returns early". The hook is **not registered at all**: `_get_client()`
builds the client with exactly the arguments it used before this feature
existed. A default-off feature that still sits in the request path is a
default-off feature you have to re-verify after every change; one that is
absent from the path is not. The test asserts the empty hook list, not a timing.
