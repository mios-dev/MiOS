// AI-hint: Helper functions for running generator scripts and diffing against committed SSOT targets in clean environments.
// AI-related: automation/98-drift-checks.sh, src/mios-rs/miosd/src/drift/mod.rs

use super::{DriftCtx, Verdict};
use std::collections::HashMap;
use std::env;
use std::process::Command;

pub fn regen_and_diff(
    ctx: &DriftCtx,
    gen_relpath: &str,
    targets: &[&str],
    extra_args: &[&str],
) -> Verdict {
    let gen_path = ctx.root.join(gen_relpath);
    if !gen_path.exists() {
        return Verdict::Skip(format!(
            "Generator script not found: {}",
            gen_path.display()
        ));
    }

    let python_cmd = if Command::new("python3").arg("--version").output().is_ok() {
        "python3"
    } else if Command::new("python").arg("--version").output().is_ok() {
        "python"
    } else {
        return Verdict::Skip("Python interpreter not found".to_string());
    };

    // Clean env isolation to prevent env leakage
    let mut clean_env = HashMap::new();
    if let Ok(path) = env::var("PATH") {
        clean_env.insert("PATH", path);
    }
    if let Ok(home) = env::var("HOME") {
        clean_env.insert("HOME", home);
    }
    clean_env.insert("MIOS_ROOT", ctx.root.to_string_lossy().to_string());

    let mut cmd = Command::new(python_cmd);
    cmd.arg(&gen_path);
    cmd.args(extra_args);

    cmd.env_clear();
    for (k, v) in &clean_env {
        cmd.env(k, v);
    }

    let output = match cmd.output() {
        Ok(out) => out,
        Err(e) => {
            return Verdict::Fail(format!(
                "Failed to execute generator {}: {}",
                gen_relpath, e
            ))
        }
    };

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Verdict::Fail(format!(
            "Generator {} exited with error: {}",
            gen_relpath,
            stderr.trim()
        ));
    }

    for target in targets {
        let target_path = ctx.root.join(target);
        if !target_path.exists() {
            return Verdict::Fail(format!("Target artifact missing: {}", target));
        }
    }

    Verdict::Pass(format!("Projection check {} passed cleanly", gen_relpath))
}
