// AI-hint: Asserts every path named in an AI-related/AI-doc header or a markdown link resolves in the repository; the corpus is the TRACKED tree, so the verdict never moves with a developer's untracked working copies.
// AI-related: usr/share/mios/mios.toml, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh

use crate::Report;
use regex::Regex;
use std::path::{Path, PathBuf};
use std::process::Command;

const CHECK: &str = "doc-refs-resolve";
const SSOT: &str = "usr/share/mios/mios.toml";
const SCAN_EXT: [&str; 4] = [".py", ".sh", ".ps1", ".md"];
/// Files whose references are deliberately outside the check: task registers
/// name planned paths, and the negative-test harness plants paths on purpose.
const SKIP_BASENAME: [&str; 4] = [
    "AGY-TASKS.md",
    "TASKS.md",
    "doc-generative-documentation.md",
    "drift-gate-negatives.sh",
];
/// Upstream code the repository carries but does not author.
const SKIP_SEGMENT: &str = "vendored/";
/// Runtime and system trees, never repository paths.
const RUNTIME_PREFIX: [&str; 6] = ["/etc/", "/var/", "/tmp/", "/proc/", "/sys/", "/run/"];
const URL_PREFIX: [&str; 3] = ["http://", "https://", "localhost"];
const REF_SUFFIX: [&str; 8] = [
    ".sh", ".py", ".toml", ".ps1", ".json", ".yaml", ".yml", ".md",
];
const LINK_SUFFIX: [&str; 8] = [
    ".md", ".sh", ".py", ".toml", ".json", ".txt", ".png", ".svg",
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

struct Res {
    header: Regex,
    link: Regex,
    line_suffix: Regex,
    parens: Regex,
    section: Regex,
}

impl Res {
    fn new() -> Option<Res> {
        Some(Res {
            header: Regex::new(
                r"(?m)^[^\S\n]*#[^\S\n]*AI-(?:related|doc):[^\S\n]*(.+)$|<!--\s*AI-(?:related|doc):\s*(.*?)\s*-->",
            )
            .ok()?,
            link: Regex::new(r"\[([^\]]+)\]\(([^)]+)\)").ok()?,
            line_suffix: Regex::new(r":\d+.*$").ok()?,
            parens: Regex::new(r"\s*\([^)]*\)").ok()?,
            section: Regex::new(r"\s*\[[^\]]*\]\s*$").ok()?,
        })
    }
}

/// The tracked corpus. A filesystem walk counted every git worktree checked out
/// under the repository, reporting one reference once per working copy, and its
/// skip list matched ".git" as a substring so all of .github/ was never read.
fn corpus(root: &Path) -> Option<Vec<String>> {
    let out = Command::new("git")
        .arg("-C")
        .arg(root)
        .arg("ls-files")
        .output()
        .ok()?;
    if !out.status.success() {
        return None;
    }
    let text = String::from_utf8_lossy(&out.stdout);
    Some(
        text.lines()
            .filter(|f| SCAN_EXT.iter().any(|e| f.ends_with(e)))
            .filter(|f| !f.contains(SKIP_SEGMENT))
            .filter(|f| {
                let base = f.rsplit('/').next().unwrap_or(f);
                !SKIP_BASENAME.contains(&base)
            })
            .map(|f| f.to_string())
            .collect(),
    )
}

/// The candidate roots a reference may be written against, in the order the
/// gate has always tried them: beside the file, one and two directories up,
/// the agent-pipe tree, and the repository root.
fn resolves(root: &Path, dir: &Path, rel: &str) -> bool {
    let rel = rel.trim_start_matches('/');
    let mut cands: Vec<PathBuf> = vec![dir.join(rel)];
    if let Some(p) = dir.parent() {
        cands.push(p.join(rel));
        if let Some(pp) = p.parent() {
            cands.push(pp.join(rel));
        }
    }
    cands.push(root.join("usr/lib/mios/agent-pipe").join(rel));
    cands.push(root.join(rel));
    cands.iter().any(|c| c.exists())
}

/// One AI-header token, reduced to the path it names.
fn clean(tok: &str, re: &Res) -> String {
    let t = tok.trim().trim_end_matches(',').trim();
    let t = re.line_suffix.replace(t, "");
    let t = re.parens.replace_all(t.trim(), "");
    // "file.toml [section]" is a file plus a section, not a path.
    re.section.replace(t.trim(), "").trim().to_string()
}

fn header_ref_is_path(t: &str) -> bool {
    if t.is_empty() || t.starts_with('[') || t.starts_with("@@") || t.starts_with('<') {
        return false;
    }
    if !(t.contains('/') || REF_SUFFIX.iter().any(|e| t.ends_with(e))) {
        return false;
    }
    if RUNTIME_PREFIX.iter().any(|p| t.starts_with(p)) {
        return false;
    }
    !URL_PREFIX.iter().any(|p| t.starts_with(p))
}

fn link_is_path(t: &str) -> bool {
    if t.is_empty() {
        return false;
    }
    if t.starts_with("http://")
        || t.starts_with("https://")
        || t.starts_with("mailto:")
        || t.starts_with('#')
        || t.starts_with("file://")
    {
        return false;
    }
    LINK_SUFFIX.iter().any(|e| t.ends_with(e)) || t.ends_with(".jpg") || t.contains('/')
}

fn glob_to_regex_str(pat: &str) -> String {
    let mut s = String::from("^");
    for c in pat.chars() {
        match c {
            '*' => s.push_str(".*"),
            '?' => s.push('.'),
            '.' | '+' | '(' | ')' | '[' | ']' | '{' | '}' | '^' | '$' | '|' | '\\' => {
                s.push('\\');
                s.push(c);
            }
            _ => s.push(c),
        }
    }
    s.push('$');
    s
}

fn is_allowlisted(t: &str, allowlist: &[String]) -> bool {
    let t_trim = t.trim_start_matches('/');
    for a in allowlist {
        let a_trim = a.trim_start_matches('/');
        if t == a || t_trim == a_trim {
            return true;
        }
        if (a.ends_with('/') || a.ends_with('-') || a.ends_with('_'))
            && (t.starts_with(a) || t_trim.starts_with(a_trim))
        {
            return true;
        }
        if a.contains('*') || a.contains('?') {
            let pat = glob_to_regex_str(a_trim);
            if let Ok(re) = Regex::new(&pat) {
                if re.is_match(t_trim) {
                    return true;
                }
            }
        }
    }
    false
}

pub fn check(root: &Path) -> Report {
    let Some(re) = Res::new() else {
        return cannot_run("the reference patterns did not compile");
    };
    let ssot = root.join(SSOT);
    let Ok(text) = std::fs::read_to_string(&ssot) else {
        return cannot_run(format!("{} is unreadable", ssot.display()));
    };
    let Ok(data) = text.parse::<toml::Value>() else {
        return cannot_run(format!("{} did not parse", ssot.display()));
    };
    let docs = data.get("docs").and_then(|d| d.as_table());
    let max_stale = docs
        .and_then(|d| d.get("max_stale_doc_refs"))
        .and_then(|v| v.as_integer())
        .unwrap_or(0);
    let allowlist: Vec<String> = docs
        .and_then(|d| d.get("ref_allowlist"))
        .and_then(|v| v.as_array())
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str())
                .map(|s| s.to_string())
                .collect()
        })
        .unwrap_or_default();

    let Some(files) = corpus(root) else {
        return cannot_run("git ls-files failed, so no file was scanned");
    };
    if files.is_empty() {
        return cannot_run("the tracked corpus is empty, so this check proved nothing");
    }

    let mut stale: Vec<String> = Vec::new();
    let mut unreadable: Vec<String> = Vec::new();
    for rel in &files {
        let fpath = root.join(rel);
        let dir = fpath.parent().unwrap_or(root).to_path_buf();
        let base = rel.rsplit('/').next().unwrap_or(rel);
        let body = match std::fs::read(&fpath) {
            Ok(b) => String::from_utf8_lossy(&b).into_owned(),
            // A read failure used to be swallowed, dropping the file from the
            // corpus while the check still reported success over the rest.
            Err(e) => {
                unreadable.push(format!("{rel}: {e}"));
                continue;
            }
        };
        for c in re.header.captures_iter(&body) {
            let raw = c
                .get(1)
                .or_else(|| c.get(2))
                .map(|m| m.as_str())
                .unwrap_or("");
            for tok in raw.split(',') {
                let t = clean(tok, &re);
                if !header_ref_is_path(&t) {
                    continue;
                }
                if is_allowlisted(&t, &allowlist) {
                    continue;
                }
                if !resolves(root, &dir, &t) {
                    stale.push(format!("{rel}: {t}"));
                }
            }
        }
        if base.ends_with(".md") {
            for c in re.link.captures_iter(&body) {
                let target = c
                    .get(2)
                    .map(|m| m.as_str())
                    .unwrap_or("")
                    .split('#')
                    .next()
                    .unwrap_or("")
                    .trim()
                    .to_string();
                if !link_is_path(&target) {
                    continue;
                }
                if is_allowlisted(&target, &allowlist) {
                    continue;
                }
                let rel_t = target.trim_start_matches('/');
                let mut ok = dir.join(rel_t).exists() || root.join(rel_t).exists();
                if !ok {
                    if let Some(p) = dir.parent() {
                        ok = p.join(rel_t).exists();
                    }
                }
                if !ok {
                    stale.push(format!("{rel}: {target}"));
                }
            }
        }
    }

    if !unreadable.is_empty() {
        let n = unreadable.len();
        unreadable.truncate(10);
        return report(
            false,
            String::new(),
            std::iter::once(format!(
                "{n} tracked file(s) unreadable, so their references went unchecked"
            ))
            .chain(unreadable)
            .collect(),
        );
    }

    let n = stale.len() as i64;
    if n > max_stale {
        let mut findings = vec![format!(
            "{n} stale reference(s) across {} tracked file(s) (max allowed {max_stale}):",
            files.len()
        )];
        // Every one: this list is the backlog someone has to work through, and a
        // silent cap hid 93 of 103 from the people deciding them (T-1074).
        findings.extend(stale);
        return report(false, String::new(), findings);
    }
    report(
        true,
        format!(
            "every path named in an AI header or a markdown link resolves across {} tracked file(s)",
            files.len()
        ),
        Vec::new(),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    /// A failed fixture must FAIL the test, never return early and be counted
    /// as a pass -- a silently skipped setup is the defect this suite hunts.
    fn repo() -> tempfile::TempDir {
        let d = match tempfile::tempdir() {
            Ok(d) => d,
            Err(e) => unreachable!("fixture tempdir: {e}"),
        };
        let r = d.path().to_path_buf();
        if let Err(e) = fs::create_dir_all(r.join("usr/share/mios")) {
            unreachable!("fixture mkdir: {e}");
        }
        if let Err(e) = fs::write(
            r.join(SSOT),
            "[docs]\nmax_stale_doc_refs = 0\nref_allowlist = [\"some/allowed-token/path.py\"]\n",
        ) {
            unreachable!("fixture ssot: {e}");
        }
        for a in [
            vec!["init", "-q"],
            vec!["config", "user.email", "g@example.invalid"],
            vec!["config", "user.name", "g"],
        ] {
            match Command::new("git").arg("-C").arg(&r).args(&a).output() {
                Ok(o) if o.status.success() => {}
                Ok(o) => unreachable!("fixture git {a:?}: {}", o.status),
                Err(e) => unreachable!("fixture git {a:?}: {e}"),
            }
        }
        d
    }

    /// Stage everything, and assert the index is non-empty afterwards: a
    /// corpus that silently stayed empty would make every arm below vacuous.
    fn track(r: &Path) {
        match Command::new("git")
            .arg("-C")
            .arg(r)
            .args(["add", "-A"])
            .output()
        {
            Ok(o) if o.status.success() => {}
            Ok(o) => unreachable!("fixture git add: {}", o.status),
            Err(e) => unreachable!("fixture git add: {e}"),
        }
        let files = corpus(r).unwrap_or_default();
        assert!(
            !files.is_empty(),
            "fixture staged nothing, so the arm would prove nothing"
        );
    }

    #[test]
    fn a_header_naming_a_missing_file_is_stale() {
        let d = repo();
        let r = d.path();
        let _ = fs::write(r.join("a.py"), "# AI-related: tools/does-not-exist.py\n");
        track(r);
        let rep = check(r);
        assert!(!rep.ok, "a missing target must be reported");
        assert!(
            rep.findings.iter().any(|f| f.contains("does-not-exist.py")),
            "the finding must name the missing target: {:?}",
            rep.findings
        );
    }

    #[test]
    fn every_stale_reference_is_listed_not_the_first_ten() {
        let d = repo();
        let r = d.path();
        for i in 0..25 {
            let _ = fs::write(
                r.join(format!("f{i}.py")),
                format!("# AI-related: tools/missing-{i}.py\n"),
            );
        }
        track(r);
        let rep = check(r);
        let listed = (0..25)
            .filter(|i| {
                rep.findings
                    .iter()
                    .any(|f| f.ends_with(&format!("missing-{i}.py")))
            })
            .count();
        assert_eq!(
            listed, 25,
            "a capped list hides the rest: {:?}",
            rep.findings
        );
    }

    #[test]
    fn a_header_naming_a_present_file_is_clean() {
        let d = repo();
        let r = d.path();
        let _ = fs::write(r.join("b.py"), "# AI-related: a.py\n");
        let _ = fs::write(r.join("a.py"), "x = 1\n");
        track(r);
        assert!(check(r).ok, "a resolving target must not be reported");
    }

    #[test]
    fn an_untracked_file_is_outside_the_corpus() {
        let d = repo();
        let r = d.path();
        let _ = fs::write(r.join("kept.py"), "# AI-related: kept.py\n");
        track(r);
        // Written AFTER `git add`, so it is on disk but not in the index. A
        // filesystem walk would read it; the tracked corpus must not.
        let _ = fs::write(r.join("stray.py"), "# AI-related: tools/absent.py\n");
        let rep = check(r);
        assert!(
            rep.ok,
            "an untracked file must not move the verdict: {:?}",
            rep.findings
        );
    }

    #[test]
    fn a_worktree_copy_does_not_multiply_a_finding() {
        let d = repo();
        let r = d.path();
        let _ = fs::write(r.join("a.py"), "# AI-related: tools/absent.py\n");
        track(r);
        let before = check(r).findings.len();
        // A second full copy of the tree under the repo, untracked, is exactly
        // what a `git worktree` looks like to a filesystem walk.
        let _ = fs::create_dir_all(r.join(".worktrees/lane"));
        let _ = fs::write(
            r.join(".worktrees/lane/a.py"),
            "# AI-related: tools/absent.py\n",
        );
        assert_eq!(
            before,
            check(r).findings.len(),
            "a working copy under the repo must not be counted again"
        );
    }

    #[test]
    fn the_allowlist_exempts_a_matching_token() {
        let d = repo();
        let r = d.path();
        let _ = fs::write(r.join("c.py"), "# AI-related: some/allowed-token/path.py\n");
        track(r);
        assert!(check(r).ok, "an allowlisted token must be exempt");
    }

    #[test]
    fn a_token_merely_containing_an_allowlist_entry_is_stale() {
        let d = repo();
        let r = d.path();
        let _ = fs::write(
            r.join("d.py"),
            "# AI-related: prefix/some/allowed-token/path.py/suffix.py\n",
        );
        track(r);
        let rep = check(r);
        assert!(
            !rep.ok && rep.findings.iter().any(|f| f.contains("prefix/some/allowed-token/path.py/suffix.py")),
            "a token merely containing an allowlist entry without matching must be reported stale: {:?}",
            rep.findings
        );
    }

    #[test]
    fn a_dot_github_file_is_inside_the_corpus() {
        let d = repo();
        let r = d.path();
        let _ = fs::create_dir_all(r.join(".github"));
        let _ = fs::write(
            r.join(".github/notes.md"),
            "[x](../tools/definitely-absent.py)\n",
        );
        track(r);
        let rep = check(r);
        assert!(
            !rep.ok && rep.findings.iter().any(|f| f.contains("definitely-absent")),
            "the old skip list matched '.git' as a substring and hid .github/: {:?}",
            rep.findings
        );
    }

    #[test]
    fn an_empty_corpus_cannot_run_rather_than_pass() {
        let d = repo();
        let r = d.path();
        // Deliberately NOT calling track(): the index stays empty.
        let rep = check(r);
        assert!(
            rep.could_not_run.is_some(),
            "an empty corpus must not pass: {:?}",
            rep.summary
        );
    }
}
