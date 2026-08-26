// AI-hint: Dynamic CPU Core Pinning and Cgroup v2 limits controller for mios-node workers.
// AI-related: src/mios-rs/mios-node/src/node.rs, usr/libexec/mios/node/cgroups.py, tests/test-node-cgroups-pinning.py
//! MiOS Dynamic Worker CPU Affinity and Cgroup v2 Controller
//! Manages CPU core pinning, cgroup v2 quotas (cpu.max, memory.max), and enforces Core 0 system reservation.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AffinityPolicy {
    /// Dedicated exclusive CPU core(s) from worker pool
    Exclusive,
    /// Shared across all available worker cores
    Shared,
    /// Lowest priority execution on safe worker cores
    LowPriority,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct NodeResourceLimits {
    pub worker_cores: Vec<usize>,
    pub cpu_quota_pct: Option<u32>,
    pub cpu_period_us: u32,
    pub memory_max_bytes: Option<u64>,
    pub memory_high_bytes: Option<u64>,
    pub exclude_core_zero: bool,
    pub cgroup_path: String,
}

impl Default for NodeResourceLimits {
    fn default() -> Self {
        Self {
            worker_cores: Vec::new(),
            cpu_quota_pct: Some(80),
            cpu_period_us: 100_000, // 100ms default period
            memory_max_bytes: Some(512 * 1024 * 1024), // 512MB
            memory_high_bytes: Some(400 * 1024 * 1024), // 400MB throttle mark
            exclude_core_zero: true,
            cgroup_path: "/sys/fs/cgroup/mios.slice/worker".to_string(),
        }
    }
}

/// Strict Architectural Invariant: Filter out Core 0 on multi-core systems to guarantee kernel & I/O responsiveness.
pub fn filter_safe_worker_cores(
    total_system_cores: usize,
    requested_cores: Option<&[usize]>,
    exclude_core_zero: bool,
) -> Vec<usize> {
    let all_cores: Vec<usize> = (0..total_system_cores).collect();
    let candidate_cores = requested_cores.unwrap_or(&all_cores);

    if total_system_cores <= 1 || !exclude_core_zero {
        return candidate_cores
            .iter()
            .copied()
            .filter(|&c| c < total_system_cores)
            .collect();
    }

    // On multi-core systems with exclude_core_zero=true: strip Core 0
    candidate_cores
        .iter()
        .copied()
        .filter(|&c| c != 0 && c < total_system_cores)
        .collect()
}

/// Dynamic Worker Affinity Controller
#[derive(Debug, Clone)]
pub struct WorkerAffinityController {
    pub total_system_cores: usize,
    pub available_worker_cores: Vec<usize>,
    pub allocated_exclusive_cores: HashSet<usize>,
    pub limits: NodeResourceLimits,
}

impl WorkerAffinityController {
    pub fn new(total_system_cores: usize, limits: NodeResourceLimits) -> Self {
        let requested = if limits.worker_cores.is_empty() {
            None
        } else {
            Some(limits.worker_cores.as_slice())
        };

        let safe_cores = filter_safe_worker_cores(
            total_system_cores,
            requested,
            limits.exclude_core_zero,
        );

        Self {
            total_system_cores,
            available_worker_cores: safe_cores,
            allocated_exclusive_cores: HashSet::new(),
            limits,
        }
    }

    pub fn allocate_cores_for_policy(
        &mut self,
        policy: AffinityPolicy,
        requested_count: usize,
    ) -> Result<Vec<usize>, String> {
        if self.available_worker_cores.is_empty() {
            return Err("No worker cores available in safe pool".to_string());
        }

        match policy {
            AffinityPolicy::Exclusive => {
                let mut chosen = Vec::new();
                for &core in &self.available_worker_cores {
                    if !self.allocated_exclusive_cores.contains(&core) {
                        chosen.push(core);
                        if chosen.len() == requested_count {
                            break;
                        }
                    }
                }

                if chosen.len() < requested_count {
                    return Err(format!(
                        "Insufficient exclusive cores available: requested {}, found {}",
                        requested_count,
                        chosen.len()
                    ));
                }

                for &c in &chosen {
                    self.allocated_exclusive_cores.insert(c);
                }
                Ok(chosen)
            }
            AffinityPolicy::Shared => {
                // Shared policy uses all safe available worker cores without locking them exclusively
                Ok(self.available_worker_cores.clone())
            }
            AffinityPolicy::LowPriority => {
                // Low priority runs on the highest indexed safe worker core
                let last_core = *self.available_worker_cores.last().unwrap();
                Ok(vec![last_core])
            }
        }
    }

    pub fn release_cores(&mut self, cores: &[usize]) {
        for &c in cores {
            self.allocated_exclusive_cores.remove(&c);
        }
    }
}

/// Linux Cgroup v2 Controller Interface
pub struct CgroupV2Controller {
    pub cgroup_root: String,
}

impl Default for CgroupV2Controller {
    fn default() -> Self {
        Self::new("/sys/fs/cgroup/mios.slice/worker")
    }
}

impl CgroupV2Controller {
    pub fn new(cgroup_root: impl Into<String>) -> Self {
        Self {
            cgroup_root: cgroup_root.into(),
        }
    }

    /// Generates the cpu.max string: "quota_us period_us" or "max period_us"
    pub fn format_cpu_max(quota_pct: Option<u32>, period_us: u32) -> String {
        match quota_pct {
            Some(pct) => {
                let quota_us = (period_us as u64 * pct as u64) / 100;
                format!("{} {}", quota_us, period_us)
            }
            None => format!("max {}", period_us),
        }
    }

    /// Initializes and applies cgroup limits
    pub fn apply_limits(&self, limits: &NodeResourceLimits) -> Result<(), String> {
        let path = Path::new(&self.cgroup_root);
        if !path.exists() {
            if let Err(e) = fs::create_dir_all(path) {
                // In unprivileged containers or non-cgroup environments, fail gracefully
                return Err(format!("Cannot initialize cgroup dir {}: {}", self.cgroup_root, e));
            }
        }

        // 1. Write cpu.max
        let cpu_max_content = Self::format_cpu_max(limits.cpu_quota_pct, limits.cpu_period_us);
        let cpu_max_path = path.join("cpu.max");
        let _ = fs::write(cpu_max_path, cpu_max_content);

        // 2. Write memory.max
        if let Some(mem_max) = limits.memory_max_bytes {
            let mem_max_path = path.join("memory.max");
            let _ = fs::write(mem_max_path, mem_max.to_string());
        }

        // 3. Write memory.high
        if let Some(mem_high) = limits.memory_high_bytes {
            let mem_high_path = path.join("memory.high");
            let _ = fs::write(mem_high_path, mem_high.to_string());
        }

        Ok(())
    }

    /// Attaches thread or process ID to cgroup.procs / cgroup.threads
    pub fn attach_pid(&self, pid: u32) -> Result<(), String> {
        let procs_path = Path::new(&self.cgroup_root).join("cgroup.procs");
        if procs_path.exists() {
            fs::write(procs_path, pid.to_string())
                .map_err(|e| format!("Failed to attach pid {} to cgroup: {}", pid, e))
        } else {
            Err("cgroup.procs does not exist".to_string())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_core_zero_exclusion_invariant() {
        // Multi-core system (4 cores: 0, 1, 2, 3) -> safe worker cores should be [1, 2, 3]
        let safe_4 = filter_safe_worker_cores(4, None, true);
        assert_eq!(safe_4, vec![1, 2, 3]);
        assert!(!safe_4.contains(&0));

        // Single-core system (1 core: 0) -> safe worker cores should retain [0]
        let safe_1 = filter_safe_worker_cores(1, None, true);
        assert_eq!(safe_1, vec![0]);

        // Explicit requested cores [0, 2, 3] on 4 cores -> safe cores should be [2, 3]
        let requested = vec![0, 2, 3];
        let safe_req = filter_safe_worker_cores(4, Some(&requested), true);
        assert_eq!(safe_req, vec![2, 3]);
    }

    #[test]
    fn test_worker_affinity_allocation() {
        let limits = NodeResourceLimits::default();
        let mut controller = WorkerAffinityController::new(4, limits);
        assert_eq!(controller.available_worker_cores, vec![1, 2, 3]);

        // Allocate exclusive core
        let ex1 = controller
            .allocate_cores_for_policy(AffinityPolicy::Exclusive, 1)
            .unwrap();
        assert_eq!(ex1, vec![1]);

        let ex2 = controller
            .allocate_cores_for_policy(AffinityPolicy::Exclusive, 2)
            .unwrap();
        assert_eq!(ex2, vec![2, 3]);

        // Now exhausted
        let ex_fail = controller.allocate_cores_for_policy(AffinityPolicy::Exclusive, 1);
        assert!(ex_fail.is_err());

        // Release core 1 and re-allocate
        controller.release_cores(&[1]);
        let ex_realloc = controller
            .allocate_cores_for_policy(AffinityPolicy::Exclusive, 1)
            .unwrap();
        assert_eq!(ex_realloc, vec![1]);

        // Shared policy allocates all safe worker cores
        let shared = controller
            .allocate_cores_for_policy(AffinityPolicy::Shared, 0)
            .unwrap();
        assert_eq!(shared, vec![1, 2, 3]);

        // Low priority allocates highest index safe worker core
        let low = controller
            .allocate_cores_for_policy(AffinityPolicy::LowPriority, 0)
            .unwrap();
        assert_eq!(low, vec![3]);
    }

    #[test]
    fn test_cgroup_format_cpu_max() {
        let formatted_80 = CgroupV2Controller::format_cpu_max(Some(80), 100_000);
        assert_eq!(formatted_80, "80000 100000");

        let formatted_max = CgroupV2Controller::format_cpu_max(None, 100_000);
        assert_eq!(formatted_max, "max 100000");
    }
}
