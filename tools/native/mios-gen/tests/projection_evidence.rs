// AI-hint: Native isolated projection evidence rejects bad roots and escaping inputs while preserving dirty caller bytes.
// AI-related: tools/native/mios-gen/src/main.rs
use std::fs;
use std::path::Path;
use std::process::{Command, Output};

fn write(root: &Path, name: &str, body: &str) {
    let path = root.join(name);
    fs::create_dir_all(path.parent().unwrap()).unwrap();
    fs::write(path, body).unwrap();
}

fn git(root: &Path, args: &[&str]) {
    assert!(Command::new("git")
        .arg("-C")
        .arg(root)
        .args(args)
        .output()
        .unwrap()
        .status
        .success());
}

fn evidence(root: &Path, target: &str) -> Output {
    Command::new(env!("CARGO_BIN_EXE_mios-gen"))
        .args(["projection-evidence", "--root"])
        .arg(root)
        .args(["--generator", "cargo-manifests", "--target", target])
        .output()
        .unwrap()
}

#[test]
fn dirty_projection_is_diffed_without_writing_or_staging_caller() {
    let temp = tempfile::tempdir().unwrap();
    let root = temp.path();
    git(root, &["init", "-q"]);
    write(
        root,
        "tools/native/example/Cargo.toml",
        "[package]\nname='example'\n",
    );
    write(root, "tools/native/Cargo.toml", "planted manifest drift\n");
    write(root, "VERSION", "0.3.0\n");
    git(root, &["add", "."]);
    write(
        root,
        "tools/native/Cargo.toml",
        "dirty concurrent contribution\n",
    );
    let indexed = Command::new("git")
        .arg("-C")
        .arg(root)
        .args(["show", ":tools/native/Cargo.toml"])
        .output()
        .unwrap()
        .stdout;
    let output = evidence(root, "tools/native/Cargo.toml");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let diff = String::from_utf8_lossy(&output.stderr);
    assert!(diff.contains("-dirty concurrent contribution"));
    assert!(diff.contains("+[workspace]"));
    assert_eq!(
        fs::read_to_string(root.join("tools/native/Cargo.toml")).unwrap(),
        "dirty concurrent contribution\n"
    );
    assert_eq!(
        Command::new("git")
            .arg("-C")
            .arg(root)
            .args(["show", ":tools/native/Cargo.toml"])
            .output()
            .unwrap()
            .stdout,
        indexed
    );
}

#[test]
fn missing_git_empty_census_and_untracked_target_fail() {
    let temp = tempfile::tempdir().unwrap();
    assert!(!evidence(temp.path(), "output").status.success());
    git(temp.path(), &["init", "-q"]);
    let empty = evidence(temp.path(), "output");
    assert!(!empty.status.success());
    assert!(String::from_utf8_lossy(&empty.stderr).contains("census is empty"));
    write(temp.path(), "VERSION", "0.3.0\n");
    git(temp.path(), &["add", "."]);
    let untracked = evidence(temp.path(), "../outside");
    assert!(!untracked.status.success());
    assert!(String::from_utf8_lossy(&untracked.stderr).contains("beneath root"));
    let untracked = evidence(temp.path(), "output");
    assert!(!untracked.status.success());
    assert!(String::from_utf8_lossy(&untracked.stderr).contains("not tracked"));
}

#[cfg(unix)]
#[test]
fn tracked_symlink_cannot_copy_external_inputs() {
    let temp = tempfile::tempdir().unwrap();
    let external = tempfile::tempdir().unwrap();
    write(external.path(), "secret", "outside input");
    git(temp.path(), &["init", "-q"]);
    std::os::unix::fs::symlink(external.path().join("secret"), temp.path().join("linked")).unwrap();
    git(temp.path(), &["add", "."]);
    let output = evidence(temp.path(), "linked");
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("escapes root"));
    assert_eq!(
        fs::read_to_string(external.path().join("secret")).unwrap(),
        "outside input"
    );
}
