<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### 'MiOS' overlay -- make BUILDER look/feel like a Live 'MiOS'...

---------------------------------------------------------------------------
'MiOS' overlay -- make BUILDER look/feel like a Live 'MiOS' environment.
Rsyncs the user-facing assets (mios CLI, motd, vendor docs, paths.sh,
profile.d hooks) into the podman-machine without touching its systemd /
sysusers / tmpfiles plumbing (those live only in the bootc image).
---------------------------------------------------------------------------

<!-- mios-src:d0d74784cb5b from automation/mios-build-builder.ps1:217-222 -->
