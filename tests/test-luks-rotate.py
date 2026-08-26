#!/usr/bin/env python3
# AI-hint: Automated unit test suite for LUKS2 and dm-crypt zero-downtime key rotation.
# AI-related: usr/libexec/mios/sec/mios-luks-rotate, usr/lib/systemd/system/mios-luks-rotate.service, usr/lib/systemd/system/mios-luks-rotate.timer
"""Automated tests for LUKS2 metadata parsing, header backup, atomic key rotation, and safety rollback."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))

sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios"))
sys.path.insert(0, os.path.join(_ROOT, "lib", "mios"))

_LUKS_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "mios-luks-rotate")
loader = importlib.machinery.SourceFileLoader("luks_rotate", _LUKS_PATH)
spec = importlib.util.spec_from_loader("luks_rotate", loader)
if spec and spec.loader:
    luks_rotate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = luks_rotate
    spec.loader.exec_module(luks_rotate)
else:
    raise ImportError(f"Could not load mios-luks-rotate module from {_LUKS_PATH}")


class MockLUKSDevice(luks_rotate.LUKSDevice):
    """Simulated LUKS device state machine for rigorous unit testing without physical disks."""

    def __init__(self, initial_slots: dict[int, str] | None = None) -> None:
        super().__init__()
        # Map slot_id -> passphrase
        self.slots: dict[int, str] = initial_slots if initial_slots is not None else {0: "initial-secret-passphrase"}
        self.header_backups: list[str] = []
        self.simulate_unlock_test_failure = False
        self.simulate_new_key_failure = False

    def dump_metadata(self, device: str) -> dict:
        active = sorted(list(self.slots.keys()))
        free = [i for i in range(32) if i not in self.slots]
        return {
            "device": device,
            "version": 2,
            "active_slots": active,
            "free_slots": free,
        }

    def backup_header(self, device: str, backup_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(backup_path)), exist_ok=True)
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"device": device, "slots": self.slots}))
        self.header_backups.append(backup_path)
        return backup_path

    def add_key(self, device: str, current_passphrase: str, new_passphrase: str, new_slot: int) -> bool:
        if current_passphrase not in self.slots.values():
            raise RuntimeError("Current passphrase does not match any active keyslot")
        if new_slot in self.slots:
            raise RuntimeError(f"Keyslot {new_slot} is already occupied")
        self.slots[new_slot] = new_passphrase
        return True

    def test_passphrase(self, device: str, passphrase: str, slot: int | None = None) -> bool:
        if self.simulate_unlock_test_failure:
            return False
        if self.simulate_new_key_failure and (slot is not None and slot != 0):
            return False
        if slot is not None:
            return self.slots.get(slot) == passphrase
        return passphrase in self.slots.values()

    def kill_slot(self, device: str, slot_to_kill: int, active_passphrase: str | None = None) -> bool:
        if slot_to_kill not in self.slots:
            raise RuntimeError(f"Keyslot {slot_to_kill} does not exist")
        del self.slots[slot_to_kill]
        return True

    def restore_header(self, device: str, backup_path: str) -> bool:
        if not os.path.exists(backup_path):
            raise FileNotFoundError(backup_path)
        with open(backup_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.slots = {int(k): v for k, v in data["slots"].items()}
        return True


class TestLUKSRotate(unittest.TestCase):
    """Tests LUKS2 metadata extraction, atomic zero-downtime key rotation, and safety rollback."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mios_luks_test_")
        self.backup_dir = os.path.join(self.test_dir, "luks-headers")
        self.audit_log = os.path.join(self.test_dir, "luks-rotation.log")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_metadata_dump_active_and_free_slots(self):
        mock_dev = MockLUKSDevice(initial_slots={0: "pass0", 1: "pass1"})
        meta = mock_dev.dump_metadata("/dev/mapper/ceph-osd-0")

        self.assertEqual(meta["active_slots"], [0, 1])
        self.assertEqual(meta["free_slots"][0], 2)
        self.assertEqual(len(meta["free_slots"]), 30)

    def test_successful_zero_downtime_key_rotation(self):
        mock_dev = MockLUKSDevice(initial_slots={0: "old-passphrase-secret"})
        engine = luks_rotate.LUKSRotationEngine(
            luks_device=mock_dev,
            backup_root=self.backup_dir,
            audit_log=self.audit_log,
        )

        receipt = engine.rotate_key(
            device="/dev/mapper/ceph-osd-0",
            current_passphrase="old-passphrase-secret",
            new_passphrase="new-cryptographic-passphrase-2026",
        )

        self.assertEqual(receipt["status"], "success")
        self.assertEqual(receipt["old_slot"], 0)
        self.assertEqual(receipt["new_slot"], 1)
        self.assertTrue(receipt["post_verify_new_unlocks"])
        self.assertTrue(receipt["post_verify_old_revoked"])

        # Check mock device state: slot 0 should be gone, slot 1 should have new passphrase
        self.assertNotIn(0, mock_dev.slots)
        self.assertEqual(mock_dev.slots.get(1), "new-cryptographic-passphrase-2026")

        # Verify header backup file was created
        self.assertTrue(os.path.exists(receipt["backup_header"]))

        # Verify audit log was recorded
        self.assertTrue(os.path.exists(self.audit_log))
        with open(self.audit_log, "r", encoding="utf-8") as f:
            log_line = f.readline()
        log_data = json.loads(log_line)
        self.assertEqual(log_data["device"], "/dev/mapper/ceph-osd-0")
        self.assertEqual(log_data["old_slot"], 0)
        self.assertEqual(log_data["new_slot"], 1)

    def test_pre_validation_fails_on_wrong_current_passphrase(self):
        mock_dev = MockLUKSDevice(initial_slots={0: "real-passphrase"})
        engine = luks_rotate.LUKSRotationEngine(
            luks_device=mock_dev,
            backup_root=self.backup_dir,
            audit_log=self.audit_log,
        )

        with self.assertRaises(ValueError) as ctx:
            engine.rotate_key(
                device="/dev/mapper/ceph-osd-0",
                current_passphrase="wrong-passphrase",
            )
        self.assertIn("Current passphrase validation failed", str(ctx.exception))
        # Initial slot untouched
        self.assertEqual(mock_dev.slots, {0: "real-passphrase"})

    def test_safety_invariant_new_key_failure_preserves_old_key(self):
        """CRITICAL: If testing new key fails, old keyslot MUST NOT be killed."""
        mock_dev = MockLUKSDevice(initial_slots={0: "safe-old-passphrase"})
        engine = luks_rotate.LUKSRotationEngine(
            luks_device=mock_dev,
            backup_root=self.backup_dir,
            audit_log=self.audit_log,
        )

        # Simulate unlock verification failure on new slot
        mock_dev.simulate_new_key_failure = True

        with self.assertRaises(RuntimeError) as ctx:
            engine.rotate_key(
                device="/dev/mapper/ceph-osd-0",
                current_passphrase="safe-old-passphrase",
                new_passphrase="bad-new-passphrase",
            )

        self.assertIn("ABORTED ROTATION", str(ctx.exception))
        # Verify old keyslot was preserved!
        mock_dev.simulate_new_key_failure = False
        self.assertIn(0, mock_dev.slots)
        self.assertEqual(mock_dev.slots[0], "safe-old-passphrase")

    def test_header_backup_and_restore(self):
        mock_dev = MockLUKSDevice(initial_slots={0: "original-key"})
        backup_file = os.path.join(self.backup_dir, "test.header.bak")

        mock_dev.backup_header("/dev/mapper/ceph-osd-0", backup_file)
        self.assertTrue(os.path.exists(backup_file))

        # Mutate device slots
        mock_dev.slots = {1: "mutated-key"}

        # Restore from backup
        mock_dev.restore_header("/dev/mapper/ceph-osd-0", backup_file)
        self.assertEqual(mock_dev.slots, {0: "original-key"})

    def test_service_and_timer_files_exist(self):
        svc_path = os.path.join(_ROOT, "usr", "lib", "systemd", "system", "mios-luks-rotate.service")
        timer_path = os.path.join(_ROOT, "usr", "lib", "systemd", "system", "mios-luks-rotate.timer")

        self.assertTrue(os.path.exists(svc_path), f"Service unit missing at {svc_path}")
        self.assertTrue(os.path.exists(timer_path), f"Timer unit missing at {timer_path}")

        with open(svc_path, "r", encoding="utf-8") as f:
            s_content = f.read()
        self.assertIn("mios-luks-rotate", s_content)

        with open(timer_path, "r", encoding="utf-8") as f:
            t_content = f.read()
        self.assertIn("OnCalendar=monthly", t_content)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLUKSRotate)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
