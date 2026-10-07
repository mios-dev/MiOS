// AI-hint: Native SSOT catalog build, static-artifact verification and atomic FHS installation.
// AI-related: automation/55-native-build.sh, usr/share/mios/mios.toml, miosd native-build
use std::path::{Path, PathBuf};
use std::process::Command;

fn run(command: &mut Command, label: &str) -> Result<(), String> {
    let status = command.status().map_err(|e| format!("{label}: {e}"))?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("{label}: {status}"))
    }
}

fn rustc(channel: &str, args: &[&str]) -> Result<String, String> {
    let output = Command::new("rustc")
        .args(args)
        .env("RUSTUP_TOOLCHAIN", channel)
        .output()
        .map_err(|e| format!("rustc: {e}"))?;
    if !output.status.success() {
        return Err(format!(
            "rustc: {}",
            String::from_utf8_lossy(&output.stderr)
        ));
    }
    Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
}

/// Compile every Linux role from both workspaces. Output and installation roots
/// are explicit; a caller's inherited Cargo output cannot select stale artifacts.
pub fn build_linux(
    root: &Path,
    output: &Path,
    install_root: &Path,
    arch: &str,
) -> Result<usize, String> {
    if std::env::consts::OS != "linux" {
        return Err("Linux native builds require a Linux builder".into());
    }
    let root = root
        .canonicalize()
        .map_err(|e| format!("source root: {e}"))?;
    let doc = super::native_document(&root)?;
    let channel = doc
        .get("build")
        .and_then(|v| v.get("toolchain"))
        .and_then(|v| v.get("channel"))
        .and_then(toml::Value::as_str)
        .filter(|s| !s.is_empty())
        .ok_or("missing SSOT toolchain channel")?;
    let components = doc
        .get("build")
        .and_then(|v| v.get("toolchain"))
        .and_then(|v| v.get("components"))
        .and_then(toml::Value::as_array)
        .filter(|v| !v.is_empty())
        .ok_or("missing SSOT toolchain components")?;
    let components = components
        .iter()
        .map(|v| v.as_str().ok_or("invalid toolchain component"))
        .collect::<Result<Vec<_>, _>>()?;
    run(
        Command::new("rustup").args(["toolchain", "install", channel, "--profile", "minimal"]),
        "provision SSOT Rust channel",
    )?;
    run(
        Command::new("rustup")
            .args(["component", "add", "--toolchain", channel])
            .args(components),
        "provision SSOT lint and format components",
    )?;
    super::verification::toolchain_check(&root, false)?;
    let policy = super::native_linux_target(&root, arch)?;
    let host = rustc(channel, &["-vV"])?
        .lines()
        .find_map(|l| l.strip_prefix("host: "))
        .ok_or("rustc omitted its host target")?
        .to_string();
    let sysroot = rustc(channel, &["--print", "sysroot"])?;
    let linker = Path::new(&sysroot)
        .join("lib/rustlib")
        .join(&host)
        .join("bin")
        .join(&policy.linker);
    if !linker.is_file() {
        return Err(format!("SSOT linker missing: {}", linker.display()));
    }
    let target_dir = rustc(
        channel,
        &["--print", "target-libdir", "--target", &policy.target],
    )?;
    let has_std = || {
        std::fs::read_dir(&target_dir).is_ok_and(|entries| {
            entries
                .flatten()
                .any(|e| e.file_name().to_string_lossy().starts_with("libstd-"))
        })
    };
    if !has_std() {
        run(
            Command::new("rustup").args(["target", "add", "--toolchain", channel, &policy.target]),
            "provision SSOT Linux target",
        )?;
    }
    if !has_std() {
        return Err(format!(
            "SSOT target standard library missing: {}",
            policy.target
        ));
    }
    std::fs::create_dir_all(output).map_err(|e| format!("Cargo output: {e}"))?;
    let output = output.canonicalize().map_err(|e| e.to_string())?;
    let plan = super::native_target_plan(&root, "linux")?;
    if plan.is_empty() {
        return Err("native Linux catalog selects zero artifacts".into());
    }
    // Pass linker as two encoded Rust arguments: paths may contain spaces.
    let mut flags = policy.rustflags.clone();
    flags.extend(["-C".into(), format!("linker={}", linker.display())]);
    let mut installed = 0;
    for selected in plan {
        for verb in ["clippy", "build"] {
            println!(
                "[native-build] {verb} {} ({})",
                selected.binary, selected.category
            );
            let mut cmd = Command::new("cargo");
            cmd.current_dir(root.join(&selected.workspace))
                .args([
                    verb,
                    "--locked",
                    "--release",
                    "--target",
                    &policy.target,
                    "-p",
                    &selected.package,
                    "--bin",
                    &selected.binary,
                    "--target-dir",
                ])
                .arg(&output)
                .env("RUSTUP_TOOLCHAIN", channel)
                .env("CARGO_BUILD_JOBS", policy.jobs.to_string())
                .env_remove("RUSTFLAGS")
                .env("CARGO_ENCODED_RUSTFLAGS", flags.join("\u{1f}"));
            if verb == "clippy" {
                cmd.args(["--", "-D", "warnings"]);
            }
            run(&mut cmd, &format!("{verb} {}", selected.binary))?;
        }
        let artifact = output
            .join(&policy.target)
            .join("release")
            .join(&selected.binary);
        install_verified(&root, &artifact, install_root, arch, &selected)?;
        installed += 1;
    }
    Ok(installed)
}

#[cfg(unix)]
fn install_verified(
    root: &Path,
    artifact: &Path,
    install_root: &Path,
    arch: &str,
    selected: &super::NativeTarget,
) -> Result<(), String> {
    use std::os::unix::fs::{symlink, PermissionsExt};
    use std::sync::atomic::{AtomicU64, Ordering};
    static SEQUENCE: AtomicU64 = AtomicU64::new(0);
    // Fail before touching the installed executable.
    super::verification::artifact_check(root, artifact, "linux", arch)?;
    std::fs::create_dir_all(install_root).map_err(|e| e.to_string())?;
    let prefix = install_root.canonicalize().map_err(|e| e.to_string())?;
    let destination = checked_directory(&prefix, &selected.install_dir)?;
    let installed = destination.join(&selected.binary);
    let temporary = destination.join(format!(
        ".{}.{}-{}",
        selected.binary,
        std::process::id(),
        SEQUENCE.fetch_add(1, Ordering::Relaxed)
    ));
    let result = (|| {
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)
            .map_err(|e| format!("create staged artifact: {e}"))?;
        let mut input = std::fs::File::open(artifact).map_err(|e| e.to_string())?;
        std::io::copy(&mut input, &mut file).map_err(|e| e.to_string())?;
        file.set_permissions(std::fs::Permissions::from_mode(0o755))
            .map_err(|e| e.to_string())?;
        file.sync_all().map_err(|e| e.to_string())?;
        // Check the staged bytes, then atomically replace the old path itself.
        super::verification::artifact_check(root, &temporary, "linux", arch)?;
        std::fs::rename(&temporary, &installed)
            .map_err(|e| format!("install {}: {e}", installed.display()))?;
        let mut aliases = selected.compat_dirs.clone();
        if selected.expose_bin {
            aliases.push("/usr/bin".into());
        }
        for alias in aliases {
            let directory = checked_directory(&prefix, &alias)?;
            if directory == destination {
                continue;
            }
            let alias_path = directory.join(&selected.binary);
            let temporary_link = directory.join(format!(
                ".{}.link.{}-{}",
                selected.binary,
                std::process::id(),
                SEQUENCE.fetch_add(1, Ordering::Relaxed)
            ));
            symlink(
                Path::new(&selected.install_dir).join(&selected.binary),
                &temporary_link,
            )
            .map_err(|e| format!("stage compatibility link: {e}"))?;
            if let Err(error) = std::fs::rename(&temporary_link, &alias_path) {
                let _ = std::fs::remove_file(&temporary_link);
                return Err(format!("install compatibility link: {error}"));
            }
        }
        super::verification::artifact_check(root, &installed, "linux", arch)?;
        println!("[native-build] verified installed {}", installed.display());
        Ok(())
    })();
    if result.is_err() {
        let _ = std::fs::remove_file(&temporary);
    }
    result
}

#[cfg(not(unix))]
fn install_verified(
    _: &Path,
    _: &Path,
    _: &Path,
    _: &str,
    _: &super::NativeTarget,
) -> Result<(), String> {
    Err("Linux FHS installation requires a Unix builder".into())
}

fn checked_directory(prefix: &Path, fhs: &str) -> Result<PathBuf, String> {
    if !matches!(fhs, "/usr/bin" | "/usr/libexec/mios") {
        return Err(format!("unsupported native FHS directory {fhs}"));
    }
    let directory = prefix.join(fhs.trim_start_matches('/'));
    std::fs::create_dir_all(&directory).map_err(|e| e.to_string())?;
    let directory = directory.canonicalize().map_err(|e| e.to_string())?;
    if !directory.starts_with(prefix) {
        return Err("native installation escapes its root".into());
    }
    Ok(directory)
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    #[test]
    fn verified_install_is_atomic_and_rejects_bad_replacements() {
        let root = tempfile::tempdir().unwrap();
        let out = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(root.path().join("usr/share/mios")).unwrap();
        std::fs::write(
            root.path().join("usr/share/mios/mios.toml"),
            include_str!("../../../../usr/share/mios/mios.toml"),
        )
        .unwrap();
        let selected = crate::NativeTarget {
            workspace: "tools/native".into(),
            package: "fixture".into(),
            binary: "fixture".into(),
            category: "cli".into(),
            install_dir: "/usr/bin".into(),
            expose_bin: false,
            compat_dirs: vec!["/usr/libexec/mios".into()],
            platform: "linux".into(),
        };
        let artifact = root.path().join("fixture");
        let bytes = crate::native_catalog_tests::static_pie();
        std::fs::write(&artifact, &bytes).unwrap();
        install_verified(root.path(), &artifact, out.path(), "x86_64", &selected).unwrap();
        let installed = out.path().join("usr/bin/fixture");
        assert_eq!(std::fs::read(&installed).unwrap(), bytes);
        assert_eq!(
            std::fs::read_link(out.path().join("usr/libexec/mios/fixture")).unwrap(),
            Path::new("/usr/bin/fixture")
        );
        std::fs::write(&artifact, b"not an executable").unwrap();
        assert!(install_verified(root.path(), &artifact, out.path(), "x86_64", &selected).is_err());
        assert_eq!(std::fs::read(installed).unwrap(), bytes);
    }
    #[test]
    fn directory_policy_rejects_traversal_and_symlink_escape() {
        let root = tempfile::tempdir().unwrap();
        let foreign = tempfile::tempdir().unwrap();
        assert!(checked_directory(root.path(), "/usr/bin/../../etc").is_err());
        std::fs::create_dir_all(root.path().join("usr")).unwrap();
        std::os::unix::fs::symlink(foreign.path(), root.path().join("usr/bin")).unwrap();
        assert!(checked_directory(root.path(), "/usr/bin")
            .unwrap_err()
            .contains("escapes"));
    }
}
