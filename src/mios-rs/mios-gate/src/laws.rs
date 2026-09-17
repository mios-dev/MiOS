// AI-hint: Asserts every [laws].enforced_by pointer resolves to live enforcement -- a function definition in the drift script, or a marker in executable text in the postcheck, never a comment.
// AI-related: usr/share/mios/mios.toml, automation/98-drift-checks.sh, automation/99-postcheck.sh

use crate::Report;
use std::path::Path;

const CHECK: &str = "law-enforcers";
const SSOT: &str = "usr/share/mios/mios.toml";
const DRIFT: &str = "automation/98-drift-checks.sh";
const POST: &str = "automation/99-postcheck.sh";

fn cannot_run(why: impl Into<String>) -> Report {
    Report {
        check: CHECK.to_string(),
        ok: false,
        could_not_run: Some(why.into()),
        summary: String::new(),
        findings: Vec::new(),
    }
}

/// The part of `99-postcheck.sh` that can actually run: everything before the
/// first top-level `exit 0`, with whole-comment lines dropped.
///
/// Both halves matter, and both were load-bearing. The file's last line was
/// `# References for laws: item14 item12 item16 item17` -- a comment, after
/// `exit 0`, naming four refs that exist nowhere else in the repo. A substring
/// search over the raw bytes matched it and reported four laws enforced.
pub fn executable_text(src: &str) -> String {
    let mut out = String::new();
    for line in src.lines() {
        if line == "exit 0" {
            break;
        }
        if line.trim_start().starts_with('#') {
            continue;
        }
        out.push_str(line);
        out.push('\n');
    }
    out
}

/// A shell function definition, the same predicate the drift script's own
/// targets have always been held to.
fn defines(src: &str, name: &str) -> bool {
    src.lines().any(|l| {
        let l = l.trim_end();
        l.strip_prefix(name)
            .map(|rest| rest.trim_start().starts_with("()"))
            .unwrap_or(false)
    })
}

pub fn check(root: &Path) -> Report {
    let Ok(ssot_text) = std::fs::read_to_string(root.join(SSOT)) else {
        return cannot_run(format!("{SSOT} could not be read"));
    };
    let Ok(ssot_val) = ssot_text.parse::<toml::Value>() else {
        return cannot_run(format!("{SSOT} did not parse"));
    };
    let Ok(drift_text) = std::fs::read_to_string(root.join(DRIFT)) else {
        return cannot_run(format!("{DRIFT} could not be read"));
    };
    // Absent is cannot-run, never a pass: with the file missing, every marker
    // target would be unverifiable and the old check reported success anyway.
    let Ok(post_raw) = std::fs::read_to_string(root.join(POST)) else {
        return cannot_run(format!("{POST} could not be read"));
    };
    let post_live = executable_text(&post_raw);

    let laws = match ssot_val
        .get("laws")
        .and_then(|l| l.get("laws"))
        .and_then(|l| l.as_array())
    {
        Some(a) if !a.is_empty() => a,
        _ => return cannot_run("mios.toml declares no [laws].laws, so nothing was checked"),
    };

    let mut findings = Vec::new();
    let (mut n_fn, mut n_marker, mut n_process) = (0usize, 0usize, 0usize);

    for law in laws {
        let id = law.get("id").and_then(|v| v.as_integer()).unwrap_or(-1);
        let slug = law.get("slug").and_then(|v| v.as_str()).unwrap_or("?");
        let enforced = law
            .get("enforced_by")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim();
        if enforced.is_empty() {
            findings.push(format!("Law {id} ({slug}) declares no enforced_by"));
            continue;
        }

        // A comma list carries the file once: "98-drift-checks.sh:a,b" means
        // both a and b live in that file. The previous reader split on comma
        // FIRST and then dropped any piece without a colon, so the second
        // enforcer of Law 12 was never checked at all.
        let mut current_file: Option<String> = None;
        for target in enforced.split(',').map(str::trim).filter(|t| !t.is_empty()) {
            let (file, refname) = match target.split_once(':') {
                Some((f, r)) => {
                    current_file = Some(f.trim().to_string());
                    (f.trim().to_string(), r.trim().to_string())
                }
                None => match &current_file {
                    Some(f) => (f.clone(), target.to_string()),
                    None => {
                        findings.push(format!(
                            "Law {id} ({slug}) -> '{target}' names no file and follows no target that did"
                        ));
                        continue;
                    }
                },
            };
            if refname.is_empty() {
                findings.push(format!("Law {id} ({slug}) -> '{target}' names no enforcer"));
                continue;
            }

            match file.as_str() {
                "98-drift-checks.sh" => {
                    n_fn += 1;
                    if !defines(&drift_text, &refname) {
                        findings.push(format!(
                            "Law {id} ({slug}) -> {file}:{refname} is not defined in {DRIFT}"
                        ));
                    }
                }
                "99-postcheck.sh" => {
                    n_marker += 1;
                    if !post_live.contains(&refname) {
                        let alibi = if post_raw.contains(&refname) {
                            " -- it appears only in a comment or after the file's `exit 0`"
                        } else {
                            ""
                        };
                        findings.push(format!(
                            "Law {id} ({slug}) -> {file}:{refname} does not appear in executable \
                             text in {POST}{alibi}"
                        ));
                    }
                }
                // A law enforced by process rather than code is a real category,
                // but it must be DECLARED as one. The previous reader matched
                // neither branch here and fell through to silence, which is the
                // same outcome as an unrecognised pointer and says nothing.
                "process" => n_process += 1,
                other => findings.push(format!(
                    "Law {id} ({slug}) -> enforcer kind '{other}' is not one this check can \
                     verify; use 98-drift-checks.sh, 99-postcheck.sh, or process"
                )),
            }
        }
    }

    let ok = findings.is_empty();
    Report {
        check: CHECK.to_string(),
        ok,
        could_not_run: None,
        summary: format!(
            "{} law(s): {n_fn} drift-check function(s), {n_marker} postcheck marker(s) in \
             executable text, {n_process} declared process-enforced",
            laws.len()
        ),
        findings,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn executable_text_drops_comments_and_stops_at_exit() {
        let src = "a=1\n# a comment\n  # indented comment\nb=2\nexit 0\n\n# References: item17\n";
        let live = executable_text(src);
        assert!(live.contains("a=1") && live.contains("b=2"));
        assert!(!live.contains("a comment"));
        assert!(!live.contains("indented comment"));
        assert!(!live.contains("item17"));
    }

    #[test]
    fn an_indented_exit_does_not_truncate_the_file() {
        // `    exit 0` inside a branch ends that path, not the script.
        let src = "if x; then\n    exit 0\nfi\nMARKER\nexit 0\n";
        assert!(executable_text(src).contains("MARKER"));
    }

    #[test]
    fn defines_wants_a_definition_not_a_call() {
        let src = "check_a() {\n    true\n}\n\nmain() {\n    check_b\n}\ncheck_c ()\n";
        assert!(defines(src, "check_a"));
        assert!(defines(src, "check_c"));
        assert!(!defines(src, "check_b"));
    }
}
