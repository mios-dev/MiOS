# Upstream researched patterns — FOSS/model

This prompt family is for primary-source research of free and open-source
upstream projects used by, or being evaluated for, the MiOS model and local
OpenAI-compatible service plane.

## Prompts

- `upstream-foss-patterns.xml.md` — verify project maturity, license,
  architecture, security posture, and integration patterns.
- `model-runtime-research.xml.md` — compare model formats, runtimes, serving
  APIs, packaging, hardware paths, and lifecycle constraints.
- `mios-cli-credential-contract.xml.md` — verify the built-in MiOS CLI
  endpoint and credential contract without exposing secrets.
- `firstboot-gguf-artifact-manifest.xml.md` — verify the publisher, file,
  size, sha256, license and runtime support behind an
  `[[ai.firstboot_models]]` entry, pinned to a repository revision.

Every prompt requires primary sources, explicit uncertainty labels, and
MiOS-SSOT-grounded recommendations. These are research prompts, not commands:
they must not mutate the repository, contact an API, or handle real secrets.
