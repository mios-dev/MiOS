<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Unit tests for mios_audit...

!/usr/bin/env python3
AI-hint: Unit tests for mios_audit, the SEC-03 SHA-256 tamper-evident event-bus hash chain. Exercises the PURE primitives headless (no DB, no web stack): deterministic chaining (two independent chainers seeded at genesis produce identical hashes; chain_seq is monotonic; the first prev_hash is the genesis sha256), clean-chain verification, tamper DETECTION (a content-edited middle event, a corrupted chain_hash, and a deleted row are all caught with the right first_broken_seq), degrade-open behaviour (disabled chainer and unseeded chainer both return the row unchanged so event logging never breaks), idempotent stamping (re-stamping an already-stamped row does not advance the chain -- the _emit_session_event pre-stamp contract), and NON-dictionary payloads (string/int/list). Stdlib unittest only.
AI-related: ./mios_audit.py, ../../../libexec/mios/mios-chain-verify, ./server.py
AI-functions: TestEventChain.* (deterministic/verify/tamper/degrade-open/idempotent/non-dict-payload)

<!-- mios-src:0c010715846b from usr/lib/mios/agent-pipe/test_mios_audit.py:1-4 -->

