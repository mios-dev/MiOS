// AI-hint: Asserts the Law 8 projection registry is complete in BOTH directions -- every generator the discovery globs find is registered or itemised exempt, and every registered entry names a check that exists.
// AI-related: usr/share/mios/mios.toml, automation/98-drift-checks.sh, tools/drift-checks.py, usr/share/doc/mios/adr/0021-rust-static-binary-consolidation.md

use crate::Report;
use std::collections::BTreeSet;
use std::path::Path;

const CHECK: &str = "projection-coverage";
const SSOT: &str = "usr/share/mios/mios.toml";
const DRIFT: &str = "automation/98-drift-checks.sh";

fn cannot_run(why: impl Into<String>) -> Report {
    Report {
        check: CHECK.to_string(),
        ok: false,
        could_not_run: Some(why.into()),
        summary: String::new(),
        findings: Vec::new(),
    }
}

/// Split `dir/pre*suf` into (dir, pre, suf).
///
/// Deliberately a single-`*`, final-segment-only matcher rather than a glob
/// crate: the patterns this consumes are SSOT and a pattern this cannot
/// express must be REJECTED loudly, not silently matched by something more
/// permissive than its author meant.
fn split_pattern(pattern: &str) -> Option<(String, String, String)> {
    let (dir, leaf) = match pattern.rsplit_once('/') {
        Some((d, l)) => (d.to_string(), l),
        None => (String::new(), pattern),
    };
    if dir.contains('*') || leaf.matches('*').count() != 1 {
        return None;
    }
    let (pre, suf) = leaf.split_once('*')?;
    Some((dir, pre.to_string(), suf.to_string()))
}

fn matches(pattern: &str, rel: &str) -> bool {
    let Some((dir, pre, suf)) = split_pattern(pattern) else {
        return false;
    };
    let (rdir, rleaf) = match rel.rsplit_once('/') {
        Some((d, l)) => (d, l),
        None => ("", rel),
    };
    rdir == dir
        && rleaf.len() >= pre.len() + suf.len()
        && rleaf.starts_with(&pre)
        && rleaf.ends_with(&suf)
}

/// Every tracked file under `dir` whose name matches `pre*suf`, as repo-relative paths.
fn discover(root: &Path, pattern: &str) -> Result<Vec<String>, String> {
    let Some((dir, pre, suf)) = split_pattern(pattern) else {
        return Err(format!(
            "[laws.projection_registry].generator_globs entry {pattern:?} is not a \
             single-`*`, final-segment pattern -- this check cannot express it"
        ));
    };
    let abs = root.join(&dir);
    let Ok(entries) = std::fs::read_dir(&abs) else {
        return Err(format!("{} is not readable", abs.display()));
    };
    let mut out = Vec::new();
    for entry in entries.flatten() {
        let name = entry.file_name().to_string_lossy().to_string();
        if !entry.path().is_file() {
            continue;
        }
        if name.len() >= pre.len() + suf.len() && name.starts_with(&pre) && name.ends_with(&suf) {
            out.push(if dir.is_empty() {
                name
            } else {
                format!("{dir}/{name}")
            });
        }
    }
    Ok(out)
}

fn str_field<'a>(entry: &'a toml::Value, key: &str) -> &'a str {
    entry.get(key).and_then(|v| v.as_str()).unwrap_or("").trim()
}

pub fn check(root: &Path) -> Report {
    let ssot = root.join(SSOT);
    let drift = root.join(DRIFT);
    let Ok(ssot_text) = std::fs::read_to_string(&ssot) else {
        return cannot_run(format!("{SSOT} could not be read"));
    };
    let Ok(ssot_val) = ssot_text.parse::<toml::Value>() else {
        return cannot_run(format!("{SSOT} did not parse"));
    };
    // The drift script is the register's other half. Unreadable is cannot-run,
    // never a pass: a missing file would make every `check = ...` unverifiable.
    let Ok(drift_text) = std::fs::read_to_string(&drift) else {
        return cannot_run(format!("{DRIFT} could not be read"));
    };

    let Some(reg) = ssot_val
        .get("laws")
        .and_then(|l| l.get("projection_registry"))
        .and_then(|r| r.as_table())
    else {
        return cannot_run("mios.toml declares no [laws.projection_registry] table");
    };

    let surfaces = match reg.get("surfaces").and_then(|v| v.as_array()) {
        Some(a) if !a.is_empty() => a,
        _ => return cannot_run("[laws.projection_registry].surfaces is absent or empty"),
    };
    let globs: Vec<String> = match reg.get("generator_globs").and_then(|v| v.as_array()) {
        Some(a) if !a.is_empty() => a
            .iter()
            .filter_map(|v| v.as_str())
            .map(str::to_string)
            .collect(),
        _ => {
            return cannot_run(
                "[laws.projection_registry].generator_globs is absent or empty -- \
                 this check's scope is SSOT, and an unscoped run would pass on the empty set",
            )
        }
    };
    // Absent `exempt` is the empty register, which is the desired state; absent
    // `max_exempt` is NOT, because then the ceiling could never be ratcheted.
    let empty = Vec::new();
    let exempt_rows = reg
        .get("exempt")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty);
    let Some(max_exempt) = reg.get("max_exempt").and_then(|v| v.as_integer()) else {
        return cannot_run(
            "[laws.projection_registry].max_exempt is absent or not an integer -- \
             an unbounded exemption list is not a shrink-only register",
        );
    };

    let mut findings = Vec::new();

    // --- discover the generators in scope -----------------------------------
    let mut discovered: BTreeSet<String> = BTreeSet::new();
    for g in &globs {
        match discover(root, g) {
            Ok(hits) => discovered.extend(hits),
            Err(why) => return cannot_run(why),
        }
    }
    if discovered.is_empty() {
        return cannot_run(format!(
            "the {} discovery glob(s) matched no file -- an empty scope is a broken \
             glob, not a clean tree",
            globs.len()
        ));
    }

    // --- read the register --------------------------------------------------
    let mut registered: BTreeSet<String> = BTreeSet::new();
    for (i, s) in surfaces.iter().enumerate() {
        let gen = str_field(s, "generator");
        let chk = str_field(s, "check");
        let out = str_field(s, "output");
        if gen.is_empty() {
            findings.push(format!(
                "[laws.projection_registry].surfaces[{i}] has no `generator`"
            ));
            continue;
        }
        // One generator can legitimately appear on several rows (one per
        // projected surface), so a repeat is not itself a finding.
        registered.insert(gen.to_string());
        if !root.join(gen).exists() {
            findings.push(format!("registered generator '{gen}' is not on disk"));
        }
        if chk.is_empty() {
            findings.push(format!("registered generator '{gen}' names no `check`"));
        } else if !drift_text.contains(&format!("\n{chk}()"))
            && !drift_text.contains(&format!("\n{chk} ()"))
        {
            findings.push(format!(
                "registered generator '{gen}' names check '{chk}', which is not \
                 defined in {DRIFT}"
            ));
        }
        // Law 8 is regenerate-and-DIFF: a row that does not say what it
        // projects cannot be diffed against anything.
        if out.is_empty() {
            findings.push(format!(
                "registered generator '{gen}' (check '{chk}') declares no `output` -- \
                 a registry row that does not name the projected surface cannot be verified"
            ));
        }
    }

    let mut exempted: BTreeSet<String> = BTreeSet::new();
    for (i, e) in exempt_rows.iter().enumerate() {
        let gen = str_field(e, "generator");
        let reason = str_field(e, "reason");
        if gen.is_empty() {
            findings.push(format!(
                "[laws.projection_registry].exempt[{i}] has no `generator`"
            ));
            continue;
        }
        if reason.is_empty() {
            findings.push(format!(
                "exempt generator '{gen}' carries no `reason` -- a bare name is a \
                 count, not an itemised register"
            ));
        }
        if registered.contains(gen) {
            findings.push(format!(
                "generator '{gen}' is both registered and exempt -- the exemption \
                 would hide a change to the registered row"
            ));
        }
        exempted.insert(gen.to_string());
    }
    if exempt_rows.len() as i64 > max_exempt {
        findings.push(format!(
            "{} exempt generator(s) against a ceiling of {max_exempt} -- the register \
             is shrink-only; close the gap instead of raising it",
            exempt_rows.len()
        ));
    }

    // --- anchor the glob against the register -------------------------------
    // The coverage assertion below is only as wide as `discovered`, so the
    // globs are the check's own allowlist and must be anchored to something
    // outside themselves -- otherwise DELETING a glob shrinks the scope and
    // the check reports clean over what is left. (That is not hypothetical:
    // dropping "tools/render-*.py" took the scope from 21 to 17 and still
    // exited 0, until this block.) The anchor is the register itself: any
    // directory a glob names is IN scope, so every registry row living in one
    // of those directories must be matched by some glob.
    let glob_dirs: BTreeSet<String> = globs
        .iter()
        .filter_map(|g| split_pattern(g).map(|(d, _, _)| d))
        .collect();
    for name in registered.iter().chain(exempted.iter()) {
        let parent = name.rsplit_once('/').map(|(d, _)| d).unwrap_or("");
        let covered = globs.iter().any(|g| matches(g, name));
        if glob_dirs.contains(parent) && !covered {
            findings.push(format!(
                "'{name}' is on the registry and sits in a directory the discovery \
                 globs claim, but no glob matches it -- the scope has narrowed and \
                 the coverage assertion no longer sees this generator"
            ));
        }
        if covered && !discovered.contains(name) {
            findings.push(format!(
                "'{name}' is on the registry and matches a discovery glob, but the \
                 glob did not find it -- the discovery scope is broken"
            ));
        }
    }

    // --- the reverse assertion this check exists for ------------------------
    for gen in &discovered {
        if !registered.contains(gen) && !exempted.contains(gen) {
            findings.push(format!(
                "generator '{gen}' writes into the tree but is on neither \
                 [laws.projection_registry].surfaces nor .exempt -- Law 8 needs a \
                 check for it, or an itemised exemption saying why it needs none"
            ));
        }
    }

    let ok = findings.is_empty();
    Report {
        check: CHECK.to_string(),
        ok,
        could_not_run: None,
        summary: format!(
            "{} generator(s) in scope, {} registry row(s) over {} generator(s), \
             {} exempt (ceiling {max_exempt})",
            discovered.len(),
            surfaces.len(),
            registered.len(),
            exempt_rows.len()
        ),
        findings,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_split_pattern_rejects_what_it_cannot_express() {
        assert!(split_pattern("tools/generate-*.py").is_some());
        // Two stars, a star in a directory component, and no star at all are
        // all rejected rather than approximated.
        assert!(split_pattern("tools/*-*.py").is_none());
        assert!(split_pattern("tools/*/gen-*.py").is_none());
        assert!(split_pattern("tools/generate.py").is_none());
    }

    #[test]
    fn test_matches_is_anchored_to_the_directory() {
        assert!(matches("tools/generate-*.py", "tools/generate-ports.py"));
        // Same leaf, different directory: not a match.
        assert!(!matches("tools/generate-*.py", "src/generate-ports.py"));
        // Nested one level deeper: not a match either.
        assert!(!matches(
            "tools/generate-*.py",
            "tools/sub/generate-ports.py"
        ));
    }

    #[test]
    fn test_matches_does_not_let_prefix_and_suffix_overlap() {
        // `generate-*.py` must not match the bare stem `generate-.py`'s
        // shorter cousin `generate-py`, nor let `*` consume the suffix.
        assert!(!matches("tools/generate-*.py", "tools/generate-py"));
        assert!(matches("tools/generate-*.py", "tools/generate-.py"));
    }
}
