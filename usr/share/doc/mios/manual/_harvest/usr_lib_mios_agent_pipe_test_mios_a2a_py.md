<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Stdlib unit test for the extracted A2A federation publish surface (mios_a2a). Injects lightweight stubs via configure() -- a fake FastAPI app, a one-agent registry, a one-verb catalog, a fake passport signer (no cryptography dependency), and a fake async HTTP client -- then asserts the AgentCard JSON shape + its A2A v1.0 JWS signature (RFC-7515 detached-JWS shape, and a real Ed25519 sign->verify round-trip with tamper-detection when python3-cryptography is present), the Open Agent Passport + AGNTCY-OASF manifest shapes, the A2A skill-directory projection, and the JSON-RPC 2.0 method dispatch (message/send round-trip, tasks/get not-found, unknown-method error) plus the principal-metadata gate. No network, no DB, no server import.
AI-related: ./mios_a2a.py, ./server.py

<!-- mios-src:a0252c7b8f54 from usr/lib/mios/agent-pipe/test_mios_a2a.py:1-2 -->

