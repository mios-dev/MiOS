# Technical Investigation & Research Spike: Artifact Publisher Contracts

**Spike ID:** `SPIKE-20260924-artifact-publisher-contracts`
**Author / Driver:** GitHub Copilot
**Status:** CONCLUDED
**Timebox:** 1 hour
**Target Completion Date:** 2026-09-24
**Related Epics / Lanes:** Artifact publication / AI training data

---

## 1. Context & Motivation
`mios-training-oci-image-2026-09-24.tar` was integrated from `origin/main`.
Its `index.json` references manifest digest
`sha256:7a513a038414f2f3486830f254a06596906bc8f5c385b249c979017626d6bc80`,
but the archive contains only `blobs/sha256/` as an empty directory. It is an
index-only OCI layout and cannot be loaded or run without an external blob store.

The artifact-publisher prompt described synchronization and release receipts but
contained no acceptance criteria for OCI closure or AI training-data validity.
The open question was whether the failure belonged to the generator/prompt
contract and which canonical constraints must become non-negotiable.

---

## 2. Research Questions & Hypotheses
| Question ID | Research Question | Hypothesis (Initial Assumption) |
| :--- | :--- | :--- |
| **Q1** | Is the pulled OCI archive self-contained? | No: its index descriptor has no corresponding manifest blob. |
| **Q2** | What must an OCI layout publisher validate? | Descriptor reachability, byte size, and digest closure. |
| **Q3** | What minimum gates make generated AI datasets usable and safe? | Strict JSONL/schema plus provenance, privacy, license, split, and deduplication controls. |

---

## 3. Experimental Methodology & Prototypes
Inspected the archive without extraction:

```bash
tar -tvf mios-training-oci-image-2026-09-24.tar
tar -xOf mios-training-oci-image-2026-09-24.tar index.json | jq .
```

Read the installed/local contract sources and primary upstream specifications:

- OCI Image Layout: https://github.com/opencontainers/image-spec/blob/main/image-layout.md
- OCI Content Descriptors: https://github.com/opencontainers/image-spec/blob/main/descriptor.md
- OpenAI supervised fine-tuning guide: https://platform.openai.com/docs/guides/supervised-fine-tuning

---

## 4. Empirical Findings & Benchmarks

### 4.1 Quantitative Data
| Probe | Result |
| :--- | :--- |
| Archive entries | `blobs/`, `blobs/sha256/`, `index.json`, `oci-layout` |
| Referenced manifest blobs present | `0` |
| `index.json` manifest descriptors | `1` |
| Archive SHA-256 | `a1cfd0a265ab4d94f7168d3d7611de85960127de3c1802d28a17e04a52767750` |

### 4.2 Qualitative Discoveries & Trade-offs
- **OCI:** OCI Image Layout requires `oci-layout` and `index.json`; referenced
  blobs may be externally fulfilled by design, but a release labelled as an
  `oci-archive` must be self-contained. The publisher must therefore reject any
  descriptor without a local blob and independently check digest and size.
- **Training data:** SFT records need structured chat messages with a usable
  assistant target. Dataset generation additionally needs provenance and
  privacy controls; syntactically valid JSONL alone is insufficient training
  evidence.
- **Two-way check:** The OCI specification permits sparse layouts for
  external-store workflows. That is not a valid exception for a portable MiOS
  release archive; sparse output must be explicitly labelled as a reference
  layout and must never be published as a runnable image.

---

## 5. Architectural Implications
- **Contract Impact:** Artifact publication now requires descriptor-closure and
  dataset gates before a commit or receipt.
- **Dependency Footprint:** No new dependency. Prefer existing `podman save
  --format oci-archive` or `skopeo copy ... oci-archive:` exports.
- **Operational Complexity:** Archive inspection, JSONL parse/schema checks,
  dataset provenance metadata, PII/secret scanning, deterministic splits, and
  retention of hashes become release evidence.

---

## 6. Final Decision & Actionable Next Steps

**Verdict:** ADOPT

### Rationale
The incomplete archive is direct evidence that the prior generic artifact prompt
was insufficient. Both canonical artifact-publisher prompt representations now
require OCI descriptor closure and AI training-data release gates. A publisher
must fail rather than commit an index-only archive or unvalidated corpus.

### Action Items
- [x] Task 1: Add OCI closure requirements to both artifact-publisher prompts.
- [x] Task 2: Add JSONL/schema/provenance/privacy/split requirements for AI
  training artifacts to both prompts.
- [ ] Task 3: Add executable artifact validators to the producing pipeline once
  the generator location is identified; prompts alone are not a substitute for
  a release gate.
