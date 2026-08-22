<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit for the WS-9 out-of-process HITL policy arbiter -- runs /usr/libexec/mios/mios-policy-arbiter (a stdlib loopback HTTP service) as the mios-ai user, answering the agent-pipe's HITL arbiter client with allow/deny verdicts decided by mios_arbiter over the operator policy (MIOS_ARBITER_* from install.env). Idle/no-op until [ai].hitl_arbiter_url points at it; default policy is allow-all so enabling it changes nothing until a deny-list/block-tier is set.
AI-related: /usr/libexec/mios/mios-policy-arbiter, /usr/lib/mios/agent-pipe/mios_arbiter.py, /usr/lib/mios/agent-pipe/server.py, /usr/share/mios/mios.toml, mios-agent-pipe.service
/usr/lib/systemd/system/mios-policy-arbiter.service
'MiOS' out-of-process HITL policy arbiter (WS-9). A second, operator-ownable
opinion ON TOP of the in-process #62 HITL gate + WS-A9 PDP: the agent-pipe POSTs
each high-risk (tier >= [ai].hitl_threshold) action here for an allow/deny
verdict. Runs as mios-ai (least privilege); binds 127.0.0.1 only. The agent-pipe
consults it ONLY when [ai].hitl_arbiter_url is set -> idle otherwise.

<!-- mios-src:814396946772 from usr/lib/systemd/system/mios-policy-arbiter.service:1-8 -->

