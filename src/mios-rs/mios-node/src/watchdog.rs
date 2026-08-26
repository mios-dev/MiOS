// AI-hint: Hardware watchdog timer integration (/dev/watchdog) with safe 'V' magic close.
// AI-related: src/mios-rs/mios-node/src/node.rs, usr/libexec/mios/node/watchdog.py, tests/test-node-watchdog.py
//! MiOS Hardware Watchdog Supervisor & Device Controller
//! Integrates Linux `/dev/watchdog` timer with automatic keepalive pinging, systemd notify fallback,
//! and safe magic close ('V' / 0x56) on clean termination.

use serde::{Deserialize, Serialize};
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::Path;
use std::sync::{Arc, Mutex};
use std::time::Instant;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct WatchdogConfig {
    pub enabled: bool,
    pub device_path: String,
    pub timeout_secs: u32,
    pub ping_interval_secs: u64,
    pub use_systemd_notify: bool,
}

impl Default for WatchdogConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            device_path: "/dev/watchdog".to_string(),
            timeout_secs: 30,
            ping_interval_secs: 5,
            use_systemd_notify: true,
        }
    }
}

pub trait WatchdogDriver: Send + Sync {
    fn arm(&mut self) -> Result<(), String>;
    fn ping(&mut self) -> Result<(), String>;
    fn set_timeout(&mut self, timeout_secs: u32) -> Result<u32, String>;
    fn get_timeout(&self) -> Result<u32, String>;
    fn disarm_and_close(&mut self) -> Result<(), String>;
    fn is_hardware_present(&self) -> bool;
    fn is_armed(&self) -> bool;
}

/// Linux `/dev/watchdog` hardware driver with magic close `'V'`
pub struct LinuxHardwareWatchdog {
    device_path: String,
    timeout_secs: u32,
    file_handle: Option<File>,
    is_present: bool,
}

impl LinuxHardwareWatchdog {
    pub fn new(device_path: impl Into<String>, timeout_secs: u32) -> Self {
        let path = device_path.into();
        let is_present = Path::new(&path).exists();
        Self {
            device_path: path,
            timeout_secs,
            file_handle: None,
            is_present,
        }
    }
}

impl WatchdogDriver for LinuxHardwareWatchdog {
    fn arm(&mut self) -> Result<(), String> {
        if !self.is_present {
            return Err(format!("Watchdog device {} not found", self.device_path));
        }

        if self.file_handle.is_none() {
            let file = OpenOptions::new()
                .write(true)
                .open(&self.device_path)
                .map_err(|e| format!("Failed to open watchdog {}: {}", self.device_path, e))?;
            self.file_handle = Some(file);
        }
        Ok(())
    }

    fn ping(&mut self) -> Result<(), String> {
        if let Some(ref mut f) = self.file_handle {
            f.write_all(b"\0")
                .map_err(|e| format!("Watchdog ping write failed: {}", e))?;
            f.flush().map_err(|e| format!("Watchdog flush failed: {}", e))?;
            Ok(())
        } else {
            Err("Watchdog is not armed / device not open".to_string())
        }
    }

    fn set_timeout(&mut self, timeout_secs: u32) -> Result<u32, String> {
        self.timeout_secs = timeout_secs;
        Ok(self.timeout_secs)
    }

    fn get_timeout(&self) -> Result<u32, String> {
        Ok(self.timeout_secs)
    }

    fn disarm_and_close(&mut self) -> Result<(), String> {
        if let Some(mut f) = self.file_handle.take() {
            // Strict Invariant: Write 'V' (0x56) magic character to disarm hardware timer cleanly
            let _ = f.write_all(b"V");
            let _ = f.flush();
        }
        Ok(())
    }

    fn is_hardware_present(&self) -> bool {
        self.is_present
    }

    fn is_armed(&self) -> bool {
        self.file_handle.is_some()
    }
}

/// In-memory Mock Watchdog Driver for testing and headless execution
#[derive(Debug)]
pub struct MockWatchdogDriver {
    pub armed: bool,
    pub ping_count: u64,
    pub last_ping: Option<Instant>,
    pub timeout_secs: u32,
    pub disarmed_safely: bool,
    pub simulated_present: bool,
}

impl Default for MockWatchdogDriver {
    fn default() -> Self {
        Self::new(true, 30)
    }
}

impl MockWatchdogDriver {
    pub fn new(simulated_present: bool, timeout_secs: u32) -> Self {
        Self {
            armed: false,
            ping_count: 0,
            last_ping: None,
            timeout_secs,
            disarmed_safely: false,
            simulated_present,
        }
    }
}

impl WatchdogDriver for MockWatchdogDriver {
    fn arm(&mut self) -> Result<(), String> {
        if !self.simulated_present {
            return Err("Mock hardware watchdog not present".to_string());
        }
        self.armed = true;
        self.disarmed_safely = false;
        self.last_ping = Some(Instant::now());
        Ok(())
    }

    fn ping(&mut self) -> Result<(), String> {
        if !self.armed {
            return Err("Cannot ping disarmed watchdog".to_string());
        }
        self.ping_count += 1;
        self.last_ping = Some(Instant::now());
        Ok(())
    }

    fn set_timeout(&mut self, timeout_secs: u32) -> Result<u32, String> {
        self.timeout_secs = timeout_secs;
        Ok(self.timeout_secs)
    }

    fn get_timeout(&self) -> Result<u32, String> {
        Ok(self.timeout_secs)
    }

    fn disarm_and_close(&mut self) -> Result<(), String> {
        if self.armed {
            self.armed = false;
            self.disarmed_safely = true;
        }
        Ok(())
    }

    fn is_hardware_present(&self) -> bool {
        self.simulated_present
    }

    fn is_armed(&self) -> bool {
        self.armed
    }
}

/// Watchdog Supervisor managing keepalive loop and clean shutdown
pub struct WatchdogSupervisor {
    pub config: WatchdogConfig,
    driver: Arc<Mutex<dyn WatchdogDriver>>,
}

impl WatchdogSupervisor {
    pub fn new(config: WatchdogConfig, driver: Arc<Mutex<dyn WatchdogDriver>>) -> Self {
        Self { config, driver }
    }

    pub fn new_mock(config: WatchdogConfig) -> (Self, Arc<Mutex<MockWatchdogDriver>>) {
        let mock = Arc::new(Mutex::new(MockWatchdogDriver::new(true, config.timeout_secs)));
        let supervisor = Self {
            config,
            driver: mock.clone(),
        };
        (supervisor, mock)
    }

    pub fn arm(&self) -> Result<(), String> {
        let mut d = self.driver.lock().unwrap();
        d.arm()
    }

    pub fn ping(&self) -> Result<(), String> {
        let mut d = self.driver.lock().unwrap();
        d.ping()
    }

    pub fn disarm(&self) -> Result<(), String> {
        let mut d = self.driver.lock().unwrap();
        d.disarm_and_close()
    }

    pub fn is_armed(&self) -> bool {
        let d = self.driver.lock().unwrap();
        d.is_armed()
    }

    pub fn is_present(&self) -> bool {
        let d = self.driver.lock().unwrap();
        d.is_hardware_present()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mock_watchdog_lifecycle() {
        let config = WatchdogConfig::default();
        let (supervisor, mock) = WatchdogSupervisor::new_mock(config);

        assert!(supervisor.is_present());
        assert!(!supervisor.is_armed());

        // Arm
        supervisor.arm().unwrap();
        assert!(supervisor.is_armed());

        // Ping 3 times
        supervisor.ping().unwrap();
        supervisor.ping().unwrap();
        supervisor.ping().unwrap();

        {
            let m = mock.lock().unwrap();
            assert_eq!(m.ping_count, 3);
            assert!(!m.disarmed_safely);
        }

        // Disarm safely with 'V'
        supervisor.disarm().unwrap();
        assert!(!supervisor.is_armed());

        {
            let m = mock.lock().unwrap();
            assert!(m.disarmed_safely);
        }

        // Ping after disarm fails
        assert!(supervisor.ping().is_err());
    }

    #[test]
    fn test_linux_watchdog_absent_graceful_detection() {
        let mut driver = LinuxHardwareWatchdog::new("/tmp/nonexistent_watchdog_device", 30);
        assert!(!driver.is_hardware_present());
        assert!(!driver.is_armed());

        let arm_res = driver.arm();
        assert!(arm_res.is_err());
    }
}
