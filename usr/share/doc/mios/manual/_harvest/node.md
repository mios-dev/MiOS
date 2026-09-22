<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: CRDT LWW-Element-Set and...

!/usr/bin/env python3
AI-hint: CRDT LWW-Element-Set and Vector Clock state synchronization engine for edge mesh nodes.
AI-related: src/mios-rs/mios-node/src/state_sync.rs, tests/test-node.py, usr/share/doc/mios/adr/0020-edge-node-mesh-protocol-and-dual-tier-execution.md

<!-- mios-src:d8cc52561817 from usr/libexec/mios/node/crdt.py:1-3 -->

### !/usr/bin/env python3 AI-hint: Ed25519 mutual...

!/usr/bin/env python3
AI-hint: Ed25519 mutual authentication, X25519 ECDH key exchange, HKDF-SHA256 key derivation, and ChaCha20-Poly1305 AEAD wire encryption.
AI-related: src/mios-rs/mios-node/src/crypto.rs, usr/libexec/mios/node/wire.py, tests/test-node-crypto-handshake.py
AI-doc: usr/share/doc/mios/manual/node.md

<!-- mios-src:b332595259fb from usr/libexec/mios/node/crypto.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Avahi/mDNS zero-conf mesh...

!/usr/bin/env python3
AI-hint: Avahi/mDNS zero-conf mesh discovery, node heartbeat monitor, 3-strike dead-peer eviction, and Ed25519 authentication handshake.
AI-related: src/mios-rs/mios-node/src/heartbeat.rs, src/mios-rs/mios-node/src/node.rs, tests/test-node-heartbeat-eviction.py, tests/test-node.py
AI-doc: usr/share/doc/mios/manual/node.md

<!-- mios-src:80f7d1cd529a from usr/libexec/mios/node/discovery.py:1-4 -->

### !/usr/bin/env python3 AI-hint: 16-byte fixed binary wire...

!/usr/bin/env python3
AI-hint: 16-byte fixed binary wire protocol encoder, decoder, and opcode dispatcher for mios-node.
AI-related: usr/share/doc/mios/adr/0020-edge-mesh-binary-wire-protocol-and-dual-tier-sandboxing.md, src/mios-rs/mios-node/src/protocol.rs
AI-doc: usr/share/doc/mios/manual/node.md

<!-- mios-src:7bb7c76dccc2 from usr/libexec/mios/node/mios-node-wire.py:1-4 -->

### AI-hint

AI-hint: MiOS system and orchestration module providing topology switch capabilities.
AI-related: mios-node, usr/libexec/mios/ai/mios_asr.py, gdm.service, pipewire.service, guacamole.service, k3s.service, ceph-mds.service, llama-rpc-server.service, cilium-bgp.service
AI-functions: __init__, transition_to, NodeProfile, DynamicTopologySwitcher

<!-- mios-src:e9b1f751ad00 from usr/libexec/mios/node/topology_switch.py:1-3 -->

### !/usr/bin/env python3 AI-hint: Tier-1 Wasm sandbox runtime...

!/usr/bin/env python3
AI-hint: Tier-1 Wasm sandbox runtime with fuel bounding, 64MB memory limit, and mios_sys_* host imports.
AI-related: src/mios-rs/mios-node/src/executor.rs, tests/test-node.py, usr/share/doc/mios/adr/0020-edge-node-mesh-protocol-and-dual-tier-execution.md

<!-- mios-src:f0157c1854c0 from usr/libexec/mios/node/wasm_sandbox.py:1-3 -->

### !/usr/bin/env python3 AI-hint: 16-byte fixed binary wire...

!/usr/bin/env python3
AI-hint: 16-byte fixed binary wire protocol encoder, decoder, async stream codec, and opcode dispatcher for mios-node.
AI-related: src/mios-rs/mios-node/src/net.rs, src/mios-rs/mios-node/src/protocol.rs, tests/test-node-async-net.py
AI-doc: usr/share/doc/mios/manual/node.md

<!-- mios-src:b6f0ef4b8832 from usr/libexec/mios/node/wire.py:1-4 -->
