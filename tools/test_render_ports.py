#!/usr/bin/env python3
# AI-hint: Unit tests for render-ports.py -- proves the [ports.categories] allocator derives base + index*stride, honours pinned ports, and that the sche...
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_test_render_ports_py.md

import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))


def load_module():
    spec = importlib.util.spec_from_file_location(
        "render_ports", os.path.join(_HERE, "render-ports.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rp = load_module()


def _schema(**overrides):
    data = {
        "ports": {
            "stack_id": 0,
            "agent_pipe": 8700,
            "prefilter": 8710,
            "hermes": 8720,
            "adguard_ui": 8050,
            "adguard_dns": 53,
            "categories": {
                "agent": {
                    "base": 8700, "stride": 10,
                    "members": ["agent_pipe", "prefilter", "hermes"],
                },
                "edge": {
                    "base": 8050, "stride": 1,
                    "members": ["adguard_ui"],
                    "pinned": {"adguard_dns": 53},
                },
            },
        }
    }
    data["ports"].update(overrides)
    return data


class TestDerivePorts(unittest.TestCase):
    def test_base_plus_index_times_stride(self):
        got = rp.derive_ports(_schema())
        self.assertEqual(got["agent_pipe"], 8700)
        self.assertEqual(got["prefilter"], 8710)
        self.assertEqual(got["hermes"], 8720)

    def test_pinned_is_verbatim_and_ignores_base(self):
        got = rp.derive_ports(_schema())
        self.assertEqual(got["adguard_dns"], 53)

    def test_retargeting_a_base_moves_the_whole_category(self):
        data = _schema()
        data["ports"]["categories"]["agent"]["base"] = 9200
        got = rp.derive_ports(data)
        self.assertEqual(
            [got["agent_pipe"], got["prefilter"], got["hermes"]],
            [9200, 9210, 9220])
        # an untouched category must not move
        self.assertEqual(got["adguard_ui"], 8050)

    def test_appending_a_member_allocates_the_next_slot(self):
        data = _schema()
        data["ports"]["categories"]["agent"]["members"].append("newsvc")
        got = rp.derive_ports(data)
        self.assertEqual(got["newsvc"], 8730)

    def test_no_categories_is_a_noop(self):
        self.assertEqual(rp.derive_ports({"ports": {"ssh": 22}}), {})


class TestFindViolations(unittest.TestCase):
    def test_clean_schema_has_no_violations(self):
        self.assertEqual(rp.find_violations(_schema()), [])

    def test_detects_band_overlap(self):
        data = _schema()
        data["ports"]["categories"]["edge"]["base"] = 8700
        data["ports"]["adguard_ui"] = 8700
        problems = rp.find_violations(data)
        self.assertTrue(any("overlap" in p for p in problems), problems)

    def test_detects_value_collision(self):
        data = _schema()
        data["ports"]["categories"]["edge"]["members"] = ["adguard_ui", "dupe"]
        data["ports"]["categories"]["edge"]["base"] = 8700
        data["ports"]["dupe"] = 8701
        problems = rp.find_violations(data)
        self.assertTrue(any("collision" in p for p in problems), problems)

    def test_detects_port_in_no_category(self):
        data = _schema()
        data["ports"]["orphan"] = 8999
        problems = rp.find_violations(data)
        self.assertTrue(any("belongs to no category" in p for p in problems), problems)

    def test_detects_member_claimed_by_two_categories(self):
        data = _schema()
        data["ports"]["categories"]["edge"]["members"].append("hermes")
        problems = rp.find_violations(data)
        self.assertTrue(any("claimed by both" in p for p in problems), problems)

    def test_detects_flat_table_out_of_step_with_schema(self):
        data = _schema()
        data["ports"]["hermes"] = 1234
        problems = rp.find_violations(data)
        self.assertTrue(any("derives" in p for p in problems), problems)


class TestCategoryBand(unittest.TestCase):
    def test_band_spans_first_to_last_member(self):
        self.assertEqual(
            rp.category_band({"base": 8700, "stride": 10,
                              "members": ["a", "b", "c"]}),
            (8700, 8720))

    def test_empty_category_is_a_point(self):
        self.assertEqual(rp.category_band({"base": 8700, "members": []}),
                         (8700, 8700))


class TestRenderTable(unittest.TestCase):
    def test_rewrites_values_and_keeps_comments(self):
        text = "[ports]\nstack_id = 0\nhermes             = 1111    # the gateway\n"
        out = rp.render_table(text, {"hermes": 8720})
        self.assertIn("8720", out)
        self.assertIn("# the gateway", out)
        self.assertNotIn("1111", out)

    def test_leaves_stack_id_alone(self):
        text = "[ports]\nstack_id = 0\n"
        self.assertIn("stack_id = 0", rp.render_table(text, {"stack_id": 99}))

    def test_stops_at_the_next_table(self):
        text = "[ports]\nhermes = 1\n\n[other]\nhermes = 1\n"
        out = rp.render_table(text, {"hermes": 8720})
        self.assertEqual(out.count("8720"), 1)


class TestSweeperSkipsItsOwnEvidence(unittest.TestCase):
    """A fixture carrying a deliberately stale literal is how the sweeper is
    proven; rewriting it turns that proof green over nothing."""

    def test_test_fixtures_are_out_of_the_sweep(self):
        import os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        swept = {os.path.relpath(p, root).replace(os.sep, "/")
                 for p in rp._sweep_files(root)}
        offenders = sorted(f for f in swept
                           if f.startswith("tests/") or f.startswith("tools/test_"))
        self.assertEqual(offenders, [])

    def test_the_sweep_still_covers_real_source(self):
        # ...and the skip must not have hollowed the sweep out.
        import os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        swept = {os.path.relpath(p, root).replace(os.sep, "/")
                 for p in rp._sweep_files(root)}
        self.assertIn("usr/libexec/mios/mios-open-url", swept)
        self.assertGreater(len(swept), 200)


class TestStackIdOffset(unittest.TestCase):
    def test_stack_id_offset_shifts_non_pinned_ports(self):
        import sys
        sys.path.insert(0, os.path.join(_HERE, "..", "usr", "lib", "mios"))
        import mios_toml

        data = mios_toml.load_merged()
        ports = data.get("ports", {}) or {}
        offset = 10000
        shifted_ports = {}

        for k, v in ports.items():
            if isinstance(v, (int, str)) and str(v).isdigit():
                val = int(v)
                proc = mios_toml.process_val(f"ports.{k}", val, offset)
                shifted_ports[k] = int(proc)

                if k == "stack_id":
                    self.assertEqual(int(proc), val)
                elif val == 53:
                    self.assertEqual(int(proc), 53)
                else:
                    self.assertEqual(int(proc), val + offset)

        vals = list(shifted_ports.values())
        self.assertEqual(len(vals), len(set(vals)), "Collisions detected in shifted ports")


class TestQuadletPortFallbacks(unittest.TestCase):
    def test_quadlet_port_fallbacks_match_ssot(self):
        import re
        import sys
        sys.path.insert(0, os.path.join(_HERE, "..", "usr", "lib", "mios"))
        import mios_toml

        data = mios_toml.load_merged()
        ports = data.get("ports", {}) or {}

        container_dir = os.path.join(_HERE, "..", "usr", "share", "containers", "systemd")
        pattern = re.compile(r"\$\{MIOS_PORT_([A-Z0-9_]+):-(\d+)\}")

        tested = 0
        for fname in os.listdir(container_dir):
            if not fname.endswith(".container"):
                continue
            fpath = os.path.join(container_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            for match in pattern.finditer(content):
                var_name, fallback_str = match.groups()
                port_key = var_name.lower()
                ssot_val = ports.get(port_key)
                self.assertIsNotNone(
                    ssot_val,
                    f"Port key '{port_key}' in {fname} not found in SSOT [ports]"
                )
                self.assertEqual(
                    int(fallback_str), int(ssot_val),
                    f"In {fname}, ${{MIOS_PORT_{var_name}:-{fallback_str}}} does not match SSOT value {ssot_val}"
                )
                tested += 1

        self.assertGreater(tested, 40, f"Expected >40 Quadlet port fallbacks tested, got {tested}")


if __name__ == "__main__":
    unittest.main()
