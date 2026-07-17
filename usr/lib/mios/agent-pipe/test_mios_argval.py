# AI-hint: Sibling unit test for the mios_argval python module, ensuring compliance with drift-check 11.
# AI-related: /usr/lib/mios/agent-pipe/mios_argval.py, /usr/lib/mios/agent-pipe/test_mios_argval.py
# AI-functions: TestMiosArgVal

import unittest
import mios_argval

class TestMiosArgVal(unittest.TestCase):
    def setUp(self):
        # Configure a mock verb catalog and synonyms map
        self.mock_catalog = {
            "test_verb": {
                "params": {
                    "mode": {
                        "enum": ["foo", "bar"]
                    }
                }
            }
        }
        self.mock_synonyms = {
            "test_verb": {
                "mode": ["m", "type"]
            }
        }
        mios_argval.configure(
            verb_catalog=self.mock_catalog,
            verb_arg_synonyms=self.mock_synonyms
        )

    def test_arg_with_synonyms_canonical(self):
        args = {"mode": "foo"}
        self.assertEqual(mios_argval._arg_with_synonyms("test_verb", "mode", args), "foo")

    def test_arg_with_synonyms_alias(self):
        args = {"m": "bar"}
        self.assertEqual(mios_argval._arg_with_synonyms("test_verb", "mode", args), "bar")
        
        args_other = {"type": "foo"}
        self.assertEqual(mios_argval._arg_with_synonyms("test_verb", "mode", args_other), "foo")

    def test_arg_with_synonyms_missing(self):
        args = {"other": "value"}
        self.assertEqual(mios_argval._arg_with_synonyms("test_verb", "mode", args), "")

    def test_validate_enum_args_valid(self):
        args = {"mode": "foo"}
        self.assertIsNone(mios_argval._validate_enum_args("test_verb", args))

    def test_validate_enum_args_invalid(self):
        args = {"mode": "baz"}
        err = mios_argval._validate_enum_args("test_verb", args)
        self.assertIsNotNone(err)
        self.assertIn("not allowed", err)

    def test_validate_enum_args_missing(self):
        args = {}
        self.assertIsNone(mios_argval._validate_enum_args("test_verb", args))

if __name__ == "__main__":
    unittest.main()
