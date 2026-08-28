# AI-hint: MiOS system and orchestration module providing conductor capabilities.
# AI-related: /usr/share/mios/conductor, mios-agent-pipe

import asyncio
import logging
import os
import re
from typing import Optional, Dict, Any, List

try:
    import jinja2
    import ruamel.yaml
except ImportError:
    # Both are baked into the image; if either is absent, fail with a legible
    # dependency error instead of a NameError leaking out of the render path.
    jinja2 = None
    ruamel = None

log = logging.getLogger("mios-agent-pipe")

_base = "/usr/share/mios/conductor"
if not os.path.exists(_base):
    _base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "share", "mios", "conductor"))
CONDUCTOR_DIR = _base

# A workflow NAME, never a path: no separators, no leading dot, so `..` and
# absolute paths cannot be spelled at all.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

_DEF_STEP_TIMEOUT = 300.0
_STEP_TIMEOUT: Optional[float] = None

def _step_timeout() -> float:
    """Per-step shell budget in seconds: MIOS_CONDUCTOR_STEP_TIMEOUT ->
    mios.toml [orchestration].conductor_step_timeout -> default. <=0 disables
    the cap. Resolved once, like the other layered dispatch tunables."""
    global _STEP_TIMEOUT
    if _STEP_TIMEOUT is None:
        try:
            from mios_pipe.kernel.config import _toml_section, _cfg_num
            _STEP_TIMEOUT = _cfg_num(_toml_section("orchestration") or {},
                                     "MIOS_CONDUCTOR_STEP_TIMEOUT",
                                     "conductor_step_timeout",
                                     _DEF_STEP_TIMEOUT, cast=float)
        except Exception as e:
            log.warning("conductor: step timeout unresolved (%s); using %ss",
                        e, _DEF_STEP_TIMEOUT)
            _STEP_TIMEOUT = _DEF_STEP_TIMEOUT
    return _STEP_TIMEOUT

def _resolve_workflow_path(workflow_name: str) -> str:
    """Map a workflow name to its YAML under CONDUCTOR_DIR.

    The name arrives from model-refined dispatch input, so it is untrusted:
    reject anything that is not a bare name, then confirm the resolved path
    really sits inside CONDUCTOR_DIR (catches symlink escapes) BEFORE the file
    is read and its shell steps are executed."""
    name = str(workflow_name or "").strip()
    if not _SAFE_NAME.match(name):
        raise ValueError(f"invalid workflow name: {workflow_name!r}")
    root = os.path.realpath(CONDUCTOR_DIR)
    path = os.path.realpath(os.path.join(root, f"{name}.yaml"))
    if os.path.commonpath([root, path]) != root:
        raise ValueError(f"workflow {name!r} resolves outside {CONDUCTOR_DIR}")
    return path

def _step_name(step: Any) -> Optional[str]:
    return step.get("name") if isinstance(step, dict) else None

def _decode(raw: Optional[bytes]) -> str:
    """Never let a binary-spewing step kill the whole workflow."""
    if not raw:
        return ""
    return raw.decode("utf-8", errors="replace")

async def _reap(proc) -> None:
    """Kill and collect a step's child process so a timed-out or cancelled
    route does not orphan the shell it spawned."""
    try:
        if proc.returncode is None:
            proc.kill()
    except (ProcessLookupError, OSError, AttributeError):
        return
    try:
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except (asyncio.TimeoutError, ProcessLookupError, OSError):
        pass

async def _run_shell(cmd: str, timeout: float) -> dict:
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        if timeout and timeout > 0:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        else:
            stdout, stderr = await proc.communicate()
    except asyncio.TimeoutError:
        await _reap(proc)
        return {"success": False, "output": "",
                "error": f"step exceeded the {timeout}s budget and was killed"}
    except asyncio.CancelledError:
        try:
            if proc.returncode is None:
                proc.kill()
        except (ProcessLookupError, OSError, AttributeError):
            pass
        raise
    return {"success": proc.returncode == 0, "output": _decode(stdout),
            "error": _decode(stderr), "returncode": proc.returncode}

async def _run_step(step: Any, timeout: float) -> dict:
    if not isinstance(step, dict):
        return {"success": False, "output": "", "error": f"malformed step: {step!r}"}
    action = step.get("action")
    args = step.get("args") or {}
    if not isinstance(args, dict):
        return {"success": False, "output": "",
                "error": f"step {_step_name(step)!r}: 'args' must be a mapping"}
    if action == "shell":
        cmd = str(args.get("cmd", "") or "")
        if not cmd.strip():
            return {"success": False, "output": "",
                    "error": f"step {_step_name(step)!r}: shell action has no 'cmd'"}
        return await _run_shell(cmd, timeout)
    return {"success": True, "output": f"Mock executed {action}"}

async def _guarded_step(step: Any, timeout: float) -> dict:
    """A step that blows up is a FAILED step, not a lost workflow: without this
    the outer handler discarded every result accumulated so far."""
    try:
        return await _run_step(step, timeout)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        log.exception("conductor step %r failed", _step_name(step))
        return {"success": False, "output": "", "error": f"{type(e).__name__}: {e}"}

def _as_result(r: Any) -> dict:
    """Normalise one asyncio.gather(return_exceptions=True) slot into a result
    dict. CancelledError is a BaseException, so the old `isinstance(r, Exception)`
    guard let it fall through to r.get() and crashed the workflow."""
    if isinstance(r, BaseException):
        return {"success": False, "output": "", "error": f"{type(r).__name__}: {r}"}
    if not isinstance(r, dict):
        return {"success": False, "output": "", "error": f"malformed step result: {r!r}"}
    return r

async def execute_conductor_workflow(workflow_name: str, params: Dict[str, Any], session_id: Optional[str] = None) -> dict:
    """Executes a YAML + Jinja2 workflow deterministically."""
    if jinja2 is None or ruamel is None:
        return {"success": False, "workflow": workflow_name, "results": [],
                "error": "conductor dependencies (jinja2, ruamel.yaml) are unavailable"}

    try:
        yaml_path = _resolve_workflow_path(workflow_name)
    except ValueError as e:
        log.warning("Conductor rejected workflow %r (session=%s): %s",
                    workflow_name, session_id, e)
        return {"success": False, "workflow": workflow_name, "results": [], "error": str(e)}

    if not os.path.exists(yaml_path):
        return {"success": False, "workflow": workflow_name, "results": [],
                "error": f"Workflow {workflow_name} not found."}

    results: List[dict] = []
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            template_str = f.read()

        template = jinja2.Template(template_str)
        rendered_yaml = template.render(**(params or {}))

        yaml = ruamel.yaml.YAML(typ='safe')
        workflow = yaml.load(rendered_yaml)

        if not isinstance(workflow, dict):
            return {"success": False, "workflow": workflow_name, "results": [],
                    "error": f"Workflow {workflow_name} did not parse to a mapping."}
        steps = workflow.get("steps") or []
        if not isinstance(steps, list):
            return {"success": False, "workflow": workflow_name, "results": [],
                    "error": f"Workflow {workflow_name}: 'steps' must be a list."}

        timeout = _step_timeout()
        all_ok = True

        for step in steps:
            if isinstance(step, dict) and step.get("parallel"):
                parallel_steps = step.get("steps") or []
                if not isinstance(parallel_steps, list):
                    parallel_steps = []
                tasks = [_guarded_step(ps, timeout) for ps in parallel_steps]
                step_results = await asyncio.gather(*tasks, return_exceptions=True)

                group_ok = True
                for i, r in enumerate(step_results):
                    if isinstance(r, asyncio.CancelledError):
                        raise r          # route cancelled: propagate, never score it
                    r = _as_result(r)
                    if not r.get("success"):
                        group_ok = False
                    results.append({"step": _step_name(parallel_steps[i]), "result": r})

                if not group_ok:
                    all_ok = False
                    # NB: a parallel group opts IN to fail_fast; a sequential step
                    # opts OUT. Asymmetric, but preserved -- workflows rely on it.
                    if step.get("fail_fast", False):
                        break
            else:
                r = _as_result(await _guarded_step(step, timeout))
                results.append({"step": _step_name(step), "result": r})
                if not r.get("success"):
                    all_ok = False
                    if not isinstance(step, dict) or step.get("fail_fast", True):
                        break

        return {
            "success": all_ok,
            "workflow": workflow_name,
            "results": results
        }
    except asyncio.CancelledError:
        log.info("Conductor workflow %r cancelled (session=%s)", workflow_name, session_id)
        raise
    except Exception as e:
        log.exception("Conductor workflow %r failed (session=%s): %s",
                      workflow_name, session_id, e)
        # Hand back whatever completed -- the caller loses no partial progress.
        return {"success": False, "workflow": workflow_name,
                "results": results, "error": str(e)}
