// AI-hint: CRDT LWW-Element-Set state sync engine with append-log persistence for mios-node.
// AI-related: src/mios-rs/mios-node/src/node.rs
//! MiOS Distributed Lock-Free State Synchronization Engine
//! Implements Last-Write-Wins Element-Set (LWW-Element-Set) CRDT, Vector Clock Causality,
//! and Disk-Backed Persistence (Snapshot & Append-Only Log)

use anyhow::{Context, Result};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct VectorClock {
    pub clocks: HashMap<u32, u64>,
}

impl VectorClock {
    pub fn new() -> Self {
        Self {
            clocks: HashMap::new(),
        }
    }

    pub fn increment(&mut self, node_id: u32) {
        let counter = self.clocks.entry(node_id).or_insert(0);
        *counter += 1;
    }

    pub fn merge(&mut self, other: &VectorClock) {
        for (&node_id, &remote_clock) in &other.clocks {
            let local_clock = self.clocks.entry(node_id).or_insert(0);
            *local_clock = (*local_clock).max(remote_clock);
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StateElement {
    pub key: String,
    pub value: Vec<u8>,
    pub timestamp_ns: u64,
    pub originating_node_id: u32,
    pub is_deleted: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateStore {
    pub node_id: u32,
    pub vector_clock: VectorClock,
    elements: HashMap<String, StateElement>,
    #[serde(skip)]
    persistence_path: Option<String>,
}

impl StateStore {
    pub fn new(node_id: u32) -> Self {
        Self {
            node_id,
            vector_clock: VectorClock::new(),
            elements: HashMap::new(),
            persistence_path: None,
        }
    }

    pub fn with_persistence(node_id: u32, path: impl Into<String>) -> Result<Self> {
        let path_str = path.into();
        let mut store = if Path::new(&path_str).exists() {
            Self::load_from_disk(&path_str, node_id).unwrap_or_else(|_| Self::new(node_id))
        } else {
            Self::new(node_id)
        };

        store.persistence_path = Some(path_str);
        Ok(store)
    }

    pub fn set(&mut self, key: String, value: Vec<u8>) {
        let timestamp_ns = Utc::now().timestamp_nanos_opt().unwrap_or(0) as u64;
        self.vector_clock.increment(self.node_id);

        let elem = StateElement {
            key: key.clone(),
            value,
            timestamp_ns,
            originating_node_id: self.node_id,
            is_deleted: false,
        };

        self.elements.insert(key, elem.clone());
        self.persist_element(&elem);
    }

    pub fn delete(&mut self, key: &str) {
        let timestamp_ns = Utc::now().timestamp_nanos_opt().unwrap_or(0) as u64;
        self.vector_clock.increment(self.node_id);

        let elem = if let Some(elem) = self.elements.get_mut(key) {
            elem.is_deleted = true;
            elem.timestamp_ns = timestamp_ns;
            elem.originating_node_id = self.node_id;
            elem.clone()
        } else {
            let elem = StateElement {
                key: key.to_string(),
                value: Vec::new(),
                timestamp_ns,
                originating_node_id: self.node_id,
                is_deleted: true,
            };
            self.elements.insert(key.to_string(), elem.clone());
            elem
        };

        self.persist_element(&elem);
    }

    pub fn get(&self, key: &str) -> Option<&Vec<u8>> {
        if let Some(elem) = self.elements.get(key) {
            if !elem.is_deleted {
                return Some(&elem.value);
            }
        }
        None
    }

    pub fn merge_element(&mut self, remote_elem: StateElement) -> bool {
        let key = remote_elem.key.clone();

        let updated = match self.elements.get(&key) {
            Some(local_elem) => {
                if remote_elem.timestamp_ns > local_elem.timestamp_ns {
                    self.elements.insert(key, remote_elem.clone());
                    true
                } else if remote_elem.timestamp_ns == local_elem.timestamp_ns {
                    if remote_elem.originating_node_id > local_elem.originating_node_id {
                        self.elements.insert(key, remote_elem.clone());
                        true
                    } else {
                        false
                    }
                } else {
                    false
                }
            }
            None => {
                self.elements.insert(key, remote_elem.clone());
                true
            }
        };

        if updated {
            self.persist_element(&remote_elem);
        }
        updated
    }

    pub fn merge_remote_store(
        &mut self,
        remote_clock: VectorClock,
        remote_elements: Vec<StateElement>,
    ) -> usize {
        self.vector_clock.merge(&remote_clock);
        let mut updated_count = 0;
        for elem in remote_elements {
            if self.merge_element(elem) {
                updated_count += 1;
            }
        }
        updated_count
    }

    pub fn active_elements(&self) -> Vec<StateElement> {
        self.elements
            .values()
            .filter(|e| !e.is_deleted)
            .cloned()
            .collect()
    }

    pub fn save_to_disk(&self, path: &str) -> Result<()> {
        if let Some(parent) = Path::new(path).parent() {
            fs::create_dir_all(parent)?;
        }
        let serialized = serde_json::to_string_pretty(self)?;
        fs::write(path, serialized).context("Failed to write state snapshot to disk")?;
        Ok(())
    }

    pub fn load_from_disk(path: &str, node_id: u32) -> Result<Self> {
        let content = fs::read_to_string(path)?;
        let mut store: StateStore = serde_json::from_str(&content)?;
        store.node_id = node_id;
        Ok(store)
    }

    fn persist_element(&self, elem: &StateElement) {
        if let Some(ref path_str) = self.persistence_path {
            let log_path = format!("{}.log", path_str);
            if let Ok(line) = serde_json::to_string(elem) {
                if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(&log_path) {
                    let _ = writeln!(file, "{}", line);
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;

    #[test]
    fn test_crdt_lww_convergence() {
        let mut node_a = StateStore::new(1);
        let mut node_b = StateStore::new(2);

        node_a.set("config.timeout".to_string(), b"30s".to_vec());

        node_b.merge_remote_store(node_a.vector_clock.clone(), node_a.active_elements());
        assert_eq!(node_b.get("config.timeout"), Some(&b"30s".to_vec()));

        node_b.set("config.timeout".to_string(), b"60s".to_vec());
        node_a.merge_remote_store(node_b.vector_clock.clone(), node_b.active_elements());
        assert_eq!(node_a.get("config.timeout"), Some(&b"60s".to_vec()));
    }

    #[test]
    fn test_crdt_tombstone_deletion() {
        let mut store = StateStore::new(101);
        store.set("temp.key".to_string(), b"val".to_vec());
        assert_eq!(store.get("temp.key"), Some(&b"val".to_vec()));

        store.delete("temp.key");
        assert_eq!(store.get("temp.key"), None);
        assert_eq!(store.active_elements().len(), 0);
    }

    #[test]
    fn test_state_store_with_persistence() {
        let tmp = NamedTempFile::new().unwrap();
        let path = tmp.path().to_str().unwrap().to_string();

        let mut store = StateStore::with_persistence(101, &path).unwrap();
        store.set("persistent.key".to_string(), b"data".to_vec());
        store.save_to_disk(&path).unwrap();

        let loaded = StateStore::load_from_disk(&path, 101).unwrap();
        assert_eq!(loaded.get("persistent.key"), Some(&b"data".to_vec()));
    }
}
