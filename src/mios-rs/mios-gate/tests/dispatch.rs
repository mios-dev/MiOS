// AI-hint: Integration tests for mios-gate's build-tool-dispatch check against synthetic trees.
// AI-related: src/mios-rs/mios-gate/src/dispatch.rs, usr/share/mios/mios.toml

use std::fs;
use std::path::Path;
use std::process::Command;

fn bin() -> &'static str {
    env!("CARGO_BIN_EXE_mios-gate")
}

/// A minimal tree: a Containerfile with a builder COPY, an SSOT register, and
/// whatever automation stages the caller asks for.
fn tree(dir: &Path, ceiling: i64, listed: &[&str], stages: &[(&str, &str)]) {
    fs::create_dir_all(dir.join("automation/lib")).unwrap();
    fs::create_dir_all(dir.join("usr/share/mios")).unwrap();
    fs::write(
        dir.join("Containerfile"),
        "FROM scratch AS rust-builder\nCOPY --from=rust-builder /out/* /usr/libexec/mios/\n",
    )
    .unwrap();
    let rows: String = listed
        .iter()
        .map(|r| format!("  \"{r}\",\n"))
        .collect::<Vec<_>>()
        .join("");
    fs::write(
        dir.join("usr/share/mios/mios.toml"),
        format!("[build.tool_dispatch]\nmax_unreachable = {ceiling}\nunreachable = [\n{rows}]\n"),
    )
    .unwrap();
    for (name, body) in stages {
        fs::write(dir.join("automation").join(name), body).unwrap();
    }
}

fn run(dir: &Path, json: bool) -> (i32, String) {
    let mut c = Command::new(bin());
    c.arg("build-tool-dispatch").arg("--root").arg(dir);
    if json {
        c.arg("--format").arg("json");
    }
    let out = c.output().unwrap();
    let mut s = String::from_utf8_lossy(&out.stdout).to_string();
    s.push_str(&String::from_utf8_lossy(&out.stderr));
    (out.status.code().unwrap_or(-1), s)
}

const DEAD: &str = "#!/usr/bin/env bash\nif command -v miosd >/dev/null 2>&1; then :; fi\n";

/// Mention is not subject: a comment recording why a branch was REMOVED counted
/// as the branch still being there, which is how retiring stage 85's lookup left
/// the register unable to go down.
#[test]
fn a_commented_lookup_is_not_a_dispatch_gate() {
    let commented =
        "#!/usr/bin/env bash\n# if command -v miosd >/dev/null 2>&1; then :; fi\ntrue\n";
    let indented = "#!/usr/bin/env bash\nif true; then\n    # command -v miosd\n    :\nfi\n";
    for body in [commented, indented] {
        let d = tempfile::tempdir().unwrap();
        tree(d.path(), 0, &[], &[("10-a.sh", body)]);
        let (code, out) = run(d.path(), false);
        assert_eq!(0, code, "a commented lookup must not count: {out}");
    }
    // The same text as CODE still counts, so the exclusion narrowed the match
    // rather than disabling it.
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), 0, &[], &[("10-a.sh", DEAD)]);
    let (code, out) = run(d.path(), false);
    assert_eq!(1, code, "a real gate must still be caught: {out}");
}

#[test]
fn a_registered_gate_at_the_ceiling_is_clean() {
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), 1, &["automation/10-a.sh"], &[("10-a.sh", DEAD)]);
    let (code, out) = run(d.path(), false);
    assert_eq!(0, code, "{out}");
}

#[test]
fn a_ceiling_above_the_measurement_is_slack_and_fails() {
    // A ceiling left high after a conversion lets a later regression back in
    // silently. The ratchet only bites when the ceiling equals what is there.
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), 5, &["automation/10-a.sh"], &[("10-a.sh", DEAD)]);
    let (code, out) = run(d.path(), false);
    assert_eq!(1, code, "{out}");
    assert!(out.contains("slack"), "{out}");
    assert!(out.contains("lower max_unreachable to 1"), "{out}");
}

#[test]
fn an_unregistered_gate_fails_and_names_the_file() {
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), 1, &[], &[("10-a.sh", DEAD)]);
    let (code, out) = run(d.path(), false);
    assert_eq!(1, code, "{out}");
    assert!(out.contains("automation/10-a.sh"), "{out}");
    assert!(out.contains("not on the register"), "{out}");
}

#[test]
fn exceeding_the_ceiling_fails_even_when_registered() {
    let d = tempfile::tempdir().unwrap();
    tree(
        d.path(),
        1,
        &["automation/10-a.sh", "automation/11-b.sh"],
        &[("10-a.sh", DEAD), ("11-b.sh", DEAD)],
    );
    let (code, out) = run(d.path(), false);
    assert_eq!(1, code, "{out}");
    assert!(out.contains("exceeds the ceiling"), "{out}");
}

#[test]
fn a_binary_on_a_shipped_path_dir_is_reachable_so_the_register_goes_stale() {
    // The half that proves the check RESOLVES rather than counting strings.
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), 1, &["automation/10-a.sh"], &[("10-a.sh", DEAD)]);
    fs::create_dir_all(d.path().join("usr/bin")).unwrap();
    fs::write(d.path().join("usr/bin/miosd"), "").unwrap();
    let (code, out) = run(d.path(), false);
    assert_eq!(1, code, "{out}");
    assert!(out.contains("no unreachable gate"), "{out}");
}

#[test]
fn the_install_dir_on_path_makes_the_register_stale() {
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), 1, &["automation/10-a.sh"], &[("10-a.sh", DEAD)]);
    fs::write(
        d.path().join("automation/build.sh"),
        "export PATH=/usr/libexec/mios:$PATH\n",
    )
    .unwrap();
    let (code, out) = run(d.path(), false);
    assert_eq!(1, code, "{out}");
    assert!(out.contains("is on PATH at bake time now"), "{out}");
}

#[test]
fn a_missing_subject_cannot_run_and_never_reads_as_a_pass() {
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), 1, &[], &[]);
    fs::remove_file(d.path().join("Containerfile")).unwrap();
    let (code, out) = run(d.path(), false);
    assert_eq!(2, code, "{out}");
    assert!(out.contains("cannot run"), "{out}");
}

#[test]
fn malformed_ssot_cannot_run() {
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), 1, &[], &[]);
    fs::write(d.path().join("usr/share/mios/mios.toml"), "[[[not toml").unwrap();
    let (code, out) = run(d.path(), false);
    assert_eq!(2, code, "{out}");
    assert!(out.contains("did not parse"), "{out}");
}

#[test]
fn an_empty_automation_dir_cannot_run_rather_than_reporting_clean() {
    // An empty corpus is not "no violations" -- nothing was read.
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), 0, &[], &[]);
    let (code, out) = run(d.path(), false);
    assert_eq!(2, code, "{out}");
}

#[test]
fn json_is_a_structured_object_with_the_same_verdict() {
    let d = tempfile::tempdir().unwrap();
    tree(d.path(), 1, &[], &[("10-a.sh", DEAD)]);
    let (code, out) = run(d.path(), true);
    assert_eq!(1, code, "{out}");
    let v: serde_json::Value = serde_json::from_str(out.trim()).expect("valid JSON");
    assert_eq!("build-tool-dispatch", v["check"]);
    assert_eq!("violations", v["status"]);
    assert!(!v["findings"].as_array().unwrap().is_empty());
}

#[test]
fn an_unknown_check_cannot_run() {
    let out = Command::new(bin()).arg("no-such-check").output().unwrap();
    assert_eq!(Some(2), out.status.code());
}
