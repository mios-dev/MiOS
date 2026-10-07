// AI-hint: Integration tests for mios-gen cosign-policy verb -- verifies byte-identical rendering, --check verification, and negative controls.
// AI-related: tools/native/mios-gen/src/main.rs, usr/share/mios/mios.toml, docs/design/doc-rust-static-port.md

use std::fs;
use std::process::Command;

fn bin() -> &'static str {
    env!("CARGO_BIN_EXE_mios-gen")
}

#[test]
fn test_cosign_policy_render_and_check() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let toml_dir = root.join("usr/share/mios");
    fs::create_dir_all(&toml_dir).unwrap();
    fs::write(
        toml_dir.join("mios.toml"),
        "[security.sigstore]\npolicy_mode = \"insecureAcceptEverything\"\n",
    )
    .unwrap();

    // 1. Generation mode
    let out = Command::new(bin())
        .arg("cosign-policy")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(0));

    let policy_path = root.join("usr/lib/containers/policy.json");
    assert!(policy_path.is_file());
    let content = fs::read_to_string(&policy_path).unwrap();
    let expected =
        "{\n  \"default\": [\n    {\n      \"type\": \"insecureAcceptEverything\"\n    }\n  ]\n}\n";
    assert_eq!(content, expected);

    // 2. Check mode - clean
    let out = Command::new(bin())
        .arg("cosign-policy")
        .arg("--root")
        .arg(root)
        .arg("--check")
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.contains("[OK] usr/lib/containers/policy.json is in sync with SSOT"));

    // 3. Check mode - tampered
    fs::write(&policy_path, "{}").unwrap();
    let out = Command::new(bin())
        .arg("cosign-policy")
        .arg("--root")
        .arg(root)
        .arg("--check")
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("out of sync"));
}

#[test]
fn test_missing_sigstore_table_fails() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let toml_dir = root.join("usr/share/mios");
    fs::create_dir_all(&toml_dir).unwrap();
    fs::write(toml_dir.join("mios.toml"), "[meta]\nname = \"test\"\n").unwrap();

    let out = Command::new(bin())
        .arg("cosign-policy")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("no [security.sigstore] table"));
}
