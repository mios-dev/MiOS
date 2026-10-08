// AI-hint: Two-sided integration test suite for mios-gen ai-manifest (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/ai_manifest.rs

use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn fixture_root() -> tempfile::TempDir {
    let dir = tempfile::tempdir().unwrap();
    fs::create_dir(dir.path().join("tools")).unwrap();
    fs::write(dir.path().join("README.md"), "# Fixture\n").unwrap();
    fs::write(dir.path().join("tools/run.sh"), "#!/bin/sh\nexit 0\n").unwrap();
    git(dir.path(), &["init", "-q"]);
    git(dir.path(), &["add", "--", "README.md", "tools/run.sh"]);
    let output = Command::new(bin())
        .args(["ai-manifest", "--root"])
        .arg(dir.path())
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    git(
        dir.path(),
        &["add", "--", "tools/manifest.json", "root-manifest.json"],
    );
    fs::write(dir.path().join("private.rs"), "operator data\n").unwrap();
    dir
}

fn git(root: &std::path::Path, args: &[&str]) {
    let mut command = Command::new("git");
    for (key, _) in std::env::vars().filter(|(key, _)| key.starts_with("GIT_")) {
        command.env_remove(key);
    }
    assert!(command
        .arg("-C")
        .arg(root)
        .args(args)
        .status()
        .unwrap()
        .success());
}

fn bin() -> &'static str {
    env!("CARGO_BIN_EXE_mios-gen")
}

#[test]
fn test_ai_manifest_render_and_check() {
    let fixture = fixture_root();
    let root = fixture.path().to_path_buf();

    // 1. Positive check on the clean repository
    let output = Command::new(bin())
        .args(["ai-manifest", "--root", &root.to_string_lossy(), "--check"])
        .output()
        .expect("Failed to execute mios-gen ai-manifest");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    println!("stdout:\n{stdout}");
    println!("stderr:\n{stderr}");

    assert!(
        output.status.success(),
        "Expected clean exit 0 for ai-manifest check, got: {:?}\nstderr: {}",
        output.status.code(),
        stderr
    );
    assert!(
        stdout.contains("[OK] AI repository and tool manifests are in sync"),
        "Expected sync confirmation message, got: {stdout}"
    );
    assert!(!fs::read_to_string(root.join("root-manifest.json"))
        .unwrap()
        .contains("private.rs"));

    // 2. Structured JSON format check
    let output_json = Command::new(bin())
        .args([
            "--format",
            "json",
            "ai-manifest",
            "--root",
            &root.to_string_lossy(),
            "--check",
        ])
        .output()
        .expect("Failed to execute mios-gen ai-manifest with --format json");

    let stdout_json = String::from_utf8_lossy(&output_json.stdout);
    let stderr_json = String::from_utf8_lossy(&output_json.stderr);
    assert!(
        output_json.status.success(),
        "Expected clean exit 0, got {:?}\nstderr: {}",
        output_json.status.code(),
        stderr_json
    );

    let parsed: serde_json::Value =
        serde_json::from_str(&stdout_json).expect("Failed to parse stdout as JSON");
    assert_eq!(parsed.get("status").and_then(|s| s.as_str()), Some("clean"));
    assert_eq!(
        parsed.get("subcommand").and_then(|s| s.as_str()),
        Some("ai-manifest")
    );
    assert_eq!(parsed.get("violations").and_then(|v| v.as_i64()), Some(0));

    // 3. Negative check: intentional mutation in repo tools/manifest.json, restored cleanly via RAII guard
    let target = root.join("tools/manifest.json");
    if target.exists() {
        let original = fs::read_to_string(&target).expect("Failed to read tools/manifest.json");

        struct Restorer(PathBuf, String);
        impl Drop for Restorer {
            fn drop(&mut self) {
                let _ = fs::write(&self.0, &self.1);
            }
        }

        let _guard = Restorer(target.clone(), original);

        // Plant manifest drift
        fs::write(&target, "{\"drift\":\"injected\"}")
            .expect("Failed to write drift into manifest.json");

        let output_neg = Command::new(bin())
            .args(["ai-manifest", "--root", &root.to_string_lossy(), "--check"])
            .output()
            .expect("Failed to execute mios-gen ai-manifest");

        let stderr_neg = String::from_utf8_lossy(&output_neg.stderr);
        assert!(
            !output_neg.status.success(),
            "Expected non-zero exit code when manifest drift is present"
        );
        assert_eq!(output_neg.status.code(), Some(1));
        assert!(
            stderr_neg.contains("Manifest drift detected: tools/manifest.json"),
            "Expected stderr to report drift on tools/manifest.json, got: {stderr_neg}"
        );
    }
}

#[test]
fn unreadable_index_fails_without_overwriting_manifests() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(dir.path().join(".git"), "gitdir: missing-repository\n").unwrap();
    fs::write(
        dir.path().join("root-manifest.json"),
        "preserve existing artifact\n",
    )
    .unwrap();
    let output = Command::new(bin())
        .args(["ai-manifest", "--root"])
        .arg(dir.path())
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&output.stderr).contains("cannot read tracked source index"));
    assert_eq!(
        fs::read_to_string(dir.path().join("root-manifest.json")).unwrap(),
        "preserve existing artifact\n"
    );
}
