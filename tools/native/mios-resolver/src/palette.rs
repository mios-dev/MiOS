// AI-hint: Palette resolution -- layers mios.toml [colors] over the semantic and ansi defaults to produce the MIOS_COLOR_* map.
// AI-related: usr/share/mios/mios.toml, usr/libexec/mios/mios-theme-render
use std::collections::BTreeMap;
use toml::Value;

pub fn palette_defaults() -> BTreeMap<&'static str, &'static str> {
    let mut map = BTreeMap::new();
    map.insert("bg", "#282262");
    map.insert("fg", "#E7DFD3");
    map.insert("accent", "#1A407F");
    map.insert("cursor", "#F35C15");
    map.insert("success", "#3E7765");
    map.insert("warning", "#F35C15");
    map.insert("error", "#DC271B");
    map.insert("info", "#1A407F");
    map.insert("muted", "#948E8E");
    map.insert("subtle", "#B7C9D7");
    map.insert("earth", "#734F39");
    map.insert("silver", "#E0E0E0");

    map.insert("ansi_0_black", "#282262");
    map.insert("ansi_1_red", "#DC271B");
    map.insert("ansi_2_green", "#3E7765");
    map.insert("ansi_3_yellow", "#F35C15");
    map.insert("ansi_4_blue", "#1A407F");
    map.insert("ansi_5_magenta", "#734F39");
    map.insert("ansi_6_cyan", "#B7C9D7");
    map.insert("ansi_7_white", "#E7DFD3");
    map.insert("ansi_8_bright_black", "#948E8E");
    map.insert("ansi_9_bright_red", "#FF6B5C");
    map.insert("ansi_10_bright_green", "#5FAA8E");
    map.insert("ansi_11_bright_yellow", "#FF8540");
    map.insert("ansi_12_bright_blue", "#3D6BA8");
    map.insert("ansi_13_bright_magenta", "#9D7660");
    map.insert("ansi_14_bright_cyan", "#E0E0E0");
    map.insert("ansi_15_bright_white", "#FFFFFF");
    map
}

pub fn resolve(merged: &Value) -> BTreeMap<String, String> {
    let mut palette = BTreeMap::new();
    let defaults = palette_defaults();

    let colors_table = merged.get("colors").and_then(|v| v.as_table());

    for (k, default_val) in defaults {
        let val = colors_table
            .and_then(|t| t.get(k))
            .and_then(|v| v.as_str())
            .unwrap_or(default_val);
        palette.insert(k.to_string(), val.to_string());
    }

    palette
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_palette_defaults() {
        let empty: Value = toml::from_str("").unwrap();
        let p = resolve(&empty);
        assert_eq!(p.get("bg").unwrap(), "#282262");
        assert_eq!(p.get("fg").unwrap(), "#E7DFD3");
        assert_eq!(p.get("ansi_15_bright_white").unwrap(), "#FFFFFF");
    }

    #[test]
    fn test_palette_override() {
        let val: Value = toml::from_str(r##"
[colors]
bg = "#000000"
accent = "#FF0000"
"##).unwrap();

        let p = resolve(&val);
        assert_eq!(p.get("bg").unwrap(), "#000000");
        assert_eq!(p.get("accent").unwrap(), "#FF0000");
        assert_eq!(p.get("fg").unwrap(), "#E7DFD3");
    }
}
