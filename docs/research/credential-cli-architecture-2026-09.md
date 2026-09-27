<!-- AI-hint: Research on CLI and API credential architecture for MiOS: clients resolve MIOS_AI_ENDPOINT and never hold upstream credentials; short-lived scoped tokens elsewhere. -->
# Secure Command-Line and API Credential Architecture for MiOS

**Research date:** 2026-09-21  
**Status:** corrected research artifact  
**Scope:** interactive CLI execution, local development, services, CI, and containers

## Executive assessment

MiOS should separate client execution from upstream credential custody. Client
processes should resolve the configured `MIOS_AI_ENDPOINT` and should not carry
upstream cloud credentials. Where a non-AI utility must authenticate directly
to a local gateway or platform service, use a short-lived, scoped credential
from an OS or deployment secret store and limit its lifetime to the smallest
possible process boundary.

The source text that motivated this artifact overstated several points. An
environment variable is not automatically hidden from the process owner:
Linux exposes a process environment through `/proc/<pid>/environ` subject to
permissions and ptrace policy, and child processes inherit the environment
unless it is explicitly replaced or cleared. A tmpfs projection reduces
persistence on ordinary storage, but it is not a kernel-isolated secret
channel; the process, privileged observers, core dumps, swap policy, backups,
and logging still matter. A local HTTP proxy also does not provide
confidentiality or authentication merely because it binds to loopback.

## Verified contract

| Question | Finding | Evidence | Confidence |
|---|---|---|---|
| Process arguments | Secrets in command arguments can be exposed through process-inspection interfaces and shell history. Do not pass credentials as flags or URL query parameters. | [proc_pid_cmdline(5)](https://man7.org/linux/man-pages/man5/proc_pid_cmdline.5.html); [Bash history](https://www.gnu.org/software/bash/manual/html_node/Bash-History-Builtins.html) | High |
| Process environment | Environment entries can be read through `/proc/<pid>/environ` subject to OS permissions and are inherited by children unless replaced. | [proc_pid_environ(5)](https://man7.org/linux/man-pages/man5/proc_pid_environ.5.html); [execve(2)](https://man7.org/linux/man-pages/man2/execve.2.html) | High |
| Shell startup files | Startup files are configuration scripts, not secret stores. A key written there persists into later sessions and may be copied or logged. | [Bash startup files](https://www.gnu.org/software/bash/manual/html_node/Bash-Startup-Files.html) | High |
| OS secret stores | Secret Service-style stores provide an access-controlled API for secret retrieval; they do not make the resulting plaintext unavailable to the requesting process. | [Secret Service specification](https://specifications.freedesktop.org/secret-service/latest/) | Medium |
| Cloud secret stores | Secret Manager-style systems support IAM-controlled retrieval, auditing, and rotation. Workload identity is preferred over exporting long-lived service credentials where supported. | [Google Secret Manager best practices](https://cloud.google.com/secret-manager/docs/best-practices) | High |
| Kubernetes projected secrets | Projected secret files can be updated atomically by the kubelet/driver, but the consuming process and node administrators remain in the trust boundary. | [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/); [Secrets Store CSI Driver](https://secrets-store-csi-driver.sigs.k8s.io/topics/secret-auto-rotation) | Medium |
| MiOS AI clients | AI clients must use the configured OpenAI-compatible `MIOS_AI_ENDPOINT`; the endpoint and port must be resolved from MiOS configuration rather than invented in a research artifact. | `usr/share/mios/mios.toml`; `usr/share/mios/ai/INDEX.md`; Architectural Law 5 | High |
| Target CLI contract | No particular variable name, flag, login command, SDK feature, or precedence rule is verified until the target's official documentation or local `--help` output confirms it. | Target-specific documentation and `--help` output are required inputs | High |

Claims about a generic SDK's workload-identity provider suite, a universal
`OPENAI_ORG_ID` contract, a universal `auth.toml`/`settings.json` format, or
specific constructor/environment precedence are **not portable facts**. They
must be verified separately for each target and version.

## Threat and recovery assessment

### Exposure classes

| Mechanism | Main exposure | Correct treatment |
|---|---|---|
| CLI argument | Process inspection, shell history, audit logs | Reject for secrets |
| Exported environment | `/proc`, child inheritance, crash/debug tooling | Use only as a tightly scoped compatibility bridge |
| Shell startup file | Persistent plaintext, backups, accidental commits | Do not store live credentials there |
| Protected file | File disclosure, backups, incorrect permissions, stale copies | Use `0600`, atomic replacement, and a narrowly scoped reader |
| OS secret store | Retrieval is visible to the requesting process | Prefer for interactive local use |
| tmpfs projection | Reduced disk persistence, but still readable by the consumer and privileged observers | Use only when the consumer requires a file |
| Loopback HTTP | Local interception or unauthorized local clients | Bind narrowly and authenticate/encrypt where the threat model requires it |

### Compromised credential protocol

1. Revoke or disable the exposed credential immediately, unless a documented
   overlapping rotation procedure is already active.
2. Issue a replacement with least privilege, resource restrictions, and a short
   lifetime where supported.
3. Update the secret store or projection without placing the value in a
   command, commit, prompt, log, or shell startup file.
4. Perform a non-echoing health check that records only success/failure and an
   HTTP status class.
5. Audit provider usage, billing, identity logs, CI logs, and network origins
   for the exposure interval.
6. Remove copies from shell history, terminal recordings, editor swap/undo
   data, CI artifacts, caches, backups, and Git history where applicable.

## Recommended implementations

### 1. One interactive invocation

Prefer an OS secret store and a wrapper that passes the value only to the
child process. If the target has no secret-store integration and requires an
environment variable, use a transient environment assignment and clear the
shell variable after the child exits:

```sh
credential="$(secret-store lookup service <SERVICE> account <ACCOUNT>)" || exit 1
[ -n "$credential" ] || exit 1
env TARGET_CREDENTIAL="$credential" target-cli "$@"
status=$?
unset credential
exit "$status"
```

`secret-store` is illustrative pseudocode until the target platform's
documented command is substituted. Do not replace it with a command that puts
the credential in its own arguments.

### 2. Repeated local development

Use a platform credential store plus a wrapper function, or a local gateway
that retrieves upstream credentials itself. The gateway must:

- bind only to the configured MiOS loopback address and port;
- reject unauthenticated or cross-user callers;
- avoid logging authorization headers and request bodies containing secrets;
- use TLS or an authenticated local transport when local-user interception is
  in scope; and
- reload or rotate credentials through an atomic, documented mechanism.

Do not hardcode `127.0.0.1:8088`; resolve the endpoint from MiOS SSOT. A
loopback address alone is not an authentication boundary.

### 3. Service, CI, and container deployment

Prefer workload identity or the platform's native secret manager. If the
consumer requires a file, project a short-lived secret onto a restricted
filesystem and update it atomically. If it requires an environment variable,
inject it at process start through the deployment platform and prevent
inspection APIs, debug endpoints, and logs from exposing the environment.

Pin secret versions where the platform supports it, validate a new version
before disabling the old one, and retain an explicit rollback procedure.

## MiOS integration

No new upstream credential variable, fixed port, vendor URL, or generic SDK
claim should be added to MiOS based on this report. The relevant integration
surfaces are:

- `usr/share/mios/mios.toml` for the configured endpoint and secret pointers;
- `usr/share/mios/ai/INDEX.md` and the existing AI contract files for Law 5;
- existing secret-store, systemd credential, or container secret mechanisms
  already defined by the target deployment surface; and
- `usr/share/mios/prompts/credential-cli-research.xml.md` for future
  target-specific research inputs.

Safe validation must not print credentials:

```sh
endpoint="${MIOS_AI_ENDPOINT:?MIOS_AI_ENDPOINT is unset}"
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' \
  --max-time 10 "$endpoint/models"
```

The expected output is an HTTP status code only. Whether authentication is
required, and which status is healthy, must be established from the configured
MiOS service contract before using this check in automation.

## Open questions

1. Which concrete CLI or service is the target, and which version is deployed?
2. Does that target document an OS secret-store, workload-identity, or
   systemd-credential integration?
3. What local threat model applies: same-user processes only, other local users,
   privileged administrators, or host compromise?
4. Which MiOS service owns upstream authentication, and what is the canonical
   endpoint key in the current `mios.toml` layer?

## Sources

1. [Linux `/proc` documentation](https://docs.kernel.org/filesystems/proc.html)
2. [`proc_pid_cmdline(5)`](https://man7.org/linux/man-pages/man5/proc_pid_cmdline.5.html)
3. [`proc_pid_environ(5)`](https://man7.org/linux/man-pages/man5/proc_pid_environ.5.html)
4. [`execve(2)`](https://man7.org/linux/man-pages/man2/execve.2.html)
5. [Bash startup files](https://www.gnu.org/software/bash/manual/html_node/Bash-Startup-Files.html)
6. [FreeDesktop Secret Service specification](https://specifications.freedesktop.org/secret-service/latest/)
7. [Google Secret Manager best practices](https://cloud.google.com/secret-manager/docs/best-practices)
8. [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
9. [Secrets Store CSI Driver rotation](https://secrets-store-csi-driver.sigs.k8s.io/topics/secret-auto-rotation)
