// AI-hint: Canonical export-map builder -- combines walked canonical keys with legacy aliases and applies WALK_MOSTLY_DEAD suppression.
// AI-related: tools/native/mios-ssot-walk, usr/lib/mios/mios_toml.py
use mios_ssot_walk::{is_emit_keep_var, is_excluded_section, is_mostly_dead_section};
use std::collections::BTreeMap;
use toml::Value;

use crate::aliases::get_aliases;
use crate::walk::{process_val, walk};

pub fn build_exports_map(merged: &Value, stack_offset: i64) -> BTreeMap<String, String> {
    let mut exports = BTreeMap::new();
    let all_pairs = walk(merged);

    // Any character that is not [A-Za-z0-9_] becomes `_`, matching
    // render-globals.py's _UNSAFE_NAME_RE. Replacing only `.`, `-` and `/` left
    // keys like ..._MIOS_LLM_WORKER@ that the Python resolver renders as
    // ..._MIOS_LLM_WORKER_, and neither shell nor PowerShell accepts the first.
    fn sanitize(name: &str) -> String {
        name.chars()
            .map(|c| {
                if c.is_ascii_alphanumeric() || c == '_' {
                    c
                } else {
                    '_'
                }
            })
            .collect()
    }

    for (path, val) in all_pairs {
        let val_processed = process_val(&path, &val, stack_offset);
        if val_processed.is_empty() {
            continue;
        }

        // Projected by their own renderers, not exported as variables.
        if is_excluded_section(path.split('.').next().unwrap_or(&path)) {
            continue;
        }

        let cbody = if let Some(rest) = path.strip_prefix("converge.") {
            format!("CONV_{}", sanitize(&rest.to_uppercase()))
        } else {
            sanitize(&path.to_uppercase())
        };

        let canonical = if cbody.starts_with("MIOS_") {
            cbody
        } else {
            format!("MIOS_{}", cbody)
        };

        let sec_name = path.split('.').next().unwrap_or(&path);
        if is_mostly_dead_section(sec_name) && !is_emit_keep_var(&canonical) {
            // Suppressed canonical key
        } else {
            exports.insert(canonical, val_processed.clone());
        }

        // An alias carries its canonical key's value, EXCEPT that
        // image.sidecars.*_VERSION carries only the tag.
        //
        // This split was removed once, on the grounds that it made
        // MIOS_ADGUARD_VERSION "latest" where globals.sh carried the full ref.
        // That traded a cosmetic disagreement on 22 unconsumed keys for a wrong
        // value on the one that IS consumed: automation/36-ceph-k3s.sh does
        // K3S_TAG="${MIOS_K3S_VERSION:-}" and then ${K3S_TAG/-k3s/+k3s}.
        // common.sh sources userenv.sh BEFORE globals.sh and globals.sh guards
        // its assignments, so the value comes from userenv.sh -- whose preferred
        // tier is this binary. Without the split a bake gets
        // docker.io/rancher/k3s:v1.36.3+k3s1 as a release tag (T-1065).
        for leg in get_aliases(&path) {
            let v = if leg.ends_with("_VERSION") && path.starts_with("image.sidecars.") {
                match val_processed.rsplit_once(':') {
                    Some((_, tag)) => tag.to_string(),
                    None => "latest".to_string(),
                }
            } else {
                val_processed.clone()
            };
            exports.insert(leg, v);
        }
    }

    exports
}

/// Resolve `${MIOS_*}` that one emitted value makes to another.
///
/// Called by the emitters whose consumer CANNOT expand -- `emit_json` (the
/// resolved-environment view) and `emit_install_env` (systemd
/// `EnvironmentFile=` and podman `--env-file`). It is deliberately NOT called
/// by `build_exports_map`, because `emit_shell` and `emit_ps` render into bash
/// and PowerShell, which expand at source time: keeping the reference live
/// there is what makes an operator's pre-exported `MIOS_PORT_AGENT_PIPE`
/// propagate into `MIOS_AI_ENDPOINT`. Baking in the shared builder would take
/// that property away from both generated globals files.
///
/// systemd `EnvironmentFile=` and podman `--env-file` have no such expansion,
/// so an emitted `MIOS_AI_ENDPOINT=http://localhost:${MIOS_PORT_AGENT_PIPE}/v1`
/// means two different things depending on who reads it. It is also why
/// `system-sync-env.sh` DROPPED that variable rather than emitting it: its
/// filter rejects any value containing `$` (T-1060).
///
/// Expansion reads a snapshot, so the result does not depend on map order, and
/// a name that resolves to nothing is left verbatim rather than blanked -- the
/// caller can then report it instead of shipping an empty string.
pub fn resolve_cross_references(exports: &mut BTreeMap<String, String>) {
    let snapshot = exports.clone();
    for value in exports.values_mut() {
        if value.contains("${") {
            *value = crate::expand::expand(value, &snapshot).text;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The tag-split has been removed once already, on cosmetic grounds, and
    /// that broke the one consumer: automation/36-ceph-k3s.sh computes
    /// K3S_TAG="${MIOS_K3S_VERSION:-}" and then ${K3S_TAG/-k3s/+k3s}. With the
    /// full ref it produces docker.io/rancher/k3s:v1.36.3+k3s1 as a release tag.
    #[test]
    fn sidecar_version_alias_carries_only_the_tag() {
        let val: Value = toml::from_str(
            r#"
[image.sidecars]
k3s = "docker.io/rancher/k3s:v1.36.3-k3s1"
"#,
        )
        .unwrap();
        let e = build_exports_map(&val, 0);
        assert_eq!(
            e.get("MIOS_K3S_VERSION").map(String::as_str),
            Some("v1.36.3-k3s1"),
            "the _VERSION alias must be the tag, not the image ref"
        );
        assert_eq!(
            e.get("MIOS_K3S_IMAGE").map(String::as_str),
            Some("docker.io/rancher/k3s:v1.36.3-k3s1"),
            "the _IMAGE alias keeps the full ref, so the two names stay distinct"
        );
    }

    /// An untagged ref has no tag to split; "latest" is what it resolves to.
    #[test]
    fn sidecar_version_without_a_tag_is_latest() {
        let val: Value = toml::from_str(
            r#"
[image.sidecars]
thing = "docker.io/library/thing"
"#,
        )
        .unwrap();
        let e = build_exports_map(&val, 0);
        assert_eq!(
            e.get("MIOS_THING_VERSION").map(String::as_str),
            Some("latest")
        );
    }

    #[test]
    fn test_mostly_dead_suppression() {
        let val: Value = toml::from_str(
            r#"
[ai]
endpoint = "http://localhost:8000"
random_setting = "test"
"#,
        )
        .unwrap();

        let exports = build_exports_map(&val, 0);
        assert!(exports.contains_key("MIOS_AI_ENDPOINT")); // In WALK_EMIT_KEEP
        assert!(!exports.contains_key("MIOS_AI_RANDOM_SETTING")); // Suppressed!
    }
}
