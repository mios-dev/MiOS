// AI-hint: Helper functions for running generator scripts and diffing against committed SSOT targets in clean environments.
// AI-related: automation/98-drift-checks.sh, src/mios-rs/miosd/src/drift/mod.rs

use super::{DriftCtx, Verdict};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::Path;
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

/// Re-render a projection whose generator is a SHELL renderer and diff it against
/// what is committed.
///
/// `regen_and_diff` above only suits generators that implement `--check` and
/// report drift through their exit code. The chrony/nut/kargs/composefs
/// projections have no such mode: `automation/NN-*-render.sh` WRITE their output.
/// Six checks in this registry were therefore wired to Python generators that do
/// not exist in the tree (`generate-kargs.py`, `generate-chrony-conf.py`, ...),
/// and because a missing generator yields `Verdict::Skip`, they never ran and
/// never said so.
///
/// This renders into a scratch directory seeded with the committed artifact,
/// then compares -- the same shape as the bash gate's kargs check.
pub fn regen_and_diff_shell(
    ctx: &DriftCtx,
    script_relpath: &str,
    out_env: &str,
    target: &str,
) -> Verdict {
    let script = ctx.root.join(script_relpath);
    if !script.exists() {
        // Loud, not Skip: a registered check whose renderer is absent is a
        // registry bug, not an environment quirk.
        return Verdict::Fail(format!(
            "Renderer not found: {} (registered by a drift check)",
            script_relpath
        ));
    }
    let committed = ctx.root.join(target);
    if !committed.exists() {
        return Verdict::Fail(format!("Target artifact missing: {}", target));
    }

    let scratch = std::env::temp_dir().join(format!("mios-drift-{}", std::process::id()));
    let _ = fs::remove_dir_all(&scratch);
    if let Err(e) = fs::create_dir_all(&scratch) {
        return Verdict::Fail(format!("Cannot create scratch dir: {e}"));
    }

    // Seed the scratch with the committed artifact so a renderer that edits in
    // place has the same starting point the real one does.
    let out_path = if committed.is_dir() {
        if let Err(e) = copy_dir(&committed, &scratch) {
            return Verdict::Fail(format!("Cannot seed scratch from {target}: {e}"));
        }
        scratch.clone()
    } else {
        let dst = scratch.join(committed.file_name().unwrap_or_default());
        if let Err(e) = fs::copy(&committed, &dst) {
            return Verdict::Fail(format!("Cannot seed scratch from {target}: {e}"));
        }
        dst
    };

    let toml = ctx.root.join("usr/share/mios/mios.toml");
    let mut cmd = Command::new("bash");
    cmd.arg(&script);
    cmd.env_clear();
    if let Ok(p) = env::var("PATH") {
        cmd.env("PATH", p);
    }
    cmd.env("MIOS_TOML", &toml)
        .env("MIOS_VENDOR_TOML", &toml)
        .env("MIOS_ROOT", &ctx.root)
        .env(out_env, &out_path);

    match cmd.output() {
        Err(e) => return Verdict::Fail(format!("Failed to run {script_relpath}: {e}")),
        Ok(out) if !out.status.success() => {
            return Verdict::Fail(format!(
                "Renderer {script_relpath} failed: {}",
                String::from_utf8_lossy(&out.stderr).trim()
            ))
        }
        Ok(_) => {}
    }

    let drifted = diff_tree(&committed, &out_path);
    let _ = fs::remove_dir_all(&scratch);

    if drifted.is_empty() {
        Verdict::Pass(format!("{target} matches the SSOT projection"))
    } else {
        Verdict::Fail(format!(
            "{target} drifted from mios.toml -- re-run {script_relpath}: {}",
            drifted.join(", ")
        ))
    }
}

fn copy_dir(src: &Path, dst: &Path) -> std::io::Result<()> {
    fs::create_dir_all(dst)?;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let to = dst.join(entry.file_name());
        if entry.file_type()?.is_dir() {
            copy_dir(&entry.path(), &to)?;
        } else {
            fs::copy(entry.path(), to)?;
        }
    }
    Ok(())
}

/// Names that differ in content. Line endings are normalised: a Windows checkout
/// and the Linux build must not read as drift.
fn diff_tree(committed: &Path, rendered: &Path) -> Vec<String> {
    fn norm(p: &Path) -> Option<String> {
        fs::read_to_string(p)
            .ok()
            .map(|s| s.replace("\r\n", "\n").trim_end().to_string())
    }
    let mut out = Vec::new();
    if committed.is_file() {
        if norm(committed) != norm(rendered) {
            out.push(
                committed
                    .file_name()
                    .map(|s| s.to_string_lossy().into_owned())
                    .unwrap_or_default(),
            );
        }
        return out;
    }
    let entries = match fs::read_dir(committed) {
        Ok(e) => e,
        Err(_) => return vec!["<unreadable>".to_string()],
    };
    for entry in entries.flatten() {
        if !entry.path().is_file() {
            continue;
        }
        let name = entry.file_name();
        let there = rendered.join(&name);
        if !there.exists() || norm(&entry.path()) != norm(&there) {
            out.push(name.to_string_lossy().into_owned());
        }
    }
    out
}
