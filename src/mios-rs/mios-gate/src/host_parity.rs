// AI-hint: Checks declared and tracked generator sources for non-portable fnmatch usage; unreadable inputs fail.
// AI-related: usr/share/mios/mios.toml, automation/98-drift-checks.sh

use crate::Report;
use std::collections::BTreeSet;
use std::path::{Component, Path};
use std::process::Command;

const CHECK: &str = "generator-host-parity";

fn inspect(root: &Path) -> Result<Report, String> {
    let policy = mios_resolver::resolve_projection(root).map_err(|e| e.to_string())?;
    let surfaces = policy
        .get("laws")
        .and_then(|v| v.get("projection_registry"))
        .and_then(|v| v.get("surfaces"))
        .and_then(|v| v.as_array())
        .filter(|v| !v.is_empty())
        .ok_or("SSOT projection registry surfaces are absent or empty")?;
    let mut sources = BTreeSet::new();
    for (index, surface) in surfaces.iter().enumerate() {
        let generator = surface
            .get("generator")
            .and_then(|v| v.as_str())
            .filter(|v| !v.trim().is_empty())
            .ok_or_else(|| format!("projection registry surface {index} has no generator"))?;
        if !Path::new(generator)
            .components()
            .all(|part| matches!(part, Component::Normal(_)))
        {
            return Err(format!(
                "generator path must stay inside the tree: {generator}"
            ));
        }
        sources.insert(generator.to_string());
    }
    let listed = Command::new("git")
        .arg("-C")
        .arg(root)
        .args(["ls-files", "-z", "--", "tools", "automation", "usr/libexec"])
        .output()
        .map_err(|e| format!("cannot enumerate tracked generators: {e}"))?;
    if !listed.status.success() {
        return Err(format!(
            "cannot enumerate tracked generators: {}",
            String::from_utf8_lossy(&listed.stderr).trim()
        ));
    }
    let listed = String::from_utf8(listed.stdout)
        .map_err(|e| format!("tracked generator paths are not UTF-8: {e}"))?;
    for path in listed.split('\0').filter(|path| !path.is_empty()) {
        let name = path.rsplit('/').next().unwrap_or(path);
        if name.starts_with("generate-")
            || name.starts_with("render-")
            || matches!(
                name,
                "mios-manual" | "mios-version-lint" | "mios_var_closure.py"
            )
        {
            sources.insert(path.to_string());
        }
    }
    let mut findings = Vec::new();
    for source in &sources {
        let text = std::fs::read_to_string(root.join(source))
            .map_err(|e| format!("cannot read generator {source}: {e}"))?;
        if text.contains("fnmatch.fnmatch(") {
            findings.push(format!(
                "{source} uses non-portable fnmatch.fnmatch instead of fnmatchcase"
            ));
        }
    }
    Ok(Report {
        check: CHECK.into(),
        ok: findings.is_empty(),
        could_not_run: None,
        summary: format!(
            "{} declared/discovered generator sources free of the non-portable fnmatch.fnmatch idiom",
            sources.len()
        ),
        findings,
    })
}

pub fn check(root: &Path) -> Report {
    inspect(root).unwrap_or_else(|error| Report {
        check: CHECK.into(),
        ok: false,
        could_not_run: Some(error),
        summary: String::new(),
        findings: Vec::new(),
    })
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
    use super::*;
    use std::fs;

    fn git(root: &Path, args: &[&str]) {
        let output = Command::new("git")
            .arg("-C")
            .arg(root)
            .args(args)
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    fn fixture() -> tempfile::TempDir {
        let tree = tempfile::tempdir().unwrap();
        git(tree.path(), &["init", "-q"]);
        git(tree.path(), &["config", "core.autocrlf", "false"]);
        fs::create_dir_all(tree.path().join("usr/share/mios")).unwrap();
        fs::create_dir_all(tree.path().join("tools/native/fixture/src")).unwrap();
        fs::write(
            tree.path().join("tools/native/fixture/src/main.rs"),
            "fn main() {}\n",
        )
        .unwrap();
        fs::write(
            tree.path().join("tools/render-fixture.py"),
            "print('fixture')\n",
        )
        .unwrap();
        fs::write(tree.path().join("usr/share/mios/mios.toml"),
            "[laws.projection_registry]\nsurfaces = [{ generator = 'tools/native/fixture/src/main.rs' }]\n").unwrap();
        git(tree.path(), &["add", "--", "tools/render-fixture.py"]);
        tree
    }

    #[test]
    fn native_and_legacy_sources_have_no_arbitrary_python_floor() {
        let tree = fixture();
        let report = check(tree.path());
        assert_eq!(report.code(), 0, "{}", report.render_text());
        assert!(report.summary.starts_with("2 declared/discovered"));
        fs::remove_file(tree.path().join("tools/render-fixture.py")).unwrap();
        git(
            tree.path(),
            &["rm", "--cached", "--", "tools/render-fixture.py"],
        );
        assert_eq!(check(tree.path()).code(), 0);
    }

    #[test]
    fn planted_idiom_is_named_and_source_bytes_are_preserved() {
        let tree = fixture();
        let path = tree.path().join("tools/render-fixture.py");
        let original = fs::read(&path).unwrap();
        let planted = b"import fnmatch\nfnmatch.fnmatch('x', 'x')\n";
        fs::write(&path, planted).unwrap();
        let report = check(tree.path());
        assert_eq!(report.code(), 1);
        assert!(report.findings[0].contains("tools/render-fixture.py"));
        assert_eq!(fs::read(&path).unwrap(), planted);
        fs::write(path, original).unwrap();
        assert_eq!(check(tree.path()).code(), 0);
    }

    #[test]
    fn listed_but_absent_or_invalid_utf8_sources_cannot_pass() {
        let tree = fixture();
        let path = tree.path().join("tools/render-fixture.py");
        fs::remove_file(&path).unwrap();
        let report = check(tree.path());
        assert_eq!(report.code(), 2);
        assert!(report
            .render_text()
            .contains("cannot read generator tools/render-fixture.py"));
        fs::write(path, [0xff]).unwrap();
        assert_eq!(check(tree.path()).code(), 2);
    }

    #[test]
    fn empty_registry_and_failed_git_enumeration_cannot_pass() {
        let tree = fixture();
        fs::write(
            tree.path().join("usr/share/mios/mios.toml"),
            "[laws.projection_registry]\nsurfaces = []\n",
        )
        .unwrap();
        let report = check(tree.path());
        assert_eq!(report.code(), 2);
        assert!(report.render_text().contains("absent or empty"));
        let tree = fixture();
        fs::remove_dir_all(tree.path().join(".git")).unwrap();
        let report = check(tree.path());
        assert_eq!(report.code(), 2);
        assert!(report
            .render_text()
            .contains("cannot enumerate tracked generators"));
    }

    #[test]
    fn layered_registry_requires_its_declared_sources() {
        let tree = fixture();
        fs::create_dir_all(tree.path().join("etc/mios")).unwrap();
        fs::write(
            tree.path().join("etc/mios/mios.toml"),
            "[laws.projection_registry]\nsurfaces = [{ generator = 'tools/native/missing.rs' }]\n",
        )
        .unwrap();
        let report = check(tree.path());
        assert_eq!(report.code(), 2);
        assert!(report.render_text().contains("tools/native/missing.rs"));
        fs::write(
            tree.path().join("tools/native/missing.rs"),
            "fn main() {}\n",
        )
        .unwrap();
        assert_eq!(check(tree.path()).code(), 0);
    }
}
