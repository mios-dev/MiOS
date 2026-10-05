#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS Antigravity CLI (AGY) agent, subagents, workflows, and CI/CD artifacting integration.
# AI-doc: usr/share/doc/mios/manual/ch04-the-agentic-ai-stack.md
"""Test suite for MiOS Antigravity CLI (AGY) agent and subagents configuration."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestAgyAgentPipeline(unittest.TestCase):
    """Verifies AGY agent and subagents configuration files for MiOS development and CI/CD."""

    def test_rules_agents_md_invariants(self):
        """Verifies .agents/rules/AGENTS.md exists and enforces core invariants."""
        rules_path = REPO_ROOT / ".agents" / "rules" / "AGENTS.md"
        self.assertTrue(rules_path.is_file(), f"Missing {rules_path}")
        content = rules_path.read_text(encoding="utf-8")

        # Invariants checks
        self.assertIn(".git", content)
        self.assertIn("/var", content)
        self.assertIn("Unified Kernel Image", content)
        self.assertIn("venus", content)
        self.assertIn("vfio", content.lower())
        self.assertIn("blade", content.lower())

        # Universal OpenAI endpoint check
        self.assertIn("MIOS_AI_ENDPOINT", content)
        self.assertIn("/v1/", content)

        # Rust & Keyring safety net
        self.assertIn("Rust", content)
        self.assertIn("Keyring", content)

    def test_subagents_json_schema_and_roles(self):
        """Verifies .agents/subagents.json contains valid JSON and required subagents."""
        subagents_path = REPO_ROOT / ".agents" / "subagents.json"
        self.assertTrue(subagents_path.is_file(), f"Missing {subagents_path}")

        data = json.loads(subagents_path.read_text(encoding="utf-8"))
        self.assertIn("subagents", data)
        subagents = data["subagents"]
        self.assertIsInstance(subagents, list)

        # Canonical roles conforming to Linux Foundation / AAIF standard
        required_roles = {
            "orchestrator",
            "worker",
            "auditor",
            "reviewer",
            "challenger",
            "explorer",
            "publisher",
            "developer",
        }
        found_names = set()
        for sa in subagents:
            self.assertIn("name", sa)
            self.assertIn("role", sa)
            self.assertIn("description", sa)
            self.assertIn("tools", sa)
            self.assertIn("system_prompt", sa)
            self.assertIsInstance(sa["tools"], list)
            self.assertTrue(len(sa["tools"]) > 0)
            self.assertTrue(len(sa["system_prompt"]) > 20)
            found_names.add(sa["name"])

        missing = required_roles - found_names
        self.assertFalse(missing, f"Missing required canonical subagents: {missing}")

    def test_workflows_exist_and_formatted(self):
        """Verifies .agents/skills/ (or .agents/workflows/) has valid dev-loop, pipeline, and artifacting skills/workflows."""
        skills_dir = REPO_ROOT / ".agents" / "skills"
        workflows_dir = REPO_ROOT / ".agents" / "workflows"
        self.assertTrue(skills_dir.is_dir() or workflows_dir.is_dir(), f"Missing {skills_dir} or {workflows_dir}")

        expected = ["dev-loop", "pipeline", "artifacting"]
        for name in expected:
            skill_path = skills_dir / name / "SKILL.md"
            wf_path = workflows_dir / f"{name}.md"
            wf_bak = workflows_dir / f"{name}.md.bak"
            self.assertTrue(skill_path.is_file() or wf_path.is_file() or wf_bak.is_file(), f"Missing skill/workflow for {name}")
            target = skill_path if skill_path.is_file() else (wf_path if wf_path.is_file() else wf_bak)
            txt = target.read_text(encoding="utf-8")
            self.assertTrue(txt.startswith("---"), f"Skill/Workflow {name} missing YAML frontmatter")
            self.assertIn("name:", txt)
            self.assertIn("description:", txt)

    def test_commands_antigravity_definitions(self):
        """Verifies commands/antigravity/ canonical definitions and absence of duplicate commands/agy/."""
        # Single canonical owner: commands/antigravity
        cmd_dir = REPO_ROOT / "commands" / "antigravity"
        self.assertTrue(cmd_dir.is_dir(), f"Missing canonical {cmd_dir}")

        for cmd_name in ["dev-loop.toml", "pipeline.toml", "agents.toml"]:
            cmd_file = cmd_dir / cmd_name
            self.assertTrue(cmd_file.is_file(), f"Missing {cmd_file}")
            txt = cmd_file.read_text(encoding="utf-8")
            self.assertIn("[command]", txt)
            self.assertIn("name =", txt)
            import tomllib
            workflow = tomllib.loads(txt)["command"]["workflow"]
            self.assertTrue((REPO_ROOT / workflow).is_file(), f"Unresolved command workflow: {workflow}")

        # Deduplication check: commands/agy must NOT exist as a redundant copy (T-1114)
        duplicate_dir = REPO_ROOT / "commands" / "agy"
        self.assertFalse(duplicate_dir.exists(), f"Duplicate directory {duplicate_dir} should not exist; keep commands/antigravity as canonical owner")

    def test_github_agent_definitions(self):
        """Verifies .github/agents/ definitions for agy-pipeline and agy-subagents."""
        gh_agents_dir = REPO_ROOT / ".github" / "agents"
        self.assertTrue(gh_agents_dir.is_dir(), f"Missing {gh_agents_dir}")

        for ag_file in ["agy-pipeline.agent.md", "agy-subagents.agent.md"]:
            path = gh_agents_dir / ag_file
            self.assertTrue(path.is_file(), f"Missing {path}")
            txt = path.read_text(encoding="utf-8")
            self.assertTrue(txt.startswith("---"))
            self.assertIn("name:", txt)
            self.assertIn("description:", txt)

    def test_plugin_bundle_structure(self):
        """Verifies .agents/plugins/mios-cicd/ bundle manifest, rules, and skills."""
        plugin_dir = REPO_ROOT / ".agents" / "plugins" / "mios-cicd"
        self.assertTrue(plugin_dir.is_dir(), f"Missing {plugin_dir}")

        manifest = plugin_dir / "plugin.json"
        self.assertTrue(manifest.is_file(), f"Missing {manifest}")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(data.get("name"), "mios-cicd")

        rules = plugin_dir / "rules" / "AGENTS.md"
        self.assertTrue(rules.is_file(), f"Missing {rules}")

        skill = plugin_dir / "skills" / "dev-pipeline" / "SKILL.md"
        self.assertTrue(skill.is_file(), f"Missing {skill}")
        skill_txt = skill.read_text(encoding="utf-8")
        self.assertIn("name: dev-pipeline", skill_txt)

    def test_wrapper_scripts_and_installer(self):
        """Verifies mios-agent-agy wrapper and install-mios-agents.sh integration."""
        installer_path = REPO_ROOT / "install-mios-agents.sh"
        self.assertTrue(installer_path.is_file())
        installer_txt = installer_path.read_text(encoding="utf-8")
        self.assertIn("mios-agent-agy", installer_txt)

        # Check local installed binary if present
        local_wrapper = Path("/usr/local/bin/mios-agent-agy")
        if local_wrapper.exists():
            self.assertTrue(os.access(local_wrapper, os.X_OK))

        # Check CI/CD runner script
        cicd_runner = REPO_ROOT / "automation" / "cicd" / "05-run-agy-pipeline-agent.sh"
        self.assertTrue(cicd_runner.is_file())
        self.assertTrue(os.access(cicd_runner, os.X_OK))

        # Check bash syntax
        bash_bin = shutil.which("bash") or "bash"
        res = subprocess.run([bash_bin, "-n", cicd_runner.as_posix()], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Syntax error in {cicd_runner}: {res.stderr}")

    def test_agents_command_definitions(self):
        """Verifies canonical commands/antigravity/agents.toml and agents workflow."""
        antigravity_agents = REPO_ROOT / "commands" / "antigravity" / "agents.toml"
        self.assertTrue(antigravity_agents.is_file(), f"Missing canonical {antigravity_agents}")
        agy_agents = REPO_ROOT / "commands" / "agy" / "agents.toml"
        self.assertFalse(agy_agents.exists(), f"Duplicate {agy_agents} must not exist")

        skill = REPO_ROOT / ".agents" / "skills" / "agents" / "SKILL.md"
        workflow = REPO_ROOT / ".agents" / "workflows" / "agents.md"
        wf_bak = REPO_ROOT / ".agents" / "workflows" / "agents.md.bak"
        self.assertTrue(skill.is_file() or workflow.is_file() or wf_bak.is_file(), "Missing agents skill or workflow")
        target = skill if skill.is_file() else (workflow if workflow.is_file() else wf_bak)
        wf_txt = target.read_text(encoding="utf-8")
        self.assertIn("pipeline-auditor", wf_txt)
        self.assertIn("pipeline-worker", wf_txt)
        self.assertIn("mios-dev", wf_txt)

    def test_workspace_agents_md_files(self):
        """Verifies .agents/agents/ contains canonical definitions for all standard MiOS-Dev agents."""
        agents_dir = REPO_ROOT / ".agents" / "agents"
        self.assertTrue(agents_dir.is_dir(), f"Missing {agents_dir}")

        expected = [
            "orchestrator.md",
            "worker.md",
            "auditor.md",
            "reviewer.md",
            "challenger.md",
            "explorer.md",
            "publisher.md",
            "developer.md",
        ]
        for fname in expected:
            fpath = agents_dir / fname
            self.assertTrue(fpath.is_file(), f"Missing {fpath}")
            txt = fpath.read_text(encoding="utf-8")
            self.assertTrue(txt.startswith("---"), f"{fname} missing YAML frontmatter")
            self.assertIn("name:", txt)
            self.assertIn("description:", txt)

    def test_cicd_scripts_behavioural_and_failure_propagation(self):
        """Verifies automation/cicd/ 01-05 execution, absence of skip-permissions, and failure propagation."""
        bash_bin = shutil.which("bash") or "bash"
        python_bin = sys.executable

        # 1. Verify all 5 scripts exist and are executable
        scripts = [
            REPO_ROOT / "automation" / "cicd" / "01-ingest-daily-telemetry.sh",
            REPO_ROOT / "automation" / "cicd" / "02-distill-agent-weights.py",
            REPO_ROOT / "automation" / "cicd" / "03-build-bootc-oci.sh",
            REPO_ROOT / "automation" / "cicd" / "04-deploy-atomic-switch.sh",
            REPO_ROOT / "automation" / "cicd" / "05-run-agy-pipeline-agent.sh",
        ]
        for s in scripts:
            self.assertTrue(s.is_file(), f"Missing {s}")
            self.assertTrue(os.access(s, os.X_OK) or os.name == "nt", f"{s} not executable")

        # 2. Invariant: 05-run-agy-pipeline-agent.sh must NOT contain --dangerously-skip-permissions or || true
        content_05 = (REPO_ROOT / "automation" / "cicd" / "05-run-agy-pipeline-agent.sh").read_text(encoding="utf-8")
        self.assertNotIn("--dangerously-skip-permissions", content_05)
        self.assertNotIn("|| true", content_05)

        # 3. Behavioral test: 01-04 run and succeed
        res_01 = subprocess.run([bash_bin, scripts[0].as_posix()], capture_output=True, text=True)
        self.assertEqual(res_01.returncode, 0, f"01 failed: {res_01.stderr}")
        self.assertIn("[01-INGEST]", res_01.stdout)

        res_02 = subprocess.run([python_bin, str(scripts[1])], capture_output=True, text=True)
        self.assertEqual(res_02.returncode, 0, f"02 failed: {res_02.stderr}")
        self.assertIn("[02-DISTILL]", res_02.stdout)

        res_03 = subprocess.run([bash_bin, scripts[2].as_posix()], capture_output=True, text=True)
        self.assertEqual(res_03.returncode, 0, f"03 failed: {res_03.stderr}")
        self.assertIn("[03-BUILD]", res_03.stdout)

        res_04 = subprocess.run([bash_bin, scripts[3].as_posix()], capture_output=True, text=True)
        self.assertEqual(res_04.returncode, 0, f"04 failed: {res_04.stderr}")
        self.assertIn("[04-DEPLOY]", res_04.stdout)

        # 4. Behavioral test for 05: Failure propagation (Negative Control)
        # When agy exits non-zero, 05-run-agy-pipeline-agent.sh MUST fail (non-zero returncode).
        with tempfile.TemporaryDirectory(prefix="mock-agy-") as tmpdir:
            tmp_path = Path(tmpdir)
            mock_sh = tmp_path / "agy"
            mock_sh.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            os.chmod(mock_sh, 0o755)
            if os.name == "nt":
                mock_bat = tmp_path / "agy.bat"
                mock_bat.write_text("@echo off\nexit /b 1\n", encoding="utf-8")

            env = dict(os.environ)
            env["PATH"] = f"{tmpdir}{os.pathsep}{env.get('PATH', '')}"
            res_fail = subprocess.run(
                [bash_bin, scripts[4].as_posix()],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertNotEqual(
                res_fail.returncode,
                0,
                "05-run-agy-pipeline-agent.sh must fail when agy fails; failure was swallowed!",
            )

            # 5. Success behavioral test: When agy succeeds
            mock_sh.write_text("#!/bin/sh\necho {}\nexit 0\n", encoding="utf-8")
            if os.name == "nt":
                mock_bat.write_text("@echo off\necho {}\nexit /b 0\n", encoding="utf-8")

            res_ok = subprocess.run(
                [bash_bin, scripts[4].as_posix()],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(res_ok.returncode, 0, f"05 failed with mock agy: {res_ok.stderr}")
            self.assertIn("Completed Successfully", res_ok.stdout)

    def test_desktop_terminal_interaction_and_ssot_alignment(self):
        """Verifies desktop and terminal interaction mechanics in doc-desktop-terminal-interaction.md,
        .agents/COORDINATION.md, and SSOT alignment in usr/share/mios/mios.toml with two-sided controls."""
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib

        # -------------------------------------------------------------
        # 1. Document Existence & Content Controls
        # -------------------------------------------------------------
        doc_path = REPO_ROOT / "docs" / "design" / "doc-desktop-terminal-interaction.md"
        self.assertTrue(doc_path.is_file(), f"Missing {doc_path}")
        doc_content = doc_path.read_text(encoding="utf-8")

        coord_path = REPO_ROOT / ".agents" / "COORDINATION.md"
        self.assertTrue(coord_path.is_file(), f"Missing {coord_path}")
        coord_content = coord_path.read_text(encoding="utf-8")

        # Verify Dual-Surface Architecture and Compositors
        self.assertIn("Desktop Environment Plane", doc_content)
        self.assertIn("Native Root Terminal Plane", doc_content)
        self.assertIn("Hyprland", doc_content)
        self.assertIn("Quickshell", doc_content)

        # Verify In-Terminal AI Sigils (!, @, %, ?, ??)
        for sigil in ["`!`", "`@`", "`%`", "`?`", "`??`"]:
            self.assertIn(sigil, doc_content, f"Missing AI sigil {sigil} in interaction spec")

        # Verify Streamlined Slash Commands
        expected_commands = [
            "/new", "/resume", "/fork", "/compact", "/tangent",
            "/plan", "/permissions", "/sandbox", "/model", "/lane",
            "/advisor", "/init", "/diff", "/undo", "/rollback", "/mcp", "/mesh"
        ]
        for cmd in expected_commands:
            self.assertIn(f"`{cmd}`", doc_content, f"Missing streamlined slash command {cmd} in interaction spec")

        # Verify Coordination Doc AAIF 8 Canonical Roles
        expected_roles = [
            "orchestrator", "worker", "auditor", "reviewer",
            "challenger", "explorer", "publisher", "developer"
        ]
        for role in expected_roles:
            self.assertIn(f"`{role}`", coord_content, f"Missing AAIF canonical role {role} in COORDINATION.md")

        # Verify Live Desktop Sub-Pane Spawning and MCP Relay
        self.assertIn("tmux-mcp", coord_content)
        self.assertIn("mios_agent_send", coord_content)
        self.assertIn("mios_agent_receive", coord_content)
        self.assertIn("mios_agent_ack", coord_content)
        self.assertIn("doc-desktop-terminal-interaction.md", coord_content)

        # -------------------------------------------------------------
        # 2. SSOT Alignment in usr/share/mios/mios.toml (Positive Controls)
        # -------------------------------------------------------------
        ssot_path = REPO_ROOT / "usr" / "share" / "mios" / "mios.toml"
        self.assertTrue(ssot_path.is_file(), f"Missing {ssot_path}")
        with open(ssot_path, "rb") as f:
            ssot_data = tomllib.load(f)

        # [aliases] table verification
        self.assertIn("aliases", ssot_data)
        aliases = ssot_data["aliases"]
        self.assertEqual(aliases.get("browser"), "firefox")
        self.assertEqual(aliases.get("file_manager"), "nautilus")
        self.assertEqual(aliases.get("editor"), "nvim")
        self.assertEqual(aliases.get("terminal"), "mios-terminal")

        # [desktop.bindings] and [desktop.applications.runtimes] verification
        self.assertIn("desktop", ssot_data)
        desktop = ssot_data["desktop"]
        self.assertIn("bindings", desktop)
        bindings = desktop["bindings"]
        self.assertEqual(bindings.get("mod_key"), "SUPER")
        self.assertEqual(bindings.get("app_drawer"), "Space")
        self.assertEqual(bindings.get("browser_launch"), "b")
        self.assertEqual(bindings.get("quick_settings"), "a")
        self.assertEqual(bindings.get("monitor_overlay"), "m")

        self.assertIn("applications", desktop)
        runtimes = desktop["applications"].get("runtimes", {})
        self.assertTrue(runtimes.get("linux_native"))
        self.assertTrue(runtimes.get("windows_seamless"))
        self.assertTrue(runtimes.get("android_waydroid"))

        # [ai.lanes] verification
        self.assertIn("ai", ssot_data)
        ai = ssot_data["ai"]
        self.assertIn("lanes", ai)
        lanes = ai["lanes"]
        self.assertIn("fast", lanes)
        self.assertIn("code", lanes)
        self.assertIn("reason", lanes)

        # -------------------------------------------------------------
        # 3. Planted Negative Controls (Deterministic Failure Verification)
        # -------------------------------------------------------------
        def verify_ssot_structure(toml_dict):
            if "aliases" not in toml_dict:
                raise ValueError("PLANT_FAULT: missing [aliases] table")
            for k in ["browser", "file_manager", "editor", "terminal"]:
                if k not in toml_dict["aliases"]:
                    raise ValueError(f"PLANT_FAULT: missing [aliases].{k} key")

            if "desktop" not in toml_dict or "bindings" not in toml_dict["desktop"]:
                raise ValueError("PLANT_FAULT: missing [desktop.bindings] table")
            for k in ["mod_key", "app_drawer", "browser_launch", "quick_settings", "monitor_overlay"]:
                if k not in toml_dict["desktop"]["bindings"]:
                    raise ValueError(f"PLANT_FAULT: missing [desktop.bindings].{k} key")

            if "ai" not in toml_dict or "lanes" not in toml_dict["ai"]:
                raise ValueError("PLANT_FAULT: missing [ai.lanes] table")
            for k in ["fast", "code", "reason"]:
                if k not in toml_dict["ai"]["lanes"]:
                    raise ValueError(f"PLANT_FAULT: missing [ai.lanes].{k} key")
            return True

        # Sanity check: valid SSOT passes
        self.assertTrue(verify_ssot_structure(ssot_data))

        # Planted Fault 1: Missing [aliases] table
        bad_ssot_1 = {k: v for k, v in ssot_data.items() if k != "aliases"}
        with self.assertRaises(ValueError) as ctx:
            verify_ssot_structure(bad_ssot_1)
        self.assertIn("PLANT_FAULT: missing [aliases] table", str(ctx.exception))

        # Planted Fault 2: Missing [desktop.bindings] key
        bad_ssot_2 = {k: (dict(v) if isinstance(v, dict) else v) for k, v in ssot_data.items()}
        bad_ssot_2["desktop"] = {k: (dict(v) if isinstance(v, dict) else v) for k, v in ssot_data["desktop"].items()}
        bad_ssot_2["desktop"]["bindings"] = {k: v for k, v in ssot_data["desktop"]["bindings"].items() if k != "browser_launch"}
        with self.assertRaises(ValueError) as ctx:
            verify_ssot_structure(bad_ssot_2)
        self.assertIn("PLANT_FAULT: missing [desktop.bindings].browser_launch key", str(ctx.exception))

        # Planted Fault 3: Missing [ai.lanes] table
        bad_ssot_3 = {k: (dict(v) if isinstance(v, dict) else v) for k, v in ssot_data.items()}
        bad_ssot_3["ai"] = {k: (dict(v) if isinstance(v, dict) else v) for k, v in ssot_data["ai"].items() if k != "lanes"}
        with self.assertRaises(ValueError) as ctx:
            verify_ssot_structure(bad_ssot_3)
        self.assertIn("PLANT_FAULT: missing [ai.lanes] table", str(ctx.exception))

        # Planted Fault 4: Omission of canonical role from coordination text
        def verify_coordination_roles(text):
            for role in expected_roles:
                pattern = f"`{role}`"
                if pattern not in text:
                    raise ValueError(f"PLANT_FAULT: missing canonical role {role}")
            return True

        self.assertTrue(verify_coordination_roles(coord_content))
        tampered_coord = coord_content.replace("`orchestrator`", "[REDACTED]")
        with self.assertRaises(ValueError) as ctx:
            verify_coordination_roles(tampered_coord)
        self.assertIn("PLANT_FAULT: missing canonical role orchestrator", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
