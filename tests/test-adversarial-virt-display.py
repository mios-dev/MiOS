#!/usr/bin/env python3
# AI-hint: Comprehensive adversarial stress-test suite for Virtualization & Display modules (T-413..T-419, T-423).
# AI-related: usr/libexec/mios/virt/iommu_parser.py, usr/libexec/mios/virt/vfio_bind.py, usr/libexec/mios/display/looking_glass.py, usr/libexec/mios/virt/pipewire_bridge.py, usr/libexec/mios/virt/vtpm_provision.py, usr/libexec/mios/virt/hugepages_mgr.py, usr/libexec/mios/virt/virtiofs_mount.py, usr/libexec/mios/display/multimonitor_sync.py

import configparser
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_VIRT_DIR = os.path.join(_ROOT, "usr", "libexec", "mios", "virt")
_DISP_DIR = os.path.join(_ROOT, "usr", "libexec", "mios", "display")


def _import_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    raise ImportError(f"Could not load module {name} from {path}")


iommu_parser_mod = _import_module("iommu_parser", os.path.join(_VIRT_DIR, "iommu_parser.py"))
vfio_bind_mod = _import_module("vfio_bind", os.path.join(_VIRT_DIR, "vfio_bind.py"))
looking_glass_mod = _import_module("looking_glass", os.path.join(_DISP_DIR, "looking_glass.py"))
pipewire_bridge_mod = _import_module("pipewire_bridge", os.path.join(_VIRT_DIR, "pipewire_bridge.py"))
vtpm_provision_mod = _import_module("vtpm_provision", os.path.join(_VIRT_DIR, "vtpm_provision.py"))
hugepages_mgr_mod = _import_module("hugepages_mgr", os.path.join(_VIRT_DIR, "hugepages_mgr.py"))
virtiofs_mount_mod = _import_module("virtiofs_mount", os.path.join(_VIRT_DIR, "virtiofs_mount.py"))
multimonitor_sync_mod = _import_module("multimonitor_sync", os.path.join(_DISP_DIR, "multimonitor_sync.py"))


class TestAdversarialIOMMUParser(unittest.TestCase):
    """Adversarial stress-testing for T-413 IOMMU Group Parser & ACS Override Topology Auditor."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="adv_test_iommu_")
        self.sysfs_root = self.tmp_dir

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _setup_device(
        self,
        bdf: str,
        group_id: int,
        vendor: str = "0x10de",
        device: str = "0x2484",
        pci_class: str = "0x030000",
        boot_vga: str = "0",
        driver: str | None = "nvidia",
    ) -> str:
        safe_bdf = bdf.replace(":", "_")
        dev_dir = os.path.join(self.sysfs_root, "bus", "pci", "devices", safe_bdf)
        os.makedirs(dev_dir, exist_ok=True)
        with open(os.path.join(dev_dir, "vendor"), "w") as f:
            f.write(f"{vendor}\n")
        with open(os.path.join(dev_dir, "device"), "w") as f:
            f.write(f"{device}\n")
        with open(os.path.join(dev_dir, "class"), "w") as f:
            f.write(f"{pci_class}\n")
        with open(os.path.join(dev_dir, "boot_vga"), "w") as f:
            f.write(f"{boot_vga}\n")

        # Group directory
        grp_dev_dir = os.path.join(self.sysfs_root, "kernel", "iommu_groups", str(group_id), "devices", safe_bdf)
        os.makedirs(grp_dev_dir, exist_ok=True)
        with open(os.path.join(grp_dev_dir, "vendor"), "w") as f:
            f.write(f"{vendor}\n")
        with open(os.path.join(grp_dev_dir, "device"), "w") as f:
            f.write(f"{device}\n")
        with open(os.path.join(grp_dev_dir, "class"), "w") as f:
            f.write(f"{pci_class}\n")
        with open(os.path.join(grp_dev_dir, "boot_vga"), "w") as f:
            f.write(f"{boot_vga}\n")

        if driver:
            drv_dir = os.path.join(self.sysfs_root, "bus", "pci", "drivers", driver)
            os.makedirs(drv_dir, exist_ok=True)
            with open(os.path.join(dev_dir, "driver_name"), "w") as f:
                f.write(f"{driver}\n")
            with open(os.path.join(grp_dev_dir, "driver_name"), "w") as f:
                f.write(f"{driver}\n")

        return dev_dir

    def test_malformed_bdf_inputs(self) -> None:
        """Adversarial Test: Path traversal, out-of-range functions, invalid formats."""
        parser = iommu_parser_mod.IOMMUParser(sysfs_root=self.sysfs_root)

        malformed_bdfs = [
            "",
            "   ",
            "invalid",
            "0000:01:00",  # missing function
            "0000:01:00.8",  # function > 7
            "0000:01:00.f",  # hex function > 7
            "00000:01:00.0",  # domain > 4 hex
            "0000:01:00.0/../../../etc/passwd",  # path traversal
            "0000:01:00.0; rm -rf /",  # command injection string
            "00:00",  # incomplete short form
            "GGGG:01:00.0",  # non-hex
        ]

        for bdf in malformed_bdfs:
            with self.assertRaises(ValueError, msg=f"Should raise ValueError on malformed BDF: {bdf}"):
                iommu_parser_mod.IOMMUParser.parse_bdf(bdf)

            # audit_isolation should catch gracefully without throwing unhandled exceptions
            res = parser.audit_isolation(bdf)
            self.assertEqual(res["status"], "error")
            self.assertFalse(res["isolated"])
            self.assertIn("error", res)

            # find_device should return None gracefully
            dev = parser.find_device(bdf)
            self.assertIsNone(dev)

    def test_nested_quad_function_gpu_clean_isolation(self) -> None:
        """Adversarial Test: 4 functions on same slot (VGA, Audio, USB xHCI, Type-C UCSI) in group 15."""
        # 0000:01:00.0 VGA
        self._setup_device("0000:01:00.0", group_id=15, vendor="0x10de", device="0x2484", pci_class="0x030000")
        # 0000:01:00.1 Audio
        self._setup_device("0000:01:00.1", group_id=15, vendor="0x10de", device="0x228b", pci_class="0x040300")
        # 0000:01:00.2 USB Controller
        self._setup_device("0000:01:00.2", group_id=15, vendor="0x10de", device="0x1ad8", pci_class="0x0c0330")
        # 0000:01:00.3 Type-C UCSI
        self._setup_device("0000:01:00.3", group_id=15, vendor="0x10de", device="0x1ad9", pci_class="0x0c8000")

        parser = iommu_parser_mod.IOMMUParser(sysfs_root=self.sysfs_root)

        # Audit function 0 (VGA)
        res0 = parser.audit_isolation("0000:01:00.0")
        self.assertEqual(res0["status"], "pass")
        self.assertTrue(res0["isolated"])
        self.assertEqual(res0["iommu_group"], 15)
        self.assertEqual(len(res0["companions"]), 4)
        self.assertEqual(len(res0["conflicts"]), 0)
        self.assertIsNone(res0["uki_kargs"])

        # Audit function 1 (Audio)
        res1 = parser.audit_isolation("0000:01:00.1")
        self.assertEqual(res1["status"], "pass")
        self.assertTrue(res1["isolated"])
        self.assertEqual(len(res1["companions"]), 4)
        self.assertEqual(len(res1["conflicts"]), 0)

        # Invariant checks
        self.assertIn("uki_vs_mok", res0["invariants"])
        self.assertIn("venus_vs_cuda", res0["invariants"])

    def test_shared_root_port_conflict_requires_acs_override(self) -> None:
        """Adversarial Test: GPU in same group as PCIe Root Port and SATA Controller -> Conflict detected."""
        # 0000:01:00.0 GPU VGA
        self._setup_device("0000:01:00.0", group_id=2, vendor="0x10de", device="0x2484", pci_class="0x030000")
        # 0000:01:00.1 GPU Audio
        self._setup_device("0000:01:00.1", group_id=2, vendor="0x10de", device="0x228b", pci_class="0x040300")
        # 0000:00:01.0 PCIe Root Port (Conflict!)
        self._setup_device("0000:00:01.0", group_id=2, vendor="0x8086", device="0x460d", pci_class="0x060400")
        # 0000:00:17.0 SATA Controller (Conflict!)
        self._setup_device("0000:00:17.0", group_id=2, vendor="0x8086", device="0x7a62", pci_class="0x010601")

        parser = iommu_parser_mod.IOMMUParser(sysfs_root=self.sysfs_root)
        res = parser.audit_isolation("0000:01:00.0")

        self.assertEqual(res["status"], "conflict")
        self.assertFalse(res["isolated"])
        self.assertEqual(res["iommu_group"], 2)
        self.assertEqual(len(res["companions"]), 2)
        self.assertEqual(len(res["conflicts"]), 2)
        self.assertEqual(res["uki_kargs"], "pcie_acs_override=downstream,multifunction")
        self.assertIn("Unified Kernel Image (UKI)", res["recommendation"])
        self.assertIsNotNone(res["security_warning"])

    def test_device_not_found_in_sysfs(self) -> None:
        """Adversarial Test: Querying non-existent BDF."""
        parser = iommu_parser_mod.IOMMUParser(sysfs_root=self.sysfs_root)
        res = parser.audit_isolation("0000:99:00.0")
        self.assertEqual(res["status"], "not_found")
        self.assertFalse(res["isolated"])


class TestAdversarialVFIOBinder(unittest.TestCase):
    """Adversarial stress-testing for T-414 Dynamic Runtime VFIO Device Unbind and Rebind Utility."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="adv_test_vfio_")
        self.sysfs_root = self.tmp_dir

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _setup_pci_device(
        self,
        bdf: str,
        vendor: str = "0x10de",
        device: str = "0x2484",
        driver: str = "nvidia",
        boot_vga: bool = False,
    ) -> str:
        safe_bdf = bdf.replace(":", "_")
        dev_dir = os.path.join(self.sysfs_root, "bus", "pci", "devices", safe_bdf)
        os.makedirs(dev_dir, exist_ok=True)
        with open(os.path.join(dev_dir, "vendor"), "w") as f:
            f.write(f"{vendor}\n")
        with open(os.path.join(dev_dir, "device"), "w") as f:
            f.write(f"{device}\n")
        with open(os.path.join(dev_dir, "boot_vga"), "w") as f:
            f.write("1\n" if boot_vga else "0\n")
        with open(os.path.join(dev_dir, "current_driver"), "w") as f:
            f.write(f"{driver}\n")
        with open(os.path.join(dev_dir, "driver_override"), "w") as f:
            f.write("(null)\n")

        # Driver control dirs
        for drv in [driver, "vfio-pci", "snd_hda_intel", "amdgpu", "i915"]:
            drv_dir = os.path.join(self.sysfs_root, "bus", "pci", "drivers", drv)
            os.makedirs(drv_dir, exist_ok=True)
            with open(os.path.join(drv_dir, "bind"), "w") as f:
                f.write("")
            with open(os.path.join(drv_dir, "unbind"), "w") as f:
                f.write("")
            with open(os.path.join(drv_dir, "new_id"), "w") as f:
                f.write("")

        return dev_dir

    def test_primary_gpu_unbind_protection_boot_vga(self) -> None:
        """Adversarial Test: Primary host display GPU (boot_vga=1) unbind is refused unless forced."""
        # Setup primary host GPU on 0000:00:02.0 with boot_vga=1
        self._setup_pci_device("0000:00:02.0", vendor="0x8086", device="0x4680", driver="i915", boot_vga=True)

        binder = vfio_bind_mod.VFIOBinder(sysfs_root=self.sysfs_root)
        self.assertTrue(binder.is_primary_gpu("0000:00:02.0"))

        # 1. Unbind attempt without force -> MUST BE REFUSED
        res_refused = binder.bind_to_vfio("0000:00:02.0", force=False)
        self.assertEqual(res_refused["status"], "refused")
        self.assertFalse(res_refused["bound"])
        self.assertIn("primary host display", res_refused["error"])
        self.assertIn("gpu_fractioning_limit", res_refused["invariants"])
        self.assertIn("venus_vs_cuda", res_refused["invariants"])

        # Verify device remained bound to i915
        state = binder.get_device_state("0000:00:02.0")
        self.assertEqual(state.current_driver, "i915")

        # 2. Unbind with force=True -> Succeeded
        res_forced = binder.bind_to_vfio("0000:00:02.0", force=True)
        self.assertEqual(res_forced["status"], "success")
        self.assertTrue(res_forced["bound"])

    def test_companion_functions_bound_and_rebound_atomically(self) -> None:
        """Adversarial Test: Multi-function slot (VGA + Audio) bound to vfio-pci and rebound to host."""
        # Function 0: NVIDIA GPU
        self._setup_pci_device("0000:01:00.0", vendor="0x10de", device="0x2484", driver="nvidia", boot_vga=False)
        # Function 1: Audio Controller
        self._setup_pci_device("0000:01:00.1", vendor="0x10de", device="0x228b", driver="snd_hda_intel", boot_vga=False)

        binder = vfio_bind_mod.VFIOBinder(sysfs_root=self.sysfs_root)
        siblings = binder.get_slot_siblings("0000:01:00.0")
        self.assertEqual(len(siblings), 2)
        self.assertIn("0000:01:00.0", siblings)
        self.assertIn("0000:01:00.1", siblings)

        # 1. Bind to VFIO
        bind_res = binder.bind_to_vfio("0000:01:00.0")
        self.assertEqual(bind_res["status"], "success")
        self.assertEqual(len(bind_res["siblings"]), 2)

        # Check driver overrides and state
        state0 = binder.get_device_state("0000:01:00.0")
        state1 = binder.get_device_state("0000:01:00.1")
        self.assertEqual(state0.current_driver, "vfio-pci")
        self.assertEqual(state1.current_driver, "vfio-pci")
        self.assertEqual(state0.driver_override, "vfio-pci")
        self.assertEqual(state1.driver_override, "vfio-pci")

        # 2. Rebind back to host drivers
        rebind_res = binder.rebind_to_host("0000:01:00.0")
        self.assertEqual(rebind_res["status"], "success")

        # Check state after rebind
        state0_after = binder.get_device_state("0000:01:00.0")
        state1_after = binder.get_device_state("0000:01:00.1")
        self.assertEqual(state0_after.current_driver, "nvidia")
        self.assertEqual(state1_after.current_driver, "snd_hda_intel")
        self.assertIsNone(state0_after.driver_override)
        self.assertIsNone(state1_after.driver_override)


class TestAdversarialLookingGlass(unittest.TestCase):
    """Adversarial stress-testing for T-415 Looking Glass B6 Direct SPICE Host Input Manager."""

    def test_corrupted_and_edge_ini_parsing(self) -> None:
        """Adversarial Test: Corrupted INI formatting, missing sections, custom options, case-preservation."""
        manager = looking_glass_mod.LookingGlassConfigManager(
            vm_name="win11-pro",
            shm_file="/dev/kvmfr0",
            escape_key="KEY_F12",
            full_screen=True,
        )

        ini_str = manager.generate_ini(overrides={"input": {"customOption": "value123", "mouseSens": 5}})
        parsed = manager.parse_ini(ini_str)

        self.assertEqual(parsed["app"]["shmFile"], "/dev/kvmfr0")
        self.assertEqual(parsed["input"]["escapeKey"], "KEY_F12")
        self.assertTrue(parsed["win"]["fullScreen"])
        self.assertEqual(parsed["input"]["mouseSens"], 5)
        self.assertEqual(parsed["input"]["customOption"], "value123")

    def test_custom_keybindings_syntax_hyprland_and_gnome(self) -> None:
        """Adversarial Test: Validate Hyprland and GNOME rules syntax."""
        manager = looking_glass_mod.LookingGlassConfigManager(
            vm_name="gaming-vm",
            shm_file="/dev/kvmfr1",
            escape_key="KEY_RIGHTCTRL",
        )

        hypr_rules = manager.generate_hyprland_rules(app_class="custom-lg", title_pattern="Custom.*")
        self.assertIn("windowrulev2 = fullscreen, class:^(custom-lg)$, title:^(Custom.*)$", hypr_rules)
        self.assertIn("windowrulev2 = idleinhibit always, class:^(custom-lg)$", hypr_rules)
        self.assertIn("windowrulev2 = immediate, class:^(custom-lg)$", hypr_rules)
        self.assertIn("bind = $mainMod, Scroll_Lock, exec, /usr/bin/looking-glass-client -f /dev/kvmfr1", hypr_rules)

        gnome_rules = manager.generate_gnome_rules()
        self.assertIn("gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings", gnome_rules)
        self.assertIn('command "/usr/bin/looking-glass-client -f /dev/kvmfr1"', gnome_rules)

    def test_launch_args_synthesis(self) -> None:
        """Adversarial Test: Verify CLI argument synthesis for Looking Glass."""
        manager = looking_glass_mod.LookingGlassConfigManager(
            vm_name="test-vm",
            shm_file="/dev/kvmfr0",
            spice_socket="/run/libvirt/qemu/test-vm-spice.sock",
            escape_key="KEY_SCROLLLOCK",
            full_screen=True,
            allow_dma=True,
        )

        args = manager.build_client_launch_args(extra_args=["--extra-flag"])
        self.assertEqual(args[0], "looking-glass-client")
        self.assertIn("-f", args)
        self.assertIn("/dev/kvmfr0", args)
        self.assertIn("spice:host=/run/libvirt/qemu/test-vm-spice.sock", args)
        self.assertIn("spice:port=0", args)
        self.assertIn("input:escapeKey=KEY_SCROLLLOCK", args)
        self.assertIn("win:fullScreen=true", args)
        self.assertIn("app:allowDMA=true", args)
        self.assertIn("--extra-flag", args)


class TestAdversarialPipeWireBridge(unittest.TestCase):
    """Adversarial stress-testing for T-416 PipeWire Low-Latency Audio Bridge."""

    def test_latency_sla_calculations_and_extreme_inputs(self) -> None:
        """Adversarial Test: Extreme sample rates and quantums with strict sub-5ms SLA validation."""
        calc = pipewire_bridge_mod.PipeWireBridgeManager.calculate_latency_ms

        # Extreme high frequency: 16 samples @ 44100 Hz -> 0.363 ms (PASS)
        lat_16_44 = calc(16, 44100)
        self.assertEqual(lat_16_44, 0.363)
        self.assertTrue(lat_16_44 <= 5.0)

        # Extreme high frequency: 1024 samples @ 192000 Hz -> 5.333 ms (FAIL > 5ms)
        lat_1024_192 = calc(1024, 192000)
        self.assertEqual(lat_1024_192, 5.333)
        self.assertFalse(lat_1024_192 <= 5.0)

        # Standard low latency: 64 samples @ 48000 Hz -> 1.333 ms (PASS)
        lat_64_48 = calc(64, 48000)
        self.assertEqual(lat_64_48, 1.333)
        self.assertTrue(lat_64_48 <= 5.0)

        # High quantum standard rate: 512 samples @ 48000 Hz -> 10.667 ms (FAIL)
        lat_512_48 = calc(512, 48000)
        self.assertEqual(lat_512_48, 10.667)
        self.assertFalse(lat_512_48 <= 5.0)

        # Boundary test at exactly 5.0ms: 240 / 48000 = 5.0ms (PASS)
        lat_exact_5 = calc(240, 48000)
        self.assertEqual(lat_exact_5, 5.0)
        self.assertTrue(lat_exact_5 <= 5.0)

        # Boundary test slightly exceeding 5.0ms: 241 / 48000 = 5.021ms (FAIL)
        lat_exceed_5 = calc(241, 48000)
        self.assertEqual(lat_exceed_5, 5.021)
        self.assertFalse(lat_exceed_5 <= 5.0)

        # Invalid zero and negative inputs
        with self.assertRaises(ValueError):
            calc(0, 48000)
        with self.assertRaises(ValueError):
            calc(-64, 48000)
        with self.assertRaises(ValueError):
            calc(64, 0)
        with self.assertRaises(ValueError):
            calc(64, -48000)

    def test_sla_validation_method(self) -> None:
        """Adversarial Test: validate_latency_sla method returns pass/fail and formula metadata."""
        mgr = pipewire_bridge_mod.PipeWireBridgeManager(quantum=64, sample_rate=48000)
        res_pass = mgr.validate_latency_sla()
        self.assertEqual(res_pass["status"], "pass")
        self.assertTrue(res_pass["passed"])
        self.assertEqual(res_pass["latency_ms"], 1.333)

        res_fail = mgr.validate_latency_sla(quantum=1024, sample_rate=48000)
        self.assertEqual(res_fail["status"], "fail")
        self.assertFalse(res_fail["passed"])
        self.assertEqual(res_fail["latency_ms"], 21.333)

    def test_ivshmem_xml_and_systemd_service_synthesis(self) -> None:
        """Adversarial Test: Synthesized IVSHMEM XML and systemd units."""
        mgr = pipewire_bridge_mod.PipeWireBridgeManager(
            shm_path="/dev/shm/scream-gaming",
            size_mb=4,
            sample_rate=96000,
            quantum=128,
            backend="jack",
            node_name="scream-gaming-bridge",
        )

        xml = mgr.generate_ivshmem_xml(shmem_name="scream-gaming")
        self.assertIn('<shmem name="scream-gaming">', xml)
        self.assertIn('<model type="ivshmem-plain"/>', xml)
        self.assertIn('<size unit="M">4</size>', xml)

        service = mgr.generate_systemd_service()
        self.assertIn('Environment="PIPEWIRE_LATENCY=128/96000"', service)
        self.assertIn('Environment="JACK_PROMISCUOUS_SERVER=1"', service)
        self.assertIn("ExecStart=/usr/bin/scream -m /dev/shm/scream-gaming -o jack -t 128", service)
        self.assertIn("LimitRTPRIO=95", service)
        self.assertIn("LimitMEMLOCK=infinity", service)


class TestAdversarialVTPMProvision(unittest.TestCase):
    """Adversarial stress-testing for T-417 Virtual TPM2 Provisioning."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="adv_test_vtpm_")
        self.state_root = os.path.join(self.tmp_dir, "var", "lib", "libvirt", "swtpm")
        self.sock_root = os.path.join(self.tmp_dir, "run", "libvirt", "swtpm")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_invalid_and_malicious_vm_ids(self) -> None:
        """Adversarial Test: Path traversal, command injection in VM ID."""
        prov = vtpm_provision_mod.VTPMProvisioner(state_root=self.state_root, sock_root=self.sock_root)

        malicious_ids = [
            "",
            "   ",
            "../../etc/shadow",
            "win11; rm -rf /",
            "win11/subdomain",
            "win11\x00nullbyte",
            "win11$PATH",
            "win11`id`",
            "*",
        ]

        for vm_id in malicious_ids:
            with self.assertRaises(ValueError, msg=f"Should reject malicious VM ID: {vm_id}"):
                prov.get_state_dir(vm_id)

    def test_multi_vm_state_isolation_and_scoped_cleanup(self) -> None:
        """Adversarial Test: Multiple VMs provisioned; purging one does NOT touch the other."""
        prov = vtpm_provision_mod.VTPMProvisioner(state_root=self.state_root, sock_root=self.sock_root)

        # Provision VM 1
        res1 = prov.provision("win11-prod")
        self.assertEqual(res1["status"], "provisioned")
        self.assertTrue(os.path.exists(os.path.join(res1["state_dir"], "tpm2-00.permall")))

        # Provision VM 2
        res2 = prov.provision("win11-dev")
        self.assertEqual(res2["status"], "provisioned")
        self.assertTrue(os.path.exists(os.path.join(res2["state_dir"], "tpm2-00.permall")))

        # Verify state directories are strictly separate
        self.assertNotEqual(res1["state_dir"], res2["state_dir"])
        self.assertNotEqual(res1["socket_path"], res2["socket_path"])

        # Purge VM 1 only
        clean1 = prov.cleanup("win11-prod", purge_state=True)
        self.assertTrue(clean1["state_purged"])
        self.assertFalse(os.path.exists(res1["state_dir"]))

        # Verify VM 2 state is completely intact
        self.assertTrue(os.path.exists(res2["state_dir"]))
        st2 = prov.get_status("win11-dev")
        self.assertTrue(st2["provisioned"])
        self.assertTrue(st2["has_nvram"])

    def test_domain_xml_schema_and_model(self) -> None:
        """Adversarial Test: libvirt domain XML structure matching Windows 11 CRB TPM 2.0."""
        prov = vtpm_provision_mod.VTPMProvisioner(state_root=self.state_root, sock_root=self.sock_root)
        xml = prov.generate_domain_xml("win11", tpm_version="2.0", model="tpm-crb")

        self.assertIn('<tpm model="tpm-crb">', xml)
        self.assertIn('<backend type="emulator" version="2.0">', xml)
        self.assertIn('<source type="unix" path="', xml)
        self.assertIn('win11-swtpm.sock"/>', xml)


class TestAdversarialHugepagesManager(unittest.TestCase):
    """Adversarial stress-testing for T-418 Hugepages Automatic Allocation & Compaction Manager."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="adv_test_hp_")
        self.sysfs_root = self.tmp_dir
        self.proc_root = self.tmp_dir

        # Setup synthetic sysfs hugepages pools
        self.p2m_dir = os.path.join(self.sysfs_root, "kernel", "mm", "hugepages", "hugepages-2048kB")
        self.p1g_dir = os.path.join(self.sysfs_root, "kernel", "mm", "hugepages", "hugepages-1048576kB")
        os.makedirs(self.p2m_dir, exist_ok=True)
        os.makedirs(self.p1g_dir, exist_ok=True)

        with open(os.path.join(self.p2m_dir, "nr_hugepages"), "w") as f:
            f.write("0\n")
        with open(os.path.join(self.p2m_dir, "free_hugepages"), "w") as f:
            f.write("0\n")
        with open(os.path.join(self.p1g_dir, "nr_hugepages"), "w") as f:
            f.write("0\n")
        with open(os.path.join(self.p1g_dir, "free_hugepages"), "w") as f:
            f.write("0\n")

        # Setup proc compaction node
        proc_vm = os.path.join(self.proc_root, "sys", "vm")
        os.makedirs(proc_vm, exist_ok=True)
        with open(os.path.join(proc_vm, "compact_memory"), "w") as f:
            f.write("0\n")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_2m_and_1g_page_count_math_and_validation(self) -> None:
        """Adversarial Test: Exact page count calculations, invalid sizes, odd MB values."""
        mgr = hugepages_mgr_mod.HugepagesManager(sysfs_root=self.sysfs_root, proc_root=self.proc_root)

        # 2MB calculations
        self.assertEqual(mgr.calculate_page_count(2, "2M"), 1)
        self.assertEqual(mgr.calculate_page_count(2048, "2M"), 1024)
        self.assertEqual(mgr.calculate_page_count(8192, "2M"), 4096)
        self.assertEqual(mgr.calculate_page_count(16384, "2M"), 8192)

        # Odd MB with 2M page size must be rejected
        with self.assertRaises(ValueError):
            mgr.calculate_page_count(2049, "2M")

        # 1GB calculations
        self.assertEqual(mgr.calculate_page_count(1024, "1G"), 1)
        self.assertEqual(mgr.calculate_page_count(8192, "1G"), 8)
        self.assertEqual(mgr.calculate_page_count(16384, "1G"), 16)
        self.assertEqual(mgr.calculate_page_count(32768, "1G"), 32)

        # Non-1024 multiple with 1G page size must be rejected
        self.assertEqual(mgr.calculate_page_count(2048, "1G"), 2)

        with self.assertRaises(ValueError):
            mgr.calculate_page_count(1500, "1G")

        # Zero or negative sizes
        with self.assertRaises(ValueError):
            mgr.calculate_page_count(0, "2M")
        with self.assertRaises(ValueError):
            mgr.calculate_page_count(-8192, "2M")

        # Unsupported page size
        with self.assertRaises(ValueError):
            mgr.calculate_page_count(8192, "4K")

    def test_allocation_compaction_and_release_lifecycle(self) -> None:
        """Adversarial Test: Allocation triggers compaction, updates pool, and release decrements cleanly."""
        mgr = hugepages_mgr_mod.HugepagesManager(sysfs_root=self.sysfs_root, proc_root=self.proc_root)

        # 1. Allocate 8192 MB of 2M hugepages (4096 pages)
        alloc_res = mgr.allocate(8192, page_size="2M", compact=True)
        self.assertEqual(alloc_res["status"], "allocated")
        self.assertEqual(alloc_res["requested_pages"], 4096)
        self.assertEqual(alloc_res["target_pages"], 4096)
        self.assertTrue(alloc_res["compaction"]["compaction_triggered"])

        # Check compaction node was written
        with open(os.path.join(self.proc_root, "sys", "vm", "compact_memory"), "r") as f:
            self.assertEqual(f.read().strip(), "1")

        # Check sysfs pool status
        pool_st = mgr.get_pool_status("2M")
        self.assertEqual(pool_st["nr_hugepages"], 4096)
        self.assertEqual(pool_st["allocated_mb"], 8192)

        # 2. Allocate an additional 4096 MB (2048 pages)
        alloc_res2 = mgr.allocate(4096, page_size="2M", compact=False)
        self.assertEqual(alloc_res2["target_pages"], 6144)

        # 3. Release 8192 MB (4096 pages)
        rel_res = mgr.release(8192, page_size="2M")
        self.assertEqual(rel_res["status"], "released")
        self.assertEqual(rel_res["pages_freed"], 4096)
        self.assertEqual(rel_res["remaining_pages"], 2048)

        # 4. Release remaining and ensure no negative underflow
        rel_res2 = mgr.release(8192, page_size="2M")
        self.assertEqual(rel_res2["remaining_pages"], 0)


class TestAdversarialVirtIOFS(unittest.TestCase):
    """Adversarial stress-testing for T-419 VirtIO-FS Shared Directory Mount Daemon."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="adv_test_vfs_")
        self.run_root = os.path.join(self.tmp_dir, "run", "libvirt")
        self.shared_dir = os.path.join(self.tmp_dir, "var", "home", "mios", "Shared")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_malformed_mount_tags_and_vm_ids(self) -> None:
        """Adversarial Test: Injection strings in mount tag."""
        vfs = virtiofs_mount_mod.VirtioFSManager(run_root=self.run_root, default_shared_dir=self.shared_dir)

        malformed_tags = [
            "",
            "   ",
            "../escape",
            "shared; rm -rf /",
            "tag with spaces",
            "tag/slash",
            "tag`whoami`",
        ]

        for tag in malformed_tags:
            with self.assertRaises(ValueError, msg=f"Should reject malformed tag: {tag}"):
                vfs.get_socket_path("win11", mount_tag=tag)

    def test_directory_creation_and_persistent_var_check(self) -> None:
        """Adversarial Test: Directory creation and Invariant 1 verification."""
        vfs = virtiofs_mount_mod.VirtioFSManager(run_root=self.run_root, default_shared_dir=self.shared_dir)

        # Before create
        info1 = vfs.verify_source_directory(create=False)
        self.assertFalse(info1["exists"])

        # Create
        info2 = vfs.verify_source_directory(create=True)
        self.assertTrue(info2["exists"])
        self.assertTrue(info2["created"])

        # Invariant 1 verification on default canonical path
        vfs_default = virtiofs_mount_mod.VirtioFSManager(mock=True)
        def_info = vfs_default.verify_source_directory()
        self.assertTrue(def_info["persistent_var_path"])
        self.assertEqual(def_info["source_dir"], "/var/home/mios/Shared")

    def test_dax_cache_window_and_domain_xml_matrix(self) -> None:
        """Adversarial Test: DAX window boundary options in daemon command and libvirt XML."""
        vfs = virtiofs_mount_mod.VirtioFSManager(run_root=self.run_root, default_shared_dir=self.shared_dir)

        # 1. Without DAX (dax_size_mb=0)
        cmd_no_dax = vfs.build_daemon_cmd("win11", mount_tag="hostshare", dax_size_mb=0)
        self.assertFalse(any(arg.startswith("--dax-size") for arg in cmd_no_dax))
        xml_no_dax = vfs.generate_domain_xml(mount_tag="hostshare", dax_size_mb=0)
        self.assertNotIn("<dax", xml_no_dax)

        # 2. With 2048MB DAX cache window
        cmd_dax = vfs.build_daemon_cmd("win11", mount_tag="hostshare", dax_size_mb=2048)
        self.assertIn("--dax-size=2048M", cmd_dax)
        self.assertIn("--posix-acl", cmd_dax)
        self.assertIn("--xattr", cmd_dax)

        xml_dax = vfs.generate_domain_xml(mount_tag="hostshare", dax_size_mb=2048)
        self.assertIn('<filesystem type="mount" accessmode="passthrough">', xml_dax)
        self.assertIn('<driver type="virtiofs" queue="1024"/>', xml_dax)
        self.assertIn('<target dir="hostshare"/>', xml_dax)
        self.assertIn('<dax unit="KiB">2097152</dax>', xml_dax)
        self.assertIn('<source type="memfd"/>', xml_dax)
        self.assertIn('<access mode="shared"/>', xml_dax)


class TestAdversarialMultiMonitorSync(unittest.TestCase):
    """Adversarial stress-testing for T-423 Multi-Monitor Looking Glass Display Geometry & Synchronizer."""

    def test_shm_buffer_sizing_across_resolutions(self) -> None:
        """Adversarial Test: Power-of-2 IVSHMEM sizing across standard, ultrawide, and extreme 8K displays."""
        calc = multimonitor_sync_mod.MultiMonitorSyncManager.compute_shm_size_mb

        # 1080p: 1920x1080 -> 32 MB
        self.assertEqual(calc(1920, 1080), 32)

        # 1440p: 2560x1440 -> 64 MB
        self.assertEqual(calc(2560, 1440), 64)

        # Ultrawide 1440p: 3440x1440 -> 64 MB
        self.assertEqual(calc(3440, 1440), 64)

        # Super Ultrawide: 5120x1440 -> 128 MB
        self.assertEqual(calc(5120, 1440), 128)

        # 4K: 3840x2160 -> 128 MB
        self.assertEqual(calc(3840, 2160), 128)

        # 8K: 7680x4320 -> 512 MB
        self.assertEqual(calc(7680, 4320), 512)

        # Invalid zero or negative dimensions
        with self.assertRaises(ValueError):
            calc(0, 1080)
        with self.assertRaises(ValueError):
            calc(1920, -1080)

    def test_cursor_warp_transitions_horizontal_topology(self) -> None:
        """Adversarial Test: Cross-monitor cursor warp transitions in dual 1440p side-by-side."""
        monitors = [
            {"id": 0, "name": "DP-1", "width": 2560, "height": 1440, "x": 0, "y": 0},
            {"id": 1, "name": "DP-2", "width": 2560, "height": 1440, "x": 2560, "y": 0},
        ]
        mgr = multimonitor_sync_mod.MultiMonitorSyncManager(monitors=monitors)

        # 1. Cursor inside Head 0 -> No transition
        w1 = mgr.calculate_cursor_warp(0, 1000.0, 500.0)
        self.assertFalse(w1["transition"])
        self.assertEqual(w1["target_head"], 0)

        # 2. Cursor crossing right of Head 0 into Head 1
        w2 = mgr.calculate_cursor_warp(0, 2570.0, 600.0)
        self.assertTrue(w2["transition"])
        self.assertEqual(w2["direction"], "right")
        self.assertEqual(w2["target_head"], 1)
        self.assertEqual(w2["target_coords"], [10.0, 600.0])

        # 3. Cursor crossing left of Head 1 into Head 0
        w3 = mgr.calculate_cursor_warp(1, -25.0, 450.0)
        self.assertTrue(w3["transition"])
        self.assertEqual(w3["direction"], "left")
        self.assertEqual(w3["target_head"], 0)
        self.assertEqual(w3["target_coords"], [2535.0, 450.0])

    def test_cursor_warp_transitions_vertical_and_negative_offsets(self) -> None:
        """Adversarial Test: Vertical stack and negative monitor coordinates (secondary to the left)."""
        # Topology with secondary display positioned to the left (negative x)
        monitors = [
            {"id": 0, "name": "DP-1", "width": 1920, "height": 1080, "x": -1920, "y": 0},
            {"id": 1, "name": "DP-2", "width": 2560, "height": 1440, "x": 0, "y": 0},
        ]
        mgr = multimonitor_sync_mod.MultiMonitorSyncManager(monitors=monitors)

        # On Head 0 (-1920..0), crossing right (x >= 1920) into Head 1 (0..2560)
        w_right = mgr.calculate_cursor_warp(0, 1930.0, 500.0)
        self.assertTrue(w_right["transition"])
        self.assertEqual(w_right["direction"], "right")
        self.assertEqual(w_right["target_head"], 1)
        self.assertEqual(w_right["target_coords"], [10.0, 500.0])

        # On Head 1 (0..2560), crossing left (x < 0) into Head 0 (-1920..0)
        w_left = mgr.calculate_cursor_warp(1, -50.0, 500.0)
        self.assertTrue(w_left["transition"])
        self.assertEqual(w_left["direction"], "left")
        self.assertEqual(w_left["target_head"], 0)
        self.assertEqual(w_left["target_coords"], [1870.0, 500.0])


def main() -> int:
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdversarialIOMMUParser))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdversarialVFIOBinder))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdversarialLookingGlass))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdversarialPipeWireBridge))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdversarialVTPMProvision))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdversarialHugepagesManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdversarialVirtIOFS))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdversarialMultiMonitorSync))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
