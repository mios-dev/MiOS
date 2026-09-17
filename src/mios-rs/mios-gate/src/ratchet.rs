// AI-hint: Asserts shrink-only ceilings in mios.toml never increase over HEAD, and that a ceiling exempted as a generated budget says so in SSOT rather than by being quietly skipped.
// AI-related: usr/share/mios/mios.toml, tools/check-ratchet-direction.py, automation/98-drift-checks.sh

use crate::Report;
use std::collections::BTreeMap;
use std::path::Path;
use std::process::Command;

const CHECK: &str = "ratchet-direction";
const SSOT: &str = "usr/share/mios/mios.toml";

/// Sections whose numeric keys are ratchets even when the key name only
/// CONTAINS `max_`/`ceiling` rather than starting or ending with it.
///
/// This is the predecessor's list minus two entries it could never use.
/// `check-ratchet-direction.py` compared against `full_key.split(".")[0]`, the
/// FIRST path component, while listing `build.ratchet` and
/// `security.privileged_quadlets` -- dotted names that comparison can never
/// match. Widening them here to `build` and `security` would be a tightening
/// smuggled into a port: it newly captures `build.rechunk_max_layers`, a tuning
/// value nobody decided was shrink-only. Filed as T-1055; behaviour preserved.
const RATCHET_SECTIONS: [&str; 14] = [
    "docs",
    "legibility",
    "resolver",
    "tasks",
    "ci",
    "tests",
    "ssot_consumers",
    "ssot_tables",
    "unit_projection",
    "ai_tag",
    "rust",
    "drift",
    "gates",
    "sandbox",
];

fn report(ok: bool, summary: String, findings: Vec<String>) -> Report {
    Report {
        check: CHECK.to_string(),
        ok,
        could_not_run: None,
        summary,
        findings,
    }
}

fn cannot_run(why: impl Into<String>) -> Report {
    Report {
        check: CHECK.to_string(),
        ok: false,
        could_not_run: Some(why.into()),
        summary: String::new(),
        findings: Vec::new(),
    }
}

fn is_ceiling_key(key: &str, section: &str) -> bool {
    if key.starts_with("max_") || key.starts_with("stay_max_") || key.ends_with("_ceiling") {
        return true;
    }
    RATCHET_SECTIONS.contains(&section)
        && (key.contains("max_") || key.contains("stay_max_") || key.contains("ceiling"))
}

/// Every numeric ceiling in the table, keyed by its dotted path.
fn ceilings(v: &toml::Value, prefix: &str, out: &mut BTreeMap<String, f64>) {
    let Some(table) = v.as_table() else { return };
    for (k, val) in table {
        let full = if prefix.is_empty() {
            k.clone()
        } else {
            format!("{prefix}.{k}")
        };
        let section = full.split('.').next().unwrap_or("");
        let num = val
            .as_integer()
            .map(|i| i as f64)
            .or_else(|| val.as_float());
        match num {
            Some(n) if is_ceiling_key(k, section) => {
                out.insert(full, n);
            }
            _ => ceilings(val, &full, out),
        }
    }
}

/// Ceilings SSOT declares are generated budgets rather than shrink-only
/// ratchets. Each carries a reason; a bare name would make this a silent skip,
/// which is the shape this binary exists to refuse.
fn exempt(ssot: &toml::Value) -> (BTreeMap<String, String>, Vec<String>) {
    let mut map = BTreeMap::new();
    let mut findings = Vec::new();
    // A TABLE of key -> reason, deliberately not an array of inline tables: that
    // shape renders differently in the two resolver twins, and its registered
    // divergence set is a shrink-only 12 that a thirteenth key breaches
    // (check_resolver_differential_parity). Law 13 costs a shape here.
    let Some(rows) = ssot
        .get("drift")
        .and_then(|d| d.get("generated_ceilings"))
        .and_then(|v| v.as_table())
    else {
        return (map, findings);
    };
    for (key, val) in rows {
        let reason = val.as_str().unwrap_or("").trim();
        if reason.is_empty() {
            findings.push(format!(
                "[drift.generated_ceilings] '{key}' carries no `reason` -- an exemption \
                 without one is a silent skip"
            ));
        }
        map.insert(key.clone(), reason.to_string());
    }
    (map, findings)
}

pub fn check(root: &Path) -> Report {
    let rel = SSOT;
    let path = root.join(rel);
    let is_checkout = root.join(".git").exists();
    let require_tools = std::env::var("MIOS_DRIFT_REQUIRE_TOOLS").ok().as_deref() == Some("1");

    if !path.is_file() {
        // Absent though TRACKED is a dropped deliverable; a tree that never had
        // it is not a checkout of this repo and has nothing to ratchet.
        let tracked = is_checkout
            && Command::new("git")
                .args(["-C"])
                .arg(root)
                .args(["ls-files", "--", rel])
                .output()
                .map(|o| o.status.success() && !o.stdout.is_empty())
                .unwrap_or(false);
        if tracked {
            return cannot_run(format!(
                "{rel} is tracked but missing from the worktree -- no ceiling was read"
            ));
        }
        return report(
            true,
            format!("{rel} is absent and untracked here; nothing to ratchet"),
            vec![],
        );
    }
    if !is_checkout {
        return report(
            true,
            format!(
                "{} is not a checkout, so there is no HEAD to compare against",
                root.display()
            ),
            vec![],
        );
    }

    let out = match Command::new("git")
        .args(["-C"])
        .arg(root)
        .args(["show", &format!("HEAD:{rel}")])
        .output()
    {
        Ok(o) => o,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            if require_tools {
                return cannot_run("git is not installed, so no ceiling was compared against HEAD");
            }
            return report(
                true,
                "git is not installed; set MIOS_DRIFT_REQUIRE_TOOLS=1 to make that a failure"
                    .into(),
                vec![],
            );
        }
        Err(e) => return cannot_run(format!("git could not be run in {} ({e})", root.display())),
    };
    if !out.status.success() {
        let detail = String::from_utf8_lossy(&out.stderr).trim().to_string();
        let detail = if detail.is_empty() {
            "no message".into()
        } else {
            detail
        };
        return cannot_run(format!(
            "git could not read HEAD:{rel} ({detail}) -- no ceiling was compared"
        ));
    }

    let Ok(head_text) = String::from_utf8(out.stdout) else {
        return cannot_run(format!("HEAD:{rel} is not valid UTF-8"));
    };
    let Ok(head_val) = head_text.parse::<toml::Value>() else {
        return cannot_run(format!(
            "the committed HEAD:{rel} does not parse -- the SSOT in HEAD is broken"
        ));
    };
    let Ok(work_text) = std::fs::read_to_string(&path) else {
        return cannot_run(format!("{rel} could not be read"));
    };
    let Ok(work_val) = work_text.parse::<toml::Value>() else {
        return cannot_run(format!("{rel} does not parse"));
    };

    let (mut work, mut head) = (BTreeMap::new(), BTreeMap::new());
    ceilings(&work_val, "", &mut work);
    ceilings(&head_val, "", &mut head);
    // Zero on either side means nothing was compared, whatever a later loop says.
    if work.is_empty() {
        return cannot_run(format!(
            "{rel} declares no shrink-only ceiling, so no direction was checked"
        ));
    }
    if head.is_empty() {
        return cannot_run(format!(
            "HEAD:{rel} declares no shrink-only ceiling, so no direction was checked"
        ));
    }

    let (exempted, mut findings) = exempt(&work_val);
    // An exemption for a key that is not a ceiling is stale bookkeeping that
    // would quietly start covering a future key of that name.
    for k in exempted.keys() {
        if !work.contains_key(k) {
            findings.push(format!(
                "[drift.generated_ceilings] '{k}' is not a ceiling in {rel} -- drop the \
                 exemption rather than leaving it to cover a future key"
            ));
        }
    }

    let mut raised = 0usize;
    for (key, w) in &work {
        let Some(h) = head.get(key) else { continue };
        if w > h {
            if exempted.contains_key(key) {
                raised += 1;
                continue;
            }
            findings.push(format!(
                "ratchet ceiling '{key}' INCREASED from {h} to {w} -- this ceiling only comes down"
            ));
        }
    }

    let ok = findings.is_empty();
    let note = if exempted.is_empty() {
        String::new()
    } else {
        format!(
            ", {} declared generated budget(s) of which {raised} rose this commit",
            exempted.len()
        )
    };
    report(
        ok,
        format!("{} shrink-only ceiling(s) are <= HEAD{note}", work.len()),
        findings,
    )
}

#[cfg(test)]
// Test fixtures are literals authored here, so a parse failure is a broken
// test rather than an input the binary must survive.
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn ceiling_keys_by_name_and_by_section() {
        assert!(is_ceiling_key("max_unregistered", "build")); // by prefix, not by section
        assert!(is_ceiling_key("stay_max_x", "anything"));
        assert!(is_ceiling_key("foo_ceiling", "anything"));
        // Contains-only matches are section-scoped, not global.
        assert!(is_ceiling_key("soft_max_lines", "legibility"));
        assert!(!is_ceiling_key("soft_max_lines", "branding"));
        // T-1055: `build` is deliberately NOT a ratchet section here, because
        // the predecessor's `build.ratchet` entry never matched anything.
        assert!(!is_ceiling_key("rechunk_max_layers", "build"));
        assert!(!is_ceiling_key("enabled", "legibility"));
    }

    #[test]
    fn ceilings_walks_nested_tables_and_keeps_dotted_keys() {
        let v: toml::Value = "[a.b]\nmax_x = 3\n[a.c]\nmax_y = 4.5\nother = 9\n"
            .parse()
            .unwrap();
        let mut got = BTreeMap::new();
        ceilings(&v, "", &mut got);
        assert_eq!(got.get("a.b.max_x"), Some(&3.0));
        assert_eq!(got.get("a.c.max_y"), Some(&4.5));
        assert!(!got.contains_key("a.c.other"));
    }

    #[test]
    fn an_exemption_without_a_reason_is_a_finding() {
        let v: toml::Value = "[drift.generated_ceilings]\n\"a.max_x\" = \"\"\n"
            .parse()
            .unwrap();
        let (map, findings) = exempt(&v);
        assert!(map.contains_key("a.max_x"));
        assert_eq!(findings.len(), 1, "{findings:?}");
    }
}
