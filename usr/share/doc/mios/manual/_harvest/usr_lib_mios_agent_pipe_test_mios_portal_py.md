<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone unit test for...

!/usr/bin/env python3
AI-hint: Standalone unit test for mios_portal (refactor R10) -- proves the moved portal logic works with stubs and no network/DB. Asserts: the signed-cookie auth round-trips (_portal_make_token -> _portal_token_ok true; a tampered/expired token false), _portal_authed honours the require-login flag, the dashboard stats/asset builders have the right shape (_host_stats reads /proc-style fields as a dict, _PORTAL_MANIFEST is valid PWA JSON with PNG icons, _read_portal_asset degrades to b"" when a file is absent), and the swarm probe (_portal_swarm_probe) returns the expected roster dict against a fake httpx client + injected _probe_auth_headers/_agent_lane (configure() DI). Pure stdlib + asyncio + unittest.mock.
AI-related: ./mios_portal.py, ./server.py, ./test_server_import.py
AI-functions: _FakeResp, _FakeClient, _FakeAsyncClient, _FakeWS, _ReqBody, _body, test_token_roundtrip, test_authed_flag, test_manifest_shape, test_read_asset_missing, test_host_stats_shape, test_swarm_probe, test_portal_stats_logic, test_portal_service_detail_logic, test_portal_swarm_logic, test_portal_term_ws_logic, test_portal_login_logic, test_portal_login_page_logic, test_portal_page_logic, main

<!-- mios-src:51f5404e0a81 from usr/lib/mios/agent-pipe/test_mios_portal.py:1-4 -->

