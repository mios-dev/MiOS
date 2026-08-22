<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines the declarative materialization of the 'mios' user's home directory, skeleton files, and local assets (icons/fonts) to ensure persistent ownership and Flatpak-accessible paths on first boot.
AI-related: /usr/libexec/mios/wsl-firstboot., mios-user
/usr/lib/tmpfiles.d/mios-user.conf

Declarative materialization of the 'mios' user's runtime state at
first boot. Replaces the imperative `useradd`/`mkdir`/`cp -a`/
`loginctl enable-linger` block that was previously in
/usr/libexec/mios/wsl-firstboot. The user account itself is created
at IMAGE BUILD TIME via /usr/lib/sysusers.d/10-mios.conf and
automation/11-user.sh -- this file only handles the few pieces
that genuinely require the persistent /var subvolume to be mounted
(which on bootc / WSL is only true at boot, not at build).

Replaces ad-hoc work that used to live in wsl-firstboot:
  * home directory creation + skel copy
  * recursive ownership of $HOME
  * systemd-logind linger marker

Native Fedora pattern:
  * `D` (delete-then-create) ensures /var/home/mios exists with
    correct perms even if a prior failed boot left it half-populated.
  * `C` (copy-if-missing) seeds the skel content non-destructively.
  * `Z` recursively normalizes ownership without re-copying.
  * `f` (create-if-missing) lays down /var/lib/systemd/linger/mios,
    which is the canonical loginctl-enable-linger marker that
    systemd-logind reads at start. Bypasses the loginctl D-Bus call
    that fails on WSL2 where logind itself is condition-skipped.

<!-- mios-src:44d717ec0461 from usr/lib/tmpfiles.d/mios-user.conf:1-27 -->

