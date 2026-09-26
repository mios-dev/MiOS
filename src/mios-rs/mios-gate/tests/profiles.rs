// AI-hint: Integration tests for mios-gate's profile-integrity check against synthetic mios.toml [profiles] tables.
// AI-related: src/mios-rs/mios-gate/src/profiles.rs, src/mios-rs/mios-build/src/lib.rs, usr/share/mios/mios.toml

use std::fs;
use std::path::Path;
use std::process::Command;

const BASE: &str = r#"
[build.phases]
list = [
  { ordinal = "01", name = "a", script = "01-a.sh", fatal = true, apply_class = "universal" },
  { ordinal = "02", name = "b", script = "02-b.sh", fatal = true, apply_class = "universal" },
]
[packages.a]
pkgs = []
[packages.s]
pkgs = []
[profiles]
default = "full"
floor = "core"
[profiles.core]
phases = ["a"]
package_sections = ["s"]
[profiles.full]
extends = ["core"]
all = true
"#;

fn run(toml: &str) -> (i32, String) {
    let dir = tempfile::tempdir().unwrap();
    fs::create_dir_all(dir.path().join("usr/share/mios")).unwrap();
    fs::write(dir.path().join("usr/share/mios/mios.toml"), toml).unwrap();
    gate(dir.path())
}

fn gate(root: &Path) -> (i32, String) {
    let out = Command::new(env!("CARGO_BIN_EXE_mios-gate"))
        .args(["profile-integrity", "--root"])
        .arg(root)
        .output()
        .unwrap();
    let mut text = String::from_utf8_lossy(&out.stdout).to_string();
    text.push_str(&String::from_utf8_lossy(&out.stderr));
    (out.status.code().unwrap_or(-1), text)
}

#[test]
fn a_consistent_table_is_clean() {
    let (code, text) = run(BASE);
    assert_eq!(code, 0, "{text}");
}

#[test]
fn a_phase_typo_under_all_is_still_a_finding() {
    let (code, text) = run(&BASE.replace(
        "extends = [\"core\"]\nall = true",
        "extends = [\"core\"]\nall = true\nphases = [\"zz-planted\"]",
    ));
    assert_ne!(code, 0, "{text}");
    assert!(text.contains("zz-planted"), "{text}");
}

#[test]
fn a_section_cannot_stand_in_for_a_floor_phase_of_the_same_name() {
    // "dev" lacks the floor phase "a" but carries a package section also named "a".
    let toml = format!("{BASE}[profiles.dev]\npackage_sections = [\"s\", \"a\"]\n");
    let (code, text) = run(&toml);
    assert_ne!(code, 0, "{text}");
    assert!(
        text.contains("does not contain the floor") && text.contains("dev"),
        "{text}"
    );
}
