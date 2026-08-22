<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Contains default configuration for the SearXNG instance, defining network ports, security headers, and search engine behavior to ensure stable results for the agent's web_search tool.
AI-related: /usr/share/mios/searxng/settings.yml, /etc/mios/searxng/settings.yml, mios-searxng, systemd-tmpfiles-setup.service, localhost:8899
/usr/share/mios/searxng/settings.yml
'MiOS' SearXNG vendor defaults.

This file is copied into /etc/mios/searxng/settings.yml on first boot
by usr/lib/tmpfiles.d/mios-searxng.conf (C= line: copy-if-absent).
Once present in /etc, operator edits survive every subsequent boot.
To restore vendor defaults: rm /etc/mios/searxng/settings.yml +
`systemctl restart systemd-tmpfiles-setup.service`.

secret_key is left as the placeholder PLACEHOLDER_SECRET_KEY_REGENERATE_ON_FIRST_BOOT;
the SearXNG entrypoint detects this sentinel and overwrites it with a
fresh 64-char value on container startup, then never touches it again.

<!-- mios-src:520fd23a4ee0 from usr/share/mios/searxng/settings.yml:1-14 -->

