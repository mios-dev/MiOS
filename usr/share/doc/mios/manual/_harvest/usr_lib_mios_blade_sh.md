<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/bash AI-hint: Shared blade-resolution library....

!/usr/bin/bash
AI-hint: Shared blade-resolution library. ONE implementation of the archetype ladder, the capability set and the alias table, sourced by usr/libexec/mios/role-apply (boot-time resolver) and usr/libexec/mios/mios-blade (the day-2 verb) so the two cannot drift. Every input is parameterized -- cmdline file, role.conf path, marker directory -- so tests/test-role-apply-precedence.sh drives the real functions rather than a copy.
AI-related: usr/libexec/mios/role-apply, usr/libexec/mios/mios-blade, usr/share/mios/mios.toml, usr/lib/bootc/kargs.d/05-mios-blade.toml, usr/share/doc/mios/adr/0016-blade-node-topology.md
AI-functions: _cmdline_tok, _conf_get, _ssot_query, _hw_demotion, _resolve_role, _canon_role, _caps_for, _is_legal_cap, _resolve_features, _ssot_security, _auth_posture, _target_for

Callers may pre-set ROLE_CONF / BLADE_D / CMDLINE_FILE; otherwise the FHS
defaults below apply.

<!-- mios-src:42793013f21d from usr/lib/mios/blade.sh:1-7 -->

