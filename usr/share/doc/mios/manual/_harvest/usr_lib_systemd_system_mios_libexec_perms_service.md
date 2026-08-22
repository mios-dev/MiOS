<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Enforces world exec+read (go+rX) perms on /usr/libexec/mios via a systemd oneshot at early boot, so MiOS services that run as a non-owner user (mios-ai, mios-skills, mios-hermes, ...) can execute their libexec scripts instead of crash-looping with 203/EXEC "Permission denied". Guards the case where the deployed root / (a git working tree of mios.git) is checked out without core.fileMode / exec bits.
AI-related: mios-additionalimagestores-perms.service, mios-libexec-perms.path, mios-hermes-browser.service, mios-skills-miner.service, mios-daemon.service, local-fs.target, multi-user.target

<!-- mios-src:f47193b576a8 from usr/lib/systemd/system/mios-libexec-perms.service:1-2 -->

