// AI-hint: Async Tokio TCP frame reader, writer, stream buffer manager, and network actor for mios-node.
// AI-related: src/mios-rs/mios-node/src/protocol.rs, src/mios-rs/mios-node/src/lib.rs, tests/test-node-async-net.py
//! MiOS Async TCP Frame Reader, Writer & Network Actor
//!
//! Implements high-concurrency, asynchronous TCP stream framing over the 16-byte fixed binary header
//! wire protocol (Magic 0x4D49, Version 1, Opcode, NodeID, PayloadLen, CRC32).

use crate::protocol::{Frame, Header, HEADER_SIZE, MIOS_MAGIC, MIOS_VERSION};
use anyhow::{anyhow, Result};
use byteorder::{BigEndian, ByteOrder};
use crc32fast::Hasher;
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::{mpsc, RwLock};

pub const MAX_PAYLOAD_LEN: usize = 64 * 1024 * 1024; // 64 MB payload ceiling

/// Codec for reading and writing 16-byte framed packets asynchronously over Tokio streams.
pub struct AsyncFrameCodec;

impl AsyncFrameCodec {
    /// Reads a single complete frame from an asynchronous reader.
    /// Handles partial reads by looping until all header bytes and payload bytes are received.
    pub async fn read_frame<R: AsyncReadExt + Unpin>(reader: &mut R) -> Result<Frame> {
        let mut header_buf = [0u8; HEADER_SIZE];
        reader.read_exact(&mut header_buf).await.map_err(|e| {
            anyhow!(
                "Failed to read frame header ({} bytes expected): {}",
                HEADER_SIZE,
                e
            )
        })?;

        let header = Header::decode(&header_buf)?;

        if (header.payload_len as usize) > MAX_PAYLOAD_LEN {
            return Err(anyhow!(
                "Payload length {} exceeds maximum allowed ceiling {}",
                header.payload_len,
                MAX_PAYLOAD_LEN
            ));
        }

        let mut payload = vec![0u8; header.payload_len as usize];
        if !payload.is_empty() {
            reader.read_exact(&mut payload).await.map_err(|e| {
                anyhow!(
                    "Failed to read frame payload ({} bytes expected): {}",
                    header.payload_len,
                    e
                )
            })?;
        }

        let mut hasher = Hasher::new();
        hasher.update(&payload);
        let actual_checksum = hasher.finalize();

        if actual_checksum != header.checksum {
            return Err(anyhow!(
                "CRC32 mismatch: expected 0x{:08X}, got 0x{:08X}",
                header.checksum,
                actual_checksum
            ));
        }

        Ok(Frame { header, payload })
    }

    /// Serializes and writes a complete frame asynchronously to a writer, then flushes.
    pub async fn write_frame<W: AsyncWriteExt + Unpin>(
        writer: &mut W,
        frame: &Frame,
    ) -> Result<()> {
        let encoded = frame.encode()?;
        writer
            .write_all(&encoded)
            .await
            .map_err(|e| anyhow!("Failed to write frame ({} bytes): {}", encoded.len(), e))?;
        writer
            .flush()
            .await
            .map_err(|e| anyhow!("Failed to flush writer after frame output: {}", e))?;
        Ok(())
    }
}

/// In-memory stream buffer for accumulating chunked TCP streams and extracting complete frames.
#[derive(Debug, Default, Clone)]
pub struct FrameStreamBuffer {
    buffer: Vec<u8>,
}

impl FrameStreamBuffer {
    pub fn new() -> Self {
        Self {
            buffer: Vec::with_capacity(4096),
        }
    }

    /// Feeds incoming raw byte chunks into the stream buffer.
    pub fn feed(&mut self, data: &[u8]) {
        self.buffer.extend_from_slice(data);
    }

    /// Current unparsed bytes in buffer.
    pub fn len(&self) -> usize {
        self.buffer.len()
    }

    pub fn is_empty(&self) -> bool {
        self.buffer.is_empty()
    }

    /// Attempts to parse and pop the next complete Frame from the buffer.
    /// Returns:
    /// - `Ok(Some(Frame))` if a complete, valid frame was extracted.
    /// - `Ok(None)` if more bytes are needed.
    /// - `Err(e)` if header or CRC32 validation fails.
    pub fn try_pop_frame(&mut self) -> Result<Option<Frame>> {
        if self.buffer.len() < HEADER_SIZE {
            return Ok(None);
        }

        // Validate magic before consuming
        let magic = BigEndian::read_u16(&self.buffer[0..2]);
        if magic != MIOS_MAGIC {
            return Err(anyhow!("Invalid MiOS magic: 0x{:04X}", magic));
        }

        let version = self.buffer[2];
        if version != MIOS_VERSION {
            return Err(anyhow!("Unsupported MiOS protocol version: {}", version));
        }

        let payload_len = BigEndian::read_u32(&self.buffer[8..12]) as usize;
        if payload_len > MAX_PAYLOAD_LEN {
            return Err(anyhow!(
                "Payload length {} exceeds maximum allowed ceiling {}",
                payload_len,
                MAX_PAYLOAD_LEN
            ));
        }

        let total_frame_len = HEADER_SIZE + payload_len;
        if self.buffer.len() < total_frame_len {
            // Need more bytes
            return Ok(None);
        }

        // We have enough bytes: decode frame
        let frame_bytes: Vec<u8> = self.buffer.drain(0..total_frame_len).collect();
        let frame = Frame::decode(&frame_bytes)?;
        Ok(Some(frame))
    }

    /// Clears any residual data in the buffer.
    pub fn clear(&mut self) {
        self.buffer.clear();
    }
}

/// Message dispatched to or from the Network Actor.
#[derive(Debug, Clone)]
pub struct NetMessage {
    pub frame: Frame,
    pub peer_addr: SocketAddr,
}

/// Asynchronous TCP Frame Actor for mios-node.
/// Manages incoming listener connections, per-peer read/write loops, and channel multiplexing.
pub struct NetActor {
    pub node_id: u32,
    pub bind_addr: SocketAddr,
    pub tx_incoming: mpsc::Sender<NetMessage>,
    pub peer_writers: Arc<RwLock<HashMap<SocketAddr, mpsc::Sender<Frame>>>>,
}

impl NetActor {
    pub fn new(node_id: u32, bind_addr: SocketAddr, tx_incoming: mpsc::Sender<NetMessage>) -> Self {
        Self {
            node_id,
            bind_addr,
            tx_incoming,
            peer_writers: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Starts the TCP listener and accepts incoming connections until cancelled.
    pub async fn run(&self, rx_outbound: Option<mpsc::Receiver<NetMessage>>) -> Result<()> {
        let listener = TcpListener::bind(self.bind_addr)
            .await
            .map_err(|e| anyhow!("Failed to bind TCP listener on {}: {}", self.bind_addr, e))?;

        let peer_writers = self.peer_writers.clone();

        // Spawn outbound routing task if rx_outbound is provided
        if let Some(mut rx) = rx_outbound {
            let writers_clone = peer_writers.clone();
            tokio::spawn(async move {
                while let Some(msg) = rx.recv().await {
                    let writers = writers_clone.read().await;
                    if let Some(tx) = writers.get(&msg.peer_addr) {
                        let _ = tx.send(msg.frame).await;
                    }
                }
            });
        }

        loop {
            let (stream, peer_addr) = listener.accept().await?;
            let tx_in = self.tx_incoming.clone();
            let writers = peer_writers.clone();

            let (tx_peer_out, rx_peer_out) = mpsc::channel::<Frame>(64);
            {
                let mut w = writers.write().await;
                w.insert(peer_addr, tx_peer_out);
            }

            tokio::spawn(async move {
                let _ = Self::handle_connection(stream, peer_addr, tx_in, rx_peer_out).await;
                let mut w = writers.write().await;
                w.remove(&peer_addr);
            });
        }
    }

    /// Handles a single bidirectional framed TCP connection.
    async fn handle_connection(
        stream: TcpStream,
        peer_addr: SocketAddr,
        tx_incoming: mpsc::Sender<NetMessage>,
        mut rx_outbound: mpsc::Receiver<Frame>,
    ) -> Result<()> {
        let (mut reader, mut writer) = stream.into_split();

        // Read loop task
        let tx_in_clone = tx_incoming.clone();
        let read_task = tokio::spawn(async move {
            while let Ok(frame) = AsyncFrameCodec::read_frame(&mut reader).await {
                let msg = NetMessage { frame, peer_addr };
                if tx_in_clone.send(msg).await.is_err() {
                    break;
                }
            }
        });

        // Write loop task
        let write_task = tokio::spawn(async move {
            while let Some(frame) = rx_outbound.recv().await {
                if AsyncFrameCodec::write_frame(&mut writer, &frame)
                    .await
                    .is_err()
                {
                    break;
                }
            }
        });

        tokio::select! {
            _ = read_task => {},
            _ = write_task => {},
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::protocol::MessageType;
    use tokio::io::duplex;

    #[tokio::test]
    async fn test_async_frame_codec_roundtrip() {
        let (mut client, mut server) = duplex(1024);

        let frame = Frame::new(
            MessageType::Heartbeat,
            101,
            b"{\"uptime_secs\":120}".to_vec(),
        );

        let send_handle = tokio::spawn(async move {
            AsyncFrameCodec::write_frame(&mut client, &frame)
                .await
                .unwrap();
        });

        let recv_handle =
            tokio::spawn(async move { AsyncFrameCodec::read_frame(&mut server).await.unwrap() });

        send_handle.await.unwrap();
        let received = recv_handle.await.unwrap();

        assert_eq!(received.header.node_id, 101);
        assert_eq!(received.header.msg_type, MessageType::Heartbeat);
        assert_eq!(received.payload, b"{\"uptime_secs\":120}");
    }

    #[tokio::test]
    async fn test_stream_buffer_chunked_feeding() {
        let mut buf = FrameStreamBuffer::new();

        let frame1 = Frame::new(MessageType::TaskOffload, 42, b"TASK_CHUNK_1".to_vec());
        let frame2 = Frame::new(MessageType::StateSync, 42, b"STATE_CHUNK_2".to_vec());

        let mut raw = frame1.encode().unwrap();
        raw.extend_from_slice(&frame2.encode().unwrap());

        // Feed byte-by-byte
        let mut popped = Vec::new();
        for byte in raw {
            buf.feed(&[byte]);
            while let Ok(Some(f)) = buf.try_pop_frame() {
                popped.push(f);
            }
        }

        assert_eq!(popped.len(), 2);
        assert_eq!(popped[0].header.msg_type, MessageType::TaskOffload);
        assert_eq!(popped[0].payload, b"TASK_CHUNK_1");
        assert_eq!(popped[1].header.msg_type, MessageType::StateSync);
        assert_eq!(popped[1].payload, b"STATE_CHUNK_2");
    }

    #[tokio::test]
    async fn test_stream_buffer_invalid_magic() {
        let mut buf = FrameStreamBuffer::new();
        let mut corrupted = [0u8; 16];
        corrupted[0] = 0xAA;
        corrupted[1] = 0xBB;
        buf.feed(&corrupted);

        let result = buf.try_pop_frame();
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("Invalid MiOS magic"));
    }
}
