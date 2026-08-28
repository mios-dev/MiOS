// AI-hint: Daemon state schema and atomic state writer for /var/lib/mios/daemon/state.json
// AI-related: usr/libexec/mios/mios-daemon, /var/lib/mios/daemon/state.json

use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::Write;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct TelemetryMetrics {
    pub cpu_percent: f32,
    pub memory_used_mb: u64,
    pub memory_total_mb: u64,
    pub memory_percent: f32,
    pub load_1m: f32,
    pub load_5m: f32,
    pub load_15m: f32,
    pub disk_used_gb: f32,
    pub disk_total_gb: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct HardwareState {
    pub gpu_util_percent: f32,
    pub gpu_detected: bool,
    pub watchdog_active: bool,
    pub iommu_enabled: bool,
    pub last_watchdog_ping_ts: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct ThemeState {
    pub current_theme: String,
    pub cursor_theme: String,
    pub last_sync_ts: u64,
    pub in_sync: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct BackupState {
    pub last_backup_ts: u64,
    pub status: String,
    pub next_scheduled_ts: u64,
    pub backup_count: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct ClassifySummary {
    pub summary: String,
    pub tags: Vec<String>,
    pub severity: String,
    pub event_count: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct RefusalSummary {
    pub phrase: String,
    pub model: String,
    pub ts: u64,
    pub service: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct CronDecision {
    pub rule: String,
    pub fired: bool,
    pub ts: u64,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct CronState {
    pub last_fire: Option<CronDecision>,
    pub decisions: Vec<CronDecision>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct DaemonState {
    pub ts: u64,
    pub uptime_s: u64,
    pub version: String,
    pub memory_ceiling_mb: u32,
    pub metrics: TelemetryMetrics,
    pub hardware: HardwareState,
    pub theme: ThemeState,
    pub backup: BackupState,
    pub classify: Option<ClassifySummary>,
    pub refusal: Option<RefusalSummary>,
    pub cron: CronState,
}

impl Default for DaemonState {
    fn default() -> Self {
        Self {
            ts: 0,
            uptime_s: 0,
            version: "0.3.0".to_string(),
            memory_ceiling_mb: 15,
            metrics: TelemetryMetrics::default(),
            hardware: HardwareState::default(),
            theme: ThemeState::default(),
            backup: BackupState::default(),
            classify: None,
            refusal: None,
            cron: CronState::default(),
        }
    }
}

pub struct StateManager {
    state_dir: PathBuf,
    state_file: PathBuf,
}

impl StateManager {
    pub fn new<P: AsRef<Path>>(dir: P) -> Self {
        let state_dir = dir.as_ref().to_path_buf();
        let state_file = state_dir.join("state.json");
        Self {
            state_dir,
            state_file,
        }
    }

    pub fn state_file_path(&self) -> &Path {
        &self.state_file
    }

    pub fn write_state_atomic(&self, state: &DaemonState) -> Result<(), std::io::Error> {
        if !self.state_dir.exists() {
            std::fs::create_dir_all(&self.state_dir)?;
        }
        let tmp_path = self.state_dir.join("state.json.tmp");
        let json_bytes = serde_json::to_vec_pretty(state)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;

        {
            let mut file = File::create(&tmp_path)?;
            file.write_all(&json_bytes)?;
            file.flush()?;
            file.sync_all()?;
        }

        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let perms = std::fs::Permissions::from_mode(0o644);
            let _ = std::fs::set_permissions(&tmp_path, perms);
        }

        std::fs::rename(&tmp_path, &self.state_file)?;
        Ok(())
    }

    pub fn read_state(&self) -> Result<DaemonState, std::io::Error> {
        let data = std::fs::read_to_string(&self.state_file)?;
        serde_json::from_str(&data)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_atomic_state_write_and_read() {
        let temp_dir = tempfile::tempdir().expect("tempdir");
        let manager = StateManager::new(temp_dir.path());

        let mut state = DaemonState {
            ts: 1724688000,
            uptime_s: 3600,
            ..Default::default()
        };
        state.metrics.cpu_percent = 12.5;
        state.metrics.memory_used_mb = 4096;
        state.metrics.memory_total_mb = 16384;
        state.metrics.memory_percent = 25.0;
        state.hardware.watchdog_active = true;

        manager.write_state_atomic(&state).expect("write atomic");
        assert!(manager.state_file_path().exists());

        let read_back = manager.read_state().expect("read back state");
        assert_eq!(read_back.ts, 1724688000);
        assert_eq!(read_back.metrics.cpu_percent, 12.5);
        assert_eq!(read_back.metrics.memory_percent, 25.0);
        assert!(read_back.hardware.watchdog_active);
    }
}
