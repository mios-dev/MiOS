# AI-hint: Two-sided native AIO MCP tests: real upstream process, private tmux sockets, protocol negotiation, exit receipts and negative controls.
# AI-related: /usr/libexec/mios/mios-mcp-server, /usr/share/mios/mios.toml [mcp.tmux], /usr/share/doc/mios/mcp-tmux.md
# AI-functions: TestMcpAio, load_relay, payload
import asyncio
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import threading
import urllib.request
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
RELAY = ROOT / "usr/libexec/mios/mios-mcp-server"
os.environ["MIOS_TOML"] = str(ROOT / "usr/share/mios/mios.toml")
os.environ["MIOS_RESOLVER_NATIVE"] = "0"

def load_relay():
    loader = importlib.machinery.SourceFileLoader("mios_mcp_aio_relay", str(RELAY))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module

relay = load_relay()
CONFIG = tomllib.loads((ROOT / "usr/share/mios/mios.toml").read_text())["mcp"]["tmux"]

# CI runs against the same verified release asset as the image installer. It
# does not depend on a previously installed binary or an upstream download.
_PAYLOAD = tempfile.TemporaryDirectory(prefix="mios-mcp-test-binary-")
asset = CONFIG["assets"][relay.platform.machine()]
archive = ROOT / asset["path"]
if hashlib.sha256(archive.read_bytes()).hexdigest() != asset["sha256"]:
    raise RuntimeError("tmux-mcp test asset checksum mismatch")
with tarfile.open(archive) as package:
    binary = Path(_PAYLOAD.name) / "tmux-mcp"
    binary.write_bytes(package.extractfile("tmux-mcp").read())
    binary.chmod(0o755)
os.environ["MIOS_TMUX_MCP_BINARY"] = str(binary)

def payload(result):
    wire = result.model_dump(by_alias=True, exclude_none=True)
    if wire.get("structuredContent"):
        return wire["structuredContent"]
    for block in result.content:
        if block.type == "text":
            try:
                return json.loads(block.text)
            except ValueError:
                continue
    raise AssertionError("missing structured command receipt")

class TestMcpAio(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bridge = relay._TmuxBridge(CONFIG)
        await self.bridge.start()

    async def asyncTearDown(self):
        await self.bridge.close()

    async def execute(self, command, **args):
        return await self.bridge.call("mios_tmux_execute_command", {"command": command, **args})

    async def test_positive_and_planted_nonzero_receipt(self):
        good = await self.execute("printf 'POSITIVE-CONTROL\\n'")
        self.assertFalse(good.model_dump(by_alias=True).get("isError"), good)
        self.assertEqual(payload(good)["exitCode"], 0)
        self.assertIn("POSITIVE-CONTROL", payload(good)["output"])
        bad = await self.execute("printf 'DEVLOOP-PLANTED-EXIT\\n'; (exit 23)")
        self.assertTrue(bad.model_dump(by_alias=True).get("isError"), bad)
        self.assertEqual(payload(bad)["exitCode"], 23)
        self.assertIn("DEVLOOP-PLANTED-EXIT", payload(bad)["output"])

    async def test_private_client_socket_and_teardown(self):
        other = relay._TmuxBridge(CONFIG)
        try:
            await other.start()
            self.assertNotEqual(self.bridge.directory.name, other.directory.name)
            self.assertEqual(os.stat(self.bridge.directory.name).st_mode & 0o777, 0o700)
            first = await self.execute('printf FIRST > "$HOME/client-marker"; printf "%s" "$HOME"')
            self.assertEqual(payload(first)["exitCode"], 0, first)
            self.assertEqual(payload(first)["output"], self.bridge.directory.name)
            again = await self.execute('cat "$HOME/client-marker"')
            self.assertEqual(payload(again)["output"], "FIRST")
            result = await other.call("mios_tmux_execute_command", {
                "command": 'test ! -e "$HOME/client-marker" && printf second:unset'})
            self.assertFalse(result.model_dump(by_alias=True).get("isError"), result)
            self.assertIn("second:unset", payload(result)["output"])
            directory = self.bridge.directory.name
            await self.bridge.close()
            self.assertFalse(os.path.exists(directory))
            survivor = await other.call("mios_tmux_execute_command", {"command": "printf SURVIVOR"})
            self.assertFalse(survivor.model_dump(by_alias=True).get("isError"), survivor)
            self.assertIn("SURVIVOR", payload(survivor)["output"])
        finally:
            await other.close()

    async def test_timeout_kills_busy_slot_and_is_error(self):
        result = await self.execute("printf DEVLOOP-PLANTED-TIMEOUT; sleep 30", timeoutSeconds=1)
        self.assertTrue(result.model_dump(by_alias=True).get("isError"), result)
        self.assertTrue(payload(result)["timedOut"])
        slots = await self.bridge.call("mios_tmux_list_slots", {})
        self.assertEqual(payload(slots), [])
        recovered = await self.execute("printf RECOVERED")
        self.assertFalse(recovered.model_dump(by_alias=True).get("isError"), recovered)
        self.assertIn("RECOVERED", payload(recovered)["output"])

    async def test_negative_policy_no_visible_pane_or_unbounded_slot(self):
        for args, needle in (({"slot": 0}, "slot"), ({"slot": CONFIG["max_slots"]+1}, "slot"),
                             ({"slot": True}, "slot"), ({"isolated": False}, "isolated"),
                             ({"paneId": "%0"}, "paneId"), ({"timeoutSeconds": 0}, "timeoutSeconds")):
            result = await self.execute("printf SHOULD-NOT-RUN", **args)
            self.assertTrue(result.model_dump(by_alias=True).get("isError"), result)
            self.assertIn(needle, result.content[0].text)
        disallowed = await self.bridge.call("mios_tmux_notify", {"message": "SHOULD-NOT-RUN"})
        self.assertTrue(disallowed.model_dump(by_alias=True).get("isError"))

    async def test_ambient_secrets_and_shell_hooks_are_absent(self):
        other = relay._TmuxBridge(CONFIG)
        with patch.dict(os.environ, {"MIOS_TEST_SECRET": "DEVLOOP-PLANTED-SECRET", "BASH_ENV": "/invalid"}):
            try:
                await other.start()
                result = await other.call("mios_tmux_execute_command", {
                    "command": "printf '%s:%s' \"${MIOS_TEST_SECRET-unset}\" \"${BASH_ENV-unset}\""})
                self.assertFalse(result.model_dump(by_alias=True).get("isError"), result)
                self.assertIn("unset:unset", payload(result)["output"])
            finally:
                await other.close()

    async def test_parallel_slots_are_independent(self):
        results = await asyncio.gather(self.execute("sleep 1; printf SLOT1", slot=1),
                                       self.execute("printf SLOT2", slot=2))
        for slot, result in enumerate(results, 1):
            self.assertFalse(result.model_dump(by_alias=True).get("isError"), result)
            self.assertIn(f"SLOT{slot}", payload(result)["output"])

    async def test_caller_theme_survives_private_worker_home(self):
        with tempfile.TemporaryDirectory() as directory:
            override = Path(directory) / "theme.toml"
            override.write_text('[colors]\nbg = "#123456"\n')
            with patch.dict(os.environ, {"MIOS_USER_TOML": str(override)}):
                other = relay._TmuxBridge(CONFIG)
                try:
                    await other.start()
                    before = (Path(other.directory.name) / "tmux.conf").read_bytes()
                    self.assertIn(b"#123456", before)
                    result = await other.call("mios_tmux_execute_command", {"command": "printf CALLER-THEME"})
                    self.assertFalse(result.model_dump(by_alias=True).get("isError"), result)
                    self.assertEqual((Path(other.directory.name) / "tmux.conf").read_bytes(), before)
                    self.assertEqual(other.env["MIOS_THEME_PROJECTED"], "1")
                finally:
                    await other.close()

    async def test_one_stdio_endpoint_lists_system_and_tmux_tools(self):
        from mcp import Client, StdioServerParameters
        env = dict(os.environ, MIOS_AGENT_PIPE_URL="http://127.0.0.1:1",
                   MIOS_MCP_LIST_TIMEOUT="1", MIOS_MCP_TOOLS_CACHE=os.devnull)
        async with Client(StdioServerParameters(command=sys.executable, args=[str(RELAY)], env=env)) as client:
            names = {t.name for t in (await client.list_tools()).tools}
            self.assertIn("mios_tmux_execute_command", names)
            self.assertTrue(any(not n.startswith("mios_tmux_") for n in names), names)
            result = await client.call_tool("mios_tmux_execute_command", {"command": "printf AIO-ENDPOINT"})
            self.assertFalse(result.model_dump(by_alias=True).get("isError"), result)
            self.assertIn("AIO-ENDPOINT", payload(result)["output"])

    async def test_packaging_positive_and_corruption_negative(self):
        for asset in CONFIG["assets"].values():
            content = (ROOT / asset["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), asset["sha256"])
            self.assertNotEqual(hashlib.sha256(content + b"DEVLOOP-PLANTED-CORRUPTION").hexdigest(), asset["sha256"])
        with patch.dict(os.environ, {"MIOS_TMUX_MCP_BINARY": "/nonexistent/DEVLOOP-PLANTED-BINARY"}):
            broken = relay._TmuxBridge(CONFIG)
            try:
                with self.assertRaisesRegex(RuntimeError, "DEVLOOP-PLANTED-BINARY"):
                    await broken.start()
            finally:
                await broken.close()

    async def test_cross_process_agent_messages_require_recipient_receipts(self):
        from mcp import Client, StdioServerParameters
        with tempfile.TemporaryDirectory(prefix="mios-agent-relay-proof-") as state:
            env = dict(os.environ, MIOS_AGENT_RELAY_STATE=state,
                       MIOS_AGENT_PIPE_URL="http://127.0.0.1:1",
                       MIOS_MCP_LIST_TIMEOUT="1", MIOS_MCP_TOOLS_CACHE=os.devnull)
            params = StdioServerParameters(command=sys.executable, args=[str(RELAY)], env=env)
            async with Client(params) as head, Client(params) as worker:
                registered = payload(await head.call_tool("mios_agent_register", {
                    "agent_id": "proof-head", "kind": "codex"}))
                recipient = payload(await worker.call_tool("mios_agent_register", {
                    "agent_id": "proof-worker", "kind": "agy"}))
                identity = {"agent_id": "proof-head", "token": registered["token"]}
                worker_identity = {"agent_id": "proof-worker", "token": recipient["token"]}
                message = {**identity, "to": "proof-worker", "message_id": "proof-1",
                           "message": "Bounded transport test; no provider invocation."}
                self.assertEqual(payload(await head.call_tool("mios_agent_send", message))["status"], "queued")
                names = {row.name for row in (await worker.list_tools()).tools}
                self.assertTrue({"mios_agent_receive", "mios_tmux_execute_command", "system_status"} <= names)
                inbox = payload(await worker.call_tool("mios_agent_receive", worker_identity))
                self.assertEqual([row["message"] for row in inbox["messages"]], [message["message"]])
                misrouted = await head.call_tool("mios_agent_ack", {**identity, "message_id": "proof-1"})
                self.assertTrue(misrouted.model_dump(by_alias=True).get("isError"))
                self.assertIn("does not belong", misrouted.content[0].text)
                stolen = await worker.call_tool("mios_agent_receive", {
                    **worker_identity, "token": "DEVLOOP-PLANTED-INVALID-LEASE-TOKEN"})
                self.assertTrue(stolen.model_dump(by_alias=True).get("isError"))
                self.assertIn("invalid lease", stolen.content[0].text)
                acknowledged = payload(await worker.call_tool("mios_agent_ack", {
                    **worker_identity, "message_id": "proof-1"}))
                self.assertEqual(acknowledged["status"], "received")
                retry = payload(await head.call_tool("mios_agent_send", message))
                self.assertEqual(retry["status"], "received")
                self.assertTrue(retry["duplicate"])
                self.assertEqual(payload(await worker.call_tool("mios_agent_receive", worker_identity))["messages"], [])
                offline = await head.call_tool("mios_agent_send", {
                    **message, "to": "DEVLOOP-PLANTED-ABSENT", "message_id": "missing-1"})
                self.assertTrue(offline.model_dump(by_alias=True).get("isError"))
                self.assertIn("offline", offline.content[0].text)
                public = payload(await worker.call_tool("mios_agent_list", {}))
                self.assertNotIn(registered["token"], json.dumps(public))
                await worker.call_tool("mios_agent_unregister", worker_identity)
                await head.call_tool("mios_agent_unregister", identity)

    async def test_cancelled_command_retires_occupied_slot(self):
        running = asyncio.create_task(self.execute("sleep 30", slot=3))
        await asyncio.sleep(0.3)
        running.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await running
        recovered = await self.execute("printf CANCEL-RECOVERED", slot=3)
        self.assertFalse(recovered.model_dump(by_alias=True).get("isError"), recovered)
        self.assertIn("CANCEL-RECOVERED", payload(recovered)["output"])

    async def test_existing_tools_dispatch_and_resources_over_stdio(self):
        from mcp import Client, StdioServerParameters
        catalog = relay._build_catalog_from_ssot()
        catalog += [{"name": name, "description": "MiOS API preservation probe",
                     "inputSchema": {"type": "object", "properties": {}}}
                    for name in ("mios_test_verb", "mios_skill__test", "mios_recipe__test")]
        resource = {"uri": "mios://recipe/test", "name": "test", "mimeType": "text/plain"}

        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def reply(self, body):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def do_GET(self):
                if self.path == "/v1/tools":
                    self.reply({"tools": catalog})
                elif self.path == "/v1/resources":
                    self.reply({"resources": [resource]})
                elif "DEVLOOP-PLANTED-MISSING" in self.path:
                    self.reply({"error": "DEVLOOP-PLANTED-MISSING"})
                else:
                    self.reply({"contents": [{"uri": resource["uri"], "mimeType": "text/plain", "text": "RESOURCE-PRESERVED"}]})

            def do_POST(self):
                args = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self.reply({"success": not args.get("args", {}).get("fail"), "path": self.path, "body": args})

        backend = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
        thread = threading.Thread(target=backend.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as cache:
                env = dict(os.environ, MIOS_AGENT_PIPE_URL=f"http://127.0.0.1:{backend.server_port}",
                           MIOS_MCP_TOOLS_CACHE=str(Path(cache) / "tools.json"))
                async with Client(StdioServerParameters(command=sys.executable, args=[str(RELAY)], env=env)) as client:
                    names = {t.name for t in (await client.list_tools()).tools}
                    self.assertEqual({n for n in names if not n.startswith(("mios_tmux_", "mios_agent_"))}, {t["name"] for t in catalog})
                    for name, path, body in (
                        ("mios_test_verb", "/v1/dispatch", {"tool": "mios_test_verb", "args": {"x": 1}}),
                        ("mios_skill__test", "/skills/run", {"name": "test", "params": {"x": 1}}),
                        ("mios_recipe__test", "/v1/dispatch", {"tool": "os_recipe", "args": {"name": "test", "params": {"x": 1}}}),
                    ):
                        result = await client.call_tool(name, {"x": 1})
                        self.assertFalse(result.model_dump(by_alias=True).get("isError"), result)
                        self.assertEqual(payload(result)["path"], path)
                        self.assertEqual(payload(result)["body"], body)
                    targeted = await client.call_tool("mios_recipe__test", {"x": 1, "os": "windows"})
                    self.assertEqual(payload(targeted)["body"], {
                        "tool": "os_recipe", "args": {"name": "test", "params": {"x": 1}, "os": "windows"}})
                    bad = await client.call_tool("mios_test_verb", {"fail": True})
                    self.assertTrue(bad.model_dump(by_alias=True).get("isError"), bad)
                    resources = (await client.list_resources()).resources
                    self.assertEqual([str(r.uri) for r in resources], [resource["uri"]])
                    read = await client.read_resource(resource["uri"])
                    self.assertEqual(read.contents[0].text, "RESOURCE-PRESERVED")
                    with self.assertRaisesRegex(Exception, "DEVLOOP-PLANTED-MISSING"):
                        await client.read_resource("mios://recipe/DEVLOOP-PLANTED-MISSING")
        finally:
            await asyncio.to_thread(backend.shutdown)
            backend.server_close()

    async def test_http_sessions_and_legacy_protocol_are_isolated(self):
        from mcp import Client
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            port = reserved.getsockname()[1]
        with tempfile.TemporaryDirectory(prefix="mios-http-test-") as directory, tempfile.TemporaryFile() as log:
            env = dict(os.environ, MIOS_MCP_PORT=str(port), RUNTIME_DIRECTORY=directory)
            process = subprocess.Popen([sys.executable, str(RELAY), "--http", "--tmux-only"],
                                       env=env, stdout=log, stderr=log)
            try:
                url = f"http://127.0.0.1:{port}"
                for _attempt in range(100):
                    try:
                        with urllib.request.urlopen(url + "/health", timeout=0.2) as response:
                            self.assertEqual(json.load(response)["status"], "ok")
                        break
                    except OSError:
                        if process.poll() is not None:
                            log.seek(0)
                            self.fail(log.read().decode())
                        await asyncio.sleep(0.05)
                else:
                    self.fail("HTTP server did not become healthy")
                async with Client(url + "/mcp") as other:
                    async with Client(url + "/mcp") as first:
                        tools = (await first.list_tools()).tools
                        self.assertIn("mios_tmux_execute_command", {t.name for t in tools})
                        denied = await first.call_tool("mios_tmux_execute_command", {"command": "printf DEVLOOP-PLANTED-SHARED"})
                        self.assertTrue(denied.model_dump(by_alias=True).get("isError"), denied)
                        a = payload(await first.call_tool("mios_tmux_session_open", {}))["session"]
                        b = payload(await other.call_tool("mios_tmux_session_open", {}))["session"]
                        self.assertNotEqual(a, b)
                        result = await first.call_tool("mios_tmux_execute_command", {"session": a, "command": 'printf FIRST > "$HOME/client-marker"'})
                        self.assertEqual(payload(result)["exitCode"], 0, result)
                        result = await first.call_tool("mios_tmux_execute_command", {"session": a, "command": 'cat "$HOME/client-marker"'})
                        self.assertEqual(payload(result)["output"], "FIRST")
                        result = await other.call_tool("mios_tmux_execute_command", {"session": b, "command": 'test ! -e "$HOME/client-marker" && printf PRIVATE'})
                        self.assertEqual(payload(result)["output"], "PRIVATE")
                        await first.call_tool("mios_tmux_session_close", {"session": a})
                        denied = await first.call_tool("mios_tmux_execute_command", {"session": a, "command": "printf DEVLOOP-PLANTED-REUSE"})
                        self.assertTrue(denied.model_dump(by_alias=True).get("isError"), denied)
                    result = await other.call_tool("mios_tmux_execute_command", {"session": b, "command": "printf HTTP-SURVIVOR"})
                    self.assertIn("HTTP-SURVIVOR", payload(result)["output"])
                    await other.call_tool("mios_tmux_session_close", {"session": b})
                async with Client(url + "/mcp", mode="legacy") as legacy:
                    token = payload(await legacy.call_tool("mios_tmux_session_open", {}))["session"]
                    result = await legacy.call_tool("mios_tmux_execute_command", {"session": token, "command": "printf LEGACY-PRESERVED"})
                    self.assertEqual(payload(result)["output"], "LEGACY-PRESERVED")
            finally:
                process.terminate()
                await asyncio.to_thread(process.wait, 10)
            self.assertEqual(list(Path(directory).iterdir()), [], "HTTP shutdown leaked tmux sessions")

    async def test_installer_refuses_corrupt_archive_before_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            target = Path(directory) / "target"
            config_path = source / "usr/share/mios/mios.toml"
            config_path.parent.mkdir(parents=True)
            config_path.write_bytes((ROOT / "usr/share/mios/mios.toml").read_bytes())
            broken = source / asset["path"]
            broken.parent.mkdir(parents=True)
            broken.write_bytes(b"DEVLOOP-PLANTED-CORRUPTION")
            existing = target / CONFIG["binary"].lstrip("/")
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"PREVIOUS-BINARY")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                relay._install_native(source, target)
            self.assertEqual(existing.read_bytes(), b"PREVIOUS-BINARY")

if __name__ == "__main__":
    if "--negative-keybindings" in sys.argv:
        data = relay.mios_toml.load_merged()["keybindings"]
        data["actions"][1]["key"] = data["actions"][0]["key"]
        with tempfile.NamedTemporaryFile(mode="w") as source:
            json.dump({"keybindings":data},source)
            source.flush()
            result = subprocess.run(["/usr/libexec/mios/mios-unit-gen","keybindings","--from-json",source.name,"--emit-json"],capture_output=True,text=True)
        print("DEVLOOP-PLANTED-KEYBIND", result.stderr)
        sys.exit(result.returncode)
    if "--negative-receipt" in sys.argv:
        async def negative():
            bridge = relay._TmuxBridge(CONFIG)
            try:
                result = await bridge.call("mios_tmux_execute_command", {
                    "command": "printf DEVLOOP-PLANTED-EXIT; (exit 23)"})
                print(payload(result)["output"])
                return payload(result)["exitCode"] if result.model_dump(by_alias=True).get("isError") else 0
            finally:
                await bridge.close()
        sys.exit(asyncio.run(negative()))
    unittest.main(verbosity=2)
