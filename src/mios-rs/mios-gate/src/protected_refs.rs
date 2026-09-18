// AI-hint: Law-9 extension gate: every bare ${MIOS_*} the Quadlet renderer leaves unbaked must be supplied at runtime by the unit's own [Service] Environment= or by the install.env system-sync-env renders.
// AI-related: tools/native/mios-render-quadlets/src/main.rs, usr/libexec/mios/system-sync-env.sh, usr/share/mios/mios.toml

use crate::Report;
use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

const CHECK: &str = "protected-refs";

fn cannot_run(why: impl Into<String>) -> Report {
    Report {
        check: CHECK.to_string(),
        ok: false,
        could_not_run: Some(why.into()),
        summary: String::new(),
        findings: Vec::new(),
    }
}

/// The renderer's rule, reproduced: a unit declaring `Environment=` or
/// `EnvironmentFile=` **in `[Service]`** owns its Exec refs. The section is
/// load-bearing -- `[Container] Environment=` is podman's `--env` and confers
/// nothing on systemd's expansion.
fn declares_unit_environment(content: &str) -> bool {
    let mut in_service = false;
    for line in content.lines() {
        let t = line.trim();
        if t.starts_with('[') && t.ends_with(']') {
            in_service = t == "[Service]";
            continue;
        }
        if in_service && (t.starts_with("Environment=") || t.starts_with("EnvironmentFile=")) {
            return true;
        }
    }
    false
}

fn directive_of(line: &str) -> Option<&str> {
    let t = line.trim_start();
    let eq = t.find('=')?;
    Some(t[..eq].trim())
}

fn continues(line: &str) -> bool {
    line.trim_end().ends_with('\\')
}

fn is_comment(line: &str) -> bool {
    let t = line.trim_start();
    t.starts_with('#') || t.starts_with(';')
}

/// Names referenced as a BARE `${MIOS_*}`. `${VAR:-default}` is excluded on
/// purpose: systemd never expands that form, so the renderer always bakes it
/// and it is never left to arrive at runtime.
fn bare_refs(line: &str, out: &mut BTreeSet<String>) {
    let bytes = line.as_bytes();
    let mut i = 0usize;
    while i + 1 < bytes.len() {
        if bytes[i] != b'$' || bytes[i + 1] != b'{' {
            i += 1;
            continue;
        }
        let start = i + 2;
        let Some(close) = line[start..].find('}') else {
            break;
        };
        let inner = &line[start..start + close];
        if inner.starts_with("MIOS_")
            && inner
                .chars()
                .all(|c| c.is_ascii_uppercase() || c.is_ascii_digit() || c == '_')
        {
            out.insert(inner.to_string());
        }
        i = start + close + 1;
    }
}

/// Names a `[Service] Environment=` line assigns.
///
/// systemd accepts several whitespace-separated assignments on one directive
/// and allows quoting a value that contains spaces, so the names are taken from
/// each token rather than from the directive as a whole.
fn env_assignments(rest: &str, out: &mut BTreeSet<String>) {
    let mut tok = String::new();
    let mut quote: Option<char> = None;
    let push = |t: &mut String, out: &mut BTreeSet<String>| {
        if let Some((k, _)) = t.split_once('=') {
            let k = k.trim();
            if !k.is_empty() && k.chars().all(|c| c.is_ascii_alphanumeric() || c == '_') {
                out.insert(k.to_string());
            }
        }
        t.clear();
    };
    for c in rest.chars() {
        match quote {
            Some(q) if c == q => quote = None,
            Some(_) => tok.push(c),
            None if c == '"' || c == '\'' => quote = Some(c),
            None if c.is_whitespace() => push(&mut tok, out),
            None => tok.push(c),
        }
    }
    push(&mut tok, out);
}

/// Per unit: the bare refs the renderer protects, and the names the unit's own
/// `[Service] Environment=` lines supply.
fn scan_unit(
    content: &str,
    runtime_ref_directives: &[String],
) -> (BTreeSet<String>, BTreeSet<String>) {
    let mut protected = BTreeSet::new();
    let mut supplied = BTreeSet::new();
    if !declares_unit_environment(content) {
        return (protected, supplied);
    }
    let mut in_service = false;
    let mut in_runtime_ref = false;
    for line in content.lines() {
        let t = line.trim();
        if !in_runtime_ref && t.starts_with('[') && t.ends_with(']') {
            in_service = t == "[Service]";
            continue;
        }
        if is_comment(line) {
            continue;
        }
        if in_service {
            if let Some(rest) = t.strip_prefix("Environment=") {
                env_assignments(rest, &mut supplied);
            }
        }
        if !in_runtime_ref {
            in_runtime_ref = match directive_of(line) {
                Some(d) => runtime_ref_directives.iter().any(|r| r == d),
                None => false,
            };
        }
        if in_runtime_ref {
            bare_refs(line, &mut protected);
        }
        // A directive continued with a trailing backslash owns its
        // continuation lines: mios-agents.service writes its whole `podman run`
        // that way and carries twelve of its thirteen refs there.
        if !continues(line) {
            in_runtime_ref = false;
        }
    }
    (protected, supplied)
}

fn walk(
    dir: &Path,
    depth: usize,
    max_depth: usize,
    exts: &BTreeSet<String>,
    out: &mut Vec<PathBuf>,
) {
    if depth > max_depth {
        return;
    }
    let Ok(rd) = std::fs::read_dir(dir) else {
        return;
    };
    let mut entries: Vec<_> = rd.flatten().map(|e| e.path()).collect();
    entries.sort();
    for p in entries {
        if p.is_dir() {
            walk(&p, depth + 1, max_depth, exts, out);
        } else if p.is_file() {
            let keep = p
                .extension()
                .and_then(|e| e.to_str())
                .map(|e| exts.contains(e))
                .unwrap_or(false);
            if keep {
                out.push(p);
            }
        }
    }
}

/// The install.env a deploy actually leaves on disk. `system-sync-env.sh` is
/// the oracle among the four environment projections because it is the LAST
/// writer of that file: whatever it does not emit is not on the host, however
/// faithfully something earlier wrote it.
fn install_env_names(root: &Path) -> Result<BTreeSet<String>, String> {
    let script = root.join("usr/libexec/mios/system-sync-env.sh");
    if !script.is_file() {
        return Err(format!("{} is missing", script.display()));
    }
    let out = std::process::Command::new("bash")
        .arg(&script)
        .arg("--dry-run")
        .env("MIOS_ROOT", root)
        .current_dir(root)
        .output()
        .map_err(|e| format!("system-sync-env.sh could not be run: {e}"))?;
    if !out.status.success() {
        return Err(format!(
            "system-sync-env.sh --dry-run failed: {}",
            String::from_utf8_lossy(&out.stderr).trim()
        ));
    }
    let text = String::from_utf8_lossy(&out.stdout);
    let mut names = BTreeSet::new();
    for line in text.lines() {
        let t = line.trim();
        if t.is_empty() || t.starts_with('#') {
            continue;
        }
        if let Some((k, _)) = t.split_once('=') {
            names.insert(k.trim().to_string());
        }
    }
    if names.is_empty() {
        return Err("system-sync-env.sh --dry-run emitted no assignments".to_string());
    }
    Ok(names)
}

fn strings(v: Option<&toml::Value>) -> Vec<String> {
    v.and_then(|x| x.as_array())
        .map(|a| {
            a.iter()
                .filter_map(|x| x.as_str())
                .map(|s| s.to_string())
                .collect()
        })
        .unwrap_or_default()
}

pub fn check(root: &Path) -> Report {
    let ssot = root.join("usr/share/mios/mios.toml");
    let Ok(text) = std::fs::read_to_string(&ssot) else {
        return cannot_run(format!("{} could not be read", ssot.display()));
    };
    let Ok(val) = text.parse::<toml::Value>() else {
        return cannot_run("usr/share/mios/mios.toml did not parse");
    };
    let Some(qr) = val.get("build").and_then(|b| b.get("quadlet_render")) else {
        return cannot_run(
            "[build.quadlet_render] is missing, so the renderer's own scope is unknown",
        );
    };

    // Read the SCOPE from the same table the renderer reads. A gate that
    // re-declares the directive list can pass while the renderer protects
    // something the gate never looked at.
    let directives = strings(qr.get("runtime_ref_directives"));
    let exts: BTreeSet<String> = strings(qr.get("extensions")).into_iter().collect();
    let dirs = strings(qr.get("dirs"));
    let max_depth = qr
        .get("max_depth")
        .and_then(|v| v.as_integer())
        .unwrap_or(2)
        .max(1) as usize;
    if directives.is_empty() || exts.is_empty() || dirs.is_empty() {
        return cannot_run(
            "[build.quadlet_render] declares no directives, extensions or dirs -- the scan would be empty",
        );
    }

    let mut files: Vec<PathBuf> = Vec::new();
    for d in &dirs {
        let rel = d.trim_start_matches('/');
        let full = root.join(rel);
        if full.is_dir() {
            walk(&full, 1, max_depth, &exts, &mut files);
        }
    }
    if files.is_empty() {
        return cannot_run("no unit files were scanned, so nothing was compared");
    }

    let supplied_globally = match install_env_names(root) {
        Ok(n) => n,
        Err(e) => return cannot_run(e),
    };

    let mut findings: Vec<String> = Vec::new();
    let mut units_with_protection = 0usize;
    let mut refs_checked = 0usize;
    let mut per_unit: BTreeMap<String, Vec<String>> = BTreeMap::new();

    for path in &files {
        let Ok(body) = std::fs::read_to_string(path) else {
            continue;
        };
        let (protected, supplied_locally) = scan_unit(&body, &directives);
        if protected.is_empty() {
            continue;
        }
        units_with_protection += 1;
        let rel = path
            .strip_prefix(root)
            .unwrap_or(path)
            .to_string_lossy()
            .replace('\\', "/");
        for name in &protected {
            refs_checked += 1;
            if supplied_locally.contains(name) || supplied_globally.contains(name) {
                continue;
            }
            per_unit.entry(rel.clone()).or_default().push(name.clone());
        }
    }

    // Empty-set pass: if nothing was protected, this gate compared nothing and
    // must say so rather than report a clean tree.
    if refs_checked == 0 {
        return cannot_run(
            "no unit protects a bare ${MIOS_*} on a runtime-ref directive, so nothing was compared",
        );
    }

    for (unit, names) in &per_unit {
        for name in names {
            findings.push(format!(
                "{unit}: ${{{name}}} is left unbaked for systemd to expand, but no [Service] \
                 Environment= in that unit and no install.env line supplies it -- systemd expands \
                 an absent name to the empty string, so the value silently disappears at runtime"
            ));
        }
    }

    let ok = findings.is_empty();
    Report {
        check: CHECK.to_string(),
        ok,
        could_not_run: None,
        summary: format!(
            "{refs_checked} protected ref(s) across {units_with_protection} unit(s) all arrive \
             from the unit's own Environment= or from install.env"
        ),
        findings,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const DIRECTIVES: [&str; 2] = ["ExecStart", "ExecStartPre"];

    fn dirs() -> Vec<String> {
        DIRECTIVES.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn a_bare_ref_on_exec_is_protected_and_reported_as_such() {
        let unit =
            "[Service]\nEnvironmentFile=-/etc/mios/install.env\nExecStart=/bin/x ${MIOS_A}\n";
        let (p, s) = scan_unit(unit, &dirs());
        assert!(p.contains("MIOS_A"));
        assert!(s.is_empty());
    }

    /// The whole point of the gate: an Environment= line in the SAME unit is a
    /// supply, so the ref arrives and is not a finding.
    #[test]
    fn a_unit_environment_line_supplies_the_name() {
        let unit = "[Service]\nEnvironment=MIOS_A=1\nExecStart=/bin/x ${MIOS_A}\n";
        let (p, s) = scan_unit(unit, &dirs());
        assert!(p.contains("MIOS_A"));
        assert!(s.contains("MIOS_A"), "Environment= must count as a supply");
    }

    /// systemd quotes a value containing spaces; the name is still assigned.
    #[test]
    fn a_quoted_environment_value_still_declares_its_name() {
        let unit =
            "[Service]\nEnvironment=\"MIOS_M=Some Model (High)\"\nExecStart=/bin/x ${MIOS_M}\n";
        let (p, s) = scan_unit(unit, &dirs());
        assert!(p.contains("MIOS_M"));
        assert!(s.contains("MIOS_M"));
    }

    /// `${VAR:-default}` is baked by the renderer, never left to arrive, so it
    /// must not be judged here -- counting it would manufacture findings for
    /// every unit that uses the defaulted form correctly.
    #[test]
    fn the_defaulted_form_is_not_protected() {
        let unit = "[Service]\nEnvironmentFile=-/x\nExecStart=/bin/x ${MIOS_A:-8900}\n";
        let (p, _) = scan_unit(unit, &dirs());
        assert!(
            p.is_empty(),
            "the :- form always bakes, so it never arrives at runtime"
        );
    }

    /// Without [Service] env the renderer bakes everything, so there is no
    /// protected ref to check.
    #[test]
    fn a_unit_without_service_env_protects_nothing() {
        let unit = "[Container]\nEnvironment=X=1\nExecStart=/bin/x ${MIOS_A}\n";
        let (p, _) = scan_unit(unit, &dirs());
        assert!(p.is_empty());
    }

    /// mios-agents.service carries twelve of its thirteen refs on backslash
    /// continuations; judging each physical line alone would miss all twelve.
    #[test]
    fn continuation_lines_belong_to_their_directive() {
        let unit = "[Service]\nEnvironmentFile=-/x\nExecStart=/bin/run \\\n  --env A=${MIOS_A} \\\n  --env B=${MIOS_B}\n";
        let (p, _) = scan_unit(unit, &dirs());
        assert!(p.contains("MIOS_A") && p.contains("MIOS_B"));
    }

    /// A ref on a directive systemd does not expand at runtime is baked, so it
    /// is out of scope.
    #[test]
    fn a_non_runtime_directive_is_out_of_scope() {
        let unit = "[Service]\nEnvironmentFile=-/x\nImage=registry/${MIOS_A}\n";
        let (p, _) = scan_unit(unit, &dirs());
        assert!(p.is_empty());
    }
}
