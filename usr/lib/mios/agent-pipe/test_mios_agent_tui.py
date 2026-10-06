# AI-hint: Exercise the actual unified MiOS Monitor at compact, portrait and desktop sizes, including selection, resize and refresh failures.
# AI-related: /usr/lib/mios/mios_agent_tui.py, /usr/libexec/mios/mios-mon.py
# AI-functions: TestAgentTui

import copy
import importlib.machinery
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "usr/lib/mios"))
from mios_agent_tui import AgentView, clean, peer_name
from textual.widgets import DataTable, Input, Static, TabbedContent

monitor = importlib.machinery.SourceFileLoader("mios_monitor_test", str(ROOT / "usr/libexec/mios/mios-mon.py")).load_module()
CLIENTS = [{"name": name, "installed": True, "mcp": name != "aider"}
           for name in ("claude", "codex", "gemini", "copilot", "opencode", "agy", "aider")]
SNAPSHOT = {"agents": [{"agent_id": "agy:unique", "kind": "agy", "label": "Antigravity · Active Orchestrator", "online": True, "pending": 2},
                        {"agent_id": "codex:unique", "kind": "codex", "label": "Codex · active integration", "online": True, "pending": 0}],
            "panes": [{"socket": "/private", "pane": f"%{i}", "role": f"W{i}", "command": "sleep", "dead": False} for i in range(1, 5)],
            "messages": [{"status": "queued"}, {"status": "received"}], "errors": []}


class TestAgentTui(unittest.IsolatedAsyncioTestCase):
    def app(self, mode="clients", observer=None, agents=None):
        return monitor.MiosMonitorApp(ui_request={"agents": agents or CLIENTS}, ui_mode=mode,
                                      observer=observer or (lambda: copy.deepcopy(SNAPSHOT)), collectors=False)

    async def test_all_clients_fit_and_select_at_native_half_width(self):
        app = self.app()
        async with app.run_test(size=(35, 19)) as pilot:
            await pilot.pause()
            table = app.query_one("#client-table", DataTable)
            self.assertEqual(table.row_count, 7)
            self.assertGreaterEqual(table.size.height, 8)
            self.assertEqual(table.get_row_at(6)[1].plain, "aider")
            self.assertLessEqual(table.region.right, 35)
            await pilot.press("7", "enter")
            await pilot.pause()
        self.assertEqual(app.return_value, "aider")

    async def test_missing_and_invalid_clients_cannot_launch(self):
        clients = copy.deepcopy(CLIENTS)
        clients[0]["installed"] = False
        clients.append({"name": "x;touch /tmp/surprise", "installed": True})
        app = self.app(agents=clients)
        async with app.run_test(size=(35, 19)) as pilot:
            await pilot.press("1", "enter")
            await pilot.pause()
            self.assertIsNone(app.return_value)
            self.assertEqual(app.query_one("#client-table", DataTable).row_count, 7)
            self.assertIn("installed", str(app.query_one("#client-status", Static).render()))
            app.query_one(Input).value = "codex"
            await pilot.press("enter")
            await pilot.pause()
        self.assertEqual(app.return_value, "codex")

    async def test_keyboard_table_selection(self):
        app = self.app()
        async with app.run_test(size=(35, 19)) as pilot:
            await pilot.press("down", "down", "enter")
            await pilot.pause()
        self.assertEqual(app.return_value, "codex")

    async def test_views_share_one_app_and_resize_without_restarting(self):
        with patch.object(monitor, "get_services", return_value=[("agent-pipe", 0, True)]), patch.object(monitor, "get_telemetry", return_value=(10, 20, 30, 0, "1.0")):
            app = self.app()
            async with app.run_test(size=(35, 19)) as pilot:
                for size in ((44, 19), (46, 30), (80, 20), (180, 50), (35, 12)):
                    await pilot.resize_terminal(*size)
                    await pilot.press("f2")
                    await pilot.pause()
                    self.assertEqual(app.query_one(TabbedContent).active, "tab-agents")
                    for id in ("peer-table", "worker-table"):
                        table = app.query_one(f"#{id}", DataTable)
                        self.assertGreaterEqual(table.size.height, 2)
                        self.assertGreater(table.size.width, 0)
                        self.assertLessEqual(table.region.right, size[0])
                    await pilot.press("f3")
                    await pilot.pause()
                    self.assertEqual(app.query_one(TabbedContent).active, "tab-global")
                await pilot.press("f1")
                await pilot.pause()
                self.assertEqual(app.query_one("#client-table", DataTable).row_count, 7)

    async def test_poll_preserves_cursor_and_failure_is_visible(self):
        app = self.app(mode="agents")
        async with app.run_test(size=(44, 19)) as pilot:
            await pilot.pause()
            view = app.query_one(AgentView)
            table = app.query_one("#peer-table", DataTable)
            table.move_cursor(row=1)
            snapshot = copy.deepcopy(SNAPSHOT)
            snapshot["agents"][1]["pending"] = 9
            view.render_snapshot(snapshot)
            self.assertEqual(table.cursor_row, 1)
            self.assertEqual(table.get_row_at(1)[2].plain, "9")
            self.assertIn("queued", str(app.query_one("#receipt", Static).render()))
            self.assertEqual(app.query_one("#worker-table", DataTable).get_row_at(0)[2].plain, "Empty")
            def fail(): raise RuntimeError("offline")
            view.observer = fail
            await view.refresh_snapshot()
            self.assertIn("unavailable", str(app.query_one("#agent-error", Static).render()))
            self.assertEqual(table.row_count, 2)

    def test_peer_labels_are_literal_and_identifiable(self):
        self.assertEqual(peer_name(SNAPSHOT["agents"][0]), "Agy Orchestrator")
        self.assertEqual(clean("[red]x\x1b\u202ey"), "[red]xy")


if __name__ == "__main__":
    unittest.main(verbosity=2)
