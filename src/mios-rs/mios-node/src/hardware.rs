// AI-hint: Hardware Abstraction Layer & Wasm host imports for GPIO and I2C with allowlist enforcement.
// AI-related: src/mios-rs/mios-node/src/executor.rs, usr/libexec/mios/node/hardware.py, usr/libexec/mios/node/wasm_sandbox.py
//! MiOS Edge Node Hardware Abstraction Layer (HAL) & Wasm Sandbox Host Imports
//! Enforces strict allowlist permissions for GPIO and I2C interactions from sandboxed Wasm guests.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use std::sync::{Arc, Mutex, RwLock};

#[repr(i32)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HardwareErrorCode {
    Success = 0,
    PermissionDenied = -1,
    DeviceNotFound = -2,
    InvalidParameter = -3,
    IoError = -4,
    ReadOnlyPin = -5,
}

impl std::fmt::Display for HardwareErrorCode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{:?} ({})", self, *self as i32)
    }
}

impl std::error::Error for HardwareErrorCode {}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HardwareAllowlist {
    pub allowed_gpio_pins: HashSet<u32>,
    pub read_only_gpio_pins: HashSet<u32>,
    pub allowed_i2c_buses: HashSet<u8>,
    pub allowed_i2c_addresses: HashSet<u16>,
    pub max_i2c_transfer_len: usize,
}

impl Default for HardwareAllowlist {
    fn default() -> Self {
        Self {
            allowed_gpio_pins: [4, 17, 27, 22].into_iter().collect(),
            read_only_gpio_pins: [4].into_iter().collect(),
            allowed_i2c_buses: [1].into_iter().collect(),
            allowed_i2c_addresses: [0x48, 0x68, 0x76, 0x77].into_iter().collect(),
            max_i2c_transfer_len: 256,
        }
    }
}

pub trait HardwareDriver: Send + Sync {
    fn gpio_read(&self, pin: u32) -> Result<u8, HardwareErrorCode>;
    fn gpio_write(&self, pin: u32, value: u8) -> Result<(), HardwareErrorCode>;
    fn i2c_transfer(
        &self,
        bus: u8,
        addr: u16,
        write_buf: &[u8],
        read_buf: &mut [u8],
    ) -> Result<usize, HardwareErrorCode>;
}

/// Thread-safe in-memory Mock Hardware Driver for testing, emulation, and containerized runtimes
#[derive(Debug, Default)]
pub struct MockHardwareDriver {
    gpio_pins: Mutex<HashMap<u32, u8>>,
    i2c_registers: Mutex<HashMap<(u8, u16, u8), u8>>,
}

impl MockHardwareDriver {
    pub fn new() -> Self {
        Self {
            gpio_pins: Mutex::new(HashMap::new()),
            i2c_registers: Mutex::new(HashMap::new()),
        }
    }

    pub fn set_mock_gpio(&self, pin: u32, val: u8) {
        let mut pins = self.gpio_pins.lock().unwrap();
        pins.insert(pin, val);
    }

    pub fn get_mock_gpio(&self, pin: u32) -> Option<u8> {
        let pins = self.gpio_pins.lock().unwrap();
        pins.get(&pin).copied()
    }

    pub fn set_mock_i2c_register(&self, bus: u8, addr: u16, reg: u8, val: u8) {
        let mut regs = self.i2c_registers.lock().unwrap();
        regs.insert((bus, addr, reg), val);
    }

    pub fn get_mock_i2c_register(&self, bus: u8, addr: u16, reg: u8) -> Option<u8> {
        let regs = self.i2c_registers.lock().unwrap();
        regs.get(&(bus, addr, reg)).copied()
    }
}

impl HardwareDriver for MockHardwareDriver {
    fn gpio_read(&self, pin: u32) -> Result<u8, HardwareErrorCode> {
        let pins = self.gpio_pins.lock().unwrap();
        Ok(*pins.get(&pin).unwrap_or(&0))
    }

    fn gpio_write(&self, pin: u32, value: u8) -> Result<(), HardwareErrorCode> {
        let mut pins = self.gpio_pins.lock().unwrap();
        pins.insert(pin, value);
        Ok(())
    }

    fn i2c_transfer(
        &self,
        bus: u8,
        addr: u16,
        write_buf: &[u8],
        read_buf: &mut [u8],
    ) -> Result<usize, HardwareErrorCode> {
        let mut regs = self.i2c_registers.lock().unwrap();

        // If writing to a register address (write_buf[0] = reg, write_buf[1..] = values)
        if !write_buf.is_empty() {
            let mut reg = write_buf[0];
            for &val in &write_buf[1..] {
                regs.insert((bus, addr, reg), val);
                reg = reg.wrapping_add(1);
            }
        }

        // If reading: if write_buf has 1 byte (register pointer), read starting at that register
        if !read_buf.is_empty() {
            let start_reg = if !write_buf.is_empty() { write_buf[0] } else { 0 };
            for (idx, slot) in read_buf.iter_mut().enumerate() {
                let current_reg = start_reg.wrapping_add(idx as u8);
                *slot = *regs.get(&(bus, addr, current_reg)).unwrap_or(&0);
            }
        }

        Ok(read_buf.len())
    }
}

/// Linux Sysfs / I2C-dev hardware driver interacting with actual kernel hardware paths
#[derive(Debug, Default)]
pub struct LinuxSysfsHardwareDriver {
    sysfs_gpio_root: String,
    dev_i2c_root: String,
}

impl LinuxSysfsHardwareDriver {
    pub fn new() -> Self {
        Self {
            sysfs_gpio_root: "/sys/class/gpio".to_string(),
            dev_i2c_root: "/dev".to_string(),
        }
    }

    pub fn with_custom_roots(sysfs_gpio_root: &str, dev_i2c_root: &str) -> Self {
        Self {
            sysfs_gpio_root: sysfs_gpio_root.to_string(),
            dev_i2c_root: dev_i2c_root.to_string(),
        }
    }
}

impl HardwareDriver for LinuxSysfsHardwareDriver {
    fn gpio_read(&self, pin: u32) -> Result<u8, HardwareErrorCode> {
        let val_path = format!("{}/gpio{}/value", self.sysfs_gpio_root, pin);
        if !Path::new(&val_path).exists() {
            return Err(HardwareErrorCode::DeviceNotFound);
        }
        match fs::read_to_string(&val_path) {
            Ok(content) => {
                let trimmed = content.trim();
                if trimmed == "1" {
                    Ok(1)
                } else {
                    Ok(0)
                }
            }
            Err(_) => Err(HardwareErrorCode::IoError),
        }
    }

    fn gpio_write(&self, pin: u32, value: u8) -> Result<(), HardwareErrorCode> {
        let val_path = format!("{}/gpio{}/value", self.sysfs_gpio_root, pin);
        if !Path::new(&val_path).exists() {
            return Err(HardwareErrorCode::DeviceNotFound);
        }
        let content = if value != 0 { "1" } else { "0" };
        match fs::write(&val_path, content) {
            Ok(_) => Ok(()),
            Err(_) => Err(HardwareErrorCode::IoError),
        }
    }

    fn i2c_transfer(
        &self,
        bus: u8,
        _addr: u16,
        _write_buf: &[u8],
        _read_buf: &mut [u8],
    ) -> Result<usize, HardwareErrorCode> {
        let dev_path = format!("{}/i2c-{}", self.dev_i2c_root, bus);
        if !Path::new(&dev_path).exists() {
            return Err(HardwareErrorCode::DeviceNotFound);
        }
        // In containerized or driver-free hosts without root i2c capabilities:
        Err(HardwareErrorCode::IoError)
    }
}

/// Sandboxed Hardware Controller with strict Allowlist enforcement for Wasm Host Imports
pub struct SandboxedHardwareController {
    allowlist: RwLock<HardwareAllowlist>,
    driver: Arc<dyn HardwareDriver>,
}

impl SandboxedHardwareController {
    pub fn new(allowlist: HardwareAllowlist, driver: Arc<dyn HardwareDriver>) -> Self {
        Self {
            allowlist: RwLock::new(allowlist),
            driver,
        }
    }

    pub fn new_mock(allowlist: HardwareAllowlist) -> (Self, Arc<MockHardwareDriver>) {
        let mock_driver = Arc::new(MockHardwareDriver::new());
        let controller = Self::new(allowlist, mock_driver.clone());
        (controller, mock_driver)
    }

    pub fn update_allowlist(&self, allowlist: HardwareAllowlist) {
        let mut w = self.allowlist.write().unwrap();
        *w = allowlist;
    }

    pub fn get_allowlist(&self) -> HardwareAllowlist {
        self.allowlist.read().unwrap().clone()
    }

    // --- Host Import Interfaces ---

    /// Host import `mios_sys_gpio_read(pin: u32) -> Result<u8, HardwareErrorCode>`
    pub fn mios_sys_gpio_read(&self, pin: u32) -> Result<u8, HardwareErrorCode> {
        let allowlist = self.allowlist.read().unwrap();
        if !allowlist.allowed_gpio_pins.contains(&pin) {
            return Err(HardwareErrorCode::PermissionDenied);
        }
        self.driver.gpio_read(pin)
    }

    /// Host import `mios_sys_gpio_write(pin: u32, value: u8) -> Result<(), HardwareErrorCode>`
    pub fn mios_sys_gpio_write(&self, pin: u32, value: u8) -> Result<(), HardwareErrorCode> {
        let allowlist = self.allowlist.read().unwrap();
        if !allowlist.allowed_gpio_pins.contains(&pin) {
            return Err(HardwareErrorCode::PermissionDenied);
        }
        if allowlist.read_only_gpio_pins.contains(&pin) {
            return Err(HardwareErrorCode::ReadOnlyPin);
        }
        self.driver.gpio_write(pin, value)
    }

    /// Host import `mios_sys_i2c_transfer`
    pub fn mios_sys_i2c_transfer(
        &self,
        bus: u8,
        addr: u16,
        write_buf: &[u8],
        read_buf: &mut [u8],
    ) -> Result<usize, HardwareErrorCode> {
        let allowlist = self.allowlist.read().unwrap();
        if !allowlist.allowed_i2c_buses.contains(&bus) {
            return Err(HardwareErrorCode::PermissionDenied);
        }
        if !allowlist.allowed_i2c_addresses.contains(&addr) {
            return Err(HardwareErrorCode::PermissionDenied);
        }
        if write_buf.len() > allowlist.max_i2c_transfer_len
            || read_buf.len() > allowlist.max_i2c_transfer_len
        {
            return Err(HardwareErrorCode::InvalidParameter);
        }
        self.driver.i2c_transfer(bus, addr, write_buf, read_buf)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_allowlist_gpio_access() {
        let mut allowlist = HardwareAllowlist::default();
        allowlist.allowed_gpio_pins.insert(17);
        allowlist.read_only_gpio_pins.insert(4);

        let (controller, mock) = SandboxedHardwareController::new_mock(allowlist);

        // Allowed write to pin 17
        assert_eq!(controller.mios_sys_gpio_write(17, 1), Ok(()));
        assert_eq!(mock.get_mock_gpio(17), Some(1));
        assert_eq!(controller.mios_sys_gpio_read(17), Ok(1));

        // Read-only pin 4 cannot be written
        assert_eq!(
            controller.mios_sys_gpio_write(4, 1),
            Err(HardwareErrorCode::ReadOnlyPin)
        );
        // But read is allowed
        assert_eq!(controller.mios_sys_gpio_read(4), Ok(0));

        // Unallowed pin 99
        assert_eq!(
            controller.mios_sys_gpio_read(99),
            Err(HardwareErrorCode::PermissionDenied)
        );
        assert_eq!(
            controller.mios_sys_gpio_write(99, 1),
            Err(HardwareErrorCode::PermissionDenied)
        );
    }

    #[test]
    fn test_allowlist_i2c_transfer() {
        let allowlist = HardwareAllowlist::default(); // allowed bus 1, addr 0x48, 0x68, 0x76, 0x77
        let (controller, mock) = SandboxedHardwareController::new_mock(allowlist);

        // Set up mock register on bus 1, addr 0x68, reg 0x10 = 0xAB
        mock.set_mock_i2c_register(1, 0x68, 0x10, 0xAB);

        // Valid transfer on allowed bus 1, addr 0x68
        let write_data = [0x10u8];
        let mut read_data = [0u8; 1];
        let res = controller.mios_sys_i2c_transfer(1, 0x68, &write_data, &mut read_data);
        assert_eq!(res, Ok(1));
        assert_eq!(read_data[0], 0xAB);

        // Disallowed address 0x55
        let res_disallowed_addr =
            controller.mios_sys_i2c_transfer(1, 0x55, &write_data, &mut read_data);
        assert_eq!(res_disallowed_addr, Err(HardwareErrorCode::PermissionDenied));

        // Disallowed bus 2
        let res_disallowed_bus =
            controller.mios_sys_i2c_transfer(2, 0x68, &write_data, &mut read_data);
        assert_eq!(res_disallowed_bus, Err(HardwareErrorCode::PermissionDenied));
    }
}
