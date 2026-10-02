// AI-hint: Asserts every MiOS image pinned to the podman machine OS uses its newest STABLE tag, from registry facts fetched by tools/fetch-image-facts.sh; all three pins must agree, the container pin through [image].machine_os_mirror when one is set.
// AI-related: tools/fetch-image-facts.sh, usr/share/mios/mios.toml, .github/workflows/mios-ci.yml

use crate::Report;
use std::path::Path;

const CHECK: &str = "image-freshness";
const SSOT: &str = "usr/share/mios/mios.toml";
const FACTS: &str = ".artifacts/image-facts.json";

fn cannot_run(why: impl Into<String>) -> Report {
    Report {
        check: CHECK.to_string(),
        ok: false,
        could_not_run: Some(why.into()),
        summary: String::new(),
        findings: Vec::new(),
    }
}

/// "6.1" -> [6, 1]; tags that are not dotted numbers (next, 6.1-amd64) are not releases.
fn version(tag: &str) -> Option<Vec<u64>> {
    tag.split('.').map(|p| p.parse::<u64>().ok()).collect()
}

/// The highest release tag whose stream is "stable".
fn newest_stable(streams: &serde_json::Map<String, serde_json::Value>) -> Option<String> {
    streams
        .iter()
        .filter(|(_, s)| s.as_str() == Some("stable"))
        .filter_map(|(t, _)| version(t).map(|v| (v, t.clone())))
        .max()
        .map(|(_, t)| t)
}

fn str_at<'a>(v: &'a toml::Value, path: &[&str]) -> Option<&'a str> {
    path.iter().try_fold(v, |acc, k| acc.get(*k))?.as_str()
}

pub fn check(root: &Path) -> Report {
    let Ok(text) = std::fs::read_to_string(root.join(SSOT)) else {
        return cannot_run(format!("{SSOT} could not be read"));
    };
    let Ok(ssot) = text.parse::<toml::Value>() else {
        return cannot_run(format!("{SSOT} did not parse"));
    };
    let (Some(repo), Some(tag)) = (
        str_at(&ssot, &["image", "machine_os_repo"]),
        str_at(&ssot, &["image", "machine_os_tag"]),
    ) else {
        return cannot_run("[image].machine_os_repo/machine_os_tag are not set");
    };
    let Ok(raw) = std::fs::read_to_string(root.join(FACTS)) else {
        return cannot_run(format!(
            "{FACTS} is absent -- run tools/fetch-image-facts.sh; no registry facts is not a pass"
        ));
    };
    let Ok(facts) = serde_json::from_str::<serde_json::Value>(&raw) else {
        return cannot_run(format!("{FACTS} is not JSON"));
    };
    let Some(streams) = facts.get(repo).and_then(|v| v.as_object()) else {
        return cannot_run(format!("{FACTS} holds no tags for {repo}"));
    };
    let Some(want) = newest_stable(streams) else {
        return cannot_run(format!("{FACTS} lists no stable release of {repo}"));
    };

    let mut findings = Vec::new();
    if tag != want {
        findings.push(format!(
            "[image].machine_os_tag is {tag} but the newest stable {repo} is {want}"
        ));
    }
    let full = format!("{repo}:{want}");
    // MiOS-DEV boots the upstream index (it carries the disk images); the
    // container pin may name the container-only mirror of the same tag.
    let mirror = str_at(&ssot, &["image", "machine_os_mirror"])
        .map_or_else(|| full.clone(), |m| format!("{m}:{want}"));
    for (key, path, expect) in [
        (
            "[bootstrap.dev_vm].base_image",
            &["bootstrap", "dev_vm", "base_image"][..],
            &full,
        ),
        ("[ci.fedora].image", &["ci", "fedora", "image"][..], &mirror),
    ] {
        match str_at(&ssot, path) {
            Some(v) if v == expect => {}
            Some(v) => findings.push(format!("{key} is {v}, not {expect}")),
            None => findings.push(format!("{key} is not set")),
        }
    }

    Report {
        check: CHECK.to_string(),
        ok: findings.is_empty(),
        could_not_run: None,
        summary: format!("every machine-os pin is {want}, the newest stable release ({full}; container pin {mirror})"),
        findings,
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    fn tree(tag: &str, facts: &str) -> tempfile::TempDir {
        let d = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(d.path().join("usr/share/mios")).unwrap();
        std::fs::create_dir_all(d.path().join(".artifacts")).unwrap();
        let img = format!("quay.io/podman/machine-os:{tag}");
        std::fs::write(
            d.path().join(SSOT),
            format!(
                "[image]\nmachine_os_repo = \"quay.io/podman/machine-os\"\nmachine_os_tag = \"{tag}\"\n\
                 [bootstrap.dev_vm]\nbase_image = \"{img}\"\n[ci.fedora]\nimage = \"{img}\"\n"
            ),
        )
        .unwrap();
        std::fs::write(d.path().join(FACTS), facts).unwrap();
        d
    }

    const FACTS_NEXT: &str = r#"{"quay.io/podman/machine-os":{"6.0":"stable","6.1":"stable","6.2":"next","next":"next"}}"#;
    const FACTS_STABLE: &str =
        r#"{"quay.io/podman/machine-os":{"6.0":"stable","6.1":"stable","6.2":"stable"}}"#;

    #[test]
    fn a_prerelease_newer_tag_does_not_count() {
        assert!(check(tree("6.1", FACTS_NEXT).path()).ok);
    }

    #[test]
    fn a_newer_stable_tag_fails_every_pin() {
        let r = check(tree("6.1", FACTS_STABLE).path());
        assert!(!r.ok);
        assert_eq!(r.findings.len(), 3, "{:?}", r.findings);
    }

    #[test]
    fn versions_compare_numerically() {
        let f = r#"{"quay.io/podman/machine-os":{"6.9":"stable","6.10":"stable"}}"#;
        let r = check(tree("6.9", f).path());
        assert!(
            r.findings.iter().any(|x| x.contains("6.10")),
            "{:?}",
            r.findings
        );
    }

    fn with_mirror(tag: &str, ci_image: &str) -> tempfile::TempDir {
        let d = tree(tag, FACTS_NEXT);
        let p = d.path().join(SSOT);
        let text = std::fs::read_to_string(&p).unwrap();
        let text = text
            .replace(
                "[image]\n",
                "[image]\nmachine_os_mirror = \"ghcr.io/mios-dev/machine-os\"\n",
            )
            .replace(
                &format!("[ci.fedora]\nimage = \"quay.io/podman/machine-os:{tag}\""),
                &format!("[ci.fedora]\nimage = \"{ci_image}\""),
            );
        std::fs::write(&p, text).unwrap();
        d
    }

    #[test]
    fn the_container_pin_names_the_mirror_when_one_is_set() {
        let r = check(with_mirror("6.1", "ghcr.io/mios-dev/machine-os:6.1").path());
        assert!(r.ok, "{:?}", r.findings);
    }

    #[test]
    fn with_a_mirror_the_upstream_container_pin_fails() {
        let r = check(with_mirror("6.1", "quay.io/podman/machine-os:6.1").path());
        assert_eq!(r.findings.len(), 1, "{:?}", r.findings);
        assert!(r.findings[0].contains("ghcr.io/mios-dev/machine-os:6.1"));
    }

    #[test]
    fn a_stale_mirror_tag_fails() {
        let r = check(with_mirror("6.1", "ghcr.io/mios-dev/machine-os:6.0").path());
        assert!(!r.ok);
    }

    #[test]
    fn missing_facts_cannot_pass() {
        let d = tree("6.1", FACTS_NEXT);
        std::fs::remove_file(d.path().join(FACTS)).unwrap();
        assert!(check(d.path()).could_not_run.is_some());
    }
}
