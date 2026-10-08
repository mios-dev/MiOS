// AI-hint: Real CLI checks prove host rendering merges vendor, host and user policy and rejects malformed effective values.
use std::{fs, path::PathBuf, process::Command};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().parent().unwrap().into()
}
fn run(host: &str, user: &str) -> std::process::Output {
    let tmp = tempfile::tempdir().unwrap();
    let host_path = tmp.path().join("host.toml");
    let user_path = tmp.path().join("user.toml");
    fs::write(&host_path, host).unwrap();
    fs::write(&user_path, user).unwrap();
    Command::new(env!("CARGO_BIN_EXE_mios-gen"))
        .args(["render-host-tmux", "--root"]).arg(root())
        .env("MIOS_VENDOR_TOML", root().join("usr/share/mios/mios.toml"))
        .env("MIOS_HOST_TOML", host_path).env("MIOS_USER_TOML", user_path)
        .env("MIOS_VENDOR_TOML_D", tmp.path().join("missing-vendor.d"))
        .env("MIOS_HOST_TOML_D", tmp.path().join("missing-host.d"))
        .env("MIOS_USER_TOML_D", tmp.path().join("missing-user.d"))
        .output().unwrap()
}
#[test]
fn host_cli_renders_layered_overrides_without_shell_or_python() {
    let output = run("[theme.tmux]\nstatus_position='top'\n[colors]\nfg='#112233'\n", "[colors]\nfg='#FEDCBA'\n[terminal]\nscrollback_rows=4567\n");
    assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
    let text = String::from_utf8(output.stdout).unwrap();
    for expected in ["#FEDCBA", "set -g status-position top", "set -g history-limit 4567", "bind-key h select-pane -L"] { assert!(text.contains(expected), "{expected}"); }
    assert!(!text.contains("#112233"));
    assert!(text.lines().count() > 55);
}
#[test]
fn host_cli_rejects_invalid_effective_color_without_output() {
    let output = run("", "[colors]\nfg='invalid-host-color'\n");
    assert!(!output.status.success());
    assert!(output.stdout.is_empty());
    assert!(String::from_utf8_lossy(&output.stderr).contains("[colors].fg"));
}
