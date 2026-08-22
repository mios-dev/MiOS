<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines systemd-tmpfiles symlinks to map mios-shell-verbs from /usr/libexec/mios/ to /usr/local/bin/ and /usr/local/sbin/ to ensure consistent tool availability across all user PATH configurations.
AI-related: /usr/libexec/mios/., /usr/libexec/mios/mios-find, /usr/libexec/mios/mios-everything, /usr/libexec/mios/mios-locate, /usr/libexec/mios/mios-kg, /usr/libexec/mios/mios-skills, /usr/libexec/mios/mios-passport, /usr/libexec/mios/mios-text-edit, /usr/libexec/mios/mios-powershell, /usr/libexec/mios/mios-ttyd-launch
Rationale per shim: usr/share/doc/mios/reference/shim-links.md
/usr/lib/tmpfiles.d/mios-shim-links.conf

Idempotent symlinks for the mios-* shell verbs into /usr/local/{s,}bin/
so they're reachable on every user's PATH without needing a per-tool
automation step. The actual scripts live in /usr/libexec/mios/.

/usr/local/bin and /usr/local/sbin are both on the standard PATH;
duplicating into both means the verb works regardless of whether the
caller has sbin in their PATH (root has it, mios-hermes service user
has it; an interactive non-root operator might not).

Operator directive 2026-05-17: the 'mios-show-image' helper landed
but the agent reported it "appears to be vendor-specific" -- because
the agent's PATH (/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:
/sbin:/bin:/var/lib/snapd/snap/bin) didn't include /usr/libexec/mios.
This file is the durable fix: every shim listed here is materialized
on every boot via systemd-tmpfiles-setup.service.

To add a new shim:
  1. Drop the script at /usr/libexec/mios/<name>, chmod +x
  2. Add two L+ lines here (sbin + bin)
  3. systemd-tmpfiles --create on the live host (rebuild not needed)

<!-- mios-src:717d05a8a506 from usr/lib/tmpfiles.d/mios-shim-links.conf:1-25 -->

