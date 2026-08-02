// AI-hint: Integration snapshot tests for the mios-resolver emit bindings.
// AI-related: tools/native/mios-resolver/src/emit_shell.rs, tools/native/mios-resolver/src/emit_json.rs
use mios_resolver::emit_json::emit_json;
use mios_resolver::emit_shell::emit_shell;

#[test]
fn test_cli_emit_shell_snapshot() {
    let val: toml::Value = toml::from_str(r#"
[identity]
role = "mini"
"#).unwrap();
    let shell_out = emit_shell(&val, 0, None);
    assert!(shell_out.contains("export MIOS_IDENTITY_ROLE='mini'"));
}

#[test]
fn test_cli_emit_json_snapshot() {
    let val: toml::Value = toml::from_str(r#"
[identity]
role = "mini"
"#).unwrap();
    let json_out = emit_json(&val, 0);
    assert!(json_out.contains("\"role\": \"mini\""));
}
