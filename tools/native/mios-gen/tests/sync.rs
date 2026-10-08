// AI-hint: Execute native sync against independent Git fixtures; prerequisite failures must preserve files and index.
// AI-related: tools/native/mios-gen/src/sync.rs, usr/share/mios/mios.toml
use std::fs;
use std::path::Path;
use std::process::{Command, Output};

fn fixture(plan: &str) -> tempfile::TempDir {
    let root = tempfile::tempdir().unwrap();
    fs::create_dir_all(root.path().join("usr/share/mios")).unwrap();
    fs::write(root.path().join("usr/share/mios/mios.toml"), plan).unwrap();
    fs::write(root.path().join("input"), b"projected bytes\n").unwrap();
    fs::write(root.path().join("output"), b"previous bytes\n").unwrap();
    assert!(Command::new("git")
        .args(["init", "-q"])
        .arg(root.path())
        .status()
        .unwrap()
        .success());
    assert!(Command::new("git")
        .current_dir(root.path())
        .args(["add", "."])
        .status()
        .unwrap()
        .success());
    root
}

fn invoke(root: &Path, args: &[&str]) -> Output {
    let mut command = Command::new(env!("CARGO_BIN_EXE_mios-gen"));
    command.args(["sync", "--root"]).arg(root).args(args);
    // Prove the selected root governs the plan, even with unrelated loader pointers.
    command.env("MIOS_VENDOR_TOML", root.join("outside-does-not-exist.toml"));
    command.output().unwrap()
}

const COPY: &str = "[generation.sync]\nunit_projections=[]\n[[generation.sync.steps]]\nid='copy'\ncopy=['input','output']\n";

#[cfg(unix)]
#[test]
fn linked_output_parent_cannot_escape_the_selected_root() {
    let outside = tempfile::tempdir().unwrap();
    let root = fixture(&format!(
        "{COPY}[[generation.sync.steps]]\nid='escape'\ncopy=['input','linked/output']\n"
    ));
    std::os::unix::fs::symlink(outside.path(), root.path().join("linked")).unwrap();
    let result = invoke(root.path(), &[]);
    assert!(!result.status.success());
    assert!(String::from_utf8_lossy(&result.stderr).contains("escapes the root through a link"));
    assert!(!outside.path().join("output").exists());
    assert_eq!(
        fs::read(root.path().join("output")).unwrap(),
        b"previous bytes\n"
    );
}

#[test]
fn plan_is_read_only_and_copy_is_idempotent() {
    let root = fixture(COPY);
    let index = root.path().join(".git/index");
    let original_index = fs::read(&index).unwrap();
    let receipt = invoke(root.path(), &["--plan"]);
    assert!(
        receipt.status.success(),
        "{}",
        String::from_utf8_lossy(&receipt.stderr)
    );
    let plan: serde_json::Value = serde_json::from_slice(&receipt.stdout).unwrap();
    assert_eq!(plan["steps"].as_array().unwrap().len(), 1);
    assert_eq!(
        fs::read(root.path().join("output")).unwrap(),
        b"previous bytes\n"
    );
    assert_eq!(fs::read(&index).unwrap(), original_index);
    for _ in 0..2 {
        assert!(invoke(root.path(), &[]).status.success());
        assert_eq!(
            fs::read(root.path().join("output")).unwrap(),
            b"projected bytes\n"
        );
        assert_eq!(fs::read(&index).unwrap(), original_index);
    }
    fs::write(root.path().join("input"), b"changed source\n").unwrap();
    assert!(invoke(root.path(), &[]).status.success());
    assert_eq!(
        fs::read(root.path().join("output")).unwrap(),
        b"changed source\n"
    );
}

#[test]
fn late_missing_native_tool_blocks_every_write_and_index_change() {
    let root = fixture(&format!("{COPY}[[generation.sync.steps]]\nid='missing'\ncalls=[{{tool='mios-deliberately-missing-fixture'}}]\n"));
    let index = fs::read(root.path().join(".git/index")).unwrap();
    for args in [&[][..], &["--plan"][..]] {
        let result = invoke(root.path(), args);
        assert!(!result.status.success());
        assert!(
            String::from_utf8_lossy(&result.stderr).contains("mios-deliberately-missing-fixture")
        );
        assert_eq!(
            fs::read(root.path().join("output")).unwrap(),
            b"previous bytes\n"
        );
        assert_eq!(fs::read(root.path().join(".git/index")).unwrap(), index);
    }
}

#[test]
fn missing_adapter_and_escaping_paths_are_fatal_before_copy() {
    for action in [
        "calls=[{script='missing-adapter.py'}]",
        "copy=['../outside','output']",
    ] {
        let root = fixture(&format!(
            "{COPY}[[generation.sync.steps]]\nid='bad'\n{action}\n"
        ));
        let result = invoke(root.path(), &[]);
        assert!(!result.status.success());
        let error = String::from_utf8_lossy(&result.stderr);
        assert!(
            error.contains("missing-adapter.py") || error.contains("../outside"),
            "{error}"
        );
        assert_eq!(
            fs::read(root.path().join("output")).unwrap(),
            b"previous bytes\n"
        );
    }
}

#[test]
fn child_failure_stops_later_projection_with_real_status() {
    let root = fixture("[generation.sync]\nunit_projections=[]\n[[generation.sync.steps]]\nid='rejected-call'\ncalls=[{tool='mios-gen',args=['--deliberately-invalid-fixture']} ]\n[[generation.sync.steps]]\nid='after'\ncopy=['input','output']\n");
    let result = invoke(root.path(), &[]);
    assert!(!result.status.success());
    let error = String::from_utf8_lossy(&result.stderr);
    assert!(
        error.contains("rejected-call") && error.contains("exit"),
        "{error}"
    );
    assert_eq!(
        fs::read(root.path().join("output")).unwrap(),
        b"previous bytes\n"
    );
}

#[test]
fn corrupt_index_is_not_rebuilt_or_ignored() {
    let root = fixture(COPY);
    let index = root.path().join(".git/index");
    fs::write(&index, b"planted corrupt index\n").unwrap();
    let result = invoke(root.path(), &[]);
    assert!(!result.status.success());
    assert!(String::from_utf8_lossy(&result.stderr).contains("index"));
    assert_eq!(fs::read(&index).unwrap(), b"planted corrupt index\n");
    assert_eq!(
        fs::read(root.path().join("output")).unwrap(),
        b"previous bytes\n"
    );
}

#[test]
fn explicit_native_directory_never_selects_other_platform_artifacts() {
    let root = fixture(&format!(
        "{COPY}[[generation.sync.steps]]\nid='tool'\ncalls=[{{tool='mios-fixture-platform'}}]\n"
    ));
    let directory = root.path().join("native binaries");
    fs::create_dir(&directory).unwrap();
    let wrong = if cfg!(windows) {
        "mios-fixture-platform"
    } else {
        "mios-fixture-platform.exe"
    };
    fs::write(directory.join(wrong), b"opposite-platform artifact").unwrap();
    let result = Command::new(env!("CARGO_BIN_EXE_mios-gen"))
        .args(["sync", "--root"])
        .arg(root.path())
        .env("MIOS_NATIVE_BIN_DIR", &directory)
        .output()
        .unwrap();
    assert!(!result.status.success());
    let error = String::from_utf8_lossy(&result.stderr);
    assert!(
        error.contains("mios-fixture-platform") && error.contains("MIOS_NATIVE_BIN_DIR"),
        "{error}"
    );
    assert_eq!(
        fs::read(root.path().join("output")).unwrap(),
        b"previous bytes\n"
    );
}
