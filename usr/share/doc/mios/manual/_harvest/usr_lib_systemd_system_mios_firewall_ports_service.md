<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Ensures critical MiOS service ports (resolved from the `[ports]` SSOT: open_webui, hermes, searxng, cockpit and peers, plus DNS 53) are opened in firewalld at boot to prevent connectivity loss for Open WebUI, Hermes, Cockpit, and SearXNG.
AI-related: mios-open-webui, mios-searxng, mios-crawl4ai, firewalld.service, hermes-agent.service, mios-open-webui.service, mios-searxng.service, mios-crawl4ai.service, network-online.target, multi-user.target

<!-- mios-src:f911394c66d5 from usr/lib/systemd/system/mios-firewall-ports.service:1-2 -->

