# AI-hint: MiOS system and orchestration module providing constrained conductor capabilities.
# AI-related: /usr/share/mios/conductor, mios-agent-pipe

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

try:
    import ruamel.yaml
except ImportError:
    ruamel = None

try:
    from jinja2 import StrictUndefined
    from jinja2.sandbox import SandboxedEnvironment
except ImportError:
    SandboxedEnvironment = None

log = logging.getLogger("mios-agent-pipe")

_base = "/usr/share/mios/conductor"
if not os.path.exists(_base):
    _base = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "..", "share", "mios", "conductor"
    ))
CONDUCTOR_DIR = _base

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_DEF_STEP_TIMEOUT = 300.0
_STEP_TIMEOUT: Optional[float] = None
_DISPATCH_VERB: Optional[Callable[..., Any]] = None
_ALLOWED_EXEC_COMMANDS: Optional[frozenset[str]] = None


class StepSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=128)
    action: Literal["exec", "verb"]
    argv: list[str] = Field(default_factory=list, max_length=64)
    verb: str = Field(default="", max_length=128)
    args: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_action_fields(self) -> "StepSpec":
        if self.action == "exec":
            if not self.argv:
                raise ValueError("exec action requires a non-empty argv")
            if self.verb:
                raise ValueError("exec action must not define verb")
        elif not self.verb:
            raise ValueError("verb action requires a verb")
        elif self.argv:
            raise ValueError("verb action must not define argv")
        return self


def configure(*, dispatch_verb: Optional[Callable[..., Any]] = None,
              allowed_exec_commands: Optional[set[str]] = None) -> None:
    global _DISPATCH_VERB, _ALLOWED_EXEC_COMMANDS
    if dispatch_verb is not None:
        _DISPATCH_VERB = dispatch_verb
    if allowed_exec_commands is not None:
        _ALLOWED_EXEC_COMMANDS = frozenset(allowed_exec_commands)


def _step_timeout() -> float:
    global _STEP_TIMEOUT
    if _STEP_TIMEOUT is None:
        try:
            from mios_pipe.kernel.config import _cfg_num, _toml_section
            _STEP_TIMEOUT = _cfg_num(
                _toml_section("orchestration") or {},
                "MIOS_CONDUCTOR_STEP_TIMEOUT",
                "conductor_step_timeout",
                _DEF_STEP_TIMEOUT,
                cast=float,
            )
        except Exception as error:
            log.warning("conductor: step timeout unresolved (%s); using %ss", error, _DEF_STEP_TIMEOUT)
            _STEP_TIMEOUT = _DEF_STEP_TIMEOUT
    return _STEP_TIMEOUT


def _allowed_exec_commands() -> frozenset[str]:
    global _ALLOWED_EXEC_COMMANDS
    if _ALLOWED_EXEC_COMMANDS is None:
        try:
            from mios_pipe.kernel.config import _toml_section
            configured = (_toml_section("orchestration") or {}).get(
                "conductor_allowed_exec_commands", []
            )
            _ALLOWED_EXEC_COMMANDS = frozenset(
                item for item in configured if isinstance(item, str) and item.startswith("/")
            )
        except Exception as error:
            log.warning("conductor: allowed commands unresolved (%s); denying exec actions", error)
            _ALLOWED_EXEC_COMMANDS = frozenset()
    return _ALLOWED_EXEC_COMMANDS


def _resolve_workflow_path(workflow_name: str) -> str:
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
    return raw.decode("utf-8", errors="replace") if raw else ""


async def _reap(proc: Any) -> None:
    try:
        if proc.returncode is None:
            proc.kill()
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except (asyncio.TimeoutError, ProcessLookupError, OSError, AttributeError):
        pass


async def _run_exec(argv: list[str], timeout: float) -> dict[str, Any]:
    if argv[0] not in _allowed_exec_commands():
        return {"success": False, "output": "", "error": f"command {argv[0]!r} is not allowlisted"}
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout) if timeout > 0 else await proc.communicate()
    except asyncio.TimeoutError:
        await _reap(proc)
        return {"success": False, "output": "", "error": f"step exceeded the {timeout}s budget and was killed"}
    return {
        "success": proc.returncode == 0,
        "output": _decode(stdout),
        "error": _decode(stderr),
        "returncode": proc.returncode,
    }


async def _run_verb(step: StepSpec, session_id: Optional[str]) -> dict[str, Any]:
    if _DISPATCH_VERB is None:
        return {"success": False, "output": "", "error": "verb dispatcher is unavailable"}
    result = await _DISPATCH_VERB(step.verb, step.args, session_id=session_id)
    if not isinstance(result, dict):
        return {"success": False, "output": "", "error": "verb dispatcher returned an invalid result"}
    return result


async def _guarded_step(raw_step: Any, timeout: float, session_id: Optional[str]) -> dict[str, Any]:
    try:
        step = StepSpec.model_validate(raw_step)
        if step.action == "exec":
            return await _run_exec(step.argv, timeout)
        return await _run_verb(step, session_id)
    except ValidationError as error:
        return {"success": False, "output": "", "error": f"invalid step: {error.errors()[0]['msg']}"}
    except asyncio.CancelledError:
        raise
    except Exception as error:
        log.exception("conductor step %r failed", _step_name(raw_step))
        return {"success": False, "output": "", "error": f"{type(error).__name__}: {error}"}


async def execute_conductor_workflow(
    workflow_name: str, params: dict[str, Any], session_id: Optional[str] = None
) -> dict[str, Any]:
    if ruamel is None or SandboxedEnvironment is None:
        return {
            "success": False,
            "workflow": workflow_name,
            "results": [],
            "error": "conductor dependencies (jinja2, pydantic, ruamel.yaml) are unavailable",
        }
    try:
        yaml_path = _resolve_workflow_path(workflow_name)
    except ValueError as error:
        log.warning("Conductor rejected workflow %r (session=%s): %s", workflow_name, session_id, error)
        return {"success": False, "workflow": workflow_name, "results": [], "error": str(error)}
    if not os.path.exists(yaml_path):
        return {"success": False, "workflow": workflow_name, "results": [], "error": f"Workflow {workflow_name} not found."}

    results: list[dict[str, Any]] = []
    try:
        with open(yaml_path, encoding="utf-8") as source:
            rendered_yaml = SandboxedEnvironment(
                autoescape=True, undefined=StrictUndefined
            ).from_string(source.read()).render(**(params or {}))
        workflow = ruamel.yaml.YAML(typ="safe").load(rendered_yaml)
        if not isinstance(workflow, dict) or not isinstance(workflow.get("steps"), list):
            return {"success": False, "workflow": workflow_name, "results": [], "error": "workflow steps must be a list"}

        timeout = _step_timeout()
        all_ok = True
        for raw_step in workflow["steps"]:
            if isinstance(raw_step, dict) and raw_step.get("parallel"):
                raw_steps = raw_step.get("steps")
                if not isinstance(raw_steps, list):
                    return {"success": False, "workflow": workflow_name, "results": results, "error": "parallel steps must be a list"}
                group = await asyncio.gather(
                    *(_guarded_step(step, timeout, session_id) for step in raw_steps),
                    return_exceptions=True,
                )
                group_ok = True
                for index, result in enumerate(group):
                    if isinstance(result, asyncio.CancelledError):
                        raise result
                    if not isinstance(result, dict):
                        result = {"success": False, "output": "", "error": f"malformed step result: {result!r}"}
                    group_ok = group_ok and bool(result.get("success"))
                    results.append({"step": _step_name(raw_steps[index]), "result": result})
                if not group_ok:
                    all_ok = False
                    if raw_step.get("fail_fast", False):
                        break
            else:
                result = await _guarded_step(raw_step, timeout, session_id)
                results.append({"step": _step_name(raw_step), "result": result})
                if not result.get("success"):
                    all_ok = False
                    if not isinstance(raw_step, dict) or raw_step.get("fail_fast", True):
                        break
        return {"success": all_ok, "workflow": workflow_name, "results": results}
    except asyncio.CancelledError:
        log.info("Conductor workflow %r cancelled (session=%s)", workflow_name, session_id)
        raise
    except Exception as error:
        log.exception("Conductor workflow %r failed (session=%s): %s", workflow_name, session_id, error)
        return {"success": False, "workflow": workflow_name, "results": results, "error": str(error)}
