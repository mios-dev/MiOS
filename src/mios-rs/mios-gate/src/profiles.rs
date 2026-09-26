// AI-hint: Asserts mios.toml [profiles] (ADR-0025) is closed: every profile resolves without a cycle, names only registered phases and real [packages] sections, contains the floor profile, and every [profiles.targets] entry names a declared profile.
// AI-related: usr/share/mios/mios.toml, src/mios-rs/mios-build/src/lib.rs, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh
// AI-functions: check

use crate::Report;
use mios_build::{PhaseRegistry, Profiles};
use std::path::Path;

const CHECK: &str = "profile-integrity";

fn cannot_run(why: impl Into<String>) -> Report {
    Report {
        check: CHECK.to_string(),
        ok: false,
        could_not_run: Some(why.into()),
        summary: String::new(),
        findings: Vec::new(),
    }
}

pub fn check(root: &Path) -> Report {
    let ssot = root.join("usr/share/mios/mios.toml");
    let Ok(text) = std::fs::read_to_string(&ssot) else {
        return cannot_run(format!("{} could not be read", ssot.display()));
    };
    let Ok(val) = text.parse::<toml::Value>() else {
        return cannot_run("usr/share/mios/mios.toml did not parse");
    };
    let registry = match PhaseRegistry::load_from_toml(&ssot) {
        Ok(r) => r,
        Err(e) => return cannot_run(e.to_string()),
    };
    let profiles = match Profiles::from_toml_str(&text) {
        Ok(p) => p,
        Err(e) => return cannot_run(e),
    };
    let sections = val.get("packages").and_then(|v| v.as_table());
    let mut findings = Vec::new();

    let names = profiles.names();
    let mut resolved = Vec::new();
    for name in &names {
        match profiles.resolve(name) {
            Ok(r) => {
                if let Err(e) = registry.for_profile(&r) {
                    findings.push(e);
                }
                for s in &r.package_sections {
                    if !sections.is_some_and(|t| t.contains_key(s)) {
                        findings.push(format!(
                            "profile {name:?} names package section {s:?} absent from [packages]"
                        ));
                    }
                }
                resolved.push(r);
            }
            Err(e) => findings.push(e),
        }
    }

    for key in ["default", "floor"] {
        match profiles.table_str(key) {
            Some(n) if names.contains(&n) => {}
            Some(n) => findings.push(format!(
                "[profiles].{key} = {n:?} is not a declared profile"
            )),
            None => findings.push(format!("[profiles].{key} is absent")),
        }
    }

    if let Some(floor) = profiles
        .table_str("floor")
        .and_then(|f| resolved.iter().find(|r| r.name == f).cloned())
    {
        for r in resolved.iter().filter(|r| !r.all && r.name != floor.name) {
            let missing: Vec<&String> = floor
                .phases
                .iter()
                .chain(floor.package_sections.iter())
                .filter(|x| !r.phases.contains(*x) && !r.package_sections.contains(*x))
                .collect();
            if !missing.is_empty() {
                findings.push(format!(
                    "profile {:?} does not contain the floor profile {:?}: missing {}",
                    r.name,
                    floor.name,
                    missing
                        .iter()
                        .map(|s| s.as_str())
                        .collect::<Vec<_>>()
                        .join(", ")
                ));
            }
        }
    }

    match profiles.targets() {
        Ok(targets) => {
            for (kind, members) in targets {
                for m in members.iter().filter(|m| !names.contains(m)) {
                    findings.push(format!(
                        "[profiles.targets].{kind} names undeclared profile {m:?}"
                    ));
                }
            }
        }
        Err(e) => findings.push(e),
    }

    Report {
        check: CHECK.to_string(),
        ok: findings.is_empty(),
        could_not_run: None,
        summary: format!(
            "{} profile(s) resolve over registered phases and real package sections; each contains the floor; every target names a declared profile",
            names.len()
        ),
        findings,
    }
}
