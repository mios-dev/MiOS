// AI-hint: Watchdog integration checking /dev/watchdog and logging hardware status.
// AI-related: usr/libexec/mios/mios-daemon, /dev/watchdog

use super::state::HardwareState;
use std::path::{Path, PathBuf};

pub struct HardwareMonitor {
    watchdog_dev: PathBuf,
    active: bool,
    last_ping_ts: u64,
}

impl HardwareMonitor {
    pub fn new(dev_path: Option<String>) -> Self {
        let watchdog_dev = PathBuf::from(dev_path.unwrap_or_else(|| "/dev/watchdog".to_string()));
        let active = watchdog_dev.exists();
        Self {
            watchdog_dev,
            active,
            last_ping_ts: 0,
        }
    }

    pub fn ping_and_sample(&mut self, current_ts: u64) -> HardwareState {
        let mut watchdog_active = self.active;
        if self.watchdog_dev.exists() {
            // Attempt to write heartbeat byte to /dev/watchdog
            if let Ok(mut f) = std::fs::OpenOptions::new().write(true).open(&self.watchdog_dev) {
                use std::io::Write;
                let _ = f.write_all(b"\0");
                let _ = f.flush();
                watchdog_active = true;
            }
        }
        self.last_ping_ts = current_ts;

        let (gpu_util, gpu_detected) = Self::sample_gpu();
        let iommu_enabled = Self::check_iommu();

        HardwareState {
            gpu_util_percent: gpu_util,
            gpu_detected,
            watchdog_active,
            iommu_enabled,
            last_watchdog_ping_ts: self.last_ping_ts,
        }
    }

    fn sample_gpu() -> (f32, bool) {
        // Best-effort check for NVIDIA or AMD GPU presence in /dev/dri or /dev/nvidia*
        let has_nvidia = Path::new("/dev/nvidia0").exists();
        let has_dri = Path::new("/dev/dri/card0").exists();
        let detected = has_nvidia || has_dri;
        (if detected { 5.0 } else { 0.0 }, detected)
    }

    fn check_iommu() -> bool {
        Path::new("/sys/kernel/iommu_groups").exists()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hardware_monitor_tick() {
        let mut monitor = HardwareMonitor::new(None);
        let state = monitor.ping_and_sample(1724688000);
        assert_eq!(state.last_watchdog_ping_ts, 1724688000);
    }
}
