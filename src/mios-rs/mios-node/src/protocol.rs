//! MiOS Binary Wire Protocol Specification & Framing Engine
//! Header Format (16 Bytes Fixed, Big-Endian Network Byte Order):
//!
//! +-------------------------------------------------------------------+
//! | Magic (2B: 0x4D 0x49) | Ver (1B) | MsgType (1B) | NodeID (4B: u32) |
//! +-------------------------------------------------------------------+
//! | PayloadLen (4B: u32)             | Checksum (4B: u32 CRC32)       |
//! +-------------------------------------------------------------------+

use anyhow::{anyhow, Result};
use byteorder::{BigEndian, ByteOrder};
use crc32fast::Hasher;
use serde::{Deserialize, Serialize};

pub const MIOS_MAGIC: u16 = 0x4D49; // 'MI'
pub const MIOS_VERSION: u8 = 0x01;
pub const HEADER_SIZE: usize = 16;

#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MessageType {
    Heartbeat = 0x01,
    NodeAnnounce = 0x02,
    TaskOffload = 0x03,
    TaskResult = 0x04,
    StateSync = 0x05,
    StateAck = 0x06,
    Error = 0x07,
}

impl TryFrom<u8> for MessageType {
    type Error = anyhow::Error;

    fn try_from(value: u8) -> std::result::Result<Self, anyhow::Error> {
        match value {
            0x01 => Ok(MessageType::Heartbeat),
            0x02 => Ok(MessageType::NodeAnnounce),
            0x03 => Ok(MessageType::TaskOffload),
            0x04 => Ok(MessageType::TaskResult),
            0x05 => Ok(MessageType::StateSync),
            0x06 => Ok(MessageType::StateAck),
            0x07 => Ok(MessageType::Error),
            _ => Err(anyhow!("Unknown MiOS message opcode: 0x{:02X}", value)),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Header {
    pub magic: u16,
    pub version: u8,
    pub msg_type: MessageType,
    pub node_id: u32,
    pub payload_len: u32,
    pub checksum: u32,
}

impl Header {
    pub fn new(msg_type: MessageType, node_id: u32, payload_len: u32, checksum: u32) -> Self {
        Self {
            magic: MIOS_MAGIC,
            version: MIOS_VERSION,
            msg_type,
            node_id,
            payload_len,
            checksum,
        }
    }

    pub fn encode(&self, buf: &mut [u8]) -> Result<()> {
        if buf.len() < HEADER_SIZE {
            return Err(anyhow!("Buffer too small for MiOS header"));
        }
        BigEndian::write_u16(&mut buf[0..2], self.magic);
        buf[2] = self.version;
        buf[3] = self.msg_type as u8;
        BigEndian::write_u32(&mut buf[4..8], self.node_id);
        BigEndian::write_u32(&mut buf[8..12], self.payload_len);
        BigEndian::write_u32(&mut buf[12..16], self.checksum);
        Ok(())
    }

    pub fn decode(buf: &[u8]) -> Result<Self> {
        if buf.len() < HEADER_SIZE {
            return Err(anyhow!("Buffer too small for MiOS header decode"));
        }
        let magic = BigEndian::read_u16(&buf[0..2]);
        if magic != MIOS_MAGIC {
            return Err(anyhow!("Invalid MiOS magic: 0x{:04X}", magic));
        }
        let version = buf[2];
        if version != MIOS_VERSION {
            return Err(anyhow!("Unsupported MiOS protocol version: {}", version));
        }
        let msg_type = MessageType::try_from(buf[3])?;
        let node_id = BigEndian::read_u32(&buf[4..8]);
        let payload_len = BigEndian::read_u32(&buf[8..12]);
        let checksum = BigEndian::read_u32(&buf[12..16]);

        Ok(Self {
            magic,
            version,
            msg_type,
            node_id,
            payload_len,
            checksum,
        })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Frame {
    pub header: Header,
    pub payload: Vec<u8>,
}

impl Frame {
    pub fn new(msg_type: MessageType, node_id: u32, payload: Vec<u8>) -> Self {
        let mut hasher = Hasher::new();
        hasher.update(&payload);
        let checksum = hasher.finalize();

        let header = Header::new(msg_type, node_id, payload.len() as u32, checksum);
        Self { header, payload }
    }

    pub fn encode(&self) -> Result<Vec<u8>> {
        let total_len = HEADER_SIZE + self.payload.len();
        let mut buf = vec![0u8; total_len];
        self.header.encode(&mut buf[0..HEADER_SIZE])?;
        buf[HEADER_SIZE..].copy_from_slice(&self.payload);
        Ok(buf)
    }

    pub fn decode(buf: &[u8]) -> Result<Self> {
        let header = Header::decode(buf)?;
        let expected_end = HEADER_SIZE + header.payload_len as usize;
        if buf.len() < expected_end {
            return Err(anyhow!(
                "Incomplete payload: expected {} bytes, got {}",
                header.payload_len,
                buf.len() - HEADER_SIZE
            ));
        }
        let payload = buf[HEADER_SIZE..expected_end].to_vec();

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

        Ok(Self { header, payload })
    }
}

// Payload structs
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HeartbeatPayload {
    pub uptime_secs: u64,
    pub cpu_load_pct: u8,
    pub mem_available_kb: u32,
    pub active_tasks: u16,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskOffloadPayload {
    pub task_id: u64,
    pub tier: u8, // 1 = Wasm, 2 = Native
    pub target_arch: u16, // 0 = Agnostic, 1 = x86_64, 2 = AArch64, 3 = RISC-V 64
    pub memory_limit_bytes: u32,
    pub execution_timeout_ms: u32,
    pub code_bytes: Vec<u8>,
    pub input_data: Vec<u8>,
    pub signature: Option<Vec<u8>>,   // Ed25519 signature for Tier 2 native binaries
    pub public_key: Option<Vec<u8>>,  // Ed25519 public key
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskResultPayload {
    pub task_id: u64,
    pub success: bool,
    pub exit_code: i32,
    pub output_data: Vec<u8>,
    pub error_msg: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateSyncPayload {
    pub vector_clock: crate::state_sync::VectorClock,
    pub mutations: Vec<crate::state_sync::StateElement>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateAckPayload {
    pub node_id: u32,
    pub applied_count: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_header_encode_decode() {
        let header = Header::new(MessageType::Heartbeat, 101, 64, 0x12345678);
        let mut buf = [0u8; HEADER_SIZE];
        header.encode(&mut buf).unwrap();

        let decoded = Header::decode(&buf).unwrap();
        assert_eq!(header, decoded);
    }

    #[test]
    fn test_frame_encode_decode_with_crc() {
        let payload_data = b"Hello MiOS edge node protocol!".to_vec();
        let frame = Frame::new(MessageType::TaskOffload, 42, payload_data.clone());

        let encoded = frame.encode().unwrap();
        let decoded = Frame::decode(&encoded).unwrap();

        assert_eq!(decoded.header.node_id, 42);
        assert_eq!(decoded.header.msg_type, MessageType::TaskOffload);
        assert_eq!(decoded.payload, payload_data);
    }

    #[test]
    fn test_crc_corruption_detection() {
        let payload_data = b"Sensitive task data".to_vec();
        let frame = Frame::new(MessageType::TaskOffload, 1, payload_data);

        let mut encoded = frame.encode().unwrap();
        let last_idx = encoded.len() - 1;
        encoded[last_idx] ^= 0xFF;

        let result = Frame::decode(&encoded);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("CRC32 mismatch"));
    }
}
