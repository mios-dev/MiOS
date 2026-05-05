# Security policy

The full security posture (kargs, SELinux, fapolicyd, USBGuard, CrowdSec,
kernel-lockdown integrity, MOK signing, kargs hardening) lives in the
canonical FHS doc location:

- [`usr/share/doc/mios/guides/security.md`](usr/share/doc/mios/guides/security.md)

Audit reports, including the `AUDIT-FINDINGS-YYYYMMDD.md` series produced
by the read-only audit prompt at `usr/share/mios/ai/audit-prompt.md`,
ship under [`usr/share/doc/mios/audits/`](usr/share/doc/mios/audits/).

## Reporting

For private disclosure of a vulnerability in 'MiOS', open a private
security advisory at <https://github.com/mios-dev/MiOS/security/advisories/new>
or contact the project maintainers via the channels listed in the GitHub
repository's security tab. Do not file a public issue for security
reports.
