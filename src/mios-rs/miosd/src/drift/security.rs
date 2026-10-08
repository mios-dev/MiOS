// AI-hint: Security, shellcheck, and eval safety checks for miosd drift runner.
// AI-related: automation/lint-python.sh, automation/98-drift-checks.sh

use super::{Check, DriftCtx, Verdict};
use super::audit;
use std::process::Command;

fn compiler_lint(ctx: &DriftCtx, python: bool) -> audit::Audit {
    let config = audit::ssot(ctx)?;
    let tool_key = if python { "drift.lint.python" } else { "drift.lint.shellcheck" };
    let tool = audit::at(&config, tool_key)?.as_str().filter(|s| !s.trim().is_empty()).ok_or_else(|| format!("Invalid SSOT {tool_key}"))?;
    let excluded = audit::strings(&config, if python { "drift.lint.python_exclude" } else { "drift.lint.shell_exclude" })?;
    let directories = audit::strings(&config, "drift.lint.shell_directories")?;
    for path in excluded.iter().chain(directories.iter()) {
        if path.starts_with('/') || path.contains('\\') || path.split('/').any(|part| part == "..") { return Err(format!("Unconfined lint policy path: {path}")); }
    }
    let severity = audit::at(&config, "drift.lint.shell_severity")?.as_str().filter(|s| matches!(*s, "error" | "warning" | "info" | "style")).ok_or("Invalid SSOT drift.lint.shell_severity")?;
    let mut subjects = 0;
    let mut errors = Vec::new();
    for path in audit::tracked(ctx)? {
        if excluded.contains(&path) { continue; }
        let absolute = ctx.root.join(&path);
        if !absolute.is_file() { return Err(format!("Tracked lint subject missing: {path}")); }
        let data = std::fs::read(&absolute).map_err(|e| format!("{path}: {e}"))?;
        let first = data.split(|b| *b == b'\n').next().unwrap_or_default();
        let shebang = std::str::from_utf8(first).unwrap_or("");
        let selected = if python {
            path.ends_with(".py") || (shebang.starts_with("#!") && shebang.contains("python"))
        } else {
            let parent = path.rsplit_once('/').map(|(parent, _)| parent).unwrap_or("");
            directories.iter().any(|directory| directory == parent)
                && (path.ends_with(".sh") || (shebang.starts_with("#!") && (shebang.contains("bash") || shebang.ends_with("/sh") || shebang.ends_with(" sh"))))
        };
        if !selected { continue; }
        subjects += 1;
        let mut command = Command::new(tool);
        if python {
            // Python is the language compiler, not the gate implementation.
            // Parsing bytes preserves encoding cookies; no module executes and
            // no __pycache__ is written into the shared source tree.
            command.args(["-c", "import sys; compile(open(sys.argv[1], 'rb').read(), sys.argv[1], 'exec', dont_inherit=True)"]);
        } else { command.arg(format!("--severity={severity}")).arg("--"); }
        let output = command.arg(&absolute).current_dir(&ctx.root).output().map_err(|e| format!("Required lint compiler {tool}: {e}"))?;
        if !output.status.success() {
            errors.push(format!("{path}: {tool} {}\n{}{}", output.status, String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr)));
        }
    }
    audit::finish(subjects, errors, if python { "Python syntax compiler" } else { "ShellCheck" })
}

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
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        audit::verdict(compiler_lint(ctx, false))
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
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        audit::verdict(compiler_lint(ctx, true))
    }
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    const POLICY: &str = "[drift.lint]\npython='python3'\nshellcheck='shellcheck'\nshell_severity='error'\nshell_directories=['']\nshell_exclude=[]\npython_exclude=[]\n";

    #[test]
    fn real_compilers_detect_source_mutations_without_executing_python_and_refuse_empty_or_missing_tools() -> Result<(), Box<dyn std::error::Error>> {
        let temp = tempfile::tempdir()?;
        std::fs::create_dir_all(temp.path().join("usr/share/mios"))?;
        let policy = temp.path().join("usr/share/mios/mios.toml");
        std::fs::write(&policy, POLICY)?;
        for args in [vec!["init", "-q"], vec!["add", "usr/share/mios/mios.toml"]] {
            assert!(Command::new("git").arg("-C").arg(temp.path()).args(args).status()?.success());
        }
        let ctx = DriftCtx::new(temp.path().into(), false);
        assert!(compiler_lint(&ctx, true).is_err());
        assert!(compiler_lint(&ctx, false).is_err());
        let python = temp.path().join("subject.py");
        let shell = temp.path().join("subject.sh");
        std::fs::write(&python, "open('SHOULD-NOT-EXECUTE', 'w').write('executed')\n")?;
        std::fs::write(&shell, "#!/bin/bash\necho \"$HOME\"\n")?;
        assert!(Command::new("git").arg("-C").arg(temp.path()).args(["add", "subject.py", "subject.sh"]).status()?.success());
        assert!(compiler_lint(&ctx, true)?.contains("1 subject"));
        assert!(!temp.path().join("SHOULD-NOT-EXECUTE").exists());
        assert!(!temp.path().join("__pycache__").exists());
        assert!(compiler_lint(&ctx, false)?.contains("1 subject"));
        std::fs::write(&python, "def malformed(:\n")?;
        assert!(compiler_lint(&ctx, true).is_err_and(|e| e.contains("subject.py") && e.contains("SyntaxError")));
        std::fs::write(&shell, "#!/bin/bash\nif then\n")?;
        assert!(compiler_lint(&ctx, false).is_err_and(|e| e.contains("subject.sh")));
        std::fs::write(&policy, POLICY.replace("shellcheck='shellcheck'", "shellcheck='missing-mios-lint-compiler'"))?;
        assert!(compiler_lint(&ctx, false).is_err_and(|e| e.contains("Required lint compiler")));
        std::fs::write(&policy, POLICY.replace("shell_directories=['']", "shell_directories=['../outside']"))?;
        assert!(compiler_lint(&ctx, false).is_err_and(|e| e.contains("Unconfined")));
        Ok(())
    }
}
