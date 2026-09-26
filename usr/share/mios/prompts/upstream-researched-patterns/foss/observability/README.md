# Upstream researched patterns -- FOSS/observability

This prompt family is for primary-source research of the free and
open-source tracing and telemetry backends behind the MiOS observability
sidecars.

## Prompts

- `tracing-backend-lifecycle.xml.md` -- v1 line status, the v2 image and its
  configuration model, and whether the `mios-otelcol` image should be pinned
  or migrated.

Every prompt requires primary sources, exact versions, a badge and a
confidence per claim, and replies with one JSON object that validates against
the strict OpenAI-format `response_format` schema embedded in the prompt.
These are research prompts, not commands: they must not mutate the
repository, authenticate to a service, or handle real secrets.
