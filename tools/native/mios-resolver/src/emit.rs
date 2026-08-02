// AI-hint: Canonical export-map builder -- combines walked canonical keys with legacy aliases and applies WALK_MOSTLY_DEAD suppression.
// AI-related: tools/native/mios-ssot-walk, usr/lib/mios/mios_toml.py
use mios_ssot_walk::{is_emit_keep_var, is_mostly_dead_section};
use std::collections::BTreeMap;
use toml::Value;

use crate::aliases::get_aliases;
use crate::walk::{process_val, walk_table};

pub fn build_exports_map(merged: &Value, stack_offset: i32) -> BTreeMap<String, String> {
    let mut exports = BTreeMap::new();
    let all_pairs = walk_table(merged, "");

    for (path, val) in all_pairs {
        let val_processed = process_val(&path, &val, stack_offset);
        if val_processed.is_empty() {
            continue;
        }

        let cbody = if let Some(rest) = path.strip_prefix("converge.") {
            format!(
                "CONV_{}",
                rest.to_uppercase().replace(['.', '-'], "_")
            )
        } else {
            path.to_uppercase().replace(['.', '-'], "_")
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

        for leg in get_aliases(&path) {
            if leg.ends_with("_VERSION") && path.starts_with("image.sidecars.") {
                let ver = if let Some((_, tag)) = val_processed.rsplit_once(':') {
                    tag.to_string()
                } else {
                    "latest".to_string()
                };
                exports.insert(leg, ver);
            } else {
                exports.insert(leg, val_processed.clone());
            }
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
