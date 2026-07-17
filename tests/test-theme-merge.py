# AI-hint: Hermetic negative-tests and validation unit tests for all dotfiles merge kinds (AGY-60).
# AI-related: tests/test-theme-merge.py, usr/libexec/mios/mios-theme-render
# AI-functions: TestThemeMerge, main

import unittest
import tempfile
import os
import shutil
import subprocess
import sys
import json

class TestThemeMerge(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = self.temp_dir.name
        
        # Create directory layout
        self.dirs = [
            "usr/share/mios",
            "usr/share/mios/theme/templates",
            "usr/share/mios/theme/fixtures",
            "usr/libexec/mios",
            "etc/mios"
        ]
        for d in self.dirs:
            os.makedirs(os.path.join(self.root, d), exist_ok=True)

        self.render_script = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "mios-theme-render")
        )

        # Standard baseline files
        self.write_vendor_toml({
            "meta": {"mios_version": "0.3.0"},
            "colors": {"accent": "#123456"}
        })

    def tearDown(self):
        self.temp_dir.cleanup()

    def get_env(self, user_toml=None):
        env = os.environ.copy()
        env["MIOS_THEME_ROOT"] = self.root
        env["MIOS_VENDOR_TOML"] = os.path.join(self.root, "usr/share/mios/mios.toml")
        env["MIOS_HOST_TOML"] = os.path.join(self.root, "etc/mios/mios-host.toml")
        if user_toml:
            env["MIOS_USER_TOML"] = user_toml
        else:
            env["MIOS_USER_TOML"] = os.path.join(self.root, "etc/mios/mios-user-none.toml")
        # Ensure sys.path includes the repo's usr/lib/mios for mios_toml import
        repo_lib = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios"))
        env["PYTHONPATH"] = repo_lib + os.pathsep + env.get("PYTHONPATH", "")
        return env

    def write_vendor_toml(self, data):
        path = os.path.join(self.root, "usr/share/mios/mios.toml")
        with open(path, "w", encoding="utf-8") as f:
            for section, keys in data.items():
                if section == "dotfiles" and "registry" in keys:
                    for name, cfg in keys["registry"].items():
                        f.write(f"[dotfiles.registry.{name}]\n")
                        for k, v in cfg.items():
                            if isinstance(v, dict):
                                f.write(f"[dotfiles.registry.{name}.{k}]\n")
                                for sk, sv in v.items():
                                    f.write(f'{sk} = "{sv}"\n')
                            elif isinstance(v, str):
                                f.write(f'{k} = "{v}"\n')
                            else:
                                f.write(f'{k} = {str(v).lower() if isinstance(v, bool) else v}\n')
                        f.write("\n")
                else:
                    f.write(f"[{section}]\n")
                    for k, v in keys.items():
                        if isinstance(v, str):
                            f.write(f'{k} = "{v}"\n')
                        else:
                            f.write(f'{k} = {str(v).lower() if isinstance(v, bool) else v}\n')
                    f.write("\n")

    def run_cmd(self, args, user_toml=None):
        cmd = [sys.executable, self.render_script] + args
        return subprocess.run(cmd, env=self.get_env(user_toml), capture_output=True, text=True)

    def test_unknown_kind_aborts(self):
        # 1. Unknown kind in surface definition => exit 3
        self.write_vendor_toml({
            "dotfiles": {
                "registry": {
                    "bad-kind": {
                        "template": "usr/share/mios/theme/templates/bad.tmpl",
                        "target": "usr/share/mios/theme/fixtures/bad.expected",
                        "kind": "unknown-kind-xyz"
                    }
                }
            }
        })
        res = self.run_cmd(["check", "bad-kind"])
        self.assertEqual(res.returncode, 3)
        self.assertIn("unknown kind", res.stderr)

    def test_missing_fixture_aborts(self):
        # 2. A merge surface missing its fixture.base/expected => exit 3
        self.write_vendor_toml({
            "dotfiles": {
                "registry": {
                    "missing-fx": {
                        "template": "usr/share/mios/theme/templates/missing.tmpl",
                        "target": "usr/share/mios/theme/fixtures/missing.expected",
                        "kind": "json-merge"
                    }
                }
            }
        })
        res = self.run_cmd(["check", "missing-fx"])
        self.assertEqual(res.returncode, 3)
        self.assertIn("MUST declare fixture.base + fixture.expected", res.stderr)

    def test_json_merge_semantics(self):
        # 3. json-merge preserves foreign top-level key, a // URL, a nested key,
        # and refuses an unparseable base (exit 2)
        self.write_vendor_toml({
            "colors": {"accent": "#112233"},
            "dotfiles": {
                "registry": {
                    "json-surface": {
                        "template": "usr/share/mios/theme/templates/jsonsurface.json.tmpl",
                        "target": "usr/share/mios/theme/fixtures/jsonsurface.expected.json",
                        "kind": "json-merge",
                        "fixture": {
                            "base": "usr/share/mios/theme/fixtures/jsonsurface.base.json",
                            "expected": "usr/share/mios/theme/fixtures/jsonsurface.expected.json"
                        }
                    }
                }
            }
        })

        # Write template
        tmpl_path = os.path.join(self.root, "usr/share/mios/theme/templates/jsonsurface.json.tmpl")
        with open(tmpl_path, "w", encoding="utf-8") as f:
            f.write('{"mykey": "@MIOS:accent@"}\n')

        # Write valid base containing foreign keys, double slashes URL, and nested keys
        base_path = os.path.join(self.root, "usr/share/mios/theme/fixtures/jsonsurface.base.json")
        base_content = {
            "foreign_key": "preserved_val",
            "url": "https://foreign-url.com//some//path",
            "nested": {
                "foreign_sub": 42
            }
        }
        with open(base_path, "w", encoding="utf-8") as f:
            json.dump(base_content, f)

        # Run render to generate expected
        res = self.run_cmd(["render", "json-surface"])
        self.assertEqual(res.returncode, 0)

        # Verify expected contains both merged and foreign/nested keys
        expected_path = os.path.join(self.root, "usr/share/mios/theme/fixtures/jsonsurface.expected.json")
        with open(expected_path, "r", encoding="utf-8") as f:
            expected = json.load(f)

        self.assertEqual(expected.get("mykey"), "#112233")
        self.assertEqual(expected.get("foreign_key"), "preserved_val")
        self.assertEqual(expected.get("url"), "https://foreign-url.com//some//path")
        self.assertEqual(expected["nested"].get("foreign_sub"), 42)

        # Refuses an unparseable base => exit 2, writes nothing
        with open(base_path, "w", encoding="utf-8") as f:
            f.write("{invalid-json-structure\n")

        res_bad = self.run_cmd(["render", "json-surface"])
        self.assertEqual(res_bad.returncode, 2)
        self.assertIn("REFUSED: json-merge base did not parse", res_bad.stderr)

    def test_ini_merge_semantics(self):
        # 4. ini-merge preserves credential/signingkey/[remote], seeds absent owned keys,
        # and under seed-or-enforce policy skips present foreign values unless operator_set.
        self.write_vendor_toml({
            "colors": {"accent": "#223344"},
            "dotfiles": {
                "registry": {
                    "ini-surface": {
                        "template": "usr/share/mios/theme/templates/inisurface.tmpl",
                        "target": "usr/share/mios/theme/fixtures/inisurface.expected",
                        "kind": "ini-merge",
                        "section": "colors",
                        "policy": "seed-or-enforce",
                        "fixture": {
                            "base": "usr/share/mios/theme/fixtures/inisurface.base",
                            "expected": "usr/share/mios/theme/fixtures/inisurface.expected"
                        }
                    }
                }
            }
        })

        # Write template
        tmpl_path = os.path.join(self.root, "usr/share/mios/theme/templates/inisurface.tmpl")
        with open(tmpl_path, "w", encoding="utf-8") as f:
            f.write("[colors]\nmykey = @MIOS:colors_accent@\n")

        # Write base containing foreign credential, signingkey, remotes + a present owned key
        base_path = os.path.join(self.root, "usr/share/mios/theme/fixtures/inisurface.base")
        base_lines = [
            "[credential]",
            "helper = cache",
            "[user]",
            "signingkey = ABCDEF",
            "[remote \"origin\"]",
            "url = git@github.com:user/repo.git",
            "[colors]",
            "mykey = #existing_val"
        ]
        with open(base_path, "w", encoding="utf-8") as f:
            f.write("\n".join(base_lines) + "\n")

        # Case A: operator_set is False (vendor color accent is #223344, no user overlay).
        # Under seed-or-enforce, the existing value #existing_val should be skipped/preserved.
        res = self.run_cmd(["render", "ini-surface"])
        self.assertEqual(res.returncode, 0)

        expected_path = os.path.join(self.root, "usr/share/mios/theme/fixtures/inisurface.expected")
        with open(expected_path, "r", encoding="utf-8") as f:
            expected_content = f.read()

        self.assertIn("signingkey = ABCDEF", expected_content)
        self.assertIn("helper = cache", expected_content)
        self.assertIn("url = git@github.com:user/repo.git", expected_content)
        # mykey is preserved as #existing_val (not updated to #223344) because operator_set is False
        self.assertIn("mykey = #existing_val", expected_content)

        # Case B: operator_set is True (user overlay overrides colors.accent to #998877).
        # Under seed-or-enforce, the user overlay should enforce the value over #existing_val.
        user_toml_path = os.path.join(self.root, "etc/mios/mios-user-overlay.toml")
        with open(user_toml_path, "w", encoding="utf-8") as f:
            f.write("[colors]\naccent = \"#998877\"\n")

        res_overlay = self.run_cmd(["render", "ini-surface"], user_toml=user_toml_path)
        self.assertEqual(res_overlay.returncode, 0)

        with open(expected_path, "r", encoding="utf-8") as f:
            expected_content_overlay = f.read()

        self.assertIn("signingkey = ABCDEF", expected_content_overlay)
        # mykey is updated to #998877 because colors.accent is explicitly overridden in user overlay
        self.assertIn("mykey = #998877", expected_content_overlay)

    def test_tampered_expected_fails_check(self):
        # 5. Tampering any merge surface's fixture.expected results in check failing
        self.write_vendor_toml({
            "colors": {"accent": "#111111"},
            "dotfiles": {
                "registry": {
                    "check-surface": {
                        "template": "usr/share/mios/theme/templates/check.tmpl",
                        "target": "usr/share/mios/theme/fixtures/check.expected",
                        "kind": "json-merge",
                        "fixture": {
                            "base": "usr/share/mios/theme/fixtures/check.base",
                            "expected": "usr/share/mios/theme/fixtures/check.expected"
                        }
                    }
                }
            }
        })

        # Write template, base, and matching expected
        tmpl_path = os.path.join(self.root, "usr/share/mios/theme/templates/check.tmpl")
        with open(tmpl_path, "w", encoding="utf-8") as f:
            f.write('{"val": "@MIOS:accent@"}\n')

        base_path = os.path.join(self.root, "usr/share/mios/theme/fixtures/check.base")
        with open(base_path, "w", encoding="utf-8") as f:
            f.write('{\n  "other": 1\n}\n')

        # Run render to generate baseline expected fixture
        res_render = self.run_cmd(["render", "check-surface"])
        self.assertEqual(res_render.returncode, 0)

        # Baseline check should pass
        res_pass = self.run_cmd(["check", "check-surface"])
        self.assertEqual(res_pass.returncode, 0)

        # Tamper expected fixture
        expected_path = os.path.join(self.root, "usr/share/mios/theme/fixtures/check.expected")
        with open(expected_path, "w", encoding="utf-8") as f:
            f.write('{\n  "other": 1,\n  "val": "#tampered_val"\n}\n')

        # Check should now fail
        res_fail = self.run_cmd(["check", "check-surface"])
        self.assertEqual(res_fail.returncode, 1)
        self.assertIn("drifted from SSOT projection", res_fail.stderr)

if __name__ == "__main__":
    unittest.main()
