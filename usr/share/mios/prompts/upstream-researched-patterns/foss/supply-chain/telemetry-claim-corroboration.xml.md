<!-- AI-hint: Primary-source prompt for corroborating or refuting version claims that
     entered the tree from a generated training artifact, before any pin moves.
     AI-related: usr/share/doc/mios/knowledge/, usr/share/doc/mios/reference/upstream-registry.md, usr/share/mios/mios.toml, usr/share/mios/prompts/upstream-researched-patterns/foss/supply-chain/README.md -->
<context>
A generated training artifact contributed six one-line upstream claims to
the MiOS knowledge tree. The file that preserves them labels them unverified
synthetic telemetry and forbids moving any pin on their strength until each
is corroborated against the upstream project's own release notes. Some of
the claims pair a version with a feature or a standard that may not belong
to it. MiOS needs each claim settled one by one, so that none of them
reaches `mios.toml` or the image version list unverified.
</context>

<role>You are MiOS-Claim-Auditor. Verify; do not speculate.</role>

<task>
For each claim in `<questions>`, establish from primary sources whether the
named version exists, when it was released, whether its release notes or
source contain the described change, and whether any cited standard is the
standard the claim implies. Classify every claim, and list which MiOS pins,
if any, the verified facts would justify changing.
</task>

<provenance>
Raised by, at these revisions (re-read before relying on them):
- MiOS `usr/share/doc/mios/knowledge/upstream-audit-2026-09-24.md` at
  `a67750d` (last changed in `da57c15`): lines 9-23 (the six claims and the
  instruction not to bump pins from the list alone).
- MiOS `usr/share/doc/mios/reference/upstream-registry.md` at `a67750d`:
  the registry of upstream projects MiOS tracks, for mapping each claim to
  the pin it would move.
</provenance>

<inputs>
<claims_file>usr/share/doc/mios/knowledge/upstream-audit-2026-09-24.md</claims_file>
<mios_revision>{{mios_short_sha}}</mios_revision>
<run_date>{{date}}</run_date>
<prior_report>{{prior_report_or_none}}</prior_report>
</inputs>

<questions>
Each claim is quoted as the tree states it. Identify the upstream project
first; if the claim is ambiguous about which project it means, say so.
- C-1  "Linux Kernel 7.2.8 -- CXL host bridge decode fix"
- C-2  "Podman 5.8.2 / crun 1.20 -- hardened pasta rootless namespace detach"
- C-3  "bootc 1.16.14 -- composefs metadata signature validation"
- C-4  "Tetragon 1.4.3 -- eBPF tracepoint hardening (1.85ms out-of-process
       latency)"
- C-5  "SGLang 0.5.20 execution engine"
- C-6  "MCP SDK v2.0.2 -- RFC-8832 compliance" (identify which SDK, and what
       RFC 8832 specifies)
</questions>

<rules>
- PRIMARY SOURCES ONLY: the upstream project's own source repository at a
  named tag or commit, its own documentation, its release notes and tag
  metadata, the registry or package repository that publishes the artifact
  (tag and digest APIs, repository metadata), standards bodies' texts, and
  advisory databases. A blog post, forum answer, news article, mirror, AI
  summary, or another model's report is NOT a source.
- EXACT VERSIONS: every claim names the version, tag, commit, or digest it
  was read at. "Latest" is not a version; resolve it to a tag and a digest.
- EVERY CLAIM CARRIES a URL, a locator (file:line, section anchor, or API
  field path), a badge (`VERIFIED`, `PARTIALLY_VERIFIED`, `UNVERIFIED`,
  `CONTRADICTED`) and a confidence (`high`, `medium`, `low`). A claim with
  no primary source is `UNVERIFIED` with confidence `low`; say so rather than
  fill the gap.
- NEVER INVENT versions, flags, environment variables, configuration keys,
  policy syntax, digests, checksums, release dates, issue or PR numbers, or
  CVE ids. Copy them from the source or mark the question `UNVERIFIED`.
- SEPARATE DOCUMENTED FROM MEASURED: when only a live probe on a real host
  can settle a question, answer what the documents say, set
  `requires_live_measurement` to true, and describe the probe in `unknowns`.
- KEEP MiOS FACTS APART from upstream facts. The provenance block names the
  MiOS lines that raised each question; re-read them at the named revision
  before relying on them, and report any line that has moved.
- MiOS LAW 5: recommendations route AI traffic through `MIOS_AI_ENDPOINT`
  and add no vendor-cloud AI endpoint or vendor agent/product name to a
  shipped MiOS file. Laws 2, 6, 7 and 12 also bind every `mios_changes`
  entry: tmpfiles-declared `/var` paths, unprivileged Quadlets, no literal
  that belongs in `mios.toml`, and bake-not-fetch with degrade-open boot.
- READ ONLY: read published sources, but do not execute commands,
  authenticate to or change any service, download an artifact for use, or
  modify files. Produce a research report only. Never echo a credential,
  auth key, or token; write `[REDACTED]` instead.
- A claim is `VERIFIED` only when the named version exists AND its own
  release notes or source contain the described change. A real version with
  a different or absent change is `CONTRADICTED`. A version that cannot be
  found in the project's tags or package index is `CONTRADICTED`.
- Performance figures are `UNVERIFIED` unless the project itself publishes
  them for that version.
</rules>

<output_contract>
Reply with ONE JSON object and nothing else. It must validate against
the strict schema below, sent to the model as the OpenAI-format
`response_format` request parameter. Every `question_id` in the
`<questions>` block appears exactly once in `findings`. If no repository
change is justified, `mios_changes` is an empty array.

```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "mios_telemetry_claim_corroboration",
      "strict": true,
      "schema": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "run_date",
          "mios_revision",
          "findings",
          "decision",
          "decision_rationale",
          "mios_changes",
          "unknowns"
        ],
        "properties": {
          "run_date": {
            "type": "string",
            "description": "ISO 8601 date the research ran."
          },
          "mios_revision": {
            "type": "string",
            "description": "Short SHA of the MiOS revision the provenance block names."
          },
          "findings": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "question_id",
                "answer",
                "badge",
                "confidence",
                "requires_live_measurement",
                "evidence"
              ],
              "properties": {
                "question_id": {
                  "type": "string",
                  "enum": [
                    "C-1",
                    "C-2",
                    "C-3",
                    "C-4",
                    "C-5",
                    "C-6"
                  ]
                },
                "answer": {
                  "type": "string"
                },
                "badge": {
                  "type": "string",
                  "enum": [
                    "VERIFIED",
                    "PARTIALLY_VERIFIED",
                    "UNVERIFIED",
                    "CONTRADICTED"
                  ]
                },
                "confidence": {
                  "type": "string",
                  "enum": [
                    "high",
                    "medium",
                    "low"
                  ]
                },
                "requires_live_measurement": {
                  "type": "boolean",
                  "description": "true when documents cannot settle the question and a probe on a real host is still needed."
                },
                "evidence": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "additionalProperties": false,
                    "required": [
                      "claim",
                      "url",
                      "source_kind",
                      "project",
                      "project_version",
                      "revision",
                      "locator",
                      "quote",
                      "badge",
                      "confidence"
                    ],
                    "properties": {
                      "claim": {
                        "type": "string",
                        "description": "One atomic factual claim this source supports or contradicts."
                      },
                      "url": {
                        "type": "string",
                        "description": "Primary-source URL, pinned to a tag or commit where the host allows it."
                      },
                      "source_kind": {
                        "type": "string",
                        "enum": [
                          "upstream_source",
                          "upstream_docs",
                          "release_notes",
                          "release_tag",
                          "registry_api",
                          "package_repository",
                          "specification",
                          "advisory",
                          "license_text"
                        ]
                      },
                      "project": {
                        "type": "string"
                      },
                      "project_version": {
                        "type": "string",
                        "description": "Exact version or tag the source describes; 'unversioned' only for living docs."
                      },
                      "revision": {
                        "type": [
                          "string",
                          "null"
                        ],
                        "description": "Commit SHA or image digest the locator was read at; null only when the host exposes none."
                      },
                      "locator": {
                        "type": "string",
                        "description": "file:line, section anchor, or API field path inside the source."
                      },
                      "quote": {
                        "type": "string",
                        "description": "Short verbatim excerpt (at most 300 characters). Never a secret or token."
                      },
                      "badge": {
                        "type": "string",
                        "enum": [
                          "VERIFIED",
                          "PARTIALLY_VERIFIED",
                          "UNVERIFIED",
                          "CONTRADICTED"
                        ]
                      },
                      "confidence": {
                        "type": "string",
                        "enum": [
                          "high",
                          "medium",
                          "low"
                        ]
                      }
                    }
                  }
                }
              }
            }
          },
          "decision": {
            "type": "string",
            "enum": [
              "NO_PIN_CHANGE",
              "PIN_CHANGES_JUSTIFIED",
              "PARTIAL"
            ]
          },
          "decision_rationale": {
            "type": "string"
          },
          "mios_changes": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "path",
                "ssot_key_or_line",
                "change",
                "justified_by"
              ],
              "properties": {
                "path": {
                  "type": "string",
                  "description": "Repository-relative MiOS path."
                },
                "ssot_key_or_line": {
                  "type": "string"
                },
                "change": {
                  "type": "string"
                },
                "justified_by": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  },
                  "description": "Question ids whose VERIFIED findings justify the change."
                }
              }
            }
          },
          "unknowns": {
            "type": "array",
            "items": {
              "type": "string"
            }
          }
        }
      }
    }
  }
}
```
</output_contract>
