# AI-hint: Provides Open WebUI tools for direct desktop interaction (vision, AT-SPI grounding, input actions) and document generation via the mios-launcher broker to bypass container isolation and execute system-level commands.
# AI-related: mios-launcher, mios-computer-use, mios-pc-control, mios-pc-vision, mios-docgen, mios-launcher.service, socket.socket
# AI-functions: _broker_send, _passthru_json, __init__, _off, _writes_off, cu_screenshot, cu_ground, cu_atspi_query, cu_window_list, cu_click, cu_type, cu_key
"""
title: MiOS Computer Use
author: MiOS
version: 0.1.0
description: |
  ONE Open WebUI Native tool surfacing the MiOS computer-use capability
  (WS-4 P0) as typed tool_calls: the EXISTING desktop control + vision
  grounding verbs (mios-computer-use / mios-pc-control / mios-pc-vision)
  PLUS the new FOSS offline document generation tool (mios-docgen ->
  Pandoc + LibreOffice). The chat model invokes these directly instead of
  indirecting through the generic `terminal:` shell tool.

  This is the LiteCUA Perceptor/Reasoner/Worker pattern assembled from
  MiOS parts (NO Wide-Moat / BSL vendor stack -- see
  concepts/aios-implementation-plan.md section 0-B):
    * Perceive : cu_screenshot  (one-shot capture)
    * Ground   : cu_ground / cu_atspi_query  (AT-SPI first, vision fallback)
    * Act      : cu_click / cu_type / cu_key / cu_key_combo / cu_window_list
    * Produce  : docgen_build / docgen_convert  (author/convert artifacts)

  Dispatch goes through the OPERATOR-side launcher broker (unix socket at
  /run/mios-launcher/launcher.sock), exactly like the sibling mios_verbs
  tool -- so the verbs inherit the operator's WSLg / Wayland session
  (WAYLAND_DISPLAY, DBUS, WSL_INTEROP) that an in-container subprocess
  could never see.

  GATING + SAFETY (binding rule -- default-off / degrade-open):
    * Master valve ENABLED (default True) toggles the whole tool.
    * WRITE_ACTIONS_ENABLED (default FALSE) gates the side-effecting input
      verbs (click/type/key/key_combo). Read-class verbs (screenshot,
      ground, atspi_query, window_list, docgen) work with writes off.
    * mios-docgen itself is independently gated by [computer_use].docgen_enable
      server-side; when off it returns ok=false (this tool surfaces that).
  Every method returns structured JSON the model can reason over, so a
  failure is unambiguous (no "I clicked the button" hallucination over a
  silently-failed call).

requirements:
  pydantic
"""

from __future__ import annotations

import json
import os
import shlex
import socket
from typing import Literal, Optional

from pydantic import BaseModel, Field

ButtonLiteral = Literal["left", "right", "middle"]
# Source content formats mios-docgen authors FROM (markup the model writes).
BuildFromLiteral = Literal["markdown", "plain", "html", "csv"]

LAUNCHER_SOCKET = os.environ.get(
    "MIOS_LAUNCHER_SOCK", "/run/mios-launcher/launcher.sock"
)


def _broker_send(line: str, timeout: float, capture: bool) -> dict:
    """Talk to the operator-side launcher broker. Returns a dict the model
    can reason over deterministically. Never raises. (Mirrors mios_verbs.)"""
    if not line.strip():
        return {"success": False, "exit_code": -1,
                "stdout": "", "stderr": "empty command"}
    if not os.path.exists(LAUNCHER_SOCKET):
        return {"success": False, "exit_code": -1, "stdout": "",
                "stderr": f"launcher broker socket not present at {LAUNCHER_SOCKET} "
                          "(mios-launcher.service down? container missing the mount?)"}
    payload = (f"CAPTURE_JSON: {line}").encode("utf-8") + b"\n" if capture \
        else line.encode("utf-8") + b"\n"
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
    raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
    if capture:
        try:
            j = json.loads(raw) if raw else {}
        except (json.JSONDecodeError, ValueError):
            j = {}
        if not j:
            if raw.startswith("ERROR:"):
                return {"success": False, "exit_code": -1, "stdout": "", "stderr": raw}
            return {"success": True, "exit_code": 0, "stdout": raw[:12000], "stderr": ""}
        exit_code = int(j.get("exit_code", -1))
        return {"success": exit_code == 0, "exit_code": exit_code,
                "stdout": (j.get("stdout") or "")[:12000],
                "stderr": (j.get("stderr") or "")[:4000]}
    if raw.startswith("OK"):
        return {"success": True, "exit_code": 0, "stdout": "", "stderr": ""}
    return {"success": False, "exit_code": -1,
            "stdout": "", "stderr": raw or "broker returned no reply"}


def _passthru_json(result: dict, **fallback) -> str:
    """A verb whose shim already emits JSON on stdout -> surface verbatim;
    else wrap the broker envelope so the model still gets structured data."""
    raw = (result.get("stdout") or "").strip()
    try:
        return json.dumps(json.loads(raw))
    except (json.JSONDecodeError, ValueError):
        return json.dumps({
            "success": result.get("success", False),
            "stderr": (result.get("stderr") or "")[:600] or f"non-JSON: {raw[:300]}",
            **fallback,
        })


class Tools:
    class Valves(BaseModel):
        ENABLED: bool = Field(
            default=True,
            description="Master on/off for all MiOS computer-use verbs.",
        )
        WRITE_ACTIONS_ENABLED: bool = Field(
            default=False,
            description="Gate the side-effecting input verbs (click/type/key/"
                        "key_combo). OFF by default -- read-class verbs "
                        "(screenshot/ground/atspi_query/window_list/docgen) "
                        "stay usable. Turn ON to let the agent drive the "
                        "operator's desktop input.",
        )
        ACTION_TIMEOUT_S: float = Field(
            default=20.0,
            description="Timeout for screenshot / ground / input verbs.",
        )
        DOCGEN_TIMEOUT_S: float = Field(
            default=150.0,
            description="Timeout for mios-docgen (LibreOffice cold start + "
                        "conversion can take ~30-60s).",
        )

    def __init__(self) -> None:
        self.valves = self.Valves()

    def _off(self) -> str:
        return json.dumps({"success": False, "stderr": "MiOS computer-use disabled by valve"})

    def _writes_off(self, verb: str) -> str:
        return json.dumps({
            "success": False,
            "stderr": f"{verb} is a WRITE action; enable Valves.WRITE_ACTIONS_ENABLED "
                      "to let the agent drive desktop input.",
        })

    # === Perceive ============================================================
    async def cu_screenshot(self, path: str, __user__: Optional[dict] = None) -> str:
        """Capture the desktop to a PNG (one-shot, read-only). Env-adaptive:
        local Wayland (portal/grim), WSLg via mios-pc-control, or a federated
        remote executor -- the same verb works everywhere.

        :param path: Output PNG path (e.g. /tmp/screen.png). Feed this to
            cu_ground to locate a UI element before clicking.
        :return: JSON {success, stdout, stderr}.
        """
        if not self.valves.ENABLED:
            return self._off()
        result = _broker_send(f"mios-computer-use screenshot {shlex.quote(path)}",
                              timeout=self.valves.ACTION_TIMEOUT_S, capture=True)
        return json.dumps({
            "success": result["success"],
            "path": path,
            "output": (result.get("stdout") or "")[:600],
            "stderr": result.get("stderr", ""),
        })

    # === Ground ==============================================================
    async def cu_ground(self, query: str, __user__: Optional[dict] = None) -> str:
        """Locate a UI element by natural-language description -> click
        coordinates. Read-only. AT-SPI accessibility tree FIRST (deterministic,
        no pixels), local vision model (qwen3-vl / UI-TARS) only as fallback.
        Returns {x, y, confidence}; pass x/y to cu_click.

        :param query: Description of the target (e.g. "the OK button",
            "the search field", "Save toolbar icon").
        :return: JSON {x, y, confidence, reasoning, source}.
        """
        if not self.valves.ENABLED:
            return self._off()
        result = _broker_send(f"mios-computer-use ground {shlex.quote(query)} --json",
                              timeout=self.valves.ACTION_TIMEOUT_S, capture=True)
        return _passthru_json(result, query=query)

    async def cu_atspi_query(self, query: str, __user__: Optional[dict] = None) -> str:
        """Semantic accessibility-tree lookup (role/name match) -> screen
        coordinates, NO pixels/vision. Read-only. Faster + more reliable than
        cu_ground for standard widgets (buttons, menus, fields).

        :param query: Element role or name substring (e.g. "Cancel", "menu",
            "text").
        :return: JSON {query, matches:[{name, role, x, y, w, h}]}.
        """
        if not self.valves.ENABLED:
            return self._off()
        result = _broker_send(f"mios-computer-use atspi-query {shlex.quote(query)} --json",
                              timeout=self.valves.ACTION_TIMEOUT_S, capture=True)
        return _passthru_json(result, query=query)

    async def cu_window_list(self, __user__: Optional[dict] = None) -> str:
        """List top-level windows on the desktop (read-only). Use to
        disambiguate / verify a window is presented before acting.

        :return: JSON {windows:[{id, pid, x, y, w, h, title}]}.
        """
        if not self.valves.ENABLED:
            return self._off()
        result = _broker_send("mios-computer-use window-list --json",
                              timeout=self.valves.ACTION_TIMEOUT_S, capture=True)
        return _passthru_json(result)

    # === Act (WRITE -- gated by WRITE_ACTIONS_ENABLED) =======================
    async def cu_click(
        self,
        x: int,
        y: int,
        button: ButtonLiteral = "left",
        __user__: Optional[dict] = None,
    ) -> str:
        """Click at pixel (x,y) on the desktop. WRITE action -- gated.
        Usually preceded by cu_ground / cu_atspi_query to find the coords.

        :param x: X pixel offset from top-left.
        :param y: Y pixel offset from top-left.
        :param button: left (default) | right | middle.
        :return: JSON {ok, action, backend} or {success:false,...}.
        """
        if not self.valves.ENABLED:
            return self._off()
        if not self.valves.WRITE_ACTIONS_ENABLED:
            return self._writes_off("cu_click")
        cmd = f"mios-computer-use click {int(x)} {int(y)} {shlex.quote(button)}"
        result = _broker_send(cmd, timeout=self.valves.ACTION_TIMEOUT_S, capture=True)
        return _passthru_json(result, x=x, y=y, button=button)

    async def cu_type(self, text: str, __user__: Optional[dict] = None) -> str:
        """Type literal text into the focused surface. WRITE action -- gated.
        For editing FILES prefer the text-editor verbs; this is for live UI.

        :param text: The literal text to type.
        :return: JSON {ok, action, backend} or {success:false,...}.
        """
        if not self.valves.ENABLED:
            return self._off()
        if not self.valves.WRITE_ACTIONS_ENABLED:
            return self._writes_off("cu_type")
        result = _broker_send(f"mios-computer-use type {shlex.quote(text)}",
                              timeout=self.valves.ACTION_TIMEOUT_S, capture=True)
        return _passthru_json(result)

    async def cu_key(self, key: str, __user__: Optional[dict] = None) -> str:
        """Press a single key (Enter, Tab, Escape, F5, Up, ...). WRITE -- gated.

        :param key: Key name (Enter | Tab | Escape | Up | Down | F1..F12 | a char).
        :return: JSON {ok, action, backend} or {success:false,...}.
        """
        if not self.valves.ENABLED:
            return self._off()
        if not self.valves.WRITE_ACTIONS_ENABLED:
            return self._writes_off("cu_key")
        result = _broker_send(f"mios-computer-use key {shlex.quote(key)}",
                              timeout=self.valves.ACTION_TIMEOUT_S, capture=True)
        return _passthru_json(result, key=key)

    async def cu_key_combo(self, combo: str, __user__: Optional[dict] = None) -> str:
        """Press a modifier combo (Ctrl+S, Alt+Tab, Ctrl+Shift+T). WRITE -- gated.

        :param combo: Combo string with + or - separators (e.g. "Ctrl+S").
        :return: JSON {ok, action, backend} or {success:false,...}.
        """
        if not self.valves.ENABLED:
            return self._off()
        if not self.valves.WRITE_ACTIONS_ENABLED:
            return self._writes_off("cu_key_combo")
        result = _broker_send(f"mios-computer-use key-combo {shlex.quote(combo)}",
                              timeout=self.valves.ACTION_TIMEOUT_S, capture=True)
        return _passthru_json(result, combo=combo)

    # === Produce (doc-gen; FOSS offline Pandoc + LibreOffice) ================
    async def docgen_build(
        self,
        out_path: str,
        content: str,
        from_fmt: BuildFromLiteral = "markdown",
        __user__: Optional[dict] = None,
    ) -> str:
        """Author a NEW document from text content you write, emitting a real
        office artifact (.docx / .pptx / .xlsx / .pdf / .html). The OUTPUT
        FORMAT is inferred from out_path's extension. You write markdown (or
        CSV for spreadsheets); MiOS renders the binary via Pandoc / LibreOffice
        -- fully local, no cloud. For .pptx, separate slides with a line of
        `---`. For .xlsx, set from_fmt="csv" and put CSV rows in content.

        :param out_path: Destination path with the target extension
            (e.g. /tmp/report.docx, /tmp/deck.pptx, /tmp/data.xlsx, /tmp/x.pdf).
        :param content: The source content to render. Markdown for docx/pptx/
            pdf/html; raw CSV rows for xlsx (with from_fmt="csv").
        :param from_fmt: Source format of `content`: markdown (default) |
            plain | html | csv.
        :return: JSON {ok, output, source, target, bytes} or {ok:false, error}.
        """
        if not self.valves.ENABLED:
            return self._off()
        if not (out_path or "").strip():
            return json.dumps({"ok": False, "error": "out_path is required"})
        if content is None:
            content = ""
        # Pass content via the broker's stdin-equivalent: write to a heredoc-
        # safe temp through the shim's --stdin. We send the content base64-free
        # by piping through printf; broker runs one shell line, so we use a
        # process-substitution-free here-string approach via printf %s.
        # shlex.quote keeps it a single safe argument; mios-docgen reads --stdin.
        q_out = shlex.quote(out_path)
        q_from = shlex.quote(from_fmt)
        q_content = shlex.quote(content)
        cmd = (f"printf %s {q_content} | "
               f"mios-docgen build {q_out} --from {q_from} --stdin")
        result = _broker_send(cmd, timeout=self.valves.DOCGEN_TIMEOUT_S, capture=True)
        return _passthru_json(result, output=out_path, source=from_fmt)

    async def docgen_convert(
        self,
        in_path: str,
        out_path: str,
        __user__: Optional[dict] = None,
    ) -> str:
        """Convert an EXISTING file to another format (e.g. .docx -> .pdf,
        .md -> .docx, .csv -> .xlsx, .pptx -> .pdf). Fully local via Pandoc /
        LibreOffice headless. Target format inferred from out_path's extension.

        :param in_path: Source file path (must exist on the host).
        :param out_path: Destination path; its extension picks the format.
        :return: JSON {ok, input, output, source, target, bytes} or
            {ok:false, error}.
        """
        if not self.valves.ENABLED:
            return self._off()
        if not (in_path or "").strip() or not (out_path or "").strip():
            return json.dumps({"ok": False, "error": "in_path and out_path are required"})
        cmd = f"mios-docgen convert {shlex.quote(in_path)} {shlex.quote(out_path)}"
        result = _broker_send(cmd, timeout=self.valves.DOCGEN_TIMEOUT_S, capture=True)
        return _passthru_json(result, input=in_path, output=out_path)
