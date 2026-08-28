// AI-hint: Task offloading priority queue with work-stealing scheduler for mios-node (T-392 / AGY-1990).
// AI-related: src/mios-rs/mios-node/src/executor.rs, usr/libexec/mios/node/scheduler.py, tests/test-node-scheduler.py
//! MiOS Task Offloading Priority Queue & Work-Stealing Scheduler
//!
//! Provides prioritized task ingestion (Critical, High, Normal, Low), lock-free/synchronized
//! per-worker deques with global injector, locality-aware work stealing, hardware pin invariants,
//! and network offload routing.

use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};

/// Priority levels for tasks. Lower integer values represent higher priority.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum TaskPriority {
    Critical = 0,
    High = 1,
    Normal = 2,
    Low = 3,
}

impl TaskPriority {
    pub fn as_u8(&self) -> u8 {
        *self as u8
    }

    pub fn from_u8(v: u8) -> Option<Self> {
        match v {
            0 => Some(TaskPriority::Critical),
            1 => Some(TaskPriority::High),
            2 => Some(TaskPriority::Normal),
            3 => Some(TaskPriority::Low),
            _ => None,
        }
    }
}

/// A schedulable task item with priority, sandboxing limits, hardware pin flags, and code payload.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TaskItem {
    pub task_id: u64,
    pub priority: TaskPriority,
    pub tier: u8,                    // 1 = Wasm, 2 = Native
    pub target_arch: u16,            // 0 = Agnostic, 1 = x86_64, 2 = aarch64, 3 = riscv64
    pub pinned_hardware: bool,       // Invariant: If true, prohibited from being stolen away
    pub pinned_node_id: Option<u32>, // Specific node requirement if pinned
    pub memory_limit_bytes: u32,
    pub execution_timeout_ms: u32,
    pub code_bytes: Vec<u8>,
    pub input_data: Vec<u8>,
    pub signature: Option<Vec<u8>>,
    pub public_key: Option<Vec<u8>>,
    pub submitted_at_ms: u64,
}

impl TaskItem {
    pub fn new(
        task_id: u64,
        priority: TaskPriority,
        tier: u8,
        code_bytes: Vec<u8>,
        input_data: Vec<u8>,
    ) -> Self {
        Self {
            task_id,
            priority,
            tier,
            target_arch: 0,
            pinned_hardware: false,
            pinned_node_id: None,
            memory_limit_bytes: 64 * 1024 * 1024,
            execution_timeout_ms: 5000,
            code_bytes,
            input_data,
            signature: None,
            public_key: None,
            submitted_at_ms: 0,
        }
    }

    /// Determines whether this task may be stolen by another worker or remote node.
    pub fn is_stealable(&self, requester_node_id: Option<u32>) -> bool {
        if self.pinned_hardware {
            return false;
        }
        if let Some(target) = self.pinned_node_id {
            if requester_node_id != Some(target) {
                return false;
            }
        }
        true
    }
}

/// Routing decision returned by the offload router.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ScheduledTarget {
    Local,
    Offload(u32),
    Rejected(String),
}

/// Per-worker prioritized task deques.
#[derive(Debug, Default)]
pub struct WorkerQueue {
    critical: VecDeque<TaskItem>,
    high: VecDeque<TaskItem>,
    normal: VecDeque<TaskItem>,
    low: VecDeque<TaskItem>,
}

impl WorkerQueue {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn push(&mut self, task: TaskItem) {
        match task.priority {
            TaskPriority::Critical => self.critical.push_back(task),
            TaskPriority::High => self.high.push_back(task),
            TaskPriority::Normal => self.normal.push_back(task),
            TaskPriority::Low => self.low.push_back(task),
        }
    }

    pub fn pop_local(&mut self) -> Option<TaskItem> {
        if let Some(task) = self.critical.pop_back() {
            return Some(task);
        }
        if let Some(task) = self.high.pop_back() {
            return Some(task);
        }
        if let Some(task) = self.normal.pop_back() {
            return Some(task);
        }
        self.low.pop_back()
    }

    /// Steals an unpinned task from this worker queue (FIFO for fairness).
    pub fn steal(&mut self, requester_node_id: Option<u32>) -> Option<TaskItem> {
        // Search Critical -> High -> Normal -> Low for a stealable task
        let find_and_remove = |deque: &mut VecDeque<TaskItem>| -> Option<TaskItem> {
            let idx = deque.iter().position(|t| t.is_stealable(requester_node_id));
            idx.and_then(|i| deque.remove(i))
        };

        if let Some(task) = find_and_remove(&mut self.critical) {
            return Some(task);
        }
        if let Some(task) = find_and_remove(&mut self.high) {
            return Some(task);
        }
        if let Some(task) = find_and_remove(&mut self.normal) {
            return Some(task);
        }
        find_and_remove(&mut self.low)
    }

    pub fn len(&self) -> usize {
        self.critical.len() + self.high.len() + self.normal.len() + self.low.len()
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

/// Global injector queue accessible to all workers and external task ingestion.
#[derive(Debug, Default)]
pub struct GlobalInjector {
    critical: VecDeque<TaskItem>,
    high: VecDeque<TaskItem>,
    normal: VecDeque<TaskItem>,
    low: VecDeque<TaskItem>,
}

impl GlobalInjector {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn push(&mut self, task: TaskItem) {
        match task.priority {
            TaskPriority::Critical => self.critical.push_back(task),
            TaskPriority::High => self.high.push_back(task),
            TaskPriority::Normal => self.normal.push_back(task),
            TaskPriority::Low => self.low.push_back(task),
        }
    }

    pub fn pop(&mut self) -> Option<TaskItem> {
        if let Some(task) = self.critical.pop_front() {
            return Some(task);
        }
        if let Some(task) = self.high.pop_front() {
            return Some(task);
        }
        if let Some(task) = self.normal.pop_front() {
            return Some(task);
        }
        self.low.pop_front()
    }

    pub fn steal(&mut self, requester_node_id: Option<u32>) -> Option<TaskItem> {
        let find_and_remove = |deque: &mut VecDeque<TaskItem>| -> Option<TaskItem> {
            let idx = deque.iter().position(|t| t.is_stealable(requester_node_id));
            idx.and_then(|i| deque.remove(i))
        };

        if let Some(task) = find_and_remove(&mut self.critical) {
            return Some(task);
        }
        if let Some(task) = find_and_remove(&mut self.high) {
            return Some(task);
        }
        if let Some(task) = find_and_remove(&mut self.normal) {
            return Some(task);
        }
        find_and_remove(&mut self.low)
    }

    pub fn len(&self) -> usize {
        self.critical.len() + self.high.len() + self.normal.len() + self.low.len()
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

/// Statistics snapshot for scheduler telemetry.
#[derive(Debug, Default, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SchedulerStats {
    pub tasks_ingested: u64,
    pub tasks_executed_local: u64,
    pub tasks_stolen_local: u64,
    pub tasks_stolen_remote: u64,
    pub tasks_offloaded: u64,
    pub tasks_rejected: u64,
}

/// Multi-worker priority work-stealing scheduler with hardware pin invariants.
pub struct WorkStealingScheduler {
    pub local_node_id: u32,
    pub num_workers: usize,
    workers: Vec<Arc<Mutex<WorkerQueue>>>,
    injector: Arc<Mutex<GlobalInjector>>,
    stats: Arc<Mutex<SchedulerStats>>,
}

impl WorkStealingScheduler {
    pub fn new(local_node_id: u32, num_workers: usize) -> Self {
        let actual_workers = if num_workers == 0 { 1 } else { num_workers };
        let mut workers = Vec::with_capacity(actual_workers);
        for _ in 0..actual_workers {
            workers.push(Arc::new(Mutex::new(WorkerQueue::new())));
        }

        Self {
            local_node_id,
            num_workers: actual_workers,
            workers,
            injector: Arc::new(Mutex::new(GlobalInjector::new())),
            stats: Arc::new(Mutex::new(SchedulerStats::default())),
        }
    }

    /// Submits a task into the scheduler.
    pub fn submit_task(&self, task: TaskItem, worker_hint: Option<usize>) -> ScheduledTarget {
        {
            let mut stats = self.stats.lock().unwrap();
            stats.tasks_ingested += 1;
        }

        if let Some(w_idx) = worker_hint {
            let target_w = w_idx % self.num_workers;
            self.workers[target_w].lock().unwrap().push(task);
        } else {
            self.injector.lock().unwrap().push(task);
        }

        ScheduledTarget::Local
    }

    /// Worker attempts to acquire the next task:
    /// 1. Local worker deque (Critical -> High -> Normal -> Low)
    /// 2. Global injector queue
    /// 3. Steal from other local workers
    pub fn pop_task(&self, worker_id: usize) -> Option<TaskItem> {
        let w_idx = worker_id % self.num_workers;

        // 1. Try local queue
        if let Some(task) = self.workers[w_idx].lock().unwrap().pop_local() {
            let mut stats = self.stats.lock().unwrap();
            stats.tasks_executed_local += 1;
            return Some(task);
        }

        // 2. Try global injector
        if let Some(task) = self.injector.lock().unwrap().pop() {
            let mut stats = self.stats.lock().unwrap();
            stats.tasks_executed_local += 1;
            return Some(task);
        }

        // 3. Try stealing from peer workers (round-robin)
        for i in 1..self.num_workers {
            let victim_idx = (w_idx + i) % self.num_workers;
            if let Some(stolen) = self.workers[victim_idx]
                .lock()
                .unwrap()
                .steal(Some(self.local_node_id))
            {
                let mut stats = self.stats.lock().unwrap();
                stats.tasks_stolen_local += 1;
                stats.tasks_executed_local += 1;
                return Some(stolen);
            }
        }

        None
    }

    /// Handles an incoming network steal request from a remote peer node.
    /// Strictly filters out pinned tasks!
    pub fn handle_remote_steal_request(
        &self,
        requester_node_id: u32,
        max_tasks: usize,
    ) -> Vec<TaskItem> {
        let mut stolen_tasks = Vec::new();

        // Try global injector first
        {
            let mut inj = self.injector.lock().unwrap();
            while stolen_tasks.len() < max_tasks {
                if let Some(task) = inj.steal(Some(requester_node_id)) {
                    stolen_tasks.push(task);
                } else {
                    break;
                }
            }
        }

        // Try workers if more tasks needed
        if stolen_tasks.len() < max_tasks {
            for worker in &self.workers {
                let mut w = worker.lock().unwrap();
                while stolen_tasks.len() < max_tasks {
                    if let Some(task) = w.steal(Some(requester_node_id)) {
                        stolen_tasks.push(task);
                    } else {
                        break;
                    }
                }
                if stolen_tasks.len() >= max_tasks {
                    break;
                }
            }
        }

        if !stolen_tasks.is_empty() {
            let mut stats = self.stats.lock().unwrap();
            stats.tasks_stolen_remote += stolen_tasks.len() as u64;
        }

        stolen_tasks
    }

    /// Evaluates whether a task should execute locally or be offloaded to a peer.
    pub fn route_task(&self, task: &TaskItem, peer_loads: &[(u32, usize)]) -> ScheduledTarget {
        // Invariant: Hardware pinned tasks MUST stay local
        if task.pinned_hardware {
            return ScheduledTarget::Local;
        }

        // Invariant: Specific pinned node ID requirement
        if let Some(target_node) = task.pinned_node_id {
            if target_node == self.local_node_id {
                return ScheduledTarget::Local;
            } else {
                return ScheduledTarget::Offload(target_node);
            }
        }

        let local_load = self.total_queue_depth();

        // If local load is low or peers are empty, run locally
        if local_load < 2 || peer_loads.is_empty() {
            return ScheduledTarget::Local;
        }

        // Find peer with lowest load
        if let Some(&(best_peer, best_load)) = peer_loads.iter().min_by_key(|(_, load)| *load) {
            if best_load + 2 <= local_load {
                let mut stats = self.stats.lock().unwrap();
                stats.tasks_offloaded += 1;
                return ScheduledTarget::Offload(best_peer);
            }
        }

        ScheduledTarget::Local
    }

    /// Calculates total queued tasks across all local worker queues and global injector.
    pub fn total_queue_depth(&self) -> usize {
        let mut count = self.injector.lock().unwrap().len();
        for w in &self.workers {
            count += w.lock().unwrap().len();
        }
        count
    }

    pub fn get_stats(&self) -> SchedulerStats {
        self.stats.lock().unwrap().clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_task_priority_ordering() {
        assert!(TaskPriority::Critical < TaskPriority::High);
        assert!(TaskPriority::High < TaskPriority::Normal);
        assert!(TaskPriority::Normal < TaskPriority::Low);
    }

    #[test]
    fn test_work_stealing_local_and_priority() {
        let scheduler = WorkStealingScheduler::new(101, 2);

        let task_low = TaskItem::new(1, TaskPriority::Low, 1, vec![1], vec![]);
        let task_crit = TaskItem::new(2, TaskPriority::Critical, 1, vec![2], vec![]);
        let task_normal = TaskItem::new(3, TaskPriority::Normal, 1, vec![3], vec![]);

        // Push all to worker 0
        scheduler.submit_task(task_low, Some(0));
        scheduler.submit_task(task_crit, Some(0));
        scheduler.submit_task(task_normal, Some(0));

        // Worker 0 pops in priority order: Critical -> Normal -> Low
        let p1 = scheduler.pop_task(0).unwrap();
        assert_eq!(p1.task_id, 2);
        assert_eq!(p1.priority, TaskPriority::Critical);

        let p2 = scheduler.pop_task(0).unwrap();
        assert_eq!(p2.task_id, 3);
        assert_eq!(p2.priority, TaskPriority::Normal);

        // Worker 1 steals the remaining Low task from worker 0
        let p3 = scheduler.pop_task(1).unwrap();
        assert_eq!(p3.task_id, 1);
        assert_eq!(p3.priority, TaskPriority::Low);

        let stats = scheduler.get_stats();
        assert_eq!(stats.tasks_stolen_local, 1);
        assert_eq!(stats.tasks_executed_local, 3);
    }

    #[test]
    fn test_pinned_hardware_task_cannot_be_stolen() {
        let scheduler = WorkStealingScheduler::new(101, 2);

        let mut pinned_task = TaskItem::new(99, TaskPriority::Critical, 1, vec![99], vec![]);
        pinned_task.pinned_hardware = true;

        scheduler.submit_task(pinned_task, Some(0));

        // Worker 1 cannot steal pinned task from worker 0
        assert!(scheduler.pop_task(1).is_none());

        // Remote peer 102 cannot steal pinned task either
        let remote_stolen = scheduler.handle_remote_steal_request(102, 5);
        assert!(remote_stolen.is_empty());

        // Worker 0 can execute it locally
        let local_task = scheduler.pop_task(0).unwrap();
        assert_eq!(local_task.task_id, 99);
    }

    #[test]
    fn test_router_hardware_pin_and_load_balance() {
        let scheduler = WorkStealingScheduler::new(101, 2);

        let mut pinned_task = TaskItem::new(10, TaskPriority::High, 1, vec![], vec![]);
        pinned_task.pinned_hardware = true;

        let peer_loads = vec![(201, 0), (202, 1)];

        // Pinned task must stay local regardless of peer loads
        assert_eq!(
            scheduler.route_task(&pinned_task, &peer_loads),
            ScheduledTarget::Local
        );

        // Fill local queue to trigger offload
        for i in 0..5 {
            let t = TaskItem::new(100 + i, TaskPriority::Normal, 1, vec![], vec![]);
            scheduler.submit_task(t, Some(0));
        }

        let unpinned_task = TaskItem::new(20, TaskPriority::Normal, 1, vec![], vec![]);
        let decision = scheduler.route_task(&unpinned_task, &peer_loads);
        assert_eq!(decision, ScheduledTarget::Offload(201));
    }
}
