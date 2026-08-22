<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-9 out-of-process policy-arbiter DECISION core. Pure-stdlib verdict logic the mios-policy-arbiter service uses to answer the agent-pipe's HITL arbiter client (_hitl_arbiter_verdict POSTs {verb,tier,args} -> {allow,reason}). decide() applies an explicit deny-list (always refuse), an allow-list (when set, only these auto-allow), and a risk-tier ceiling (verbs at/above arbiter_block_tier are refused) -- a SECOND, out-of-process opinion ON TOP of the in-process #62 HITL gate + WS-A9 PDP, so dangerous-verb policy can be changed/owned without redeploying the agent-pipe. The service wrapper owns HTTP + config load; this module is pure so it unit-tests in isolation.
AI-related: ./server.py, /usr/libexec/mios/mios-policy-arbiter, /usr/lib/systemd/system/mios-policy-arbiter.service, /usr/share/mios/mios.toml, ./mios_pdp.py, ./test_mios_arbiter.py
AI-functions: decide, class Verdict

<!-- mios-src:223118f27e80 from usr/lib/mios/agent-pipe/mios_pipe/access/arbiter.py:1-3 -->

