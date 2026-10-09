// AI-hint: Canonical export-map builder -- combines walked canonical keys with legacy aliases and applies WALK_MOSTLY_DEAD suppression.
// AI-related: tools/native/mios-ssot-walk, usr/lib/mios/mios_toml.py
use mios_ssot_walk::{is_emit_keep_var, is_excluded_section, is_mostly_dead_section};
use std::collections::BTreeMap;
use toml::Value;

use crate::aliases::get_aliases;
use crate::walk::{process_val, walk};

pub fn build_exports_map(merged: &Value, stack_offset: i64) -> BTreeMap<String, String> {
    build_exports(merged, stack_offset, false, None)
}

/// Emitted name -> the SSOT key path whose value it carries, traced with the
/// emitters' own precedence; a name whose value is computed has no entry.
pub fn export_sources(merged: &Value, stack_offset: i64) -> BTreeMap<String, String> {
    let mut sources = BTreeMap::new();
    let exports = build_exports(merged, stack_offset, false, Some(&mut sources));
    // A derived port carries the category value it was copied from verbatim.
    let origins = crate::ports::port_origins(merged);
    for source in sources.values_mut() {
        if let Some(origin) = origins.get(source.as_str()) {
            *source = origin.clone();
        }
    }
    // A value that is exactly one `${MIOS_X}` reference carries MIOS_X's value
    // whenever MIOS_X is set, so it is MIOS_X's declaration, not a second one.
    // An unset reference falls back to its default and stays its own.
    let traced = sources.clone();
    for (name, source) in sources.iter_mut() {
        let mut current = name.clone();
        for _ in 0..crate::expand::MAX_DEPTH {
            let Some(target) = exports
                .get(&current)
                .and_then(|v| crate::expand::sole_reference(v))
                .filter(|t| exports.get(*t).is_some_and(|v| !v.is_empty()))
            else {
                break;
            };
            current = target.to_string();
        }
        if &current != name {
            if let Some(origin) = traced.get(&current) {
                *source = origin.clone();
            }
        }
    }
    sources
}

/// Globals use the same naming/value engine. Only their historical projection
/// scope differs: comments, env overrides and the dead Guacamole aliases.
pub fn build_globals_map(merged: &Value, stack_offset: i64) -> BTreeMap<String, String> {
    let mut exports = build_exports(merged, stack_offset, true, None);
    exports.remove("MIOS_PORT_GUACAMOLE");
    exports.remove("MIOS_GUACAMOLE_PORT");
    exports
}

fn build_exports(
    merged: &Value,
    stack_offset: i64,
    globals: bool,
    mut sources: Option<&mut BTreeMap<String, String>>,
) -> BTreeMap<String, String> {
    let mut exports = BTreeMap::new();
    let mut legacy = BTreeMap::new();
    // An alias two declarations write has no single source: which one lands
    // follows table iteration order, which the toml crate's preserve_order
    // feature flips between builds of this same code. None keeps it
    // untraceable everywhere rather than traced differently per build.
    let mut legacy_source: BTreeMap<String, Option<String>> = BTreeMap::new();
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
        if globals && path.rsplit('.').next() == Some("comment") {
            continue;
        }
        let val_processed = process_val(&path, &val, stack_offset);
        if val_processed.is_empty() {
            continue;
        }

        // Projected by their own renderers, not exported as variables.
        if is_excluded_section(path.split('.').next().unwrap_or(&path)) {
            continue;
        }

        let canonical = crate::names::canonical_name(&path);

        let sec_name = path.split('.').next().unwrap_or(&path);
        if is_mostly_dead_section(sec_name) && !is_emit_keep_var(&canonical) {
            // Suppressed canonical key
        } else {
            if let Some(sources) = sources.as_deref_mut() {
                sources.insert(canonical.clone(), path.clone());
            }
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
            legacy_source
                .entry(leg.clone())
                .and_modify(|seen| {
                    if seen.as_deref() != Some(path.as_str()) {
                        *seen = None;
                    }
                })
                .or_insert_with(|| Some(path.clone()));
            legacy.insert(leg, v);
        }
    }
    // Canonical keys retain their own typed value even when another key once
    // used the same spelling as a compatibility alias (database vs OS account).
    for (name, value) in legacy {
        if let std::collections::btree_map::Entry::Vacant(slot) = exports.entry(name) {
            if let Some(sources) = sources.as_deref_mut() {
                if let Some(Some(path)) = legacy_source.get(slot.key()) {
                    sources.insert(slot.key().clone(), path.clone());
                }
            }
            slot.insert(value);
        }
    }

    // MIOS_COLOR_<name> for every palette entry ([colors] over the palette
    // table), never overriding a walked key -- mios_toml.emit_exports' setdefault.
    for (name, value) in crate::palette::resolve(merged) {
        let upper = name.to_uppercase();
        let key = if upper.starts_with("MIOS_COLOR_") {
            upper
        } else {
            format!("MIOS_COLOR_{}", upper)
        };
        exports.entry(sanitize(&key)).or_insert(value);
    }

    // [env] verbatim, last, so it wins -- mios_toml.emit_exports' env_tbl
    // merge (empty values skipped). Every emitter and runtime::get see it.
    if let Some(env_table) = merged
        .get("env")
        .and_then(|v| v.as_table())
        .filter(|_| !globals)
    {
        for (k, v) in env_table {
            let val = process_val(&format!("env.{k}"), v, stack_offset);
            if !val.is_empty() {
                if let Some(sources) = sources.as_deref_mut() {
                    sources.insert(sanitize(k), format!("env.{k}"));
                }
                exports.insert(sanitize(k), val);
            }
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
/// there is what makes an operator's pre-exported `MIOS_PORTS_AGENT_PIPE`
/// propagate into `MIOS_AI_ENDPOINT`. Baking in the shared builder would take
/// that property away from both generated globals files.
///
/// systemd `EnvironmentFile=` and podman `--env-file` have no such expansion,
/// so an emitted `MIOS_AI_ENDPOINT=http://localhost:${MIOS_PORTS_AGENT_PIPE}/v1`
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
    fn sources_trace_every_spelling_to_its_declaration() {
        let val: Value = toml::from_str(
            r#"
[converge]
memory_dir = "/var/lib/x"

[ports]
radosgw = 8470
pgvector_internal = 1
agent_pipe = 1
llm_heavy = 1

[ports.categories.data]
base = 8600
stride = 10
members = ["pgvector"]
pinned = { pgvector_internal = 5432 }

[ports.categories.agent]
base = 8700
stride = 10
members = ["agent_pipe", "llm_heavy"]

[image.sidecars]
sglang = "docker.io/lmsysorg/sglang:latest"

[images.heavy.Image]
Image = "${MIOS_SGLANG_IMAGE:-docker.io/lmsysorg/sglang:latest}"

[dispatch]
hint = "http://${MIOS_PORTS_LLM_HEAVY}/v1"

[pgvector]
user = "database"

[services.pgvector]
user = "os-account"

[env]
MIOS_OVERRIDDEN = "x"

[other]
overridden = "y"
"#,
        )
        .unwrap();
        let mut merged = val;
        crate::ports::derive_ports(&mut merged);
        let s = export_sources(&merged, 0);
        // One declaration, three spellings.
        assert_eq!(s["MIOS_CONVERGE_MEMORY_DIR"], "converge.memory_dir");
        assert_eq!(s["MIOS_CONV_MEMORY_DIR"], "converge.memory_dir");
        assert_eq!(s["MIOS_PORTS_RADOSGW"], "ports.radosgw");
        assert_eq!(s["MIOS_RADOSGW_PORT"], "ports.radosgw");
        // A pinned or offset-0 port IS its category key.
        assert_eq!(
            s["MIOS_PORT_PGVECTOR_INTERNAL"],
            "ports.categories.data.pinned.pgvector_internal"
        );
        assert_eq!(s["MIOS_PORTS_AGENT_PIPE"], "ports.categories.agent.base");
        // A computed member keeps its own declaration.
        assert_eq!(s["MIOS_PORTS_LLM_HEAVY"], "ports.llm_heavy");
        // A whole-value reference is the referenced declaration...
        assert_eq!(s["MIOS_IMAGES_HEAVY_IMAGE_IMAGE"], "image.sidecars.sglang");
        // ...a composition is its own.
        assert_eq!(s["MIOS_DISPATCH_HINT"], "dispatch.hint");
        // A canonical key keeps its value against another key's alias.
        assert_eq!(s["MIOS_PGVECTOR_USER"], "pgvector.user");
        assert_eq!(s["MIOS_SERVICES_PGVECTOR_USER"], "services.pgvector.user");
        // [env] wins, and says so.
        assert_eq!(s["MIOS_OVERRIDDEN"], "env.MIOS_OVERRIDDEN");
        // Two declarations writing one alias: no single source, in any build.
        let two: Value =
            toml::from_str("[urls]\nbootstrap_repo = \"u\"\n[bootstrap]\nbootstrap_repo = \"u\"\n")
                .unwrap();
        let s = export_sources(&two, 0);
        assert!(!s.contains_key("MIOS_BOOTSTRAP_REPO_URL"), "{s:?}");
        assert_eq!(s["MIOS_URLS_BOOTSTRAP_REPO"], "urls.bootstrap_repo");
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

#[cfg(test)]
mod canonical_export_tests {
    #[test]
    fn signing_build_inputs_survive_security_suppression() {
        let data: toml::Value = "[security.sigstore]\ncosign_version='fixture-pin'\ncosign_release_url='https://example.invalid/releases'\nprivate_setting='must-not-export'\n".parse().unwrap();
        for exports in [
            super::build_exports_map(&data, 0),
            super::build_globals_map(&data, 0),
        ] {
            assert_eq!(
                exports["MIOS_SECURITY_SIGSTORE_COSIGN_VERSION"],
                "fixture-pin"
            );
            assert_eq!(
                exports["MIOS_SECURITY_SIGSTORE_COSIGN_RELEASE_URL"],
                "https://example.invalid/releases"
            );
            assert!(!exports.contains_key("MIOS_SECURITY_SIGSTORE_PRIVATE_SETTING"));
        }
    }

    #[test]
    fn service_account_alias_cannot_replace_database_username() {
        let data: toml::Value =
            "[pgvector]\nuser='database'\n[services.pgvector]\nuser='os-account'\n"
                .parse()
                .unwrap();
        for exports in [
            super::build_exports_map(&data, 0),
            super::build_globals_map(&data, 0),
        ] {
            assert_eq!(exports["MIOS_PGVECTOR_USER"], "database");
            assert_eq!(exports["MIOS_PG_USER"], "database");
            assert_eq!(exports["MIOS_SERVICES_PGVECTOR_USER"], "os-account");
        }
    }
}
