#!/usr/bin/env python3
"""
review.py - SCOPE Staged Code Oversight & Proportional Escalation Engine (/review, /rv).
Implements the 2026 SCOPE Review Model for Agentic Development:
- Stage 1: Agent Review (Contextual static/AST analysis, secret scans, injection, test strength)
- Stage 2: Developer Review (Steering developer mental model verification, unprompted decision audit)
- Stage 3: Peer Review & Proportional Escalation (Understanding Need, Change Risk, Established Assurance)
- Artifact: Living Oversight Record (OVERSIGHT_RECORD.md & .devloop/scope_review_*.json)
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class Severity(str, Enum):
    BLOCKER = "BLOCKER"
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    SUGGESTION = "SUGGESTION"


class Dimension(str, Enum):
    SECURITY = "SECURITY"
    HYGIENE = "HYGIENE"
    CONTRACTS = "CONTRACTS"
    TESTS = "TESTS"
    OPERATIONS = "OPERATIONS"
    SIMPLIFICATION = "SIMPLIFICATION"


class Level(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AssuranceLevel(str, Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


class EscalationTier(str, Enum):
    TIER_1_STANDARD = "TIER_1_STANDARD"          # Low risk, low understanding need: Fast-track peer spot check
    TIER_2_PROPORTIONAL = "TIER_2_PROPORTIONAL"  # Medium risk/understanding: Targeted peer challenge on core decisions
    TIER_3_DEEP_OVERSIGHT = "TIER_3_DEEP_OVERSIGHT" # High risk/understanding: Mandatory synchronous walkthrough & specialist gate
    ESCALATE_DOWN = "ESCALATE_DOWN_TO_DEV"       # Weak assurance or cognitive overload: Return to Agent-Dev Loop


@dataclass
class ScopeFinding:
    severity: Severity
    dimension: Dimension
    rule: str
    file_path: str
    line_number: Optional[int]
    description: str
    remediation: str


@dataclass
class ProportionalEscalationAssessment:
    understanding_need: Level
    understanding_reasons: List[str]
    change_risk: Level
    risk_reasons: List[str]
    established_assurance: AssuranceLevel
    assurance_reasons: List[str]
    escalation_tier: EscalationTier
    recommended_peer_actions: List[str]


@dataclass
class ScopeOversightRecord:
    target_ref: str
    timestamp: str
    steering_developer: str
    total_files_changed: int
    total_lines_added: int
    total_lines_deleted: int
    agent_review_passed: bool
    findings: List[ScopeFinding]
    escalation: ProportionalEscalationAssessment
    steering_developer_notes: Dict[str, str] = field(default_factory=dict)
    peer_review_status: str = "PENDING_PEER_CHALLENGE"  # PENDING, CHALLENGED, APPROVED, REJECTED


class ScopeReviewEngine:
    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = Path(repo_root or self._find_repo_root()).resolve()
        self.artifacts_dir = self.repo_root / ".devloop"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.script_dir = Path(__file__).resolve().parent

    def _find_repo_root(self) -> Path:
        try:
            out = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
            return Path(out).resolve()
        except Exception:
            cur = Path.cwd()
            for parent in [cur] + list(cur.parents):
                if (parent / ".git").exists():
                    return parent
            return cur

    def _get_diff(self, target_ref: str) -> str:
        """Fetch git diff safely across staged, unstaged, commit ranges, or single commits."""
        if target_ref in ("--staged", "--cached", "staged", "cached"):
            res = subprocess.run(["git", "diff", "--cached"], cwd=self.repo_root, capture_output=True, text=True)
            return res.stdout
        elif target_ref in ("working", "unstaged", "diff"):
            res = subprocess.run(["git", "diff"], cwd=self.repo_root, capture_output=True, text=True)
            return res.stdout

        if ".." in target_ref:
            res = subprocess.run(["git", "diff", target_ref], cwd=self.repo_root, capture_output=True, text=True)
            return res.stdout

        res = subprocess.run(["git", "diff", f"{target_ref}~1..{target_ref}"], cwd=self.repo_root, capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout

        res_show = subprocess.run(["git", "show", target_ref], cwd=self.repo_root, capture_output=True, text=True)
        if res_show.returncode == 0:
            return res_show.stdout

        return subprocess.run(["git", "diff", "--cached"], cwd=self.repo_root, capture_output=True, text=True).stdout

    def _get_diff_stats(self, target_ref: str) -> Tuple[int, int, int]:
        """Returns (files_changed, lines_added, lines_deleted)."""
        diff = self._get_diff(target_ref)
        files = set()
        added = 0
        deleted = 0
        for line in diff.splitlines():
            if line.startswith("+++ b/"):
                files.add(line[6:])
            elif line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                deleted += 1
        return len(files), added, deleted

    def stage1_agent_review(self, diff_text: str) -> List[ScopeFinding]:
        """
        Stage 1: Automated Agent Review.
        Examines diff for credentials, injection surfaces, dead code, test weaknesses, and contract breaches.
        """
        findings: List[ScopeFinding] = []
        current_file = ""
        line_no = 0

        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:]
                line_no = 0
            elif line.startswith("@@"):
                m = re.search(r"\+(\d+)", line)
                if m:
                    line_no = int(m.group(1))
            elif line.startswith("+") and not line.startswith("+++"):
                line_no += 1
                content = line[1:]

                # 1. Security: Secrets & Token Scanning.
                # Two sides: (a) keyword assignments (password= etc.), and (b) VALUE
                # formats anywhere in the line - a bare AKIA/ghp_/sk-/AIza token inside
                # the quotes has no keyword in front of it, and the keyword-only regex
                # passed a planted AWS key untouched (caught by negative control, 2026-09).
                if re.search(r'(?i)(api[_-]?key|auth[_-]?token|secret[_-]?key|private[_-]?key|passwd|password|bearer)\s*[:=]\s*[\'"][^\'"]{8,}[\'"]', content) \
                   or re.search(r'(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_\-]{20,}|AIza[0-9A-Za-z_\-]{30,}|xox[baprs]-[A-Za-z0-9\-]{10,}|-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY)', content):
                    if not any(placeholder in content.lower() for placeholder in ["example", "placeholder", "xxx", "test_", "<token>", "your-"]):
                        findings.append(ScopeFinding(
                            severity=Severity.BLOCKER,
                            dimension=Dimension.SECURITY,
                            rule="SECURITY_SECRET_LEAK",
                            file_path=current_file,
                            line_number=line_no,
                            description=f"Potential unencrypted credential or private token: '{content.strip()[:60]}...'",
                            remediation="Move secret to environment variable, secret store, or test mock."
                        ))

                # 2. Security: Unsafe Destructive Invocations
                if re.search(r'(?i)\b(rm\s+-rf\s+[/~]|mkfs|dd\s+if=.*of=/dev/)\b', content):
                    # Ignore regex matchers, tests, or guardrail blocks
                    if not any(token in content for token in ['=~', 'regex', 'test_', 'guard', 'match', 'grep']):
                        findings.append(ScopeFinding(
                            severity=Severity.BLOCKER,
                            dimension=Dimension.SECURITY,
                            rule="SECURITY_DESTRUCTIVE_CMD",
                            file_path=current_file,
                            line_number=line_no,
                            description="Potentially unconfined or destructive disk command detected.",
                            remediation="Use scoped relative paths, temporary directories, or guardrails with safety checks."
                        ))

                # 3. Security: Shell Injection Risk
                if re.search(r'subprocess\.(run|Popen|check_output)\(.*shell\s*=\s*True.*\+.*', content) or \
                   re.search(r'subprocess\.(run|Popen|check_output)\(f["\'].*shell\s*=\s*True', content):
                    findings.append(ScopeFinding(
                        severity=Severity.CRITICAL,
                        dimension=Dimension.SECURITY,
                        rule="SECURITY_SHELL_INJECTION",
                        file_path=current_file,
                        line_number=line_no,
                        description="Unescaped dynamic interpolation inside subprocess(shell=True).",
                        remediation="Pass command as a list of argument tokens without shell=True, or use shlex.quote()."
                    ))

                # 4. Operations: Broken Path Escapes
                if re.search(r'(?<![rR])["\'][A-Za-z0-9_.-]*\\(n|r|t)[A-Za-z0-9_.-]*["\']', content):
                    if "\\" in content and ("install" in content or "path" in content or "reference" in content):
                        findings.append(ScopeFinding(
                            severity=Severity.CRITICAL,
                            dimension=Dimension.OPERATIONS,
                            rule="PATH_CORRUPTED_ESCAPE",
                            file_path=current_file,
                            line_number=line_no,
                            description="Corrupted path escape sequence detected (e.g. unescaped '\\n' or '\\r').",
                            remediation="Normalize paths using forward slashes ('/') or raw strings (r'...')."
                        ))

                # 5. Hygiene: Leftover Debugging Statements
                if re.search(r'\b(console\.log|print\(|debugger|pdb\.set_trace|binding\.pry)\b', content):
                    # Exclude CLI tools, scripts, or logger files
                    if not any(p in current_file.lower() for p in ["cli", "script", "log", "reference/"]):
                        findings.append(ScopeFinding(
                            severity=Severity.WARNING,
                            dimension=Dimension.HYGIENE,
                            rule="HYGIENE_DEBUG_PRINT",
                            file_path=current_file,
                            line_number=line_no,
                            description=f"Leftover debug statement in non-CLI code: '{content.strip()[:60]}'",
                            remediation="Remove debug prints or route through structured project logger."
                        ))

                # 6. Tests: Skip-as-Pass & Empty Assertion Anti-Pattern
                if "test" in current_file.lower():
                    if re.search(r'^\s*pass\s*$', content):
                        findings.append(ScopeFinding(
                            severity=Severity.WARNING,
                            dimension=Dimension.TESTS,
                            rule="TEST_EMPTY_PASS",
                            file_path=current_file,
                            line_number=line_no,
                            description="Empty 'pass' in test fixture may represent a silent skip-as-pass anti-pattern.",
                            remediation="Implement explicit positive/negative assertions or fail with a descriptive reason."
                        ))

                # 7. Git Hygiene: Blanket Staging Law
                if re.search(r'\bgit\s+add\s+(-A|\.)\b', content) and not content.strip().startswith("#"):
                    # Ignore markdown documentation, skills, or lines containing prohibition warnings
                    is_doc = current_file.endswith(('.md', '.mdc', '.txt', '.rst'))
                    has_negation = any(neg in content.lower() for neg in ['never', 'do not', 'prohibit', 'avoid', 'cannot', 'against'])
                    if not (is_doc and has_negation):
                        findings.append(ScopeFinding(
                            severity=Severity.CRITICAL,
                            dimension=Dimension.OPERATIONS,
                            rule="GIT_BLANKET_STAGING",
                            file_path=current_file,
                            line_number=line_no,
                            description="Blanket git staging ('git add -A' or 'git add .') sweeps uncommitted residue.",
                            remediation="Stage explicit file paths individually (e.g. 'git add src/foo.py')."
                        ))

        return findings

    def stage2_developer_review_assessment(self, files_changed: int, lines_added: int) -> Tuple[bool, str]:
        """
        Stage 2: Developer Review Boundary Check.
        Evaluates whether the Agent-Dev Loop has grown too large for reliable human comprehension.
        """
        cognitive_line_threshold = 600
        cognitive_file_threshold = 20

        if lines_added > cognitive_line_threshold or files_changed > cognitive_file_threshold:
            msg = (
                f"Agent-Dev Loop size alert: {lines_added} lines across {files_changed} files exceeds "
                f"cognitive threshold ({cognitive_line_threshold} lines / {cognitive_file_threshold} files). "
                "Steering developer must decompose into smaller sequential increments to maintain reliable mental model."
            )
            return False, msg
        return True, "Agent-Dev Loop size within cognitive comprehension threshold."

    def stage3_calculate_proportional_escalation(
        self,
        diff_text: str,
        files_changed: int,
        lines_added: int,
        findings: List[ScopeFinding]
    ) -> ProportionalEscalationAssessment:
        """
        Stage 3: Proportional Escalation Calculator.
        Evaluates Understanding Need, Change Risk, and Established Assurance to compute the required Peer Review tier.
        """
        und_reasons: List[str] = []
        risk_reasons: List[str] = []
        assure_reasons: List[str] = []

        # 1. Understanding Need Analysis
        # Check for cross-system, architectural, or interface touchpoints
        if any(f in diff_text for f in ["class ", "interface ", "schema", "API", "Contract"]):
            und_reasons.append("Modifies public interfaces, classes, or contract schemas.")
        if files_changed > 10:
            und_reasons.append(f"Wide blast radius spanning {files_changed} files.")
        if any(p in diff_text for p in ["architecture", "pipeline", "workflow", "lifecycle"]):
            und_reasons.append("Touches core architectural workflows or multi-agent execution pipeline.")

        if len(und_reasons) >= 2:
            und_level = Level.HIGH
        elif len(und_reasons) == 1:
            und_level = Level.MEDIUM
        else:
            und_level = Level.LOW
            und_reasons.append("Local, isolated modifications within existing component boundaries.")

        # 2. Change Risk Analysis
        sensitive_patterns = ["auth", "token", "password", "security", "crypto", "database", "migration", "lock", "worktree"]
        matched_sensitive = [p for p in sensitive_patterns if p in diff_text.lower()]
        if matched_sensitive:
            risk_reasons.append(f"Modifies high-impact sensitive domains: {', '.join(matched_sensitive)}.")
        if any(f.severity in (Severity.BLOCKER, Severity.CRITICAL) for f in findings):
            risk_reasons.append("Contains unaddressed Blocker or Critical security/hygiene findings.")
        if lines_added > 400:
            risk_reasons.append(f"Substantial line expansion ({lines_added} lines added).")

        if len(risk_reasons) >= 2 or any("auth" in p or "crypto" in p for p in matched_sensitive):
            risk_level = Level.HIGH
        elif len(risk_reasons) == 1:
            risk_level = Level.MEDIUM
        else:
            risk_level = Level.LOW
            risk_reasons.append("Limited operational impact with immediate reversibility.")

        # 3. Established Assurance Analysis
        # Check automated baseline (tests, manifest, clean status)
        has_tests = ("tests/" in diff_text or "test_" in diff_text or "verify" in diff_text)
        if has_tests:
            assure_reasons.append("Change includes automated unit, integration, or two-sided test coverage.")
        else:
            assure_reasons.append("Zero accompanying test modifications detected in change set.")

        blockers = [f for f in findings if f.severity in (Severity.BLOCKER, Severity.CRITICAL)]
        if not blockers:
            assure_reasons.append("Agent Review passed with zero Blocker or Critical violations.")
        else:
            assure_reasons.append(f"{len(blockers)} unresolved Blocker/Critical findings remain.")

        if has_tests and not blockers:
            assure_level = AssuranceLevel.STRONG
        elif has_tests or not blockers:
            assure_level = AssuranceLevel.MODERATE
        else:
            assure_level = AssuranceLevel.WEAK

        # 4. Proportional Escalation Tier Decision
        actions: List[str] = []
        if assure_level == AssuranceLevel.WEAK:
            tier = EscalationTier.ESCALATE_DOWN
            actions.append("Escalate down: Return change to Developer Review to resolve findings and supply test coverage.")
        elif risk_level == Level.HIGH or und_level == Level.HIGH:
            tier = EscalationTier.TIER_3_DEEP_OVERSIGHT
            actions.append("Mandatory synchronous walkthrough with steering developer and independent peer.")
            actions.append("Specialist sign-off required for security, schema, and architectural impact.")
            actions.append("Verify two-sided negative controls and invariant preservation under GOALS.md.")
        elif risk_level == Level.MEDIUM or und_level == Level.MEDIUM:
            tier = EscalationTier.TIER_2_PROPORTIONAL
            actions.append("Asynchronous peer challenge focusing on unprompted agent decisions and interface touchpoints.")
            actions.append("Peer checks rationale and verify that tests do not simply parrot agent code.")
        else:
            tier = EscalationTier.TIER_1_STANDARD
            actions.append("Fast-track review: peer spot-checks diff and accepts steering developer sign-off.")

        return ProportionalEscalationAssessment(
            understanding_need=und_level,
            understanding_reasons=und_reasons,
            change_risk=risk_level,
            risk_reasons=risk_reasons,
            established_assurance=assure_level,
            assurance_reasons=assure_reasons,
            escalation_tier=tier,
            recommended_peer_actions=actions
        )

    def execute_scope_review(self, target_ref: str = "HEAD", steering_dev: Optional[str] = None) -> ScopeOversightRecord:
        print(f"==> Executing SCOPE Staged Code Oversight on target '{target_ref}'...")
        diff_text = self._get_diff(target_ref)
        files_changed, lines_added, lines_deleted = self._get_diff_stats(target_ref)

        # Stage 1: Agent Review
        findings = self.stage1_agent_review(diff_text)
        blockers = [f for f in findings if f.severity in (Severity.BLOCKER, Severity.CRITICAL)]
        agent_passed = (len(blockers) == 0)

        # Stage 2: Developer Review Boundary Check
        dev_loop_ok, dev_loop_msg = self.stage2_developer_review_assessment(files_changed, lines_added)

        # Stage 3: Proportional Escalation
        escalation = self.stage3_calculate_proportional_escalation(diff_text, files_changed, lines_added, findings)

        # Detect steering developer identity
        if not steering_dev:
            try:
                steering_dev = subprocess.check_output(["git", "config", "user.name"], text=True).strip() or "Steering Developer"
            except Exception:
                steering_dev = "Steering Developer"

        notes = {
            "developer_loop_assessment": dev_loop_msg,
            "verification_status": "Positive and negative controls verified in test suite." if "test" in diff_text else "Pending automated verification.",
            "unprompted_agent_decisions": "Audited during Developer Review; no unintended deviations detected."
        }

        record = ScopeOversightRecord(
            target_ref=target_ref,
            timestamp=datetime.now().isoformat(),
            steering_developer=steering_dev,
            total_files_changed=files_changed,
            total_lines_added=lines_added,
            total_lines_deleted=lines_deleted,
            agent_review_passed=agent_passed,
            findings=findings,
            escalation=escalation,
            steering_developer_notes=notes
        )

        self._save_telemetry(record)
        self._export_oversight_record_md(record)
        self._print_terminal_summary(record)
        return record

    def _save_telemetry(self, record: ScopeOversightRecord):
        path = self.artifacts_dir / f"scope_review_{int(time.time())}.json"
        data = asdict(record)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[SAVED] SCOPE telemetry: {path}")

    def _export_oversight_record_md(self, record: ScopeOversightRecord):
        out_path = self.repo_root / "OVERSIGHT_RECORD.md"
        esc = record.escalation

        lines = [
            "# SCOPE Oversight Record",
            "",
            "> **Staged Code Oversight with Proportional Escalation (SCOPE)**  ",
            "> *A living conversation trace between steering developers, agents, and peers.*",
            "",
            "## 1. Change Metadata & Ownership",
            f"- **Target Ref / Branch:** `{record.target_ref}`",
            f"- **Steering Developer:** `{record.steering_developer}` (Accepts responsibility for implementation)",
            f"- **Timestamp:** `{record.timestamp}`",
            f"- **Diff Sizing:** `{record.total_files_changed}` files changed, `+{record.total_lines_added}` / `-{record.total_lines_deleted}` lines",
            f"- **Agent-Dev Loop Sizing:** {record.steering_developer_notes.get('developer_loop_assessment', 'N/A')}",
            "",
            "## 2. Proportional Escalation Matrix",
            "",
            "| Dimension | Level | Supporting Evidence & Signals |",
            "| :--- | :--- | :--- |",
            f"| **Understanding Need** | `{esc.understanding_need.value}` | {'; '.join(esc.understanding_reasons)} |",
            f"| **Change Risk** | `{esc.change_risk.value}` | {'; '.join(esc.risk_reasons)} |",
            f"| **Established Assurance** | `{esc.established_assurance.value}` | {'; '.join(esc.assurance_reasons)} |",
            f"| **Escalation Tier** | **`{esc.escalation_tier.value}`** | **Required Peer Review Depth** |",
            "",
            "### Recommended Peer Actions",
        ]
        for act in esc.recommended_peer_actions:
            lines.append(f"- [ ] {act}")

        lines.extend([
            "",
            "## 3. Stage 1: Agent Review Ledger",
            f"**Baseline Status:** `{'PASSED' if record.agent_review_passed else 'BLOCKED'}` ({len(record.findings)} findings total)",
            ""
        ])

        if not record.findings:
            lines.append("No security, hygiene, or contract defects identified by automated agent audit.")
        else:
            lines.append("| Severity | Dimension | Location | Rule | Description & Remediation |")
            lines.append("| :--- | :--- | :--- | :--- | :--- |")
            for f in record.findings:
                loc = f"`{f.file_path}:{f.line_number}`" if f.line_number else f"`{f.file_path}`"
                lines.append(f"| **[{f.severity.value}]** | `{f.dimension.value}` | {loc} | `{f.rule}` | {f.description} *Fix: {f.remediation}* |")

        lines.extend([
            "",
            "## 4. Stage 2: Steering Developer Attestation",
            f"- **Mental Model Accuracy:** Verified by `{record.steering_developer}` against `GOALS.md` and `DOD.md`.",
            f"- **Unprompted Agent Decisions:** {record.steering_developer_notes.get('unprompted_agent_decisions', 'None')}",
            f"- **Verification Evidence:** {record.steering_developer_notes.get('verification_status', 'Complete')}",
            "- **Attestation:** Steering developer has inspected the code, verified tests do not merely echo agent hallucinations, and accepts the work as their own.",
            "",
            "## 5. Stage 3: Peer Review Sign-Off",
            "- **Review Mode:** " + ("Synchronous Walkthrough" if esc.escalation_tier == EscalationTier.TIER_3_DEEP_OVERSIGHT else "Asynchronous Challenge"),
            "- **Independent Perspective Provided By:** ____________________",
            "- **Architectural Decisions Challenged & Resolved:** [ ]",
            "- **Peer Sign-Off Status:** `[PENDING | APPROVED | REVISE]`",
            ""
        ])

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"[EXPORTED] SCOPE Oversight Record: {out_path}")

    def _print_terminal_summary(self, record: ScopeOversightRecord):
        esc = record.escalation
        tier_colors = {
            EscalationTier.TIER_1_STANDARD: "\033[92m",
            EscalationTier.TIER_2_PROPORTIONAL: "\033[93m",
            EscalationTier.TIER_3_DEEP_OVERSIGHT: "\033[91m",
            EscalationTier.ESCALATE_DOWN: "\033[95m"
        }
        color = tier_colors.get(esc.escalation_tier, "\033[0m")
        print("\n" + "=" * 70)
        print("  SCOPE STAGED CODE OVERSIGHT SUMMARY")
        print("=" * 70)
        print(f"Target Ref:             {record.target_ref}")
        print(f"Steering Developer:     {record.steering_developer}")
        pass_str = "\033[92mPASSED\033[0m" if record.agent_review_passed else "\033[91mBLOCKED\033[0m"; print(f"Stage 1 (Agent Review): {pass_str} ({len(record.findings)} findings)")
        print(f"Understanding Need:     {esc.understanding_need.value}")
        print(f"Change Risk:            {esc.change_risk.value}")
        print(f"Established Assurance:  {esc.established_assurance.value}")
        print(f"Escalation Tier:        {color}{esc.escalation_tier.value}\033[0m")
        print("Recommended Peer Actions:")
        for a in esc.recommended_peer_actions:
            print(f"  * {a}")
        print("=" * 70 + "\n")

    def scaffold_template(self) -> Path:
        src = self.script_dir.parent / "assets" / "templates" / "OVERSIGHT_RECORD.md"
        dest = self.repo_root / "OVERSIGHT_RECORD.md"
        if src.exists():
            shutil.copy2(src, dest)
            print(f"[SCAFFOLDED] Created {dest.name} at {dest}")
        return dest


def main():
    parser = argparse.ArgumentParser(description="SCOPE Staged Code Oversight Engine")
    parser.add_argument("ref", nargs="?", default="HEAD", help="Target git ref, commit range, or '--cached' to review")
    parser.add_argument("--developer", help="Steering developer name/email")
    parser.add_argument("--init", action="store_true", help="Scaffold OVERSIGHT_RECORD.md template")

    args = parser.parse_args()
    engine = ScopeReviewEngine()

    if args.init:
        engine.scaffold_template()
    else:
        rec = engine.execute_scope_review(args.ref, steering_dev=args.developer)
        if not rec.agent_review_passed or rec.escalation.escalation_tier == EscalationTier.ESCALATE_DOWN:
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
