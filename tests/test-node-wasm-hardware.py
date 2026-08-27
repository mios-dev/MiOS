#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-389 Wasm sandbox hardware GPIO & I2C host imports with allowlist enforcement.
# AI-related: usr/libexec/mios/node/hardware.py, usr/libexec/mios/node/wasm_sandbox.py, src/mios-rs/mios-node/src/hardware.rs
"""Automated tests for WS-NODE Tier-1 Wasm sandbox GPIO and I2C hardware host imports."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_HW_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "hardware.py")
_WASM_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "wasm_sandbox.py")

spec_hw = importlib.util.spec_from_file_location("hardware", _HW_PATH)
if spec_hw and spec_hw.loader:
    hardware = importlib.util.module_from_spec(spec_hw)
    sys.modules["hardware"] = hardware
    sys.modules["usr.libexec.mios.node.hardware"] = hardware
    spec_hw.loader.exec_module(hardware)
else:
    raise ImportError(f"Could not load hardware module from {_HW_PATH}")

spec_wasm = importlib.util.spec_from_file_location("wasm_sandbox", _WASM_PATH)
if spec_wasm and spec_wasm.loader:
    wasm_sandbox = importlib.util.module_from_spec(spec_wasm)
    sys.modules["wasm_sandbox"] = wasm_sandbox
    sys.modules["usr.libexec.mios.node.wasm_sandbox"] = wasm_sandbox
    spec_wasm.loader.exec_module(wasm_sandbox)
else:
    raise ImportError(f"Could not load wasm_sandbox module from {_WASM_PATH}")

class TestNodeWasmHardware(unittest.TestCase):
    """Validates Wasm Host Imports for hardware access with strict allowlist enforcement."""

    def setUp(self):
        self.allowlist = hardware.HardwareAllowlist(
            allowed_gpio_pins={4, 17, 27},
            read_only_gpio_pins={4},
            allowed_i2c_buses={1},
            allowed_i2c_addresses={0x48, 0x68},
            max_i2c_transfer_len=64,
        )
        self.mock_driver = hardware.MockHardwareDriver()
        self.controller = hardware.SandboxedHardwareController(
            allowlist=self.allowlist, driver=self.mock_driver
        )

    def test_gpio_allowlist_write_and_read(self):
        # 1. Allowed write to pin 17
        err = self.controller.mios_sys_gpio_write(17, 1)
        self.assertEqual(err, hardware.HardwareErrorCode.SUCCESS)
        self.assertEqual(self.mock_driver.gpio_read(17), 1)

        err_r, val = self.controller.mios_sys_gpio_read(17)
        self.assertEqual(err_r, hardware.HardwareErrorCode.SUCCESS)
        self.assertEqual(val, 1)

        # 2. Read-only pin 4 cannot be written
        err_ro = self.controller.mios_sys_gpio_write(4, 1)
        self.assertEqual(err_ro, hardware.HardwareErrorCode.READ_ONLY_PIN)
        # Read from read-only pin is permitted
        err_ro_r, val_ro = self.controller.mios_sys_gpio_read(4)
        self.assertEqual(err_ro_r, hardware.HardwareErrorCode.SUCCESS)

        # 3. Disallowed pin 99
        err_unauth = self.controller.mios_sys_gpio_write(99, 1)
        self.assertEqual(err_unauth, hardware.HardwareErrorCode.PERMISSION_DENIED)
        err_unauth_r, _ = self.controller.mios_sys_gpio_read(99)
        self.assertEqual(err_unauth_r, hardware.HardwareErrorCode.PERMISSION_DENIED)

    def test_i2c_allowlist_transfers(self):
        # Write mock register at bus 1, addr 0x68, reg 0x10 = 0x55
        self.mock_driver.i2c_transfer(1, 0x68, bytes([0x10, 0x55]), 0)

        # Allowed read
        err, rdata = self.controller.mios_sys_i2c_transfer(1, 0x68, bytes([0x10]), 1)
        self.assertEqual(err, hardware.HardwareErrorCode.SUCCESS)
        self.assertEqual(list(rdata), [0x55])

        # Disallowed address 0x77
        err_addr, _ = self.controller.mios_sys_i2c_transfer(1, 0x77, bytes([0x10]), 1)
        self.assertEqual(err_addr, hardware.HardwareErrorCode.PERMISSION_DENIED)

        # Disallowed bus 2
        err_bus, _ = self.controller.mios_sys_i2c_transfer(2, 0x68, bytes([0x10]), 1)
        self.assertEqual(err_bus, hardware.HardwareErrorCode.PERMISSION_DENIED)

    def test_wasm_sandbox_engine_hardware_execution(self):
        config = wasm_sandbox.WasmExecutionConfig(allowlist=self.allowlist)
        engine = wasm_sandbox.WasmSandboxEngine(
            config=config, hardware_controller=self.controller
        )

        # 1. Execute task with valid GPIO write
        payload_write = json.dumps({"action": "gpio_write", "pin": 17, "value": 1}).encode("utf-8")
        res_w = engine.execute(b"WASM_BYTECODE", payload_write)
        self.assertTrue(res_w.success)
        self.assertEqual(res_w.exit_code, 0)
        self.assertIn(b"GPIO pin 17 set to 1", res_w.output_data)

        # 2. Execute task with valid GPIO read
        payload_read = json.dumps({"action": "gpio_read", "pin": 17}).encode("utf-8")
        res_r = engine.execute(b"WASM_BYTECODE", payload_read)
        self.assertTrue(res_r.success)
        self.assertIn(b"GPIO pin 17 value = 1", res_r.output_data)

        # 3. Disallowed pin triggers permission denial
        payload_denied = json.dumps({"action": "gpio_write", "pin": 999, "value": 1}).encode("utf-8")
        res_d = engine.execute(b"WASM_BYTECODE", payload_denied)
        self.assertFalse(res_d.success)
        self.assertEqual(res_d.exit_code, hardware.HardwareErrorCode.PERMISSION_DENIED)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeWasmHardware)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
