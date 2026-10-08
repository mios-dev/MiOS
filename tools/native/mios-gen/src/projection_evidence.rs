// AI-hint: Native projection diagnostics render tracked working bytes privately without restoring or writing caller files.
// AI-related: automation/98-drift-checks.sh, tools/native/mios-gen/tests/projection_evidence.rs
use std::collections::BTreeSet;
use std::fs;
use std::path::{Component, Path};
use std::process::{Command, Output};

const PREFIX: &str = "[98-drift-checks][diff]";

fn relative(name: &str) -> Result<&Path, String> {
    let path = Path::new(name);
    if name.is_empty()
        || path
            .components()
            .any(|c| !matches!(c, Component::Normal(_)))
    {
        return Err(format!("projection path must stay beneath root: {name}"));
    }
    Ok(path)
}

fn successful(output: Output, action: &str) -> Result<Vec<u8>, String> {
    if !output.status.success() {
        return Err(format!(
            "{action}: {}: {}",
            output.status,
            String::from_utf8_lossy(&output.stderr)
                .chars()
                .take(4096)
                .collect::<String>()
        ));
    }
    Ok(output.stdout)
}

pub fn run(root: &Path, generator: &str, targets: &[String]) -> Result<(), String> {
    if !matches!(generator, "cargo-manifests" | "gate-index" | "bib-configs") || targets.is_empty()
    {
        return Err("native projection and nonempty target list required".into());
    }
    // Keep ordinary absolute paths for Git: Windows canonicalization adds a
    // verbatim prefix that Git's no-index hashing does not consistently accept.
    let actual_root = root.canonicalize().map_err(|e| e.to_string())?;
    let root = std::path::absolute(root).map_err(|e| e.to_string())?;
    let census = successful(
        Command::new("git")
            .arg("-C")
            .arg(&root)
            .args(["ls-files", "-z"])
            .output()
            .map_err(|e| e.to_string())?,
        "tracked census",
    )?;
    let census = String::from_utf8(census).map_err(|e| e.to_string())?;
    let tracked: BTreeSet<_> = census.split('\0').filter(|s| !s.is_empty()).collect();
    if tracked.is_empty() {
        return Err("tracked census is empty; no projection evidence collected".into());
    }
    for name in targets {
        relative(name)?;
        if !tracked.contains(name.as_str()) {
            return Err(format!("projection target is not tracked: {name}"));
        }
    }
    let snapshot = tempfile::tempdir().map_err(|e| e.to_string())?;
    for name in &tracked {
        let path = relative(name)?;
        let source = root.join(path);
        let resolved = source.canonicalize().map_err(|e| format!("{name}: {e}"))?;
        if !resolved.starts_with(&actual_root) || !resolved.is_file() {
            return Err(format!(
                "tracked input escapes root or is not a file: {name}"
            ));
        }
        let destination = snapshot.path().join(path);
        fs::create_dir_all(destination.parent().ok_or("missing snapshot parent")?)
            .map_err(|e| e.to_string())?;
        fs::copy(&resolved, destination).map_err(|e| format!("copy {name}: {e}"))?;
    }
    let mut command = Command::new(std::env::current_exe().map_err(|e| e.to_string())?);
    command
        .arg(generator)
        .arg("--root")
        .arg(snapshot.path())
        .current_dir(snapshot.path());
    for (key, _) in std::env::vars_os() {
        if key.to_string_lossy().starts_with("MIOS_") {
            command.env_remove(key);
        }
    }
    command
        .env("MIOS_DRIFT_ROOT", snapshot.path())
        .env("MIOS_ROOT", snapshot.path());
    successful(
        command.output().map_err(|e| e.to_string())?,
        "native rendering",
    )?;
    eprintln!("{PREFIX} generator: mios-gen {generator} --root <private tracked-byte snapshot>");
    for name in targets {
        let expected = snapshot.path().join(relative(name)?);
        if !expected.is_file() {
            return Err(format!("native rendering produced no target: {name}"));
        }
        let diff = Command::new("git")
            .current_dir(snapshot.path())
            .args([
                "--no-pager",
                "diff",
                "--no-index",
                "--no-ext-diff",
                "--no-textconv",
                "--",
            ])
            .arg(root.join(name))
            .arg(expected)
            .output()
            .map_err(|e| e.to_string())?;
        if !matches!(diff.status.code(), Some(0 | 1)) {
            return Err(format!(
                "diff {name}: {}: {}",
                diff.status,
                String::from_utf8_lossy(&diff.stderr)
            ));
        }
        eprintln!("{PREFIX} target {name}: ACTUAL on-disk -> GENERATED from SSOT");
        let text = String::from_utf8_lossy(&diff.stdout);
        for line in text.lines().take(200) {
            eprintln!("{PREFIX} {line}");
        }
        if text.lines().count() > 200 {
            eprintln!("{PREFIX} remaining diff lines omitted");
        }
    }
    Ok(())
}
