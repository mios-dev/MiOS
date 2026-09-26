<!-- AI-hint: Index of the tracked, non-secret MiOS prompt catalog and its primary report contract; shipped prompts live under usr/share/mios/prompts/. -->
# MiOS prompt catalog

`.prompts/` is the tracked, non-secret catalog for MiOS prompt contracts. It
does not define a deployment pipeline, runtime endpoint, credential boundary,
or second system identity.

## Primary report contract

The external research and engineering report contract is:

- [`.mios/system-prompt.md`](../.mios/system-prompt.md)
- [`.prompt.MD`](../.prompt.MD) - root-level shortcut to the contract

It covers FOSS and generative patterns across OCI, CI/CD, supply chain,
immutable operating systems, and local AIOS architecture. It also defines the
repository bootstrap order, evidence rules, report schema, authentication
profiles, and required MiOS context for every change submission.

## Shipped prompt contracts

Runtime prompt files are owned by the FHS overlay under
[`usr/share/mios/prompts/`](../usr/share/mios/prompts/). The current FOSS/model
research family is:

- [`upstream-foss-patterns.xml.md`](../usr/share/mios/prompts/upstream-researched-patterns/foss/model/upstream-foss-patterns.xml.md)
- [`model-runtime-research.xml.md`](../usr/share/mios/prompts/upstream-researched-patterns/foss/model/model-runtime-research.xml.md)
- [`mios-cli-credential-contract.xml.md`](../usr/share/mios/prompts/upstream-researched-patterns/foss/model/mios-cli-credential-contract.xml.md)

Use those contracts for focused upstream research. Use
`.mios/system-prompt.md` when the output must be a formal architecture,
operations, OCI, CI/CD, or AIOS report.

## Contract rules

- Keep prompt text FOSS-first, standards-based, reproducible, and safe to
  regenerate from explicit inputs.
- Keep MiOS context in every report and commit submission.
- Cite primary sources, revisions, paths, evidence IDs, and confidence.
- Keep credentials, private identities, decrypted configuration, and runtime
  secrets out of prompts and reports.
- Do not duplicate the canonical runtime identity in this catalog.
- Do not add vendor-cloud URLs or proprietary agent protocols to MiOS prompt
  contracts.
