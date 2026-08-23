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

        // An alias carries the same value as its canonical key. Splitting the
        // tag out of image.sidecars.* for *_VERSION made MIOS_ADGUARD_VERSION
        // "latest" where globals.sh, generated from Python, has the full ref.
        for leg in get_aliases(&path) {
            exports.insert(leg, val_processed.clone());
        }
    }

    exports
}

#[cfg(test)]
mod tests {
    use super::*;

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
