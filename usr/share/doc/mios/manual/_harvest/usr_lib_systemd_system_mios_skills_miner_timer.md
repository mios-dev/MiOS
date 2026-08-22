<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines the systemd timer for the mios-skills-miner.service, controlling the periodic execution interval (default 60m) for background skill mining and pattern discovery.
AI-related: /usr/libexec/mios/mios-skills, mios-skills-miner, mios-skills, mios-skills-miner.service, timers.target
/usr/lib/systemd/system/mios-skills-miner.timer
Phase C.2 of the AgentOS roadmap: cadence for the background
skill miner. Interval lifted to mios.toml [skills].
mine_interval_minutes (default 60). Operator override:
  sudo systemctl edit mios-skills-miner.timer
  [Timer]
  OnUnitActiveSec=30min

Disabled by default; operator opts in (or it inherits enablement
from the configurator HTML "Skills mining" toggle which maps to
[skills].enable). The .service ConditionPathExists guard means a
stripped-down deployment with the libexec script absent skips
silently.

<!-- mios-src:5c6bacfe75c5 from usr/lib/systemd/system/mios-skills-miner.timer:1-15 -->

