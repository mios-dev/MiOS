// AI-hint: Runtime port allocator -- derives every [ports] value from the [ports.categories] schema (base + index*stride) after layer merging, so operator/OEM overrides re-derive live. Mirrors mios_toml.derive_ports.
// AI-related: usr/lib/mios/mios_toml.py, usr/share/mios/mios.toml, tools/render-ports.py
use toml::Value;

/// Allocate every `[ports]` value from `[ports.categories]`, in place.
///
/// Must run AFTER all layers merge so a factory/OEM default in the vendor
/// mios.toml, an operator override in /etc/mios/mios.toml, and a user override
/// in ~/.config all feed the same derivation. `members` is ordered and the order
/// IS the numbering, so adding or removing a service reallocates the category
/// without a hand edit. `pinned` entries are protocol contracts (DNS/53) and are
/// written verbatim.
///
/// This OVERRIDES the flat `[ports]` table, which is only a rendered projection
/// kept for readability -- otherwise a stale vendor literal would silently beat
/// an operator who retargeted a category base.
pub fn derive_ports(merged: &mut Value) {
    let cats: Vec<(String, Value)> = match merged
        .get("ports")
        .and_then(|p| p.get("categories"))
        .and_then(|c| c.as_table())
    {
        Some(table) => table.iter().map(|(k, v)| (k.clone(), v.clone())).collect(),
        None => return,
    };

    let ports = match merged.get_mut("ports").and_then(|p| p.as_table_mut()) {
        Some(table) => table,
        None => return,
    };

    let mut names: Vec<&String> = cats.iter().map(|(k, _)| k).collect();
    names.sort();

    for cat_name in names {
        let cfg = match cats.iter().find(|(k, _)| k == cat_name).map(|(_, v)| v) {
            Some(v) => v,
            None => continue,
        };
        let base = cfg.get("base").and_then(|v| v.as_integer()).unwrap_or(0);
        let stride = cfg.get("stride").and_then(|v| v.as_integer()).unwrap_or(1);

        if let Some(members) = cfg.get("members").and_then(|v| v.as_array()) {
            for (idx, member) in members.iter().enumerate() {
                if let Some(name) = member.as_str() {
                    if !name.is_empty() {
                        ports.insert(name.to_string(), Value::Integer(base + idx as i64 * stride));
                    }
                }
            }
        }

        if let Some(pinned) = cfg.get("pinned").and_then(|v| v.as_table()) {
            for (name, value) in pinned {
                if let Some(n) = value.as_integer() {
                    ports.insert(name.clone(), Value::Integer(n));
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture() -> Value {
        toml::from_str(
            r#"
[ports]
agent_pipe = 1
hermes = 2
adguard_dns = 9999

[ports.categories.agent]
base = 8700
stride = 10
members = ["agent_pipe", "prefilter", "hermes"]

[ports.categories.edge]
base = 8050
stride = 1
members = ["adguard_ui"]
pinned = { adguard_dns = 53 }
"#,
        )
        .unwrap()
    }

    #[test]
    fn derives_from_base_and_stride() {
        let mut v = fixture();
        derive_ports(&mut v);
        let p = v.get("ports").unwrap();
        assert_eq!(p.get("agent_pipe").unwrap().as_integer(), Some(8700));
        assert_eq!(p.get("prefilter").unwrap().as_integer(), Some(8710));
        assert_eq!(p.get("hermes").unwrap().as_integer(), Some(8720));
        assert_eq!(p.get("adguard_ui").unwrap().as_integer(), Some(8050));
    }

    #[test]
    fn derivation_overrides_the_flat_table() {
        let mut v = fixture();
        derive_ports(&mut v);
        // flat table said 1 / 2 / 9999 -- the schema must win
        let p = v.get("ports").unwrap();
        assert_eq!(p.get("agent_pipe").unwrap().as_integer(), Some(8700));
        assert_eq!(p.get("adguard_dns").unwrap().as_integer(), Some(53));
    }

    #[test]
    fn retargeting_a_base_moves_the_whole_category() {
        let mut v = fixture();
        v["ports"]["categories"]["agent"]["base"] = Value::Integer(9200);
        derive_ports(&mut v);
        let p = v.get("ports").unwrap();
        assert_eq!(p.get("agent_pipe").unwrap().as_integer(), Some(9200));
        assert_eq!(p.get("prefilter").unwrap().as_integer(), Some(9210));
        assert_eq!(p.get("hermes").unwrap().as_integer(), Some(9220));
        // an untouched category must not move
        assert_eq!(p.get("adguard_ui").unwrap().as_integer(), Some(8050));
    }
}
