# Gemini Deep Research Prompt — MiOS secrets transport and FOSS harness conformance

**Use:** Paste this entire file into Gemini Apps with `/deep-research`
enabled. If reviewing an implementation, append its GitHub commit URL or
compare URL after this prompt and review that exact revision.

**Canonical repository path:** `.research/gemini-deep-research-foss-harness-secrets-2026-09.md`

Copy the prompt below into Gemini Deep Research. Do not provide real
credentials, private keys, OAuth codes, decrypted files, or secret repository
contents to the research system.

---

## Research brief

You are researching and specifying a provider-neutral, FOSS-compatible
engineering system for MiOS. The system must transport encrypted operator
secrets from the private Git repository
`github.com/mios-dev/.secrets.git`, accessed from a mobile remote shell such as
Blink Shell, into a GitHub Codespace or MiOS remote Linux shell, and then into
the shortest-lived possible runtime process.

The same system must support interchangeable LLM and coding-agent harnesses.
Harnesses are launchers and adapters, not the application contract. The
application-facing model interface must remain OpenAI-compatible and resolve
through MiOS configuration variables such as `MIOS_AI_ENDPOINT`,
`MIOS_AI_MODEL`, and `MIOS_AI_KEY`. Do not assume that a named harness,
provider, model family, editor, or proprietary protocol is available.

Treat this as an evidence-first research task followed by an implementation
design. Never request, accept, reproduce, transform, or store real secrets.

## Required research areas

### 1. Encrypted secret repository and lifecycle

Research the secure use of a private repository containing only encrypted
operator data:

- SOPS and age payload formats, recipient files, external identity handling,
  rotation, revocation, recovery, and auditability.
- Repository layout for encrypted common, host, user, Blade, and fleet scopes.
- Stable non-secret `secret_ref` names and validation rules.
- Read-only Git access, deploy keys, short-lived credentials, SSH agent
  forwarding, and the risks of forwarding signing capability to a remote host.
- Fetching ciphertext, decrypting one requested entry, ephemeral handoff to a
  child process, cleanup, and failure behavior.
- Plaintext exposure through process environments, `/proc`, arguments, shell
  history, workspaces, temporary files, logs, crash dumps, telemetry,
  transcripts, image layers, and caches.

Do not infer that private Git hosting replaces encryption. Do not recommend
cloning decrypted material into a worktree.

### 2. Blink Shell and mobile remote-shell transport

Use official Blink documentation and relevant OpenSSH documentation to verify:

- Secure Enclave or platform-protected SSH key storage.
- Integrated SSH agent behavior, `ssh-add`, agent forwarding, and prompts.
- Threats from a remote process that can request signatures.
- Separate single-purpose keys, least privilege, revocation, and alternatives
  such as ProxyJump.
- Safe transport from a mobile shell to a Codespace or MiOS host.

Clearly separate SSH transport authentication from application/API bearer
credentials and from SOPS/age decryption identities.

### 3. GitHub Codespaces and GitHub CLI

Research official GitHub documentation for:

- Codespaces account, repository, and organization secrets.
- Repository access scope, restart behavior, size/quantity limits, and
  environment-variable exposure.
- `gh auth login`, Codespaces SSH, `gh codespace ssh`, and file-copy behavior.
- Devcontainer lifecycle trust, extensions, `postCreateCommand`,
  `postStartCommand`, forks, pull requests, and untrusted repository risks.
- Safe use of a Codespace as a transport/decryption execution boundary.

Do not put secret values in `devcontainer.json`, a Dockerfile `ENV`, image
layers, or committed lifecycle scripts.

### 4. Development Containers

Use the current Development Containers specification and JSON reference to
research:

- Standard config discovery and image-embedded `devcontainer.metadata`.
- Configuration precedence and lifecycle semantics.
- `containerEnv` versus `remoteEnv`.
- `remoteUser`, `containerUser`, mounts, features, ports, capabilities,
  `privileged`, `securityOpt`, and device access.
- A portable default that works without NVIDIA, KVM, proprietary devices, or
  a specific editor.

Define which features are portable, optional, host-only, or not applicable.
Never turn a missing hardware capability into a false passing test.

### 5. OCI images and container security

Use the OCI Image and Distribution specifications to research:

- Manifests, indexes, layers, descriptors, content digests, local OCI
  layouts, multi-platform images, and registry interoperability.
- Standard OCI annotations for source, revision, version, license, creation,
  base image, and provenance.
- Digest pinning, signature verification, SBOM attachment, and artifact
  discovery.
- Non-root defaults, capability minimization, read-only filesystems,
  seccomp/LSM boundaries, device exposure, and explicit privilege review.

Exclude Docker-only assumptions from the core design.

### 6. OpenAI-compatible model and tool interface

Use the current official OpenAI API reference and standards-compatible
implementations to research:

- Authentication headers, endpoint configuration, `/v1/models`,
  `/v1/chat/completions`, `/v1/responses`, embeddings, streaming events,
  function/tool calls, structured outputs, errors, request IDs, cancellation,
  retries, timeouts, and rate-limit behavior.
- Capability discovery and explicit feature negotiation.
- Server-side secret handling and request correlation without logging secrets.
- Interoperability across local or self-hosted OpenAI-compatible endpoints.
- Which behaviors are genuinely standardized versus merely common extensions.

Do not claim that a named external CLI supports a generic OpenAI provider
without authoritative documentation and a reproducible probe.

### 7. Model Context Protocol

Use the current MCP specification and authorization/transport documents to
research:

- JSON-RPC initialization, protocol-version negotiation, capabilities,
  notifications, progress, cancellation, sessions, errors, roots, resources,
  prompts, tools, sampling, elicitation, and user consent.
- `stdio` framing requirements, stdout/stderr separation, and process
  lifecycle.
- Streamable HTTP POST/GET, SSE, `Accept` headers, session IDs, reconnect,
  cancellation, Origin validation, and DNS-rebinding defenses.
- OAuth discovery, audience-bound authorization, token forwarding, and the
  prohibition on query-string tokens.
- Treating tool metadata and repository content as untrusted input.

Separate MCP transport authorization from the MiOS application API key.

### 8. Reproducible builds and supply-chain provenance

Use authoritative Reproducible Builds, `SOURCE_DATE_EPOCH`, SLSA, in-toto,
SBOM, and OCI provenance guidance to research:

- Pinned source revisions, dependencies, base image digests, toolchains, and
  package repositories.
- Deterministic timestamps, file ordering, locale, timezone, archive,
  manifest, and image generation.
- Clean-room rebuilds and digest comparison.
- SLSA/in-toto provenance, artifact signing, verification, and key rotation.
- Dependency and container SBOM formats and attachment to immutable digests.

Define a minimum viable FOSS release gate and a stronger target gate.

### 9. FOSS licensing and provenance

Use REUSE and SPDX documentation to research:

- SPDX identifiers and license expressions.
- Complete license texts, copyright notices, third-party notices, and
  generated-file coverage.
- Provenance for copied code, prompts, schemas, tests, documentation, model
  files, and generated artifacts.
- Treatment of source-available, non-free, usage-restricted, trademark,
  network-service, and proprietary dependencies.
- How optional provider adapters can remain outside the FOSS-compatible core.

### 10. Harness adapter conformance

Derive a common adapter contract that can be tested against any coding-agent
or LLM harness. It must cover:

- Objective input and structured result output.
- Workspace isolation and explicit mount policy.
- Process execution, exit-code preservation, output limits, cancellation,
  timeouts, cleanup, and readiness/health.
- Secret-use consent and redaction.
- OpenAI-compatible model calls and MCP tool calls.
- Portable Dev Container and OCI operation.
- Reproducible build and license/provenance reporting.

Do not make one vendor's command syntax the canonical protocol.

## Threat model

Model at least these actors and failures:

1. A malicious repository change or lifecycle hook.
2. A compromised dependency, extension, MCP server, or model tool.
3. A remote process abusing forwarded SSH-agent signing capability.
4. A Codespace process reading inherited environment variables.
5. A leaked GitHub credential or revoked encryption recipient.
6. Accidental plaintext in logs, arguments, caches, artifacts, or Git history.
7. A malicious or malformed OCI image, MCP message, tool schema, or prompt.
8. A non-reproducible build that cannot be independently verified.

For each, state prevention, detection, containment, rotation/revocation, and
residual risk.

## Implementation-review mode

If the operator supplies a GitHub commit, pull-request, or compare URL,
inspect only publicly available files at that revision and map findings to
exact paths and line ranges. Research upstream implementations before
recommending changes. For every proposed file change, provide the reason,
the relevant upstream evidence, compatibility impact, and a focused test.
Separate verified facts, recommendations, assumptions, and blockers. Do not
pretend to have applied, committed, or pushed changes.

## Required deliverables

Return all of the following:

1. An evidence table with authoritative URL, date/version, verified claim,
   applicability, and confidence.
2. A trust-boundary and data-flow diagram from Blink/mobile shell to the
   target process.
3. A recommended encrypted repository layout using placeholders only.
4. A secret lifecycle and plaintext-lifetime table.
5. A provider-neutral harness adapter protocol and capability matrix.
6. A FOSS release checklist covering Dev Containers, OCI, OpenAI, MCP,
   secrets, reproducibility, provenance, and SPDX/REUSE.
7. A minimal implementation plan for MiOS, naming files and tests but never
   generating credentials.
8. Positive and negative test cases for missing references, invalid
   permissions, decryption failure, redaction, cleanup, capability absence,
   protocol errors, and license/provenance gaps.
9. Unresolved questions and decisions that require operator approval.
10. A concise executive summary that distinguishes verified facts from
    recommendations and assumptions.

## Hard constraints

- Never ask the operator to paste a secret, token, private key, OAuth code, or
  decrypted payload.
- Never include a secret-looking value in examples; use `[REDACTED]`.
- Never recommend plaintext secret storage in Git, workspaces, images,
  arguments, shell profiles, logs, prompts, transcripts, or caches.
- Never use a vendor cloud fallback or vendor-native protocol in the MiOS core
  contract.
- Never fabricate support for a harness, API, MCP feature, or secret backend.
- Do not clone, decrypt, or inspect `mios-dev/.secrets.git` contents as part
  of the research.
- Do not commit, deploy, boot-switch, or push code.

## Output format

Return the deliverables in this order:

1. Executive summary.
2. Evidence table with citations and access dates.
3. Verified upstream implementation patterns.
4. MiOS-specific architecture and trust boundaries.
5. Exact implementation plan with file paths.
6. Test matrix with positive, negative, and not-applicable cases.
7. Licensing, provenance, and reproducibility gate.
8. Open decisions and blockers.

Use Markdown tables and Mermaid only when they improve precision. Keep all
examples synthetic and use `[REDACTED]` for any secret-shaped value.
