<!-- AI-hint: Primary-source prompt for the lifecycle of the tracing backend image behind
     mios-otelcol: v1 line status, the v2 image and its configuration model,
     and whether the in-tree tag should be pinned or migrated.
     AI-related: usr/share/mios/mios.toml [image.sidecars] [containers.mios-otelcol] [observability], TASKS.md, .prompts/README.md -->
<context>
The `mios-otelcol` sidecar runs the FOSS tracing backend Jaeger from its v1
`all-in-one` image. It receives OTLP gRPC on the SSOT port `otelcol_otlp`
and serves the query UI on `otelcol_ui`, bound through two environment
variables whose names depend on the v1 configuration model. The tree
currently disagrees with itself: the task register records the image as
pinned to an exact v1 release, the Quadlet comment says the tag "cannot
float", and the three places that carry the image all float `:latest`,
with a second comment arguing that floating is safe because the v1
repository can never receive a v2 tag. Whether that argument holds, and
whether the v1 line is still maintained at all, are upstream facts.
</context>

<role>You are MiOS-Observability-Researcher. Verify; do not speculate.</role>

<task>
Answer every question in `<questions>` from the tracing project's source,
release metadata, documentation and container registry, then decide whether
MiOS should pin the v1 image, migrate to v2, or replace the backend, and name
the exact SSOT keys that change.
</task>

<provenance>
Raised by, at these revisions (re-read before relying on them):
- MiOS `usr/share/mios/mios.toml` at `a67750d`: lines 7151-7154
  (`[image.sidecars].otelcol` floats `all-in-one:latest`; comment says
  floating is safe), 7608 (bound-images entry, also `:latest`), 9924-9932
  (`[containers.mios-otelcol]`: comment says "Pinned" and "cannot float",
  image default is `:latest`; v1 env names `COLLECTOR_OTLP_GRPC_HOST_PORT`
  and `QUERY_HTTP_SERVER_HOST_PORT`).
- MiOS `TASKS.md` at `a67750d`: line 3652 (records the image as pinned at
  `1.76.0` in `[image.sidecars]`, the bound-images list and the inline
  default, and the v1 flag-to-env mapping read from source at that tag).
</provenance>

<inputs>
<project>{{tracing_backend_default_jaeger}}</project>
<v1_image>{{v1_image_reference}}</v1_image>
<v1_version_in_tree>{{v1_version_or_unknown}}</v1_version_in_tree>
<otlp_port_key>otelcol_otlp</otlp_port_key>
<ui_port_key>otelcol_ui</ui_port_key>
<mios_revision>{{mios_short_sha}}</mios_revision>
<run_date>{{date}}</run_date>
<prior_report>{{prior_report_or_none}}</prior_report>
</inputs>

<questions>
- Q-1  v1 lifecycle: has upstream announced end of life or end of support
       for the v1 line? Give the announcement's own text, the last v1
       release (tag, date, commit), and whether the v1 `all-in-one`
       repository still receives new tags.
- Q-2  Tag identity: the current digest of the v1 `all-in-one:latest` tag
       and of the last v1 release tag, read from the registry API, and
       whether they match.
- Q-3  v2 image: the image repository and current stable v2 release (tag,
       date, digest), and whether it runs as a non-root user by default
       (numeric UID and GID).
- Q-4  v2 configuration: how v2 sets the OTLP gRPC receiver address and the
       query UI address (configuration file keys, command-line overrides,
       environment variables). State whether the two v1 environment names
       above have any effect in v2.
- Q-5  Migration: the official v1-to-v2 migration guidance, the default
       storage backend of the v2 all-in-one mode, and the default ports.
- Q-6  Security: advisories published against the last v1 release and the
       current v2 release, from an advisory database.
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
      "name": "mios_tracing_backend_lifecycle",
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
                    "Q-1",
                    "Q-2",
                    "Q-3",
                    "Q-4",
                    "Q-5",
                    "Q-6"
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
              "PIN_V1",
              "MIGRATE_V2",
              "REPLACE_BACKEND",
              "WATCH"
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
