<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Provision the MiOS agent mTLS keypair + CA (#54)....

Provision the MiOS agent mTLS keypair + CA (#54).

Zero-trust federation needs peers to mutually authenticate. The ed25519 *message*
principal (#60) signs delegations; mTLS authenticates the *transport*. This mints
the PKI for that: a self-signed local CA + an agent leaf certificate (clientAuth +
serverAuth) signed by it. Peers trust each other by exchanging CA certs.

Trust model: self-signed local CA per node is the standard self-hosted default
(point [security.mtls] at an existing org CA to override). The enforcing half --
making the A2A endpoint REQUIRE client certs -- is reverse-proxy deployment
(MiOS terminates TLS at the proxy), documented in security/README.md; this tool
only provisions the credentials.

Idempotent: an existing CA is reused (so peer trust survives re-runs); the agent
leaf is re-issued. Requires `cryptography`. Run where the certs should live.

<!-- mios-src:1655be81ab25 from tools/provision-agent-mtls.py:3-18 -->
