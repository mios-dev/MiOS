<!-- AI-hint: Top-level security policy entry point for MiOS — frames security as the trust layer beneath both the immutable bootc/OCI image and the local agentic AI stack, then directs agents to the canonical FHS hardening guide, the audit-report series, and the private vulnerability-disclosure procedure. Carries no hardening config itself; it is a pointer.
     AI-related: mios-dev, mios-hardening, audit-prompt -->
# Security policy

## What this document is for

MiOS is one system built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image you `bootc
upgrade` like a `git pull` and `bootc rollback` like a Ctrl-Z) that is *also* a
**local, self-hosted agentic AI operating system** — a full inference + agent
stack running on the operator's own hardware behind one OpenAI-compatible
endpoint (`MIOS_AI_ENDPOINT`).

Both halves raise the security stakes, which is why MiOS treats hardening as a
first-class, defense-in-depth layer rather than an afterthought:

- The **image-mode** half means the root filesystem is content-addressed and
  tamper-evident, so verification has to extend from the OCI layer all the way
  down to per-file integrity (MOK-signed modules, kernel-lockdown integrity,
  fapolicyd, USBGuard).
- The **agentic** half means the machine runs code on the operator's behalf and
  reasons about itself, so the agent plane — the `agent-pipe`/MiOS-Hermes
  orchestrator, the `mios-llm-light` inference lane (`:11450`, also embeddings)
  and gated heavy GPU lanes, and the PostgreSQL+pgvector memory — must be
  **unprivileged, network-fenced, and sandboxed by default** (Architectural Law
  6, UNPRIVILEGED-QUADLETS).

This file is the top-level **entry point** for the security topic: a short
pointer that tells you where the enforced posture lives, where the audit record
lives, and how to report a vulnerability privately. It deliberately carries no
hardening configuration itself — the canonical guide below is the single source
of truth, and every control there cites the exact file that enforces it.

## Where the posture lives

The full security posture (kargs, SELinux, fapolicyd, USBGuard, CrowdSec
sovereign-mode IPS, kernel-lockdown integrity, MOK signing, kargs hardening)
lives in the canonical FHS doc location:

- [`usr/share/doc/mios/guides/security.md`](usr/share/doc/mios/guides/security.md)

That guide is the defense-in-depth map: each control is tied to the exact file
that enforces it (`usr/lib/bootc/kargs.d/*.toml`, the SELinux modules under
`usr/share/selinux/packages/mios/`, the `33-firewall`/`37-selinux` automation
steps, and the `mios-hardening`/`mios-firewall-init` units), with the admin
override for each.

## Audit record

Audit reports, including the `AUDIT-FINDINGS-YYYYMMDD.md` series produced
by the read-only audit prompt at `usr/share/mios/ai/audit-prompt.md`,
ship under [`usr/share/doc/mios/audits/`](usr/share/doc/mios/audits/).

These are a **historical record** of point-in-time reviews — they are kept as
the audit trail and are not edited to track the current state. The live posture
is always the canonical guide above.

## Reporting

For private disclosure of a vulnerability in 'MiOS', open a private
security advisory at <https://github.com/mios-dev/MiOS/security/advisories/new>
or contact the project maintainers via the channels listed in the GitHub
repository's security tab. Do not file a public issue for security
reports.
