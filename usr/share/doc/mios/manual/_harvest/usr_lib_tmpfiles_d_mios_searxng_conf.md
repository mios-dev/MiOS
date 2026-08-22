<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines filesystem permissions and ownership for SearXNG configuration and cache directories, ensuring the uwsgi worker (UID 818) has write access to the cache and the settings.yml file is correctly provisioned.
AI-related: /etc/mios/searxng, /usr/share/mios/searxng/settings.yml, /etc/mios/searxng/, /etc/mios/searxng/settings.yml, mios-searxng, mios-services, mios-searxng.container
/usr/lib/tmpfiles.d/mios-searxng.conf
'MiOS' SearXNG metasearch -- runtime directories.

/etc/mios/searxng    config dir (settings.yml, uwsgi.ini)
/var/cache/searxng   on-disk result cache (per-user TTL)

UID 818 is pinned in /usr/lib/sysusers.d/50-mios-services.conf and
referenced by etc/containers/systemd/mios-searxng.container's
User=818/Group=818 directives. Both directories must already be
chowned 818:818 before the Quadlet starts, otherwise the container's
uwsgi worker can't write its socket / cache files and exits with EACCES.

<!-- mios-src:75cd19e48a44 from usr/lib/tmpfiles.d/mios-searxng.conf:1-13 -->

