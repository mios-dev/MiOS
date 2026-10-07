// AI-hint: Two-sided integration test suite for mios-gen ai-manifest (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/ai_manifest.rs, tools/generate-ai-manifest.py

use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn get_repo_root() -> PathBuf {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .and_then(|p| p.parent())
        .and_then(|p| p.parent())
        .expect("Failed to find repo root from CARGO_MANIFEST_DIR")
        .to_path_buf()
}

fn bin() -> &'static str {
    env!("CARGO_BIN_EXE_mios-gen")
}

#[test]
fn test_ai_manifest_render_and_check() {
    let root = get_repo_root();

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
