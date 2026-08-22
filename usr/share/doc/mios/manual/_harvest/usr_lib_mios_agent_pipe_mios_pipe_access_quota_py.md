<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-6 per-user quota + rate-limit core. Pure-stdlib tracker modelled on the LiteLLM per-key budget + RPM pattern: each user gets a sliding-window request-rate cap (RPM) AND a per-window cost budget, checked before a dispatch so one principal can't exhaust the shared local lanes / a paid remote budget. check() prunes the window, denies on rate or budget, else records + allows. Pure (caller passes `now` -> deterministic); server.py keys it on the WS-A10 verified principal; snapshot()/restore() carry a principal's window across a restart, so an exhausted budget is not refilled by a bootc upgrade. Per-user isolation; limits<=0 disable a dimension (the single-user default = unlimited = behaviour-preserving).
AI-related: ./mios_smartroute.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_quota.py
AI-functions: check, spent, reset, snapshot, restore, class QuotaTracker, class QuotaVerdict

<!-- mios-src:6a7b13807cad from usr/lib/mios/agent-pipe/mios_pipe/access/quota.py:1-3 -->

