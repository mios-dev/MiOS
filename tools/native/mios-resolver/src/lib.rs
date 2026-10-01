// AI-hint: Crate root for mios-resolver -- the native layered mios.toml resolver that subsumes mios_toml.py / userenv.sh / globals.ps1.
// AI-related: usr/lib/mios/mios_toml.py, usr/lib/mios/userenv.sh, tools/native/mios-ssot-walk
pub mod aliases;
pub mod db_overlay;
pub mod emit;
pub mod emit_install_env;
pub mod emit_json;
pub mod emit_ps;
pub mod emit_shell;
pub mod error;
pub mod expand;
pub mod layers;
pub mod merge;
pub mod model;
pub mod palette;
pub mod ports;
pub mod walk;

use crate::error::ResolverError;
use crate::model::MiosModel;
use std::collections::BTreeMap;
use std::path::Path;
use toml::Value;

pub fn load_model(root_dir: Option<&Path>) -> Result<MiosModel, ResolverError> {
    let fig = layers::create_figment(root_dir);
    fig.extract::<MiosModel>()
        .map_err(|e| ResolverError::TypeShape { msg: e.to_string() })
}

/// stack_offset = [ports].stack_id * 10000 -- the multi-stack port shift the
/// Python resolver applies in process_val(). Absent stack_id means no shift.
pub fn stack_offset_of(merged: &Value) -> i64 {
    merged
        .get("ports")
        .and_then(|p| p.get("stack_id"))
        .and_then(|v| {
            v.as_integer()
                .or_else(|| v.as_str().and_then(|s| s.parse::<i64>().ok()))
        })
        .map(|id| id * 10000)
        .unwrap_or(0)
}

/// The merged SSOT every emitter renders: all six tiers, the DB overlay when
/// active or forced, and [ports] derived from [ports.categories] last so an
/// override in any tier re-derives.
pub fn resolve_merged(root_dir: Option<&Path>, db_overlay: bool) -> Result<Value, ResolverError> {
    let mut merged = layers::create_figment(root_dir)
        .extract::<Value>()
        .map_err(|e| ResolverError::TypeShape { msg: e.to_string() })?;
    db_overlay::maybe_apply_db_overlay(&mut merged, db_overlay);
    ports::derive_ports(&mut merged);
    Ok(merged)
}

/// The resolved MIOS_* environment, ${MIOS_*} references expanded -- the same
/// values `mios-resolver --emit=json` prints. Native programs read the SSOT
/// through this at run time instead of carrying their own copies of it.
pub fn resolve_env(root_dir: Option<&Path>) -> Result<BTreeMap<String, String>, ResolverError> {
    let merged = resolve_merged(root_dir, false)?;
    let mut exports = emit::build_exports_map(&merged, stack_offset_of(&merged));
    emit::resolve_cross_references(&mut exports);
    Ok(exports)
}

/// Run-time SSOT lookup for native programs: the process environment (a
/// unit's Environment=, the operator) wins, then the resolved six-tier
/// mios.toml. A name neither provides is an error that names it -- callers
/// never substitute a compiled-in value.
pub mod runtime {
    use crate::error::ResolverError;
    use std::collections::BTreeMap;
    use std::sync::OnceLock;

    static RESOLVED: OnceLock<BTreeMap<String, String>> = OnceLock::new();

    /// `name` from `env`, else from `resolved`; empty strings count as unset.
    pub fn lookup_in(
        name: &str,
        env: impl Fn(&str) -> Option<String>,
        resolved: &BTreeMap<String, String>,
    ) -> Option<String> {
        env(name)
            .filter(|v| !v.is_empty())
            .or_else(|| resolved.get(name).filter(|v| !v.is_empty()).cloned())
    }

    fn resolved() -> &'static BTreeMap<String, String> {
        RESOLVED.get_or_init(|| crate::resolve_env(None).unwrap_or_default())
    }

    pub fn get(name: &str) -> Option<String> {
        lookup_in(name, |n| std::env::var(n).ok(), resolved())
    }

    fn missing(name: &str) -> ResolverError {
        ResolverError::TypeShape {
            msg: format!("{name} is unset and the layered mios.toml does not resolve it"),
        }
    }

    pub fn require(name: &str) -> Result<String, ResolverError> {
        get(name).ok_or_else(|| missing(name))
    }

    pub fn require_port(name: &str) -> Result<u16, ResolverError> {
        let raw = require(name)?;
        raw.parse::<u16>()
            .map_err(|_| ResolverError::InvalidPortValue {
                key: name.to_string(),
                value: raw,
            })
    }

    /// Replace every `${MIOS_*}` in `text` through `lookup`; an unresolved
    /// reference is an error rather than an empty string.
    pub fn expand_refs_with(
        text: &str,
        lookup: impl Fn(&str) -> Option<String>,
    ) -> Result<String, ResolverError> {
        let mut out = String::with_capacity(text.len());
        let mut rest = text;
        while let Some(start) = rest.find("${") {
            out.push_str(&rest[..start]);
            let after = &rest[start + 2..];
            let Some(end) = after.find('}') else {
                out.push_str(&rest[start..]);
                return Ok(out);
            };
            let name = &after[..end];
            out.push_str(&lookup(name).ok_or_else(|| missing(name))?);
            rest = &after[end + 1..];
        }
        out.push_str(rest);
        Ok(out)
    }

    pub fn expand_refs(text: &str) -> Result<String, ResolverError> {
        expand_refs_with(text, get)
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        fn ssot() -> BTreeMap<String, String> {
            BTreeMap::from([("MIOS_PORT_NODE".to_string(), "8650".to_string())])
        }

        #[test]
        fn environment_wins_over_the_resolved_ssot() {
            let env = |_: &str| Some("9100".to_string());
            assert_eq!(
                lookup_in("MIOS_PORT_NODE", env, &ssot()).as_deref(),
                Some("9100")
            );
        }

        #[test]
        fn empty_environment_falls_back_to_the_ssot() {
            let env = |_: &str| Some(String::new());
            assert_eq!(
                lookup_in("MIOS_PORT_NODE", env, &ssot()).as_deref(),
                Some("8650")
            );
        }

        #[test]
        fn a_name_nothing_provides_is_none() {
            assert_eq!(lookup_in("MIOS_PORT_MISSING", |_| None, &ssot()), None);
        }

        #[test]
        fn references_expand_and_unresolved_ones_fail() {
            let look = |n: &str| (n == "MIOS_PORT_A").then(|| "8900".to_string());
            assert_eq!(
                expand_refs_with("http://localhost:${MIOS_PORT_A}/", look).unwrap(),
                "http://localhost:8900/"
            );
            assert!(expand_refs_with("http://localhost:${MIOS_PORT_B}/", look).is_err());
            assert_eq!(expand_refs_with("no refs", look).unwrap(), "no refs");
        }
    }
}
