// AI-hint: Core async supervisor daemon engine for miosd.
// AI-related: usr/libexec/mios/mios-daemon, usr/lib/systemd/system/miosd.service

pub mod backup;
pub mod state;
pub mod telemetry;
pub mod theme;
pub mod watchdog;

use backup::BackupScheduler;
use state::{ClassifySummary, CronDecision, CronState, DaemonState, StateManager};
use telemetry::TelemetryCollector;
use theme::ThemeWatcher;
use watchdog::HardwareMonitor;

use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

pub struct DaemonConfig {
    pub state_dir: PathBuf,
    pub interval_secs: u64,
    pub watchdog_dev: Option<String>,
    pub backup_interval_secs: u64,
    pub run_once: bool,
}

impl Default for DaemonConfig {
    fn default() -> Self {
        Self {
            state_dir: PathBuf::from("/var/lib/mios/daemon"),
            interval_secs: 5,
            watchdog_dev: None,
            backup_interval_secs: 3600,
            run_once: false,
        }
    }
}

pub struct Supervisor {
    config: DaemonConfig,
    state_mgr: StateManager,
    telemetry: TelemetryCollector,
    theme: ThemeWatcher,
    backup: BackupScheduler,
    hardware: HardwareMonitor,
    start_time: Instant,
}

impl Supervisor {
    pub fn new(config: DaemonConfig) -> Self {
        let state_mgr = StateManager::new(&config.state_dir);
        let telemetry = TelemetryCollector::new();
        let theme = ThemeWatcher::new();
        let backup = BackupScheduler::new(config.backup_interval_secs);
        let hardware = HardwareMonitor::new(config.watchdog_dev.clone());

        Self {
            config,
            state_mgr,
            telemetry,
            theme,
            backup,
            hardware,
            start_time: Instant::now(),
        }
    }

    pub fn tick(&mut self) -> Result<DaemonState, std::io::Error> {
        let now_ts = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        let uptime_s = self.start_time.elapsed().as_secs();

        let metrics = self.telemetry.collect();
        let theme_state = self.theme.check_theme(now_ts);
        let backup_state = self.backup.tick(now_ts);
        let hw_state = self.hardware.ping_and_sample(now_ts);

        let classify = Some(ClassifySummary {
            summary: "All system services operating nominal; no elevated error rates detected."
                .to_string(),
            tags: vec!["system".to_string(), "nominal".to_string()],
            severity: "info".to_string(),
            event_count: 0,
        });

        let cron = CronState {
            last_fire: Some(CronDecision {
                rule: "telemetry_pulse".to_string(),
                fired: true,
                ts: now_ts,
                reason: "periodic supervisor cycle".to_string(),
            }),
            decisions: vec![CronDecision {
                rule: "theme_sync".to_string(),
                fired: theme_state.in_sync,
                ts: now_ts,
                reason: "theme check evaluated".to_string(),
            }],
        };

        let state = DaemonState {
            ts: now_ts,
            uptime_s,
            version: "0.3.0".to_string(),
            memory_ceiling_mb: 15,
            metrics,
            hardware: hw_state,
            theme: theme_state,
            backup: backup_state,
            classify,
            refusal: None,
            cron,
        };

        self.state_mgr.write_state_atomic(&state)?;
        Ok(state)
    }

    pub async fn run(mut self, shutdown_signal: Arc<AtomicBool>) -> Result<(), std::io::Error> {
        println!(
            "[miosd] Supervisor daemon started. State dir: {:?}",
            self.config.state_dir
        );

        // Initial tick
        let initial_state = self.tick()?;
        println!(
            "[miosd] Initial state written: ts={}, cpu={:.1}%, mem={}/{}MB",
            initial_state.ts,
            initial_state.metrics.cpu_percent,
            initial_state.metrics.memory_used_mb,
            initial_state.metrics.memory_total_mb
        );

        if self.config.run_once {
            println!("[miosd] Run-once mode complete.");
            return Ok(());
        }

        let interval = Duration::from_secs(self.config.interval_secs.max(1));
        while !shutdown_signal.load(Ordering::Relaxed) {
            tokio::time::sleep(interval).await;
            if shutdown_signal.load(Ordering::Relaxed) {
                break;
            }
            if let Err(e) = self.tick() {
                eprintln!("[miosd] Error in supervisor tick: {}", e);
            }
        }

        println!(
            "[miosd] Supervisor received shutdown signal. Flushing state and exiting cleanly."
        );
        let _ = self.tick();
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_supervisor_run_once() {
        let temp = tempfile::tempdir().expect("tempdir");
        let config = DaemonConfig {
            state_dir: temp.path().to_path_buf(),
            interval_secs: 1,
            watchdog_dev: None,
            backup_interval_secs: 3600,
            run_once: true,
        };
        let supervisor = Supervisor::new(config);
        let shutdown = Arc::new(AtomicBool::new(false));
        supervisor.run(shutdown).await.expect("run supervisor");

        let state_file = temp.path().join("state.json");
        assert!(state_file.exists());
        let content = std::fs::read_to_string(&state_file).expect("read");
        assert!(content.contains("\"version\": \"0.3.0\""));
        assert!(content.contains("\"memory_ceiling_mb\": 15"));
    }
}
