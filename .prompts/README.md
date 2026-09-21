# Prompt source and index

This is the root-level authoring surface for MiOS prompts.

Prompts intended to ship in the image remain complete files under
`usr/share/mios/prompts/`. This directory holds source organization,
cross-prompt indexes, research bundles, and promotion metadata; it is not a
second runtime endpoint or a secret store.

## Current research family

The FOSS/model upstream research prompts are deployed at:

`usr/share/mios/prompts/upstream-researched-patterns/foss/model/`

That family contains:

- `upstream-foss-patterns.xml.md`
- `model-runtime-research.xml.md`
- `mios-cli-credential-contract.xml.md`
