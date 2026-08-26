<!-- AI-hint: Manual pages distilled from the source comments of node, sanitized, each passage anchored to the comment it came from. -->

# node

### Compacts tombstone entries older than `ttl_s`. Strict...

Compacts tombstone entries older than `ttl_s`.
        Strict invariant: Never purges fresh tombstones within the TTL horizon or active keys.

<!-- mios-src:3e1775ef1679 from usr/libexec/mios/node/crdt.py:179-182 -->

### MiOS Node Cryptographic Handshake & Wire AEAD Encryption...

MiOS Node Cryptographic Handshake & Wire AEAD Encryption Engine (T-388 / AGY-1986).
Provides mutual Ed25519 identity verification, X25519 ephemeral Diffie-Hellman key exchange,
HKDF-SHA256 session key derivation, and ChaCha20-Poly1305 authenticated symmetric payload encryption.

<!-- mios-src:f494bf02e58f from usr/libexec/mios/node/crypto.py:5-9 -->

### MiOS Edge Node Mesh Discovery, Heartbeat Monitor &...

MiOS Edge Node Mesh Discovery, Heartbeat Monitor & Dead-Peer Eviction Engine (T-387 / AGY-1985).
Manages zero-conf peer announcements, periodic 5s heartbeats, 3-strike dead peer detection (15s eviction threshold),
degraded state transitions, routing table pruning, and eviction event dispatching.

<!-- mios-src:d5aa1dd418b8 from usr/libexec/mios/node/discovery.py:5-9 -->

### WS-NODE

WS-NODE: Edge Micro-Mesh 16-Byte Fixed Binary Wire Protocol Engine.
Provides byte-for-byte wire compatibility with the Rust mios-node runtime.

Header Format (16 Bytes Fixed, Big-Endian Network Byte Order):
+-------------------------------------------------------------------+
| Magic (2B: 0x4D 0x49) | Ver (1B) | Opcode (1B) | NodeID (4B: u32) |
+-------------------------------------------------------------------+
| PayloadLen (4B: u32)             | Checksum (4B: u32 CRC32)       |
+-------------------------------------------------------------------+

<!-- mios-src:81a5422c9ae0 from usr/libexec/mios/node/mios-node-wire.py:5-15 -->

### WS-NODE

WS-NODE: Edge Micro-Mesh 16-Byte Fixed Binary Wire Protocol & Async TCP Stream Engine.
Provides byte-for-byte wire compatibility with the Rust mios-node runtime (T-386 / AGY-1984).

Header Format (16 Bytes Fixed, Big-Endian Network Byte Order):
+-------------------------------------------------------------------+
| Magic (2B: 0x4D 0x49) | Ver (1B) | Opcode (1B) | NodeID (4B: u32) |
+-------------------------------------------------------------------+
| PayloadLen (4B: u32)             | Checksum (4B: u32 CRC32)       |
+-------------------------------------------------------------------+

<!-- mios-src:c20a378cf0d7 from usr/libexec/mios/node/wire.py:5-15 -->
### Strict Architectural Invariant

Strict Architectural Invariant:
    On multi-core systems, strips Core 0 to reserve it for kernel interrupts and system scheduling.
    On single-core systems, Core 0 is retained.

<!-- mios-src:3386c02b7254 from usr/libexec/mios/node/cgroups.py:49-53 -->
