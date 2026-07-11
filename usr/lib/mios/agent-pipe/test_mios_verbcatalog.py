# AI-hint: Stdlib unit test for mios_verbcatalog -- the verb/recipe catalog loader + 3-projection SSOT source. Writes a synthetic mios.toml [verbs.*]/[recipes.*], points MIOS_TOML at it, and asserts _load_verb_catalog parses it, the three projections (planner prose _render_verb_catalog, OpenAI/MCP schemas _verb_to_openai_tool / _recipe_to_openai_tool, model_name reverse map _build_model_name_map -> _resolve_verb_key) render the expected shapes, the per-arg synonym projection, and the deterministic _identity_answer. No network/DB.
# AI-related: ./mios_verbcatalog.py
# AI-functions: -
"""Offline unit tests for ``mios_verbcatalog`` (no network, no DB)."""

import os
import tempfile
import unittest

import mios_verbcatalog as VC


SYNTH_TOML = """
[verbs.open_app]
section = "Window / app launch"
sig = "name"
desc = "Open an application by name"
tier = "common"
permission = "write"
model_name = "launch_application"
hidden_aliases = ["open_application", "start_app"]
[verbs.open_app.params.name]
type = "string"
desc = "application name"
aliases = ["query", "title", "app", "target", "program", "path", "file", "binary", "exe"]

[verbs.recall]
section = "Memory"
sig = "query"
desc = "Recall a stored fact"
tier = "common"
permission = "read"
[verbs.recall.params.query]
type = "string"
desc = "what to recall"
default = ""
[verbs.recall.params.limit]
type = "integer"
default = 30
aliases = ["n", "top_k"]

[verbs.ui_button]
# No `section` key -> NOT an agent verb; must be rejected by the loader.
label = "Build"

[recipes.toast]
description = "Show a desktop toast"
args = ["message"]
permission = "read"
"""


class VerbCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.NamedTemporaryFile(
            "w", suffix=".toml", delete=False, encoding="utf-8")
        cls._tmp.write(SYNTH_TOML)
        cls._tmp.close()
        os.environ["MIOS_TOML"] = cls._tmp.name
        VC.configure(CATALOG_FAIL_MODE="warn")
        VC._DB_UNREACHABLE = True
        cls.cat = VC._load_verb_catalog()
        cls.model_map = VC._build_model_name_map(cls.cat)
        VC.configure(_VERB_CATALOG=cls.cat, _MODEL_NAME_TO_VERB=cls.model_map)

    @classmethod
    def tearDownClass(cls):
        try:
            os.unlink(cls._tmp.name)
        except OSError:
            pass

    def test_load_parses_only_agent_verbs(self):
        # open_app + recall carry `section`; ui_button does not -> rejected.
        self.assertIn("open_app", self.cat)
        self.assertIn("recall", self.cat)
        self.assertNotIn("ui_button", self.cat)
        self.assertEqual(self.cat["open_app"]["permission"], "write")
        self.assertEqual(self.cat["open_app"]["model_name"], "launch_application")
        self.assertEqual(
            self.cat["open_app"]["hidden_aliases"], ["open_application", "start_app"])

    def test_verb_to_openai_projection(self):
        tool = VC._verb_to_openai_tool("open_app", self.cat["open_app"])
        self.assertEqual(tool["type"], "function")
        # Model-facing name is the model_name alias; canonical key rides x-mios-verb.
        self.assertEqual(tool["function"]["name"], "launch_application")
        self.assertEqual(tool["x-mios-verb"], "open_app")
        self.assertEqual(tool["x-mios-permission"], "write")
        self.assertTrue(tool["function"]["strict"])
        params = tool["function"]["parameters"]
        self.assertEqual(params["additionalProperties"], False)
        self.assertIn("name", params["properties"])
        self.assertIn("name", params["required"])
        self.assertEqual(params["properties"]["name"]["type"], "string")

    def test_verb_to_openai_optional_param_nullable(self):
        # recall.limit has a default -> strict-mode nullable type.
        tool = VC._verb_to_openai_tool("recall", self.cat["recall"])
        spec = tool["function"]["parameters"]["properties"]["limit"]
        self.assertEqual(spec["type"], ["integer", "null"])
        # name == key when no model_name declared.
        self.assertEqual(tool["function"]["name"], "recall")

    def test_recipe_projection(self):
        rec = VC._load_recipe_catalog()
        self.assertIn("toast", rec)
        tool = VC._recipe_to_openai_tool("toast", rec["toast"])
        self.assertEqual(tool["function"]["name"], "mios_recipe__toast")
        self.assertEqual(tool["x-mios-recipe"], "toast")
        props = tool["function"]["parameters"]["properties"]
        self.assertIn("message", props)
        self.assertIn("os", props)            # injected OS selector
        self.assertEqual(props["message"]["type"], ["string", "null"])
        # Test typed dict recipe arguments
        rich_cfg = {
            "description": "Rich toast",
            "args": {
                "message": {
                    "type": "string",
                    "description": "the message"
                },
                "duration": {
                    "type": "integer",
                    "description": "duration in seconds"
                }
            },
            "permission": "read"
        }
        tool_rich = VC._recipe_to_openai_tool("toast_rich", rich_cfg)
        self.assertEqual(tool_rich["function"]["name"], "mios_recipe__toast_rich")
        props_rich = tool_rich["function"]["parameters"]["properties"]
        self.assertIn("message", props_rich)
        self.assertIn("duration", props_rich)
        self.assertIn("os", props_rich)
        self.assertEqual(props_rich["message"]["type"], ["string", "null"])
        self.assertEqual(props_rich["message"]["description"], "the message")
        self.assertEqual(props_rich["duration"]["type"], ["integer", "null"])
        self.assertEqual(props_rich["duration"]["description"], "duration in seconds")
        self.assertTrue(tool_rich["function"]["strict"])

    def test_render_verb_catalog_prose(self):
        prose = VC._render_verb_catalog(self.cat)
        self.assertIn("open_app", prose)
        self.assertIn("Window / app launch", prose)
        self.assertIn("Memory", prose)

    def test_render_recipe_catalog_prose(self):
        rec = VC._load_recipe_catalog()
        prose = VC._render_recipe_catalog(rec)
        self.assertIn("toast", prose)

    def test_model_name_and_alias_resolution(self):
        self.assertEqual(self.model_map["launch_application"], "open_app")
        self.assertEqual(self.model_map["open_application"], "open_app")
        self.assertEqual(self.model_map["start_app"], "open_app")
        # _resolve_verb_key: alias -> key, key -> key, unknown -> identity.
        self.assertEqual(VC._resolve_verb_key("launch_application"), "open_app")
        self.assertEqual(VC._resolve_verb_key("open_app"), "open_app")
        self.assertEqual(VC._resolve_verb_key("nope"), "nope")
        self.assertEqual(VC._resolve_verb_key(""), "")

    def test_arg_synonyms_projection(self):
        syn = VC._verb_arg_synonyms_from_catalog(self.cat)
        self.assertEqual(syn["open_app"]["name"], ["app", "binary", "exe", "file", "path", "program", "query", "target", "title"])
        # The compat shim reads the injected _VERB_CATALOG.
        self.assertEqual(VC._load_verb_arg_synonyms(), syn)

    def test_identity_answer_from_live_catalog(self):
        ans = VC._identity_answer()
        self.assertTrue(ans)
        self.assertIn("MiOS-Agent", ans)


if __name__ == "__main__":
    unittest.main()
