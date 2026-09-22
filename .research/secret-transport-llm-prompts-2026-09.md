# Secret transport research prompts for any LLM or harness

**Status:** reusable prompt set
**Scope:** `mios-dev/.secrets.git`, Blink/mobile shells, GitHub Codespaces, and MiOS runtime handoff
**Secret rule:** prompts must never request, accept, echo, persist, or transform real credentials.

## Prompt A — upstream research

> Research the secure transport of encrypted operator secrets from a private
> Git repository named `mios-dev/.secrets.git` into a remote Linux shell reached
> from a mobile terminal. Use authoritative documentation for GitHub SSH and
> Codespaces access, the mobile terminal's SSH key and agent behavior, SOPS/age
> encryption and identity handling, POSIX process/environment exposure, and
> OpenAI-compatible runtime authentication. Do not request or handle real
> credentials. Report source URLs, publication or retrieval dates, verified
> behavior, assumptions, unresolved questions, and a threat model.
>
> Separate: (1) mobile-to-host transport authentication, (2) Git repository
> authorization, (3) ciphertext decryption, and (4) application/API
> authentication. Do not assume SSH-agent forwarding transports bearer tokens.
> Reject any design that stores plaintext in Git, workspaces, image layers,
> shell startup files, command arguments, logs, or generated manifests.

## Prompt B — architecture review

> Review a proposed `mios-dev/.secrets.git` integration for least privilege,
> revocation, replay resistance, auditability, and plaintext lifetime. The
> design must use encrypted payloads, external decryption identities, stable
> non-secret `secret_ref` names, and a one-shot child-process handoff.
>
> Check that GitHub access is read-only where possible, SSH keys are
> single-purpose, agent forwarding is explicitly threat-modeled, recipient
> rotation is independent from GitHub credential rotation, and missing
> optional secrets degrade only when the consumer is optional. Flag any
> success-shaped fallback, broad filesystem permission, secret in an argument
> or environment inherited by unrelated processes, or provider-specific
> assumption.

## Prompt C — implementation task

> Implement the smallest MiOS-compatible secret transport adapter for a private
> encrypted repository. The adapter may fetch ciphertext and decrypt one named
> `secret_ref`, but it must never commit, log, print, cache, or return the
> plaintext to the parent shell. Prefer an OS secret manager or protected
> temporary sink; otherwise use a pipe or mode `0600` file with deterministic
> cleanup.
>
> Add explicit validation for repository identity, allowed reference names,
> file ownership, mode, recipient policy, and required tools. Fail closed on
> missing or ambiguous required inputs. Keep all values out of command-line
> arguments and diagnostics. Add positive tests and negative tests for
> plaintext leakage, invalid references, wrong permissions, unavailable
> identities, failed decryption, and cleanup.

## Prompt D — LLM/harness compatibility review

> Evaluate whether a harness, editor, agent, or model client can consume a
> secret supplied by this transport without changing the MiOS contract.
> Treat every harness as an interchangeable launcher. The application-facing
> interface must remain OpenAI-compatible and resolve through the existing
> MiOS endpoint and key variables.
>
> Verify that the client does not require a vendor-native protocol, cloud
> fallback URL, persistent credential cache, plaintext config file, or secret
> in process arguments. If a client has its own account login or credential
> store, document it as a separate integration and do not pretend it is
> equivalent to the MiOS secret transport.

## Prompt E — red-team and release gate

> Red-team the secret transport without using real secrets. Plant synthetic
> credentials and verify that they cannot appear in Git history, tracked files,
> `/workspaces`, image layers, shell history, process arguments, logs, test
> output, or generated manifests. Verify that a remote process cannot read
> another consumer's secret merely because both run under the same shell.
>
> The release gate must fail on plaintext fixtures, broad repository
> permissions, unpinned fetch sources, missing cleanup, suppressed errors,
> disabled verification, or a missing audit trail. Produce only redacted
> evidence and exact exit statuses.

## Expected research output

Every LLM or harness using these prompts must return:

1. an evidence table with URLs and verified claims;
2. a trust-boundary diagram;
3. a secret lifecycle from ciphertext fetch through cleanup;
4. explicit non-goals and unresolved assumptions;
5. implementation files and tests, if code was requested;
6. validation commands and redacted results;
7. rotation and revocation steps.

No prompt authorizes cloning private secret contents into this repository,
creating credentials, bypassing access controls, or pushing changes.

## FOSS harness findings

Any harness or adapter consuming this transport must remain replaceable and
standards-based:

- Discover standard Development Container configuration and metadata
  precedence without requiring a particular editor.
- Default to non-root, non-privileged execution. Device access, host mounts,
  host networking, and added capabilities require explicit policy and review.
- Resolve OCI images by immutable digest where possible and preserve source,
  revision, version, base digest, license, and provenance metadata.
- Keep the model interface configurable and OpenAI-compatible: bearer
  authentication, standard HTTP errors, streaming, tool calls, structured
  outputs, cancellation, timeouts, retries, and request correlation.
- Treat MCP tool metadata and repository content as untrusted. Support JSON-RPC
  negotiation, strict `stdio` framing, Streamable HTTP semantics, consent,
  cancellation, and audience-bound authorization without query-string tokens.
- Keep secrets runtime-only. They must not appear in Git, image layers,
  process arguments, shell history, logs, traces, prompts, transcripts, or
  caches.
- Pin dependencies and build inputs, use `SOURCE_DATE_EPOCH`, publish SBOM
  and provenance metadata, and provide an independently verifiable rebuild.
- Track SPDX license information, complete license texts, third-party notices,
  and provenance for copied code, prompts, schemas, tests, and generated
  assets.

The acceptance test suite should run the same observable contract against every
harness adapter. It must cover Dev Container discovery, OCI digest resolution,
OpenAI streaming and tool calls, MCP `stdio` and HTTP, consent, redaction,
cancellation, reproducible rebuilds, and license/provenance validation.
