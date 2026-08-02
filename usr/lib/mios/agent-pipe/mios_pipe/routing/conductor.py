import os
import asyncio
import logging
from typing import Optional, Dict, Any

try:
    import jinja2
    import ruamel.yaml
except ImportError:
    pass

log = logging.getLogger("mios-agent-pipe")

_base = "/usr/share/mios/conductor"
if not os.path.exists(_base):
    _base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "share", "mios", "conductor"))
CONDUCTOR_DIR = _base

async def execute_conductor_workflow(workflow_name: str, params: Dict[str, Any], session_id: Optional[str] = None) -> dict:
    """Executes a YAML + Jinja2 workflow deterministically."""
    yaml_path = os.path.join(CONDUCTOR_DIR, f"{workflow_name}.yaml")
    if not os.path.exists(yaml_path):
        return {"success": False, "error": f"Workflow {workflow_name} not found."}

    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            template_str = f.read()

        template = jinja2.Template(template_str)
        rendered_yaml = template.render(**params)

        yaml = ruamel.yaml.YAML(typ='safe')
        workflow = yaml.load(rendered_yaml)

        results = []
        all_ok = True

        async def run_step(step):
            action = step.get("action")
            args = step.get("args", {})
            if action == "shell":
                cmd = args.get("cmd", "")
                proc = await asyncio.create_subprocess_shell(
                    cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                return {"success": proc.returncode == 0, "output": stdout.decode(), "error": stderr.decode()}
            else:
                return {"success": True, "output": f"Mock executed {action}"}

        for step in workflow.get("steps", []):
            if step.get("parallel"):
                parallel_steps = step.get("steps", [])
                tasks = [run_step(ps) for ps in parallel_steps]
                step_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                group_ok = True
                for i, r in enumerate(step_results):
                    if isinstance(r, Exception) or not r.get("success"):
                        group_ok = False
                    results.append({"step": parallel_steps[i].get("name"), "result": r})

                if not group_ok:
                    all_ok = False
                    if step.get("fail_fast"):
                        break
            else:
                r = await run_step(step)
                results.append({"step": step.get("name"), "result": r})
                if not r.get("success"):
                    all_ok = False
                    if step.get("fail_fast", True):
                        break

        return {
            "success": all_ok,
            "workflow": workflow_name,
            "results": results
        }
    except Exception as e:
        log.error(f"Conductor workflow failed: {e}")
        return {"success": False, "error": str(e)}

