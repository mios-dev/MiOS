// AI-hint: JSON binding -- emits the merged SSOT table plus the resolved export map for the Python resolver shim to consume.
// AI-related: usr/lib/mios/mios_toml.py
use serde_json::{json, Value as JsonValue};
use toml::Value;

use crate::emit::build_exports_map;

pub fn emit_json(merged: &Value, stack_offset: i32) -> String {
    let exports = build_exports_map(merged, stack_offset);
    let merged_json: JsonValue = serde_json::to_value(merged).unwrap_or(json!({}));

    let res = json!({
        "merged": merged_json,
        "exports": exports,
    });

    serde_json::to_string_pretty(&res).unwrap_or_else(|_| "{}".to_string()) + "\n"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_emit_json() {
        let val: Value = toml::from_str(r#"
[identity]
role = "mini"
"#).unwrap();
        let j_str = emit_json(&val, 0);
        let parsed: JsonValue = serde_json::from_str(&j_str).unwrap();
        assert!(parsed.get("merged").is_some());
        assert!(parsed.get("exports").is_some());
    }
}
