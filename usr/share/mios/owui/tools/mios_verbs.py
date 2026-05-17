"""
title: MiOS Verbs
author: MiOS
version: 1.1.0
description: |
  Native typed tools exposing the MiOS shell verbs (launch_app,
  everything_search, mios_apps, mios_find) to the chat model. The
  model sees them in its tool_calls schema and invokes them
  directly -- no more `terminal: mios-launch beamng` indirection
  through the generic shell tool.

  Dispatch goes through the OPERATOR-side launcher broker (unix
  socket at /run/mios-launcher/launcher.sock, mode 0666, mounted
  into the OWUI container by the Quadlet). The broker runs in
  user@<uid>.service so it inherits full WSLg env (WAYLAND_DISPLAY,
  WSL2_GUI_APPS_ENABLED=1, WSL_INTEROP=/run/WSL/<pid>_interop, the
  whole DBUS session). Without that, in-container subprocess of
  /mnt/m/Programs/Everything/es.exe just returns "no match" -- WSL
  interop only works in the operator's exec context, not inside
  podman's isolated namespace.

  Broker protocol (per mios-launcher-daemon docstring):
    "<one line of shell>\\n"           -> fire-and-forget, "OK\\n" reply
    "CAPTURE: <one line of shell>\\n"  -> sync run, raw stdout+stderr reply

  Operator directive 2026-05-17: "AI-stack native (Hermes
  tools???!!)". This is the OWUI-native answer; a parallel follow-up
  could expose the same verbs as a stdio MCP server.

  Each tool returns structured JSON the model can reason over
  ({success, target, paths, output, stderr}) so a failure is
  unambiguous -- prior chats had the model claiming "I tried to
  launch X" while the shell call had silently failed.

requirements:
  pydantic
"""

from __future__ import annotations

import json
import os
import shlex
import socket
from typing import Optional

from pydantic import BaseModel, Field


LAUNCHER_SOCKET = os.environ.get(
    "MIOS_LAUNCHER_SOCK", "/run/mios-launcher/launcher.sock"
)


def _broker_send(line: str, timeout: float, capture: bool) -> dict:
    """Talk to the operator-side launcher broker. Returns a dict the
    model can reason over deterministically. Never raises."""
    if not line.strip():
        return {"success": False, "exit_code": -1,
                "stdout": "", "stderr": "empty command"}
    if not os.path.exists(LAUNCHER_SOCKET):
        return {"success": False, "exit_code": -1, "stdout": "",
                "stderr": f"launcher broker socket not present at {LAUNCHER_SOCKET} "
                          "(mios-launcher.service down? container missing the mount?)"}
    payload = (f"CAPTURE: {line}" if capture else line).encode("utf-8") + b"\n"
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(LAUNCHER_SOCKET)
        s.sendall(payload)
        chunks: list[bytes] = []
        try:
            while True:
                buf = s.recv(65536)
                if not buf:
                    break
                chunks.append(buf)
        except socket.timeout:
            pass
        finally:
            s.close()
    except OSError as e:
        return {"success": False, "exit_code": -1,
                "stdout": "", "stderr": f"broker connect: {e}"}
    raw = b"".join(chunks).decode("utf-8", errors="replace")
    if capture:
        # CAPTURE mode: raw output (no OK/ERROR framing). Empty reply =
        # command produced no output (still a success if no error).
        if raw.startswith("ERROR:"):
            return {"success": False, "exit_code": -1,
                    "stdout": "", "stderr": raw.strip()}
        return {"success": True, "exit_code": 0,
                "stdout": raw.strip()[:12000], "stderr": ""}
    # Fire-and-forget: "OK\n" or "ERROR: ..."
    if raw.strip().startswith("OK"):
        return {"success": True, "exit_code": 0,
                "stdout": "", "stderr": ""}
    return {"success": False, "exit_code": -1,
            "stdout": "", "stderr": raw.strip() or "broker returned no reply"}


class Tools:
    class Valves(BaseModel):
        ENABLED: bool = Field(
            default=True,
            description="Master on/off for all MiOS verbs.",
        )
        LAUNCH_TIMEOUT_S: float = Field(
            default=15.0,
            description="Timeout for launch_app dispatch (Steam/Epic protocol handler returns near-instantly; long timeout only matters if the broker stalls).",
        )
        SEARCH_TIMEOUT_S: float = Field(
            default=20.0,
            description="Timeout for everything_search (Voidtools es.exe; sub-100ms typical).",
        )
        INVENTORY_TIMEOUT_S: float = Field(
            default=60.0,
            description="Timeout for mios_apps inventory (rebuilds Windows app cache on first call after wipe; can take ~30s).",
        )

    def __init__(self) -> None:
        self.valves = self.Valves()

    # ─── launch_app ─────────────────────────────────────────────────
    async def launch_app(self, name: str, __user__: Optional[dict] = None) -> str:
        """Launch a MiOS-registered app by short name. Resolves through
        the canonical mios-launch chain (internal-service alias ->
        URL/URI literal -> Windows GUI shortname -> Windows games
        inventory -> MiOS shim -> Linux GUI -> plain CLI). Steam, Epic,
        GOG, Xbox, Battle.net games all dispatch via the Windows
        protocol handler.

        Uses the launcher broker's CAPTURE mode so the resolved target
        line ("mios-launch: <DisplayName> -> <cmd>") comes back and the
        tool can surface it. Launch is still detached on the broker
        side -- mios-launch exec's into mios-windows which Start-Process
        the URI; the protocol handler takes over and returns instantly.

        :param name: App short name. Case-insensitive substring matches
            against the Windows games inventory; exact for shortnames.
            Examples: "beamng", "notepad", "chromedev", "marvel rivals".
        :return: JSON string with {success, target, stderr}.
            success=true means the launch was DISPATCHED (the protocol
            handler took over); the app may take seconds to render its
            window.
        """
        if not self.valves.ENABLED:
            return json.dumps({"success": False, "stderr": "MiOS verbs disabled by valve"})
        cmd = f"mios-launch {shlex.quote(name)}"
        result = _broker_send(cmd, timeout=self.valves.LAUNCH_TIMEOUT_S, capture=True)
        # mios-launch prints "mios-launch: <DisplayName> -> <cmd>" on
        # successful resolve; extract for visibility.
        target = ""
        for line in (result.get("stdout") or "").splitlines():
            if line.startswith("mios-launch:") and " -> " in line:
                target = line.split(" -> ", 1)[1].strip()
                break
        return json.dumps({
            "success": result["success"],
            "target": target,
            "broker_output": result.get("stdout", "")[:600],
            "stderr": result.get("stderr", ""),
        })

    # ─── everything_search ──────────────────────────────────────────
    async def everything_search(
        self,
        query: str,
        limit: int = 10,
        ext: str = "",
        __user__: Optional[dict] = None,
    ) -> str:
        """Search the Windows NTFS index via Voidtools Everything CLI.
        Returns one Windows path per stdout line. Sub-100ms typical;
        covers EVERY mounted NTFS drive. ALWAYS prefer this over
        recursive `find` / `dir /s` / `Get-ChildItem -Recurse` when
        looking for any file or installation on the host.

        :param query: Everything query string. Supports substring,
            wildcards ("BeamNG*.exe"), path filters ("path:steamapps"),
            size ("size:>1gb"), modify-date ("dm:today"), etc.
        :param limit: Max results to return (default 10).
        :param ext: Optional comma-separated extension filter
            (e.g. "exe,lnk"). Empty = no filter.
        :return: JSON string with {success, paths[], count, stderr}.
        """
        if not self.valves.ENABLED:
            return json.dumps({"success": False, "stderr": "MiOS verbs disabled by valve"})
        cmd = f"mios-everything {shlex.quote(query)} -n {int(limit)}"
        if ext.strip():
            cmd += f" -ext {shlex.quote(ext.strip())}"
        result = _broker_send(cmd, timeout=self.valves.SEARCH_TIMEOUT_S, capture=True)
        paths = [p for p in (result.get("stdout") or "").splitlines() if p.strip()]
        return json.dumps({
            "success": result["success"] and bool(paths),
            "paths": paths,
            "count": len(paths),
            "stderr": result.get("stderr", ""),
        })

    # ─── mios_apps ──────────────────────────────────────────────────
    async def mios_apps(
        self,
        filter: str = "",
        __user__: Optional[dict] = None,
    ) -> str:
        """Inventory every installed app across all sources (Steam,
        Epic, Xbox/Microsoft Store, flatpak, RPM with .desktop,
        Windows shortcuts, MiOS shims, CLIs). Cached 5 minutes.

        :param filter: Optional case-insensitive substring filter on
            display name. Empty = full inventory.
        :return: JSON string with {success, output, stderr} where
            output is the formatted inventory block (one section per
            source).
        """
        if not self.valves.ENABLED:
            return json.dumps({"success": False, "stderr": "MiOS verbs disabled by valve"})
        cmd = "mios-apps"
        if filter.strip():
            cmd += f" --filter {shlex.quote(filter.strip())}"
        result = _broker_send(cmd, timeout=self.valves.INVENTORY_TIMEOUT_S, capture=True)
        return json.dumps({
            "success": result["success"],
            "output": (result.get("stdout") or "")[:10000],
            "stderr": result.get("stderr", ""),
        })

    # ─── mios_find ──────────────────────────────────────────────────
    async def mios_find(self, name: str, __user__: Optional[dict] = None) -> str:
        """Look up an app's launch info across all MiOS-known sources.
        Faster than mios_apps when you just need ONE app's metadata
        (~60ms vs ~2s). Returns the launch command + source category
        if found.

        :param name: App short name or display-name substring.
        :return: JSON string with {success, output, stderr}.
            If found, output is the launch hint; if not, suggested
            next steps (try everything_search with broader query, etc.).
        """
        if not self.valves.ENABLED:
            return json.dumps({"success": False, "stderr": "MiOS verbs disabled by valve"})
        cmd = f"mios-find {shlex.quote(name)}"
        result = _broker_send(cmd, timeout=self.valves.SEARCH_TIMEOUT_S, capture=True)
        return json.dumps({
            "success": result["success"],
            "output": (result.get("stdout") or "")[:4000],
            "stderr": result.get("stderr", ""),
        })

    # ─── system_status ──────────────────────────────────────────────
    async def system_status(self, __user__: Optional[dict] = None) -> str:
        """Return a structured snapshot of the live MiOS host: GPU(s) +
        VRAM, RAM, disk, failed/active service count, MiOS service
        health roll-up (hermes / OWUI / prefilter / hermes-tail /
        ollama), and the full ollama model list. ONE tool call,
        deterministic JSON, no fabrication.

        Use this when the operator asks "system status", "dashboard",
        "what's running", "what GPU do I have", "how much disk left",
        "list ollama models", or any system-overview question. Beats
        running df / nvidia-smi / systemctl / ollama list separately
        and assembling them in prose -- the model has been observed
        fabricating GPU fields ("No NVIDIA driver detected") when
        forced to do the assembly itself.

        :return: JSON string with {ts, uptime_s, gpu[], memory{},
            disk[], services{failed[], active_count, mios{}},
            ollama[]}. Missing probes come back as null or empty
            list -- never fabricated.
        """
        if not self.valves.ENABLED:
            return json.dumps({"success": False, "stderr": "MiOS verbs disabled by valve"})
        # mios-system-status is a self-contained JSON-emitting helper.
        # Broker dispatch so we hit it from the operator-side context
        # (nvidia-smi + ollama list + systemctl all behave the same in
        # the broker context, but going through the broker keeps the
        # tool stateless and consistent with the other verbs).
        result = _broker_send("mios-system-status",
                              timeout=self.valves.INVENTORY_TIMEOUT_S,
                              capture=True)
        raw = result.get("stdout") or ""
        # If the helper emitted JSON, pass it through; else surface the
        # error so the model knows it can't trust the answer.
        try:
            parsed = json.loads(raw)
            parsed["success"] = True
            return json.dumps(parsed)
        except (json.JSONDecodeError, ValueError):
            return json.dumps({
                "success": False,
                "stderr": result.get("stderr", "") or f"non-JSON from mios-system-status: {raw[:300]}",
            })
