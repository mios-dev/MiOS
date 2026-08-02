# AI-hint: stub
# AI-related: stub
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mios_pipe.routing.conductor as mios_conductor

async def main():
    with patch("os.path.exists", return_value=True), patch("builtins.open", MagicMock()):
        jinja2_mock = MagicMock()
        template_instance = MagicMock()
        template_instance.render.return_value = "fake_yaml"
        jinja2_mock.Template.return_value = template_instance
        
        yaml_mock = MagicMock()
        yaml_instance = MagicMock()
        yaml_instance.load.return_value = {
            "steps": [
                {
                    "name": "step1",
                    "action": "shell",
                    "args": {"cmd": "echo 'step 1'"}
                },
                {
                    "name": "parallel_group",
                    "parallel": True,
                    "fail_fast": True,
                    "steps": [
                        {
                            "name": "step2a",
                            "action": "shell",
                            "args": {"cmd": "echo 'step 2a'"}
                        },
                        {
                            "name": "step2b_fail",
                            "action": "shell",
                            "args": {"cmd": "exit 1"}
                        }
                    ]
                },
                {
                    "name": "step3_skipped",
                    "action": "shell",
                    "args": {"cmd": "echo 'step 3'"}
                }
            ]
        }
        yaml_mock.YAML.return_value = yaml_instance
        
        mios_conductor.jinja2 = jinja2_mock
        mios_conductor.ruamel = MagicMock()
        mios_conductor.ruamel.yaml = yaml_mock
        
        process_mock_success = MagicMock()
        process_mock_success.communicate = AsyncMock(return_value=(b"output\n", b""))
        process_mock_success.returncode = 0

        process_mock_fail = MagicMock()
        process_mock_fail.communicate = AsyncMock(return_value=(b"", b"error"))
        process_mock_fail.returncode = 1

        def side_effect(cmd, **kwargs):
            if "exit 1" in cmd:
                return process_mock_fail
            return process_mock_success

        with patch("asyncio.create_subprocess_shell", side_effect=AsyncMock(side_effect=side_effect)) as m_subprocess:
            res = await mios_conductor.execute_conductor_workflow("test-workflow", {})
            print("Result:", res)
            assert res["success"] is False, "Workflow should fail due to step2b_fail"
            assert res["workflow"] == "test-workflow"
            
            assert len(res["results"]) == 3, f"Expected 3 step results, got {len(res['results'])}"
            assert res["results"][0]["step"] == "step1"
            assert res["results"][1]["step"] == "step2a"
            assert res["results"][2]["step"] == "step2b_fail"
            
            print("PASS: Conductor deterministic orchestration via DAG handler.")

if __name__ == "__main__":
    asyncio.run(main())
