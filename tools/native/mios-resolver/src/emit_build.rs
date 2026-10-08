// AI-hint: Validated native SSOT inputs for shared service-image builds on both platforms.
// AI-related: usr/libexec/mios/57-mios-sys-build.sh, usr/share/mios/mios.toml
use std::collections::BTreeSet;
use toml::Value;

pub fn emit_build_shell(merged: &Value, stack_offset: i64) -> Result<String, String> {
    let mut packages = Vec::new();
    let mut seen = BTreeSet::new();
    for section in ["mcp", "agent_cli"] {
        let values = merged
            .get("packages")
            .and_then(|v| v.get(section))
            .and_then(|v| v.get("pkgs"))
            .and_then(Value::as_array)
            .ok_or_else(|| format!("SSOT packages.{section}.pkgs must be an array"))?;
        for value in values {
            let package = value
                .as_str()
                .filter(|s| !s.is_empty() && !s.chars().any(char::is_whitespace))
                .ok_or_else(|| {
                    format!("SSOT packages.{section}.pkgs contains an invalid package")
                })?;
            if seen.insert(package) {
                packages.push(package);
            }
        }
    }
    if packages.is_empty() {
        return Err("SSOT service-base packages are empty".into());
    }
    let reference = merged
        .get("build")
        .and_then(|v| v.get("bake_refs"))
        .and_then(|v| v.get("searxng"))
        .and_then(Value::as_str)
        .filter(|s| !s.is_empty())
        .ok_or("SSOT build.bake_refs.searxng is empty")?;
    let mut exports = crate::emit::build_exports_map(merged, stack_offset);
    crate::emit::resolve_cross_references(&mut exports);
    let mut output = format!(
        "export MIOS_MCP_PACKAGES={}\nexport SEARXNG_REF={}\n",
        crate::emit_shell::shlex_quote(&packages.join(" ")),
        crate::emit_shell::shlex_quote(reference)
    );
    for key in [
        "MIOS_PIPER_BASE",
        "MIOS_PIPER_VERSION",
        "MIOS_PIPER_VOICE",
        "MIOS_PIPER_UID",
        "MIOS_PIPER_GID",
    ] {
        let value = exports
            .get(key)
            .filter(|v| !v.is_empty())
            .ok_or_else(|| format!("SSOT {key} is empty"))?;
        output.push_str(&format!(
            "export {key}={}\n",
            crate::emit_shell::shlex_quote(value)
        ));
    }
    Ok(output)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> Value {
        "[packages.mcp]\npkgs=['python3','git']\n[packages.agent_cli]\npkgs=['git','tmux']\n[build.bake_refs]\nsearxng='custom'\n[env]\nMIOS_PIPER_BASE='base'\nMIOS_PIPER_VERSION='v1'\nMIOS_PIPER_VOICE='voice'\nMIOS_PIPER_UID='1000'\nMIOS_PIPER_GID='1000'".parse().unwrap()
    }
    #[test]
    fn selections_are_deduplicated_and_shell_quoted() {
        let mut data = fixture();
        data["build"]["bake_refs"]["searxng"] = Value::String("branch'; touch /tmp/control".into());
        let text = emit_build_shell(&data, 0).unwrap();
        assert!(text.contains("MIOS_MCP_PACKAGES='python3 git tmux'"));
        assert!(text.contains("SEARXNG_REF='branch'\"'\"'; touch /tmp/control'"));
    }
    #[test]
    fn missing_and_malformed_inputs_do_not_emit_partial_exports() {
        let mut data = fixture();
        data["packages"]["mcp"]["pkgs"] = Value::Array(vec![Value::String("two packages".into())]);
        assert!(emit_build_shell(&data, 0).is_err());
        let mut data = fixture();
        data["env"]["MIOS_PIPER_VOICE"] = Value::String(String::new());
        assert!(emit_build_shell(&data, 0).is_err());
    }
}
