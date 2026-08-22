<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Declares the persistent /home/coder volume for the mios-agents super-container (agy/claude logins + war-room state survive container restarts). Law 2 (NO-MKDIR-IN-VAR): the /var path is declared here, never written at build time. Owned by uid/gid 1000 (the container's coder user maps 1:1 to host uid 1000 under rootful podman).
AI-related: mios-agents.service, /usr/libexec/mios/mios-agents-firstboot.sh, /var/lib/mios/agents
/usr/lib/tmpfiles.d/mios-agents.conf

<!-- mios-src:a4712103ed20 from usr/lib/tmpfiles.d/mios-agents.conf:1-3 -->

