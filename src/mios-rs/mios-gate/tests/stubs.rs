// AI-hint: Integration tests for mios-gate's drift-stubs check -- a Check that never reads the tree must not claim a verdict.
// AI-related: src/mios-rs/mios-gate/src/stubs.rs, src/mios-rs/miosd/src/drift/, usr/share/mios/mios.toml

use std::fs;
use std::path::Path;
use std::process::Command;

fn bin() -> &'static str {
    env!("CARGO_BIN_EXE_mios-gate")
}

/// `impls` is (struct, id, body-of-run).
fn tree(dir: &Path, impls: &[(&str, &str, &str)], listed: &[&str], ceiling: i64) {
    fs::create_dir_all(dir.join("src/mios-rs/miosd/src/drift")).unwrap();
    fs::create_dir_all(dir.join("usr/share/mios")).unwrap();
    let mut src = String::new();
    for (s, id, body) in impls {
        src.push_str(&format!(
            "impl Check for {s} {{\n    fn id(&self) -> &str {{\n        \"{id}\"\n    }}\n    {body}\n}}\n\n"
        ));
    }
    fs::write(dir.join("src/mios-rs/miosd/src/drift/probe.rs"), src).unwrap();
    let rows: String = listed.iter().map(|r| format!("  \"{r}\",\n")).collect();
    fs::write(
        dir.join("usr/share/mios/mios.toml"),
        format!("[drift.unimplemented]\nmax_unimplemented = {ceiling}\nchecks = [\n{rows}]\n"),
    )
    .unwrap();
}

fn run(dir: &Path) -> (i32, String) {
    let out = Command::new(bin())
        .args(["drift-stubs", "--root"])
        .arg(dir)
        .output()
        .unwrap();
    let mut t = String::from_utf8_lossy(&out.stdout).to_string();
    t.push_str(&String::from_utf8_lossy(&out.stderr));
    (out.status.code().unwrap_or(-1), t)
}

const STUB: &str =
    "fn run(&self, _ctx: &DriftCtx) -> Verdict {\n        Verdict::Skip(\"NOT IMPLEMENTED: probe\".to_string())\n    }";
const LIAR: &str =
    "fn run(&self, _ctx: &DriftCtx) -> Verdict {\n        Verdict::Pass(\"probe verified\".to_string())\n    }";
const REAL: &str =
    "fn run(&self, ctx: &DriftCtx) -> Verdict {\n        let _ = ctx.root.is_dir();\n        Verdict::Pass(\"probe verified\".to_string())\n    }";

#[test]
fn a_registered_stub_and_a_real_check_are_clean() {
    let d = tempfile::tempdir().unwrap();
    tree(
        d.path(),
        &[("A", "check_a", STUB), ("B", "check_b", REAL)],
        &["check_a"],
        1,
    );
    let (code, out) = run(d.path());
    assert_eq!(code, 0, "{out}");
}

/// The defect: 54 impls took `_ctx`, never read the tree, and returned a
/// constant Pass whose message claimed verification.
#[test]
fn a_check_that_cannot_look_must_not_claim() {
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), &[("A", "check_a", LIAR)], &[], 0);
    let (code, out) = run(d.path());
    assert_eq!(code, 1, "{out}");
    assert!(out.contains("must not claim"), "{out}");
}

#[test]
fn an_unregistered_stub_fails() {
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), &[("A", "check_a", STUB)], &[], 0);
    let (code, out) = run(d.path());
    assert_eq!(code, 1, "{out}");
    assert!(out.contains("not on [drift.unimplemented]"), "{out}");
}

#[test]
fn a_raised_ceiling_does_not_absorb_an_unregistered_stub() {
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), &[("A", "check_a", STUB)], &[], 999);
    let (code, out) = run(d.path());
    assert_eq!(code, 1, "{out}");
    assert!(out.contains("not on [drift.unimplemented]"), "{out}");
}

#[test]
fn a_ceiling_above_the_measurement_is_itself_a_finding() {
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), &[("A", "check_a", REAL)], &[], 3);
    let (code, out) = run(d.path());
    assert_eq!(code, 1, "{out}");
    assert!(out.contains("lower the ceiling"), "{out}");
}

#[test]
fn a_stale_register_entry_fails() {
    let d = tempfile::tempdir().unwrap();
    tree(
        d.path(),
        &[("A", "check_a", STUB)],
        &["check_a", "check_gone"],
        2,
    );
    let (code, out) = run(d.path());
    assert_eq!(code, 1, "{out}");
    assert!(out.contains("check_gone"), "{out}");
}

/// Empty-Set Pass guards: nothing to scan, and no register, must each be
/// could-not-run rather than clean.
#[test]
fn an_empty_scan_or_absent_register_cannot_run() {
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), &[], &[], 0);
    let (code, out) = run(d.path());
    assert_eq!(code, 2, "{out}");
    assert!(out.contains("nothing was compared"), "{out}");

    let d2 = tempfile::tempdir().unwrap();
    tree(d2.path(), &[("A", "check_a", STUB)], &["check_a"], 1);
    fs::write(
        d2.path().join("usr/share/mios/mios.toml"),
        "[other]\nk = 1\n",
    )
    .unwrap();
    let (code2, out2) = run(d2.path());
    assert_eq!(code2, 2, "{out2}");
}

#[test]
fn a_missing_root_cannot_run() {
    let d = tempfile::tempdir().unwrap();
    let (code, _) = run(d.path());
    assert_eq!(code, 2);
}
