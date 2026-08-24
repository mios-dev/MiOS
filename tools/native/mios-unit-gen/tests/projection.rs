// AI-hint: Tests systemd unit projection against the shipped units in usr/lib/systemd/system.

//! The projection contract: `[units.*]` in the SSOT must RENDER the units the
//! tree ships. What replaced `golden_master.rs`, which diffed
//! `usr/lib/systemd/system` against `tests/golden/` -- a byte copy of that same
//! tree. It could only fail when someone forgot to update the copy, which is
//! what eventually happened, and it never once called the renderer.

use mios_unit_gen::{drift_register, project};
use std::path::{Path, PathBuf};

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn ssot() -> String {
    std::fs::read_to_string(root().join("usr/share/mios/mios.toml")).expect("SSOT is readable")
}

#[test]
fn test_declared_units_render_or_are_registered() {
    let p = project(&root()).expect("projection runs");
    let register = drift_register(&ssot()).expect("register parses");

    let unexpected: Vec<&String> = p.drifted.iter().filter(|f| !register.contains(f)).collect();
    assert!(
        unexpected.is_empty(),
        "[units.*] no longer renders these units, and they are not in \
         [unit_projection].drift -- either fix the declaration or register the debt: {unexpected:#?}"
    );
}

#[test]
fn test_the_register_only_shrinks() {
    let p = project(&root()).expect("projection runs");
    let register = drift_register(&ssot()).expect("register parses");

    let stale: Vec<&String> = register.iter().filter(|f| !p.drifted.contains(f)).collect();
    assert!(
        stale.is_empty(),
        "these units render faithfully now -- drop them from [unit_projection].drift. \
         A register that keeps entries it no longer needs stops measuring the debt \
         and starts hiding the next one: {stale:#?}"
    );
}

#[test]
fn test_every_declared_unit_exists_on_disk() {
    let p = project(&root()).expect("projection runs");
    assert!(
        p.missing.is_empty(),
        "[units.*] declares units the tree does not ship: {:#?}",
        p.missing
    );
}

/// The gate must not be able to pass over an empty set. `[units.*]` covering
/// nothing would make every other assertion here vacuously true.
#[test]
fn test_the_projection_is_not_empty() {
    let p = project(&root()).expect("projection runs");
    let declared = p.faithful.len() + p.drifted.len() + p.missing.len();
    assert!(declared > 0, "[units.*] declares no units at all");
    assert!(
        !p.faithful.is_empty(),
        "not one declared unit renders faithfully -- the renderer is broken, not the SSOT"
    );
}

#[test]
fn test_every_shipped_unit_is_declared_in_ssot() {
    let sys_dir = root().join("usr/share/mios/systemd");
    if !sys_dir.exists() {
        return;
    }
    let toml_content = ssot();
    let doc: toml::Table = toml::from_str(&toml_content).expect("SSOT parses as TOML");
    let units_table = doc.get("units").and_then(|u| u.as_table()).cloned().unwrap_or_default();

    let mut declared_files = std::collections::HashSet::new();
    for (name, val) in &units_table {
        if let Some(tbl) = val.as_table() {
            let fn_str = tbl.get("file").and_then(|f| f.as_str()).map(|s| s.to_string()).unwrap_or_else(|| {
                if name.ends_with(".service") || name.ends_with(".timer") || name.ends_with(".path") || name.ends_with(".target") {
                    name.clone()
                } else {
                    format!("{}.service", name)
                }
            });
            declared_files.insert(fn_str);
        } else {
            let fn_str = if name.ends_with(".service") || name.ends_with(".timer") || name.ends_with(".path") || name.ends_with(".target") {
                name.clone()
            } else {
                format!("{}.service", name)
            };
            declared_files.insert(fn_str);
        }
    }

    let mut untracked = Vec::new();
    if let Ok(entries) = std::fs::read_dir(&sys_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() {
                if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                    if name.ends_with(".service") || name.ends_with(".timer") || name.ends_with(".path") || name.ends_with(".target") {
                        if !declared_files.contains(name) {
                            untracked.push(name.to_string());
                        }
                    }
                }
            }
        }
    }

    assert!(
        untracked.is_empty(),
        "un-tracked systemd unit files shipped under usr/share/mios/systemd/ not declared in [units.*]: {untracked:#?}"
    );
}

