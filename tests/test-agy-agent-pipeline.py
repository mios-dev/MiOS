#!/usr/bin/env python3
# AI-hint: Unit tests for MiOS Antigravity CLI (AGY) agent, subagents, workflows, and CI/CD artifacting integration.
# AI-doc: usr/share/doc/mios/manual/ch04-the-agentic-ai-stack.md
"""Test suite for MiOS Antigravity CLI (AGY) agent and subagents configuration."""

import json
import os
import re
import subprocess
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

        required_roles = {
            "pipeline-auditor",
            "pipeline-worker",
            "pipeline-reviewer",
            "artifact-publisher",
            "pipeline-orchestrator",
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
        self.assertFalse(missing, f"Missing required subagent definitions: {missing}")

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

    def test_commands_agy_definitions(self):
        """Verifies commands/agy/ and commands/antigravity/ definitions."""
        cmd_dir = REPO_ROOT / "commands" / "agy"
        self.assertTrue(cmd_dir.is_dir(), f"Missing {cmd_dir}")

        for cmd_name in ["dev-loop.toml", "pipeline.toml"]:
            cmd_file = cmd_dir / cmd_name
            self.assertTrue(cmd_file.is_file(), f"Missing {cmd_file}")
            txt = cmd_file.read_text(encoding="utf-8")
            self.assertIn("[command]", txt)
            self.assertIn("name =", txt)

        # Antigravity mirror check
        mirror_dir = REPO_ROOT / "commands" / "antigravity"
        self.assertTrue(mirror_dir.is_dir(), f"Missing {mirror_dir}")
        self.assertTrue((mirror_dir / "dev-loop.toml").is_file())
        self.assertTrue((mirror_dir / "pipeline.toml").is_file())

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
        res = subprocess.run(["bash", "-n", str(cicd_runner)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Syntax error in {cicd_runner}: {res.stderr}")

    def test_agents_command_definitions(self):
        """Verifies commands/agy/agents.toml, commands/antigravity/agents.toml, and agents workflow."""
        agy_agents = REPO_ROOT / "commands" / "agy" / "agents.toml"
        antigravity_agents = REPO_ROOT / "commands" / "antigravity" / "agents.toml"
        self.assertTrue(agy_agents.is_file(), f"Missing {agy_agents}")
        self.assertTrue(antigravity_agents.is_file(), f"Missing {antigravity_agents}")

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
        """Verifies .agents/agents/ contains definitions for all 6 MiOS-Dev agents."""
        agents_dir = REPO_ROOT / ".agents" / "agents"
        self.assertTrue(agents_dir.is_dir(), f"Missing {agents_dir}")

        expected = [
            "mios-dev.md",
            "pipeline-auditor.md",
            "pipeline-worker.md",
            "pipeline-reviewer.md",
            "artifact-publisher.md",
            "pipeline-orchestrator.md",
        ]
        for fname in expected:
            fpath = agents_dir / fname
            self.assertTrue(fpath.is_file(), f"Missing {fpath}")
            txt = fpath.read_text(encoding="utf-8")
            self.assertTrue(txt.startswith("---"), f"{fname} missing YAML frontmatter")
            self.assertIn("name:", txt)
            self.assertIn("description:", txt)


if __name__ == "__main__":
    unittest.main()
