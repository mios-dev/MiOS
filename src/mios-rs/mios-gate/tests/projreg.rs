// AI-hint: Integration tests for mios-gate's projection-coverage check against synthetic trees -- the reverse direction of the Law 8 registry.
// AI-related: src/mios-rs/mios-gate/src/projreg.rs, usr/share/mios/mios.toml, automation/98-drift-checks.sh

use std::fs;
use std::path::Path;
use std::process::Command;

fn bin() -> &'static str {
    env!("CARGO_BIN_EXE_mios-gate")
}

/// A minimal tree: generators on disk, the checks defined in the drift script,
/// and the register. Nothing else the check reads.
fn tree(
    dir: &Path,
    on_disk: &[&str],
    defined_checks: &[&str],
    surfaces: &[(&str, &str, &str)],
    globs: &[&str],
    exempt: &[(&str, &str)],
    max_exempt: i64,
) {
    fs::create_dir_all(dir.join("tools")).unwrap();
    fs::create_dir_all(dir.join("usr/share/mios")).unwrap();
    fs::create_dir_all(dir.join("automation")).unwrap();
    for g in on_disk {
        fs::write(dir.join(g), "#!/usr/bin/env python3\n").unwrap();
    }
    let body: String = defined_checks
        .iter()
        .map(|c| format!("{c}() {{\n    true\n}}\n"))
        .collect();
    fs::write(
        dir.join("automation/98-drift-checks.sh"),
        format!("#!/usr/bin/env bash\n{body}"),
    )
    .unwrap();

    let rows: String = surfaces
        .iter()
        .map(|(gen, chk, out)| {
            format!("  {{ generator = \"{gen}\", check = \"{chk}\", output = \"{out}\" }},\n")
        })
        .collect();
    let gl: String = globs
        .iter()
        .map(|g| format!("\"{g}\", "))
        .collect::<String>();
    let ex: String = exempt
        .iter()
        .map(|(gen, why)| format!("  {{ generator = \"{gen}\", reason = \"{why}\" }},\n"))
        .collect();
    fs::write(
        dir.join("usr/share/mios/mios.toml"),
        format!(
            "[laws.projection_registry]\nsurfaces = [\n{rows}]\n\
             generator_globs = [{gl}]\nexempt = [\n{ex}]\nmax_exempt = {max_exempt}\n"
        ),
    )
    .unwrap();
}

fn run(dir: &Path) -> (i32, String) {
    let out = Command::new(bin())
        .args(["projection-coverage", "--root"])
        .arg(dir)
        .output()
        .unwrap();
    let mut text = String::from_utf8_lossy(&out.stdout).to_string();
    text.push_str(&String::from_utf8_lossy(&out.stderr));
    (out.status.code().unwrap_or(-1), text)
}

const G: &[&str] = &["tools/generate-*.py"];

#[test]
fn a_fully_registered_tree_is_clean() {
    let d = tempfile::tempdir().unwrap();
    tree(
        d.path(),
        &["tools/generate-a.py", "tools/generate-b.py"],
        &["check_a", "check_b"],
        &[
            ("tools/generate-a.py", "check_a", "usr/share/a"),
            ("tools/generate-b.py", "check_b", "usr/share/b"),
        ],
        G,
        &[],
        0,
    );
    let (code, text) = run(d.path());
    assert_eq!(code, 0, "{text}");
    assert!(text.contains("2 generator(s) in scope"), "{text}");
}

#[test]
fn an_unregistered_generator_fails() {
    let d = tempfile::tempdir().unwrap();
    tree(
        d.path(),
        &["tools/generate-a.py", "tools/generate-b.py"],
        &["check_a"],
        &[("tools/generate-a.py", "check_a", "usr/share/a")],
        G,
        &[],
        0,
    );
    let (code, text) = run(d.path());
    assert_eq!(code, 1, "{text}");
    assert!(text.contains("tools/generate-b.py"), "{text}");
}

#[test]
fn an_itemised_exemption_is_accepted_and_a_bare_one_is_not() {
    let d = tempfile::tempdir().unwrap();
    let disk = &["tools/generate-a.py", "tools/generate-b.py"];
    let surf = &[("tools/generate-a.py", "check_a", "usr/share/a")];
    tree(
        d.path(),
        disk,
        &["check_a"],
        surf,
        G,
        &[(
            "tools/generate-b.py",
            "prints to stdout, projects nothing tracked",
        )],
        1,
    );
    let (code, text) = run(d.path());
    assert_eq!(code, 0, "{text}");

    // Same exemption with no reason: a count, not a register.
    tree(
        d.path(),
        disk,
        &["check_a"],
        surf,
        G,
        &[("tools/generate-b.py", "")],
        1,
    );
    let (code, text) = run(d.path());
    assert_eq!(code, 1, "{text}");
    assert!(text.contains("carries no `reason`"), "{text}");
}

#[test]
fn a_ceiling_below_the_exemption_count_fails() {
    let d = tempfile::tempdir().unwrap();
    tree(
        d.path(),
        &[
            "tools/generate-a.py",
            "tools/generate-b.py",
            "tools/generate-c.py",
        ],
        &["check_c"],
        &[("tools/generate-c.py", "check_c", "usr/share/c")],
        G,
        &[
            ("tools/generate-a.py", "why a"),
            ("tools/generate-b.py", "why b"),
        ],
        1,
    );
    let (code, text) = run(d.path());
    assert_eq!(code, 1, "{text}");
    assert!(text.contains("ceiling of 1"), "{text}");
}

#[test]
fn a_check_name_that_is_not_defined_fails() {
    let d = tempfile::tempdir().unwrap();
    tree(
        d.path(),
        &["tools/generate-a.py"],
        &["check_something_else"],
        &[("tools/generate-a.py", "check_a", "usr/share/a")],
        G,
        &[],
        0,
    );
    let (code, text) = run(d.path());
    assert_eq!(code, 1, "{text}");
    assert!(text.contains("names check 'check_a'"), "{text}");
    assert!(text.contains("98-drift-checks.sh"), "{text}");
}

#[test]
fn a_row_with_no_output_fails() {
    let d = tempfile::tempdir().unwrap();
    tree(
        d.path(),
        &["tools/generate-a.py"],
        &["check_a"],
        &[("tools/generate-a.py", "check_a", "")],
        G,
        &[],
        0,
    );
    let (code, text) = run(d.path());
    assert_eq!(code, 1, "{text}");
    assert!(text.contains("declares no `output`"), "{text}");
}

#[test]
fn a_generator_both_registered_and_exempt_fails() {
    let d = tempfile::tempdir().unwrap();
    tree(
        d.path(),
        &["tools/generate-a.py"],
        &["check_a"],
        &[("tools/generate-a.py", "check_a", "usr/share/a")],
        G,
        &[("tools/generate-a.py", "also exempt somehow")],
        1,
    );
    let (code, text) = run(d.path());
    assert_eq!(code, 1, "{text}");
    assert!(text.contains("both registered and exempt"), "{text}");
}

/// The defect this check would otherwise reproduce: its scope is its own
/// allowlist, so narrowing the allowlist must not be able to buy a pass.
#[test]
fn deleting_a_glob_cannot_narrow_the_scope_into_a_pass() {
    let d = tempfile::tempdir().unwrap();
    let disk = &["tools/generate-a.py", "tools/render-b.py"];
    let checks = &["check_a", "check_b"];
    let surf = &[
        ("tools/generate-a.py", "check_a", "usr/share/a"),
        ("tools/render-b.py", "check_b", "usr/share/b"),
    ];
    tree(
        d.path(),
        disk,
        checks,
        surf,
        &["tools/generate-*.py", "tools/render-*.py"],
        &[],
        0,
    );
    assert_eq!(run(d.path()).0, 0);

    // Drop the render glob. render-b.py is still registered and still sits in
    // a directory the remaining glob claims, so the narrowing is visible.
    tree(
        d.path(),
        disk,
        checks,
        surf,
        &["tools/generate-*.py"],
        &[],
        0,
    );
    let (code, text) = run(d.path());
    assert_eq!(code, 1, "{text}");
    assert!(text.contains("the scope has narrowed"), "{text}");
}

#[test]
fn an_empty_scope_or_an_unbounded_register_cannot_run() {
    let d = tempfile::tempdir().unwrap();
    let disk = &["tools/generate-a.py"];
    let surf = &[("tools/generate-a.py", "check_a", "usr/share/a")];

    // No glob at all: an unscoped run would pass on the empty set.
    tree(d.path(), disk, &["check_a"], surf, &[], &[], 0);
    assert_eq!(run(d.path()).0, 2);

    // A glob that matches nothing is a broken glob, not a clean tree.
    tree(
        d.path(),
        disk,
        &["check_a"],
        surf,
        &["tools/nothing-*.py"],
        &[],
        0,
    );
    let (code, text) = run(d.path());
    assert_eq!(code, 2, "{text}");
    assert!(text.contains("matched no file"), "{text}");
}

#[test]
fn a_pattern_the_matcher_cannot_express_is_rejected_not_widened() {
    let d = tempfile::tempdir().unwrap();
    tree(
        d.path(),
        &["tools/generate-a.py"],
        &["check_a"],
        &[("tools/generate-a.py", "check_a", "usr/share/a")],
        &["tools/*-*.py"],
        &[],
        0,
    );
    let (code, text) = run(d.path());
    assert_eq!(code, 2, "{text}");
    assert!(text.contains("single-`*`"), "{text}");
}

#[test]
fn an_absent_max_exempt_cannot_run() {
    let d = tempfile::tempdir().unwrap();
    fs::create_dir_all(d.path().join("tools")).unwrap();
    fs::create_dir_all(d.path().join("usr/share/mios")).unwrap();
    fs::create_dir_all(d.path().join("automation")).unwrap();
    fs::write(d.path().join("tools/generate-a.py"), "x").unwrap();
    fs::write(
        d.path().join("automation/98-drift-checks.sh"),
        "check_a() {\n true\n}\n",
    )
    .unwrap();
    fs::write(
        d.path().join("usr/share/mios/mios.toml"),
        "[laws.projection_registry]\n\
         surfaces = [\n  { generator = \"tools/generate-a.py\", check = \"check_a\", output = \"x\" },\n]\n\
         generator_globs = [\"tools/generate-*.py\"]\n",
    )
    .unwrap();
    let (code, text) = run(d.path());
    assert_eq!(code, 2, "{text}");
    assert!(text.contains("max_exempt"), "{text}");
}
