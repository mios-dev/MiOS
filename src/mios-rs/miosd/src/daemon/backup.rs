// AI-hint: Interval backup scheduler managing pgvector and config snapshots.
// AI-related: tests/test-backup-pgvector.py, usr/lib/systemd/system/mios-backup-pgvector.service

use super::state::BackupState;
use std::path::{Path, PathBuf};

pub struct BackupScheduler {
    interval_s: u64,
    last_run_ts: u64,
    backup_count: u32,
    state_file: PathBuf,
}

impl BackupScheduler {
    pub fn new(interval_s: u64) -> Self {
        let root = std::env::var("MIOS_ROOT").unwrap_or_else(|_| ".".to_string());
        let state_file = Path::new(&root).join("var/lib/mios/backup/last-backup.txt");
        Self::with_path(state_file, interval_s)
    }

    pub fn with_path(state_file: PathBuf, interval_s: u64) -> Self {
        Self {
            interval_s,
            last_run_ts: 0,
            backup_count: 0,
            state_file,
        }
    }

    pub fn tick(&mut self, current_ts: u64) -> BackupState {
        let mut status = "idle".to_string();

        if self.last_run_ts == 0 {
            // Check if on-disk sentinel exists
            if let Ok(content) = std::fs::read_to_string(&self.state_file) {
                if let Ok(ts) = content.trim().parse::<u64>() {
                    self.last_run_ts = ts;
                }
            }
            if self.last_run_ts == 0 {
                self.last_run_ts = current_ts;
            }
        }

        if current_ts >= self.last_run_ts.saturating_add(self.interval_s) {
            status = "completed".to_string();
            self.last_run_ts = current_ts;
            self.backup_count = self.backup_count.saturating_add(1);

            // Attempt to write sentinel
            if let Some(parent) = self.state_file.parent() {
                let _ = std::fs::create_dir_all(parent);
            }
            let _ = std::fs::write(&self.state_file, current_ts.to_string());
        }

        BackupState {
            last_backup_ts: self.last_run_ts,
            status,
            next_scheduled_ts: self.last_run_ts.saturating_add(self.interval_s),
            backup_count: self.backup_count,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_backup_scheduler_cadence() {
        let temp = tempfile::tempdir().expect("tempdir");
        let state_file = temp.path().join("last-backup.txt");
        let mut scheduler = BackupScheduler::with_path(state_file, 3600);
        let s1 = scheduler.tick(1000);
        assert_eq!(s1.last_backup_ts, 1000);
        assert_eq!(s1.next_scheduled_ts, 4600);

        let s2 = scheduler.tick(2000);
        assert_eq!(s2.last_backup_ts, 1000);
        assert_eq!(s2.status, "idle");

        let s3 = scheduler.tick(4700);
        assert_eq!(s3.last_backup_ts, 4700);
        assert_eq!(s3.status, "completed");
        assert_eq!(s3.backup_count, 1);
    }
}
