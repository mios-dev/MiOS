// AI-hint: Security, shellcheck, and eval safety checks for miosd drift runner.
// AI-related: automation/lint-python.sh, automation/98-drift-checks.sh

use super::{Check, DriftCtx, Verdict};

pub struct CLIEvalSafetyCheck;
impl Check for CLIEvalSafetyCheck {
    fn id(&self) -> &'static str {
        "check_cli_eval_safety"
    }
    fn describe(&self) -> &'static str {
        "Assert no unsafe eval-on-agent-args pattern exists in CLI verb scripts"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: CLI eval safety".to_string())
    }
}

pub struct ShellcheckLintCheck;
impl Check for ShellcheckLintCheck {
    fn id(&self) -> &'static str {
        "check_shellcheck"
    }
    fn describe(&self) -> &'static str {
        "Assert all shell scripts pass shellcheck lint"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: Shellcheck lint".to_string())
    }
}

pub struct PythonCompileLintCheck;
impl Check for PythonCompileLintCheck {
    fn id(&self) -> &'static str {
        "check_python_lint"
    }
    fn describe(&self) -> &'static str {
        "Assert all python scripts compile without syntax errors"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: Python compile lint".to_string())
    }
}
