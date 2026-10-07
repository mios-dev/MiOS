// AI-hint: Two-sided integration test suite for mios-gen render-btop-theme (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/btop_theme.rs, automation/98-drift-checks.sh

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

struct TempCleaner {
    target: PathBuf,
}

impl Drop for TempCleaner {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.target);
    }
}

#[test]
fn test_render_btop_theme_cli_e2e() {
    let root = get_repo_root();
    let bin_path = bin();

    // 1. Positive control: standard check mode passes with exit code 0
    let output = Command::new(bin_path)
        .arg("render-btop-theme")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen render-btop-theme --check");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "Expected exit code 0, got: {:?}\nstdout: {}\nstderr: {}",
        output.status.code(),
        stdout,
        stderr
    );
    assert!(
        stdout.contains("[btop-theme] btop theme matches SSOT"),
        "stdout should confirm match: {}",
        stdout
    );

    // 2. Positive control: JSON output contains valid schema
    let json_output = Command::new(bin_path)
        .arg("--format")
        .arg("json")
        .arg("render-btop-theme")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen --format json render-btop-theme --check");

    assert!(
        json_output.status.success(),
        "Expected exit code 0 in JSON mode"
    );
    let json_str = String::from_utf8_lossy(&json_output.stdout);
    assert!(
        json_str.contains("\"violations\": 0"),
        "JSON output should indicate 0 violations: {}",
        json_str
    );

    // 3. Positive control: render to custom output path
    let tmp_out = root.join("tests/golden/btop-test-output.theme");
    let _cleaner = TempCleaner {
        target: tmp_out.clone(),
    };

    let render_output = Command::new(bin_path)
        .arg("render-btop-theme")
        .arg("--root")
        .arg(&root)
        .arg("--out")
        .arg(&tmp_out)
        .output()
        .expect("Failed to execute mios-gen render-btop-theme --out");

    assert!(
        render_output.status.success(),
        "Render to file should succeed"
    );
    assert!(tmp_out.is_file(), "Rendered target file must exist");
    let content = fs::read_to_string(&tmp_out).unwrap();
    assert!(
        content.contains("theme[main_bg]="),
        "Content must contain main_bg"
    );
    assert!(
        content.contains("theme[cpu_box]="),
        "Content must contain cpu_box"
    );

    // 4. Negative control: invalid theme syntax triggers exit code 1
    let corrupted_target = root.join("tests/golden/btop-corrupted.theme");
    fs::write(&corrupted_target, "theme[main_bg]=\"INVALID_HEX\"\n").unwrap();
    let _cleaner2 = TempCleaner {
        target: corrupted_target.clone(),
    };

    let fail_output = Command::new(bin_path)
        .arg("render-btop-theme")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .arg("--out")
        .arg(&corrupted_target)
        .output()
        .expect("Failed to execute check on corrupted theme");

    assert_eq!(
        fail_output.status.code(),
        Some(1),
        "Expected exit code 1 on corrupted target file"
    );
}
