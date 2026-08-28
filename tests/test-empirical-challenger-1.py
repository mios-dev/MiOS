# AI-hint: Unit and regression test suite for test-empirical-challenger-1 functionality.
# AI-related: mios-cephfs-provision, mios-sec-idemp, mios-perm-scan
# AI-functions: load_module, test_fuel_exhaustion_boundaries, test_memory_ceiling_boundaries, test_host_imports_stress_and_edge_cases, test_escape_toml_key_special_characters, test_format_toml_value_escaped_strings_and_types, test_format_toml_value_nested_tables_and_lists, test_format_toml_value_null_observation, test_resolve_uid_numeric_and_edge_cases, test_get_user_info_numeric_and_edge_cases, test_load_cephfs_config_schema, test_cli_argument_handling

import os
import sys
import unittest
import tempfile
import stat
import secrets
import json
import tomllib
import subprocess
import time
import math
import importlib.util
import importlib.machinery

_HERE = os.path.abspath(os.path.dirname(__file__)) if "__file__" in globals() else os.path.abspath(".")
_ROOT = os.path.normpath(os.path.join(_HERE, "..")) if os.path.basename(_HERE) == "tests" else _HERE

def load_module(name, rel_path):
    full_path = os.path.join(_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, full_path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    loader = importlib.machinery.SourceFileLoader(name, full_path)
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios"))
sys.path.insert(0, os.path.join(_ROOT, "lib", "mios"))

wasm = load_module("wasm_sandbox", "usr/libexec/mios/node/wasm_sandbox.py")
mat = load_module("materialize_config_toml", "usr/libexec/mios/materialize-config-toml.py")
cephfs = load_module("cephfs_provision", "usr/libexec/mios/mios-cephfs-provision")
boot = load_module("verify_boot_chain", "usr/libexec/mios/sec/verify-boot-chain.py")
sec = load_module("rotate_quadlet_secrets", "usr/libexec/mios/sec/rotate-quadlet-secrets.py")
lg = load_module("setup_looking_glass", "usr/libexec/mios/vfio/setup-looking-glass.py")

class TestAdversarialWasmSandbox(unittest.TestCase):
    """Stress tests on Wasm Sandbox fuel, memory, opcodes, and host imports."""

    def test_fuel_exhaustion_boundaries(self):
        # 1. Exact fuel limit boundary
        config = wasm.WasmExecutionConfig(max_fuel=1000)
        engine = wasm.WasmSandboxEngine(config)

        # fuel == max_fuel (1000 == 1000) -> should PASS
        res_exact = engine.execute(b"\x00asm\x01\x00\x00\x00", b"test", simulated_fuel_cost=1000)
        self.assertTrue(res_exact.success)
        self.assertEqual(res_exact.exit_code, 0)
        self.assertEqual(res_exact.fuel_consumed, 1000)

        # fuel == max_fuel + 1 (1001 > 1000) -> should FAIL with 124
        res_over = engine.execute(b"\x00asm\x01\x00\x00\x00", b"test", simulated_fuel_cost=1001)
        self.assertFalse(res_over.success)
        self.assertEqual(res_over.exit_code, 124)
        self.assertIn("Fuel limit exhausted", res_over.error_msg)

        # zero fuel limit with non-zero cost -> should FAIL with 124
        config_zero = wasm.WasmExecutionConfig(max_fuel=0)
        engine_zero = wasm.WasmSandboxEngine(config_zero)
        res_zero = engine_zero.execute(b"\x00asm\x01\x00\x00\x00", b"test", simulated_fuel_cost=1)
        self.assertFalse(res_zero.success)
        self.assertEqual(res_zero.exit_code, 124)

    def test_memory_ceiling_boundaries(self):
        limit = 64 * 1024 * 1024  # 64MB
        config = wasm.WasmExecutionConfig(max_memory_bytes=limit)
        engine = wasm.WasmSandboxEngine(config)

        # Exact boundary: alloc == limit -> PASS
        res_exact = engine.execute(b"\x00asm\x01\x00\x00\x00", b"test", simulated_alloc_bytes=limit)
        self.assertTrue(res_exact.success)
        self.assertEqual(res_exact.exit_code, 0)
        self.assertEqual(res_exact.memory_used_bytes, limit)

        # Over-allocation by 1 byte: alloc == limit + 1 -> FAIL with 137
        res_over_1 = engine.execute(b"\x00asm\x01\x00\x00\x00", b"test", simulated_alloc_bytes=limit + 1)
        self.assertFalse(res_over_1.success)
        self.assertEqual(res_over_1.exit_code, 137)
        self.assertIn("Memory limit exceeded", res_over_1.error_msg)

        # Massive over-allocation: 1GB, 10GB
        res_huge = engine.execute(b"\x00asm\x01\x00\x00\x00", b"test", simulated_alloc_bytes=10 * 1024 * 1024 * 1024)
        self.assertFalse(res_huge.success)
        self.assertEqual(res_huge.exit_code, 137)

    def test_host_imports_stress_and_edge_cases(self):
        # Test HostImports with empty payload
        host_empty = wasm.HostImports(b"")
        self.assertEqual(host_empty.mios_sys_read(0, 10), b"")
        self.assertEqual(host_empty.mios_sys_read(100, 50), b"")

        # Test HostImports with large payload and out-of-bounds offsets
        payload = b"X" * 1_000_000  # 1MB input
        host = wasm.HostImports(payload)
        self.assertEqual(len(host.mios_sys_read(0, 500)), 500)
        self.assertEqual(len(host.mios_sys_read(999_900, 200)), 100) # clamped to remaining bytes
        self.assertEqual(host.mios_sys_read(2_000_000, 100), b"")

        # Test mios_sys_write with binary data including null bytes and unicode
        written = host.mios_sys_write(b"\x00\xff\xfe\xfd" * 1000)
        self.assertEqual(written, 4000)
        self.assertEqual(len(host.output_data), 4000)

        # Test logging special characters and rapid succession
        for i in range(100):
            host.mios_sys_log(f"log_{i}: \x00 <xml> & \" ' \n")
        self.assertEqual(len(host.logs), 100)
        self.assertTrue(host.logs[0].startswith("[wasm_guest] log_0:"))

        # Test time monotonically increases or stays non-negative
        t1 = host.mios_sys_time()
        t2 = host.mios_sys_time()
        self.assertIsInstance(t1, int)
        self.assertGreater(t1, 0)
        self.assertGreaterEqual(t2, t1)

        # Test exit codes
        host.mios_sys_exit(42)
        self.assertTrue(host.exited)
        self.assertEqual(host.exit_code, 42)

class TestAdversarialTOMLMaterializer(unittest.TestCase):
    """Stress tests on TOML key escaping and value formatting against the TOML spec."""

    def test_escape_toml_key_special_characters(self):
        # Bare keys: letters, digits, underscores, hyphens
        self.assertEqual(mat.escape_toml_key("valid_key-123"), "valid_key-123")
        self.assertEqual(mat.escape_toml_key("ALPHA_BETA"), "ALPHA_BETA")

        # Special characters must be quoted
        self.assertEqual(mat.escape_toml_key("key.with.dots"), '"key.with.dots"')
        self.assertEqual(mat.escape_toml_key("key with spaces"), '"key with spaces"')
        self.assertEqual(mat.escape_toml_key("key:colon"), '"key:colon"')
        self.assertEqual(mat.escape_toml_key("key/slash"), '"key/slash"')
        self.assertEqual(mat.escape_toml_key('key"with"quotes'), '"key\\"with\\"quotes"')
        self.assertEqual(mat.escape_toml_key("key\\backslash"), '"key\\\\backslash"')

        # Check that generated escaped keys parse in a TOML doc
        test_keys = ["foo", "foo-bar", "foo_bar", "foo.bar", "foo bar", "foo:bar", 'foo"bar', "foo\\bar", "123", ""]
        for k in test_keys:
            esc = mat.escape_toml_key(k)
            doc = f"{esc} = 42\n"
            try:
                parsed = tomllib.loads(doc)
                self.assertIn(k, parsed)
                self.assertEqual(parsed[k], 42)
            except Exception as e:
                self.fail(f"Failed to parse TOML key {k!r} (escaped as {esc!r}): {e}")

    def test_format_toml_value_escaped_strings_and_types(self):
        # Standard primitives
        self.assertEqual(mat.format_toml_value(True), "true")
        self.assertEqual(mat.format_toml_value(False), "false")
        self.assertEqual(mat.format_toml_value(0), "0")
        self.assertEqual(mat.format_toml_value(-42), "-42")
        self.assertEqual(mat.format_toml_value(3.14159), "3.14159")

        # Strings with escaped characters
        s_quote = 'string with "quotes" and \\backslashes\\ and \nnewlines'
        formatted_s = mat.format_toml_value(s_quote)
        doc = f"val = {formatted_s}\n"
        parsed = tomllib.loads(doc)
        self.assertEqual(parsed["val"], s_quote)

        # Unicode and emojis
        unicode_str = "MiOS 🚀 日本語 🤖 \u2764"
        formatted_u = mat.format_toml_value(unicode_str)
        doc_u = f"val = {formatted_u}\n"
        parsed_u = tomllib.loads(doc_u)
        self.assertEqual(parsed_u["val"], unicode_str)

    def test_format_toml_value_nested_tables_and_lists(self):
        # Nested list of strings and ints
        nested_list = [1, "two", [3, "four", [5, 6]]]
        fmt_list = mat.format_toml_value(nested_list)
        doc_list = f"list_key = {fmt_list}\n"
        parsed_list = tomllib.loads(doc_list)
        self.assertEqual(parsed_list["list_key"], nested_list)

        # Nested dict (inline table)
        nested_dict = {
            "a": 1,
            "b": "text",
            "c": {"sub1": True, "sub2": [10, 20]}
        }
        fmt_dict = mat.format_toml_value(nested_dict)
        doc_dict = f"table_key = {fmt_dict}\n"
        parsed_dict = tomllib.loads(doc_dict)
        self.assertEqual(parsed_dict["table_key"], nested_dict)

        # Empty structures
        self.assertEqual(mat.format_toml_value([]), "[]")
        self.assertEqual(mat.format_toml_value({}), "{}")
        parsed_empty = tomllib.loads("empty_list = []\nempty_dict = {}\n")
        self.assertEqual(parsed_empty["empty_list"], [])
        self.assertEqual(parsed_empty["empty_dict"], {})

    def test_format_toml_value_null_observation(self):
        # Document the behavior for None
        res_none = mat.format_toml_value(None)
        self.assertEqual(res_none, "None")
        # In TOML, 'None' as an unquoted token is invalid syntax
        with self.assertRaises(Exception):
            tomllib.loads(f"key = {res_none}\n")

class TestAdversarialCephFSProvisioner(unittest.TestCase):
    """Stress tests on CephFS Provisioner UID resolution, user lookup, and argument handling."""

    def test_resolve_uid_numeric_and_edge_cases(self):
        self.assertEqual(cephfs.resolve_uid_number("1000"), 1000)
        self.assertEqual(cephfs.resolve_uid_number("0"), 0)
        self.assertEqual(cephfs.resolve_uid_number("  65534  "), 65534)

        # Non-existent user fallback
        self.assertEqual(cephfs.resolve_uid_number("nonexistent_user_xyz_9999"), 1000)
        self.assertEqual(cephfs.resolve_uid_number(""), 1000)
        self.assertEqual(cephfs.resolve_uid_number("!@#$%^"), 1000)

    def test_get_user_info_numeric_and_edge_cases(self):
        # Numeric UID string
        name, gid = cephfs.get_user_info("1000")
        self.assertTrue(len(name) > 0)
        self.assertIsInstance(gid, int)

        # String username
        name_str, gid_str = cephfs.get_user_info("root")
        self.assertEqual(name_str, "root")
        self.assertIsInstance(gid_str, int)

        # Arbitrary/Unknown user string fallback
        name_unk, gid_unk = cephfs.get_user_info("unknown_test_user")
        self.assertEqual(name_unk, "unknown_test_user")
        self.assertEqual(gid_unk, 1000)

    def test_load_cephfs_config_schema(self):
        cfg = cephfs.load_cephfs_config()
        self.assertIsInstance(cfg, dict)
        self.assertIn("cluster_name", cfg)
        self.assertIn("monitors", cfg)
        self.assertIn("fs_name", cfg)
        self.assertIn("tenant_id", cfg)
        self.assertIn("keyring_dir", cfg)
        self.assertIn("subvolume_mode", cfg)

    def test_cli_argument_handling(self):
        # Test subcommands with missing arguments via subprocess
        script_path = os.path.join(_ROOT, "usr", "libexec", "mios", "mios-cephfs-provision")

        # When CephFS is disabled, main() exits 0 as no-op early
        p = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.assertIn("CephFS storage integration is disabled", p.stdout)

class TestAdversarialBootChainVerifier(unittest.TestCase):
    """Stress tests on UKI PE header magic, PCR measurements, and fs-verity digests."""

    def test_check_uki_structure_pe_magic(self):
        verifier = boot.BootChainVerifier(mock=True)

        # Valid MZ PE magic
        valid_pe = b"MZ" + (b"\x00" * 62)
        self.assertTrue(verifier.check_uki_structure(valid_pe))

        # Valid with trailing payload
        self.assertTrue(verifier.check_uki_structure(b"MZ" + (b"\xff" * 2048)))

        # Invalid magic: reversed "ZM"
        self.assertFalse(verifier.check_uki_structure(b"ZM" + (b"\x00" * 62)))

        # Invalid magic: ELF header
        self.assertFalse(verifier.check_uki_structure(b"\x7fELF" + (b"\x00" * 60)))

        # Truncated headers (< 64 bytes)
        self.assertFalse(verifier.check_uki_structure(b""))
        self.assertFalse(verifier.check_uki_structure(b"MZ"))
        self.assertFalse(verifier.check_uki_structure(b"MZ" + (b"\x00" * 61)))  # 63 bytes

    def test_verify_pcr_measurements(self):
        verifier = boot.BootChainVerifier(mock=True)

        valid_pcrs = {
            4: "4" * 64,
            7: "7" * 64,
            11: "a" * 64,
        }
        self.assertTrue(verifier.verify_pcr_measurements(valid_pcrs))

        # Missing required PCRs
        for missing in [4, 7, 11]:
            corrupted = dict(valid_pcrs)
            del corrupted[missing]
            self.assertFalse(verifier.verify_pcr_measurements(corrupted))

        # Corrupted PCR lengths (SHA256 must be 64 hex chars)
        self.assertFalse(verifier.verify_pcr_measurements({4: "a" * 63, 7: "b" * 64, 11: "c" * 64}))
        self.assertFalse(verifier.verify_pcr_measurements({4: "a" * 65, 7: "b" * 64, 11: "c" * 64}))
        self.assertFalse(verifier.verify_pcr_measurements({4: "", 7: "b" * 64, 11: "c" * 64}))

        # Extra PCRs present alongside required 4, 7, 11
        extended_pcrs = dict(valid_pcrs)
        extended_pcrs[0] = "0" * 64
        extended_pcrs[1] = "1" * 64
        self.assertTrue(verifier.verify_pcr_measurements(extended_pcrs))

    def test_verify_fsverity_digest_real_file(self):
        verifier = boot.BootChainVerifier(mock=False)
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"fsverity_test_content_block")
            temp_name = tf.name

        try:
            import hashlib
            expected = hashlib.sha256(b"fsverity_test_content_block").hexdigest()
            # Matching digest
            self.assertTrue(verifier.verify_fsverity_digest(temp_name, expected))
            self.assertTrue(verifier.verify_fsverity_digest(temp_name, expected.upper()))

            # Mismatched digest
            wrong = hashlib.sha256(b"corrupted_block").hexdigest()
            self.assertFalse(verifier.verify_fsverity_digest(temp_name, wrong))
        finally:
            os.remove(temp_name)

    def test_cli_verification_runner(self):
        rc_mock = boot.run_verification(mock=True, json_output=True)
        self.assertEqual(rc_mock, 0)

class TestAdversarialQuadletSecrets(unittest.TestCase):
    """Stress tests on Quadlet secrets token entropy, idempotency, and permission hardening."""

    def test_token_rotation_entropy_and_uniqueness(self):
        hardener = sec.QuadletSecretsHardener()
        tokens = set()
        count = 10_000

        for _ in range(count):
            tok, line = hardener.generate_rotated_secret("TEST_SECRET", length_bytes=32)
            self.assertEqual(len(tok), 64)
            self.assertTrue(all(c in "0123456789abcdef" for c in tok))
            self.assertEqual(line, f"TEST_SECRET={tok}\n")
            tokens.add(tok)

        # Verify zero collisions across 10,000 generated 256-bit tokens
        self.assertEqual(len(tokens), count)

    def test_init_secrets_env_idempotency_and_preservation(self):
        with tempfile.TemporaryDirectory(prefix="mios-sec-idemp-") as tmpdir:
            sec_file = os.path.join(tmpdir, "secrets.env")
            hardener = sec.QuadletSecretsHardener(secrets_dir=tmpdir)

            # 1. First initialization on empty file
            first_run = hardener.init_secrets_env(secrets_file=sec_file)
            self.assertIn("POSTGRES_PASSWORD", first_run)
            self.assertIn("K3S_TOKEN", first_run)
            first_token = first_run["K3S_TOKEN"]

            # 2. Run 10 consecutive times — all tokens MUST remain identical
            for _ in range(10):
                subsequent_run = hardener.init_secrets_env(secrets_file=sec_file)
                self.assertEqual(subsequent_run, first_run)
                self.assertEqual(subsequent_run["K3S_TOKEN"], first_token)

            # 3. Add custom complex secrets with =, #, and spaces
            with open(sec_file, "a", encoding="utf-8") as f:
                f.write("CUSTOM_CONN_STR=postgresql://user:p=w@d/db?ssl=true\n")
                f.write("SPACED_KEY = spaced_value_123 \n")

            custom_run = hardener.init_secrets_env(secrets_file=sec_file)
            self.assertEqual(custom_run["CUSTOM_CONN_STR"], "postgresql://user:p=w@d/db?ssl=true")
            self.assertEqual(custom_run["SPACED_KEY"], "spaced_value_123")
            self.assertEqual(custom_run["K3S_TOKEN"], first_token)

    def test_permission_hardening_scan(self):
        with tempfile.TemporaryDirectory(prefix="mios-perm-scan-") as tmpdir:
            f1 = os.path.join(tmpdir, "app.env")
            f2 = os.path.join(tmpdir, "db.secret")
            f3 = os.path.join(tmpdir, "ignored.txt")

            for f in [f1, f2, f3]:
                with open(f, "w") as fp:
                    fp.write("KEY=VAL\n")
                os.chmod(f, 0o644)

            hardener = sec.QuadletSecretsHardener(secrets_dir=tmpdir)
            fixed = hardener.audit_and_harden_permissions(tmpdir)

            self.assertIn(f1, fixed)
            self.assertIn(f2, fixed)
            self.assertNotIn(f3, fixed)

class TestAdversarialLookingGlass(unittest.TestCase):
    """Stress tests on Looking Glass IVSHMEM sizing, XML generation, and verification."""

    def test_xml_generation_standard_and_extreme_sizes(self):
        sizes = [16, 32, 64, 128, 256, 512, 1024, 0, -64, 33]
        for sz in sizes:
            lg_mgr = lg.LookingGlassManager(size_mb=sz)
            xml = lg_mgr.generate_ivshmem_xml()
            self.assertIn('<shmem name="looking-glass">', xml)
            self.assertIn('<model type="ivshmem-plain"/>', xml)
            self.assertIn(f'<size unit="M">{sz}</size>', xml)

    def test_mock_and_real_verification(self):
        lg_mgr = lg.LookingGlassManager(shm_path="/nonexistent/shm/file", device_node="/nonexistent/kvmfr")
        # Mock mode passes
        res_mock = lg_mgr.verify_all(mock=True)
        self.assertEqual(res_mock["status"], "pass")

        # Non-mock mode on nonexistent files fails (on POSIX systems)
        if os.name != "nt":
            res_real = lg_mgr.verify_all(mock=False)
            self.assertEqual(res_real["status"], "fail")
            self.assertEqual(res_real["checks"]["shm_allocation"], "fail")
            self.assertEqual(res_real["checks"]["kvmfr_device"], "fail")

if __name__ == "__main__":
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialWasmSandbox))
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialTOMLMaterializer))
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialCephFSProvisioner))
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialBootChainVerifier))
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialQuadletSecrets))
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialLookingGlass))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
