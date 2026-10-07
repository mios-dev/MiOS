// AI-hint: Two-sided integration test suite for mios-gen render-fastfetch (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/fastfetch.rs, automation/98-drift-checks.sh

use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

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

fn run(root: &Path, args: &[&str]) -> Output {
    Command::new(bin())
        .arg("render-fastfetch")
        .arg("--root")
        .arg(root)
        .args(args)
        .output()
        .expect("Failed to execute mios-gen render-fastfetch")
}

fn text(o: &Output) -> String {
    format!(
        "{}{}",
        String::from_utf8_lossy(&o.stdout),
        String::from_utf8_lossy(&o.stderr)
    )
}

#[test]
fn test_render_fastfetch_cli_e2e() {
    let root = get_repo_root();
    let td = tempfile::tempdir().unwrap();
    let out_path = td.path().join("fastfetch.jsonc");
    let out_s = out_path.to_string_lossy().to_string();

    // 1. Positive control: mock execution generates a valid configuration, writes nothing.
    let o = run(&root, &["--mock"]);
    assert!(o.status.success(), "{}", text(&o));
    assert!(text(&o).contains("[fastfetch] SUCCESS: Generated Fastfetch config"));

    // 2. Positive control: logo-type flag and JSON output mode.
    assert!(run(&root, &["--mock", "--logo-type", "auto"])
        .status
        .success());
    let j = Command::new(bin())
        .args(["--format", "json", "render-fastfetch", "--mock", "--root"])
        .arg(&root)
        .output()
        .unwrap();
    assert!(j.status.success());
    assert!(String::from_utf8_lossy(&j.stdout).contains("\"violations\": 0"));

    // 3. Legacy byte parity: json.dumps(indent=2) => ASCII-escaped, no trailing newline.
    let o = run(&root, &["--mock", "--out", &out_s]);
    assert!(o.status.success(), "{}", text(&o));
    let bytes = fs::read(&out_path).unwrap();
    assert!(
        bytes.is_ascii(),
        "non-ASCII must be \\u-escaped like Python ensure_ascii"
    );
    assert!(
        !bytes.ends_with(b"\n"),
        "legacy output has no trailing newline"
    );
    let body = String::from_utf8(bytes).unwrap();
    assert!(
        body.contains("\"separator\": \" \\udb80\\udd3e \""),
        "surrogate-pair escape"
    );
    assert_eq!(body.lines().count(), 106);
    assert_eq!(body.len(), 1766, "legacy mock render is 1766 bytes");

    // 4. Check mode passes on a matching artifact (mock render compares too).
    let o = run(&root, &["--check", "--mock", "--out", &out_s]);
    assert!(o.status.success(), "{}", text(&o));

    // 5. --dry-run never writes.
    let dry = td.path().join("dry.jsonc");
    let o = run(
        &root,
        &["--mock", "--dry-run", "--out", &dry.to_string_lossy()],
    );
    assert!(o.status.success());
    assert!(!dry.exists(), "dry-run must not write");

    // 6. Negative: a corrupted artifact fails in check mode (also with --mock).
    fs::write(&out_path, "{\"corrupted\": true}\n").unwrap();
    for extra in [
        &["--check", "--out", out_s.as_str()][..],
        &["--check", "--mock", "--out", out_s.as_str()][..],
    ] {
        let o = run(&root, extra);
        assert_eq!(o.status.code(), Some(1), "{}", text(&o));
        assert!(text(&o).contains("drifted"));
    }
}

#[test]
fn check_without_subject_or_with_missing_artifact_fails() {
    let root = get_repo_root();
    let td = tempfile::tempdir().unwrap();

    // The old default `--check` compared nothing and exited 0.
    for extra in [&["--check"][..], &["--check", "--mock"][..]] {
        let o = run(&root, extra);
        assert_eq!(o.status.code(), Some(1), "{}", text(&o));
        assert!(text(&o).contains("requires --out"), "{}", text(&o));
    }

    // A missing artifact is not a pass.
    let missing = td.path().join("absent.jsonc");
    let o = run(
        &root,
        &["--check", "--mock", "--out", &missing.to_string_lossy()],
    );
    assert_eq!(o.status.code(), Some(1));
    assert!(text(&o).contains("does not exist"));
}

#[test]
fn missing_ssot_input_is_an_error_even_with_mock() {
    let td = tempfile::tempdir().unwrap();
    let o = run(td.path(), &["--mock"]);
    assert_eq!(o.status.code(), Some(1), "{}", text(&o));
    assert!(text(&o).contains("Missing SSOT toml file"));
}

#[test]
fn committed_golden_fixture_matches_deterministic_render() {
    let root = get_repo_root();
    let fixture = root.join("tests/golden/fastfetch/mock.jsonc");
    assert!(fixture.is_file(), "golden fixture is committed");
    let o = run(
        &root,
        &["--check", "--mock", "--out", &fixture.to_string_lossy()],
    );
    assert!(o.status.success(), "{}", text(&o));
}
