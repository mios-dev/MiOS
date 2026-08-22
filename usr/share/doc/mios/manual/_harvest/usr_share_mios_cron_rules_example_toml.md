<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Reference template for mios-cron-director defining cron rules, shell commands, and LLM-gated logic (qwen3:0.6b) to conditionally execute tasks like cache clearing or briefings based on system state.
AI-related: /usr/share/mios/cron-rules.example.toml, /etc/mios/cron-rules.toml, mios-cron-director, mios-cron, mios-cache-clear, mios-cron-update
/usr/share/mios/cron-rules.example.toml

Vendor template for the mios-cron-director (LLM-gated cron). Copy
to /etc/mios/cron-rules.toml + customise. Operator's
/etc/mios/cron-rules.toml is the authoritative file the daemon
reads; this vendor copy is for reference + as a starting point.

Schema (per [[rule]]):
  name = "<short-id>"          REQUIRED -- used in journal + dedup state
  cron = "<5-field cron>"      REQUIRED -- "min hour dom mon dow"
  do   = "<shell command>"     REQUIRED -- bash -lc <do>
  gate = "<NL question>"       OPTIONAL -- if present, asked of the
                                           micro-LLM with current state
                                           context; YES -> fire, NO -> skip

When a rule's cron expression matches the current minute:
  - No gate present  -> fire `do` immediately
  - Gate present     -> evaluate gate via micro-LLM (qwen3:0.6b),
                        fire if YES, log+skip if NO

State file at /var/lib/mios/cron-director/state.json prevents
double-firing within a minute. Reload rules on SIGHUP without
restarting the daemon: `systemctl kill -s HUP mios-cron-director`.

<!-- mios-src:ed5ac683b773 from usr/share/mios/cron-rules.example.toml:1-25 -->

