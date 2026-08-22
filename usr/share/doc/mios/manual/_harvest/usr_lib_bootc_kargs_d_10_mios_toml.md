<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines bootc kernel arguments for x86_64 systems, enforcing integrity lockdown, disabling memory randomization, and configuring NVIDIA driver behavior and mode setting.
/usr/lib/bootc/kargs.d/10-mios.toml
Flat array only. Honored by bootc per bootc.dev/bootc/building/kernel-arguments.html
Schema: kargs = [...]  and optional match-architectures = [...].
Do NOT introduce a [kargs] section header.

<!-- mios-src:ac2bd361d4c5 from usr/lib/bootc/kargs.d/10-mios.toml:1-5 -->

