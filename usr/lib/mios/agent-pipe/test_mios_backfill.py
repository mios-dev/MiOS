import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import mios_pipe.memory.embed_backfill as eb

class TestMiosEmbedBackfill(unittest.IsolatedAsyncioTestCase):

    def test_text_projections(self):
        # 1. skill
        s_row = {"name": "TestSkill", "description": "Doing cool things"}
        self.assertEqual(eb.get_text_projection("skill", s_row), "Skill: TestSkill\nDescription: Doing cool things")
        
        # 2. verb
        v_row = {
            "name": "test_verb",
            "desc_default": "A description of a verb",
            "model_name": "TestVerb",
            "examples": ["test standard usage", "another test"]
        }
        self.assertEqual(
            eb.get_text_projection("verb", v_row),
            "TestVerb: A description of a verb\nExample requests: test standard usage | another test"
        )
        
        # 3. tool_call
        tc_row = {
            "tool": "web_search",
            "args": {"query": "hello"},
            "result_preview": "some search results"
        }
        self.assertEqual(
            eb.get_text_projection("tool_call", tc_row),
            'Tool Call: web_search\nArguments: {"query": "hello"}\nResult: some search results'
        )
        
        # 4. directory_entry
        de_row = {
            "path": "/etc/hosts",
            "kind": "file",
            "size": 128,
            "summary": "Local DNS mappings"
        }
        self.assertEqual(
            eb.get_text_projection("directory_entry", de_row),
            "File: /etc/hosts\nKind: file\nSize: 128 bytes\nSummary: Local DNS mappings"
        )

    @patch("mios_pipe.memory.pg.execute", new_callable=AsyncMock)
    @patch("httpx.AsyncClient")
    async def test_run_backfill_success(self, mock_client_cls, mock_execute):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": [0.1] * 768}
        mock_client.post.return_value = mock_response
        
        select_results = {
            "skill": [{"id": 1, "name": "skill_1", "description": "desc_1"}],
            "verb": [{"name": "verb_1", "desc_default": "desc_1", "examples": None, "model_name": None}],
            "tool_call": [{"id": 10, "tool": "tc_1", "args": "{}", "result_preview": "res", "output": None}],
            "directory_entry": [{"id": 100, "path": "p_1", "kind": "file", "size": 10, "summary": "sum_1"}]
        }
        
        def execute_side_effect(sql, params=None, fetch=False, **kwargs):
            if "SELECT" in sql:
                for k in select_results:
                    if f"FROM {k}" in sql:
                        return select_results[k]
                return []
            return None
            
        mock_execute.side_effect = execute_side_effect
        
        res = await eb.run_backfill("nomic-768-v1")
        
        self.assertEqual(res["skill"], 1)
        self.assertEqual(res["verb"], 1)
        self.assertEqual(res["tool_call"], 1)
        self.assertEqual(res["directory_entry"], 1)

    @patch("mios_pipe.memory.pg.execute", new_callable=AsyncMock)
    @patch("httpx.AsyncClient")
    async def test_run_backfill_fail_open(self, mock_client_cls, mock_execute):
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        mock_client.post.side_effect = Exception("Connection refused")
        
        select_results = {
            "skill": [{"id": 1, "name": "skill_1", "description": "desc_1"}]
        }
        
        def execute_side_effect(sql, params=None, fetch=False, **kwargs):
            if "SELECT" in sql:
                if "FROM skill" in sql:
                    return select_results["skill"]
                return []
            return None
            
        mock_execute.side_effect = execute_side_effect
        
        res = await eb.run_backfill("nomic-768-v1")
        self.assertEqual(res.get("skill"), 0)

if __name__ == "__main__":
    unittest.main()
