# Upstream researched patterns -- FOSS/supply-chain

This prompt family is for primary-source corroboration of upstream version
and change claims before any MiOS pin moves on their strength.

## Prompts

- `telemetry-claim-corroboration.xml.md` -- settle, claim by claim, the
  unverified upstream bullets a generated training artifact contributed to
  the knowledge tree.

Every prompt requires primary sources, exact versions, a badge and a
confidence per claim, and replies with one JSON object that validates against
the strict OpenAI-format `response_format` schema embedded in the prompt.
These are research prompts, not commands: they must not mutate the
repository, authenticate to a service, or handle real secrets.
