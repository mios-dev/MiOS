// AI-hint: Two-sided integration tests for `mios-gen render-tmux-theme --runtime DIR` (Phase 3.18 regression fix: layered runtime projection that the deleted tmux_theme.py provided).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/tmux_theme.rs, usr/libexec/mios/ux/theme_sync.py, etc/profile.d/mios-prompt.sh, usr/libexec/mios/mios-terminal

use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|p| p.parent())
        .and_then(|p| p.parent())
        .expect("repo root")
        .to_path_buf()
}

fn exe(name: &str) -> String {
    if cfg!(windows) {
        format!("{name}.exe")
    } else {
        name.to_string()
    }
}

/// mios-unit-gen is a sibling workspace member the projector shells to; build it once
/// if the workspace has not produced it yet so the positive control is never skipped.
fn unit_gen() -> PathBuf {
    // Cargo places integration-test executables under <profile>/deps, next to
    // the binaries it built. This follows --target-dir/CARGO_TARGET_DIR and
    // cross-target profiles without guessing a checkout-local target tree.
    let profile = std::env::current_exe()
        .expect("integration test executable")
        .parent()
        .and_then(Path::parent)
        .expect("Cargo profile directory")
        .to_path_buf();
    let sibling = profile.join(exe("mios-unit-gen"));
    if sibling.is_file() {
        return sibling;
    }
    let native = repo_root().join("tools/native");
    let found = |p: &PathBuf| p.is_file();
    for profile in ["debug", "release"] {
        let p = native
            .join("target")
            .join(profile)
            .join(exe("mios-unit-gen"));
        if found(&p) {
            return p;
        }
    }
    let status = Command::new(std::env::var("CARGO").unwrap_or_else(|_| "cargo".into()))
        .args(["build", "-p", "mios-unit-gen", "--manifest-path"])
        .arg(native.join("Cargo.toml"))
        .status()
        .expect("spawn cargo build -p mios-unit-gen");
    assert!(status.success(), "building mios-unit-gen failed");
    let p = sibling;
    assert!(p.is_file(), "mios-unit-gen missing after build");
    p
}

fn python() -> &'static str {
    if cfg!(windows) {
        "python"
    } else {
        "python3"
    }
}

fn run(dir: &Path, user_toml: Option<&str>, extra: &[&str]) -> (Output, PathBuf) {
    let tmp = dir.to_path_buf();
    let user = tmp.join("user.toml");
    match user_toml {
        Some(s) => fs::write(&user, s).unwrap(),
        None => {
            let _ = fs::remove_file(&user);
        }
    }
    let out_dir = tmp.join("runtime");
    let root = repo_root();
    let output = Command::new(env!("CARGO_BIN_EXE_mios-gen"))
        .arg("render-tmux-theme")
        .arg("--root")
        .arg(&root)
        .args(extra)
        .env("MIOS_TOML_ROOT", &root)
        .env("MIOS_HOST_TOML", tmp.join("absent-host.toml"))
        .env("MIOS_USER_TOML", &user)
        .env("MIOS_RESOLVER_NATIVE", "0")
        .env("MIOS_UNIT_GEN", unit_gen())
        .env(
            "MIOS_THEME_SYNC",
            root.join("usr/libexec/mios/ux/theme_sync.py"),
        )
        .env_remove("SSH_CONNECTION")
        .env_remove("SSH_CLIENT")
        .env_remove("SSH_TTY")
        .env_remove("MIOS_REMOTE_TERMINAL")
        .output()
        .expect("run mios-gen");
    (output, out_dir)
}

fn have_python() -> bool {
    Command::new(python())
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

#[test]
fn runtime_projects_layered_tmux_conf_and_prompt() {
    assert!(have_python(), "python is required for the prompt renderer");
    let td = tempfile::tempdir().unwrap();

    // Baseline: vendor tier only.
    let dir_s = td.path().join("runtime").to_string_lossy().to_string();
    let args = vec!["--runtime", dir_s.as_str()];
    let (o, d) = run(td.path(), None, &args);
    assert!(
        o.status.success(),
        "baseline failed: {}",
        String::from_utf8_lossy(&o.stderr)
    );
    let conf = fs::read_to_string(d.join("tmux.conf")).unwrap();
    assert!(
        conf.contains("set -g status-position bottom"),
        "vendor default"
    );
    assert!(
        conf.contains("unbind-key -a -T prefix"),
        "keybindings appended"
    );
    let omp: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(d.join("mios.omp.json")).unwrap()).unwrap();
    assert!(omp.get("blocks").is_some(), "omp has blocks");
    assert!(
        o.stdout.is_empty(),
        "runtime mode must be silent on success (login shells)"
    );

    // Layer proof: the USER tier must win over the vendor tier.
    let (o2, d2) = run(
        td.path(),
        Some("[theme.tmux]\nstatus_position = \"top\"\n"),
        &args,
    );
    assert!(
        o2.status.success(),
        "{}",
        String::from_utf8_lossy(&o2.stderr)
    );
    let conf2 = fs::read_to_string(d2.join("tmux.conf")).unwrap();
    assert!(
        conf2.contains("set -g status-position top"),
        "user layer wins"
    );
    assert!(!conf2.contains("set -g status-position bottom"));

    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mode = fs::metadata(&d2).unwrap().permissions().mode() & 0o777;
        assert_eq!(mode, 0o700, "projection directory must be private");
    }
}

#[test]
fn runtime_rejects_invalid_layer_and_writes_nothing() {
    let td = tempfile::tempdir().unwrap();
    let dir = td.path().join("runtime");
    let dir_s = dir.to_string_lossy().to_string();
    let (o, d) = run(
        td.path(),
        Some("[theme.tmux]\nstyle = \"bogus\"\n"),
        &["--runtime", &dir_s],
    );
    assert!(!o.status.success(), "invalid user-tier style must fail");
    assert!(String::from_utf8_lossy(&o.stderr).contains("style must be"));
    assert!(!d.join("tmux.conf").exists(), "no half-projected tmux.conf");
    assert!(
        !d.join("mios.omp.json").exists(),
        "no half-projected prompt"
    );
}

#[test]
fn runtime_conflicts_with_check_modes() {
    let td = tempfile::tempdir().unwrap();
    let dir_s = td.path().join("runtime").to_string_lossy().to_string();
    let (o, _) = run(td.path(), None, &["--runtime", &dir_s, "--check"]);
    assert_eq!(o.status.code(), Some(2), "clap usage error expected");
}

#[cfg(unix)]
#[test]
fn runtime_refuses_symlinked_directory() {
    let td = tempfile::tempdir().unwrap();
    let real = td.path().join("real");
    fs::create_dir(&real).unwrap();
    let link = td.path().join("link");
    std::os::unix::fs::symlink(&real, &link).unwrap();
    let link_s = link.to_string_lossy().to_string();
    let (o, _) = run(td.path(), None, &["--runtime", &link_s]);
    assert!(
        !o.status.success(),
        "symlinked projection dir must be refused"
    );
    assert!(!real.join("tmux.conf").exists());
}
