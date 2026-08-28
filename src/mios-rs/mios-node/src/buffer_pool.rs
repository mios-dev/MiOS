// AI-hint: Zero-copy network buffer pooling for mios-node frames (T-393 / AGY-1991).
// AI-related: src/mios-rs/mios-node/src/net.rs, usr/libexec/mios/node/buffer_pool.py, tests/test-node-buffer-pool.py
//! MiOS Zero-Copy Network Buffer Pool
//!
//! Provides bucketed pre-allocation (Small 256B, Medium 4KB, Large 64KB, Huge 1MB),
//! RAII auto-recycling via drop guards, bounded memory footprint, zero-copy slicing,
//! and allocation telemetry.

use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};
use std::ops::{Deref, DerefMut};
use std::sync::{Arc, Mutex};

/// Buffer size tiers for bucketed memory allocation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum BucketTier {
    Small = 256,    // 256 B: 16B header, heartbeats, node announce, acks
    Medium = 4096,  // 4 KB: standard payloads, telemetry
    Large = 65536,  // 64 KB: CRDT state sync batches, medium chunks
    Huge = 1048576, // 1 MB: Wasm modules, native code payloads
}

impl BucketTier {
    pub fn capacity_bytes(&self) -> usize {
        *self as usize
    }

    /// Maximum number of buffers retained in the pool for this tier.
    pub fn max_pool_capacity(&self) -> usize {
        match self {
            BucketTier::Small => 256,
            BucketTier::Medium => 64,
            BucketTier::Large => 32,
            BucketTier::Huge => 8,
        }
    }

    /// Selects the smallest tier that fits the requested size.
    pub fn from_size(size: usize) -> Self {
        if size <= BucketTier::Small.capacity_bytes() {
            BucketTier::Small
        } else if size <= BucketTier::Medium.capacity_bytes() {
            BucketTier::Medium
        } else if size <= BucketTier::Large.capacity_bytes() {
            BucketTier::Large
        } else {
            BucketTier::Huge
        }
    }
}

/// Telemetry metrics for buffer pool performance.
#[derive(Debug, Default, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PoolStats {
    pub allocations: u64,
    pub recycles: u64,
    pub pool_hits: u64,
    pub pool_misses: u64,
    pub active_leased: u64,
}

/// Thread-safe bucketed memory buffer pool.
pub struct BufferPool {
    small_bucket: Mutex<Vec<Vec<u8>>>,
    medium_bucket: Mutex<Vec<Vec<u8>>>,
    large_bucket: Mutex<Vec<Vec<u8>>>,
    huge_bucket: Mutex<Vec<Vec<u8>>>,
    stats: Mutex<PoolStats>,
}

impl BufferPool {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            small_bucket: Mutex::new(Vec::with_capacity(BucketTier::Small.max_pool_capacity())),
            medium_bucket: Mutex::new(Vec::with_capacity(BucketTier::Medium.max_pool_capacity())),
            large_bucket: Mutex::new(Vec::with_capacity(BucketTier::Large.max_pool_capacity())),
            huge_bucket: Mutex::new(Vec::with_capacity(BucketTier::Huge.max_pool_capacity())),
            stats: Mutex::new(PoolStats::default()),
        })
    }

    /// Pre-populates the pool with a specified number of buffers per tier.
    pub fn preallocate(self: &Arc<Self>, small_count: usize, medium_count: usize) {
        let mut smalls = self.small_bucket.lock().unwrap();
        for _ in 0..small_count.min(BucketTier::Small.max_pool_capacity()) {
            smalls.push(Vec::with_capacity(BucketTier::Small.capacity_bytes()));
        }

        let mut mediums = self.medium_bucket.lock().unwrap();
        for _ in 0..medium_count.min(BucketTier::Medium.max_pool_capacity()) {
            mediums.push(Vec::with_capacity(BucketTier::Medium.capacity_bytes()));
        }
    }

    /// Leases a buffer suitable for the requested size hint.
    pub fn acquire(self: &Arc<Self>, size_hint: usize) -> PooledBuffer {
        let tier = BucketTier::from_size(size_hint);
        self.acquire_exact(tier)
    }

    /// Leases a buffer of the exact requested tier.
    pub fn acquire_exact(self: &Arc<Self>, tier: BucketTier) -> PooledBuffer {
        let bucket_guard = match tier {
            BucketTier::Small => &self.small_bucket,
            BucketTier::Medium => &self.medium_bucket,
            BucketTier::Large => &self.large_bucket,
            BucketTier::Huge => &self.huge_bucket,
        };

        let mut bucket = bucket_guard.lock().unwrap();
        let (buf, is_hit) = if let Some(reused) = bucket.pop() {
            (reused, true)
        } else {
            (Vec::with_capacity(tier.capacity_bytes()), false)
        };
        drop(bucket);

        let mut stats = self.stats.lock().unwrap();
        stats.allocations += 1;
        stats.active_leased += 1;
        if is_hit {
            stats.pool_hits += 1;
        } else {
            stats.pool_misses += 1;
        }
        drop(stats);

        PooledBuffer {
            buffer: Some(buf),
            tier,
            pool: Some(Arc::clone(self)),
        }
    }

    /// Internal recycling hook invoked by `PooledBuffer::drop`.
    pub(crate) fn recycle(&self, tier: BucketTier, mut buf: Vec<u8>) {
        buf.clear();
        let max_cap = tier.max_pool_capacity();

        let bucket_guard = match tier {
            BucketTier::Small => &self.small_bucket,
            BucketTier::Medium => &self.medium_bucket,
            BucketTier::Large => &self.large_bucket,
            BucketTier::Huge => &self.huge_bucket,
        };

        let mut bucket = bucket_guard.lock().unwrap();
        let was_recycled = if bucket.len() < max_cap {
            bucket.push(buf);
            true
        } else {
            false
        };
        drop(bucket);

        let mut stats = self.stats.lock().unwrap();
        if stats.active_leased > 0 {
            stats.active_leased -= 1;
        }
        if was_recycled {
            stats.recycles += 1;
        }
    }

    pub fn get_stats(&self) -> PoolStats {
        self.stats.lock().unwrap().clone()
    }

    pub fn bucket_depths(&self) -> (usize, usize, usize, usize) {
        (
            self.small_bucket.lock().unwrap().len(),
            self.medium_bucket.lock().unwrap().len(),
            self.large_bucket.lock().unwrap().len(),
            self.huge_bucket.lock().unwrap().len(),
        )
    }
}

/// RAII smart pointer wrapping a pooled buffer with zero-copy operations.
pub struct PooledBuffer {
    buffer: Option<Vec<u8>>,
    tier: BucketTier,
    pool: Option<Arc<BufferPool>>,
}

impl PooledBuffer {
    /// Creates an unpooled standalone buffer.
    pub fn standalone(tier: BucketTier) -> Self {
        Self {
            buffer: Some(Vec::with_capacity(tier.capacity_bytes())),
            tier,
            pool: None,
        }
    }

    pub fn tier(&self) -> BucketTier {
        self.tier
    }

    pub fn capacity(&self) -> usize {
        self.buffer.as_ref().map_or(0, |b| b.capacity())
    }

    pub fn len(&self) -> usize {
        self.buffer.as_ref().map_or(0, |b| b.len())
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    pub fn clear(&mut self) {
        if let Some(buf) = self.buffer.as_mut() {
            buf.clear();
        }
    }

    pub fn extend_from_slice(&mut self, slice: &[u8]) {
        if let Some(buf) = self.buffer.as_mut() {
            buf.extend_from_slice(slice);
        }
    }

    pub fn as_slice(&self) -> &[u8] {
        self.buffer.as_ref().map_or(&[], |b| b.as_slice())
    }

    pub fn as_mut_slice(&mut self) -> &mut [u8] {
        self.buffer.as_mut().map_or(&mut [], |b| b.as_mut_slice())
    }

    /// Zero-copy subslice inspection.
    pub fn slice(&self, start: usize, end: usize) -> Result<&[u8]> {
        let b = self
            .buffer
            .as_ref()
            .ok_or_else(|| anyhow!("Buffer already released"))?;
        if start > end || end > b.len() {
            return Err(anyhow!(
                "Slice range {}..{} out of bounds (len: {})",
                start,
                end,
                b.len()
            ));
        }
        Ok(&b[start..end])
    }

    /// Splits off the first `at` bytes, copying only what is necessary and keeping the rest.
    pub fn split_prefix(&mut self, at: usize) -> Result<Vec<u8>> {
        let b = self
            .buffer
            .as_mut()
            .ok_or_else(|| anyhow!("Buffer already released"))?;
        if at > b.len() {
            return Err(anyhow!(
                "Split prefix index {} exceeds buffer length {}",
                at,
                b.len()
            ));
        }
        let prefix = b[..at].to_vec();
        b.drain(..at);
        Ok(prefix)
    }

    /// Consumes the pooled buffer without recycling, returning the underlying Vec.
    pub fn into_vec(mut self) -> Vec<u8> {
        let pool = self.pool.take();
        if let Some(p) = pool {
            let mut stats = p.stats.lock().unwrap();
            if stats.active_leased > 0 {
                stats.active_leased -= 1;
            }
        }
        self.buffer.take().unwrap_or_default()
    }
}

impl Deref for PooledBuffer {
    type Target = [u8];

    fn deref(&self) -> &Self::Target {
        self.as_slice()
    }
}

impl DerefMut for PooledBuffer {
    fn deref_mut(&mut self) -> &mut Self::Target {
        self.as_mut_slice()
    }
}

impl Drop for PooledBuffer {
    fn drop(&mut self) {
        if let Some(buf) = self.buffer.take() {
            if let Some(pool) = self.pool.take() {
                pool.recycle(self.tier, buf);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bucket_tier_resolution() {
        assert_eq!(BucketTier::from_size(16), BucketTier::Small);
        assert_eq!(BucketTier::from_size(256), BucketTier::Small);
        assert_eq!(BucketTier::from_size(257), BucketTier::Medium);
        assert_eq!(BucketTier::from_size(4096), BucketTier::Medium);
        assert_eq!(BucketTier::from_size(4097), BucketTier::Large);
        assert_eq!(BucketTier::from_size(65536), BucketTier::Large);
        assert_eq!(BucketTier::from_size(65537), BucketTier::Huge);
    }

    #[test]
    fn test_raii_buffer_recycling() {
        let pool = BufferPool::new();

        {
            let mut buf1 = pool.acquire(100);
            assert_eq!(buf1.tier(), BucketTier::Small);
            buf1.extend_from_slice(b"12345678");
            assert_eq!(buf1.len(), 8);
            assert_eq!(buf1.as_slice(), b"12345678");

            let stats = pool.get_stats();
            assert_eq!(stats.allocations, 1);
            assert_eq!(stats.pool_misses, 1);
            assert_eq!(stats.active_leased, 1);
        } // buf1 dropped here -> recycled into small_bucket

        let stats = pool.get_stats();
        assert_eq!(stats.recycles, 1);
        assert_eq!(stats.active_leased, 0);

        // Next allocation should hit the recycled buffer
        {
            let mut buf2 = pool.acquire(100);
            assert_eq!(buf2.tier(), BucketTier::Small);
            assert_eq!(buf2.len(), 0); // Cleared upon recycling
            buf2.extend_from_slice(b"reused");

            let stats2 = pool.get_stats();
            assert_eq!(stats2.allocations, 2);
            assert_eq!(stats2.pool_hits, 1);
            assert_eq!(stats2.active_leased, 1);
        }
    }

    #[test]
    fn test_zero_copy_slicing_and_split() {
        let pool = BufferPool::new();
        let mut buf = pool.acquire(500); // Medium tier
        buf.extend_from_slice(b"HEADER_16BYTES__PAYLOAD_BODY_DATA");

        let sub = buf.slice(0, 16).unwrap();
        assert_eq!(sub, b"HEADER_16BYTES__");

        let payload_sub = buf.slice(16, buf.len()).unwrap();
        assert_eq!(payload_sub, b"PAYLOAD_BODY_DATA");

        let prefix = buf.split_prefix(16).unwrap();
        assert_eq!(prefix, b"HEADER_16BYTES__");
        assert_eq!(buf.as_slice(), b"PAYLOAD_BODY_DATA");
    }
}
