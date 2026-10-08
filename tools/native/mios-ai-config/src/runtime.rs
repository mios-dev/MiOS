// AI-hint: Shared layered endpoint selection, OpenCode projection and bounded readiness probe; never starts inference or substitutes a model.
// AI-related: usr/libexec/mios/mios-mcp-server, usr/share/mios/windows/mios-native-client-setup.ps1
use serde_json::{json, Value};
use std::{collections::BTreeMap, path::Path, process::Command};

pub fn connection(root: &Path) -> Result<(String, String), String> {
    let doc = mios_resolver::resolve_merged(Some(root), false).map_err(|e| e.to_string())?;
    let mut exports =
        mios_resolver::emit::build_exports_map(&doc, mios_resolver::stack_offset_of(&doc));
    mios_resolver::emit::resolve_cross_references(&mut exports);
    // The agent-pipe front door advertises ai.agent_model, not the inference
    // backend's ai.model. An explicit client model still has to pass /models.
    select(
        &exports,
        std::env::var("MIOS_AI_ENDPOINT").ok(),
        std::env::var("MIOS_AI_GATEWAY_MODEL").ok(),
    )
}

fn select(
    exports: &BTreeMap<String, String>,
    endpoint: Option<String>,
    model: Option<String>,
) -> Result<(String, String), String> {
    let get = |key: &str, override_value: Option<String>| {
        override_value
            .or_else(|| exports.get(key).cloned())
            .filter(|v| {
                !v.trim().is_empty() && !v.contains("${") && !v.chars().any(char::is_control)
            })
            .ok_or_else(|| format!("{key} is missing, empty or unresolved"))
    };
    let endpoint = get("MIOS_AI_ENDPOINT", endpoint)?;
    let model = get("MIOS_AI_AGENT_MODEL", model)?;
    validate_endpoint(&endpoint)?;
    Ok((endpoint.trim_end_matches('/').into(), model))
}

fn validate_endpoint(endpoint: &str) -> Result<(), String> {
    let rest = endpoint
        .strip_prefix("http://")
        .or_else(|| endpoint.strip_prefix("https://"))
        .ok_or("MIOS_AI_ENDPOINT must use http or https")?;
    let (authority, path) = rest
        .split_once('/')
        .ok_or("MIOS_AI_ENDPOINT must end in /v1")?;
    if authority.is_empty()
        || authority.contains('@')
        || authority.chars().any(char::is_whitespace)
        || path != "v1"
        || endpoint.contains(['?', '#', '$'])
    {
        return Err("MIOS_AI_ENDPOINT must name the local OpenAI-compatible /v1 surface without credentials or placeholders".into());
    }
    // An endpoint is an explicit operator setting, including private blade DNS.
    // Reject public vendor surfaces; never choose an alternate endpoint here.
    let host = authority
        .split(':')
        .next()
        .unwrap_or_default()
        .to_ascii_lowercase();
    for domain in [
        "openai.com",
        "anthropic.com",
        "googleapis.com",
        "groq.com",
        "deepseek.com",
        "openrouter.ai",
        "together.xyz",
    ] {
        if host == domain || host.ends_with(&format!(".{domain}")) {
            return Err("MIOS_AI_ENDPOINT references a prohibited cloud API".into());
        }
    }
    Ok(())
}

pub fn opencode(mut config: Value, endpoint: &str, model: &str) -> Result<Value, String> {
    validate_endpoint(endpoint)?;
    let object = config
        .as_object_mut()
        .ok_or("OpenCode config must be an object")?;
    let providers = object
        .entry("provider")
        .or_insert_with(|| json!({}))
        .as_object_mut()
        .ok_or("OpenCode provider must be an object")?;
    if let Some(existing) = providers.get("local") {
        if existing.get("name").and_then(Value::as_str) != Some("Local MiOS") {
            return Err("OpenCode provider.local is operator-owned; refusing to replace it".into());
        }
    }
    providers.insert("local".into(), json!({"name":"Local MiOS","npm":"@ai-sdk/openai-compatible","options":{"baseURL":endpoint},"models":{model:{"name":model}}}));
    if let Some(legacy) = object.get_mut("providers").and_then(Value::as_object_mut) {
        if legacy
            .get("local")
            .and_then(|v| v.get("name"))
            .and_then(Value::as_str)
            == Some("Local MiOS")
        {
            legacy.remove("local");
        }
        if legacy.is_empty() {
            object.remove("providers");
        }
    }
    if object
        .get("model")
        .and_then(Value::as_str)
        .is_none_or(|m| m.starts_with("local/"))
    {
        object.insert("model".into(), json!(format!("local/{model}")));
    }
    Ok(config)
}

pub fn validate_models(body: &[u8], model: &str) -> Result<usize, String> {
    let value: Value = serde_json::from_slice(body)
        .map_err(|e| format!("/v1/models returned invalid JSON: {e}"))?;
    let rows = value
        .get("data")
        .and_then(Value::as_array)
        .ok_or("/v1/models did not return an OpenAI data array")?;
    if !rows
        .iter()
        .any(|v| v.get("id").and_then(Value::as_str) == Some(model))
    {
        return Err(format!("selected model {model:?} is not advertised by MIOS_AI_ENDPOINT ({} model(s)); model substitution refused", rows.len()));
    }
    Ok(rows.len())
}

pub fn probe(endpoint: &str, model: &str) -> Result<usize, String> {
    validate_endpoint(endpoint)?;
    let executable = if cfg!(windows) { "curl.exe" } else { "curl" };
    let mut command = Command::new(executable);
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    command.args([
        "--silent",
        "--show-error",
        "--fail",
        "--connect-timeout",
        "2",
        "--max-time",
        "5",
        "--max-filesize",
        "1048576",
        "--noproxy",
        "*",
        "--proto",
        "=http,https",
        "--url",
        &format!("{endpoint}/models"),
    ]);
    // No redirect following: bearer material cannot leave the selected surface.
    // Supply credentials through curl's stdin config, never argv or diagnostics.
    use std::io::Write;
    use std::process::Stdio;
    command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    if std::env::var_os("MIOS_AI_KEY").is_some() {
        command.args(["--config", "-"]);
    }
    let mut child = command
        .spawn()
        .map_err(|e| format!("local AI readiness probe could not start {executable}: {e}"))?;
    if let Some(mut input) = child.stdin.take() {
        if let Ok(key) = std::env::var("MIOS_AI_KEY") {
            if key.chars().any(char::is_control) {
                let _ = child.kill();
                let _ = child.wait();
                return Err("MIOS_AI_KEY contains invalid control characters".into());
            }
            let key = key.replace('\\', "\\\\").replace('"', "\\\"");
            if let Err(e) = writeln!(input, "header = \"Authorization: Bearer {key}\"") {
                let _ = child.kill();
                let _ = child.wait();
                return Err(format!("local AI probe input failed: {e}"));
            }
        }
    }
    let output = child
        .wait_with_output()
        .map_err(|e| format!("local AI readiness probe failed: {e}"))?;
    if !output.status.success() {
        return Err(format!("MIOS_AI_ENDPOINT {endpoint} is unavailable or rejected /models (curl exit {:?}); check agent-pipe and its configured inference backend", output.status.code()));
    }
    validate_models(&output.stdout, model)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn explicit_route_and_model_win_without_a_lane_fallback() -> Result<(), String> {
        let exports = BTreeMap::from([
            ("MIOS_AI_ENDPOINT".into(), "http://localhost:9100/v1".into()),
            ("MIOS_AI_AGENT_MODEL".into(), "brain".into()),
            ("MIOS_AI_MODEL".into(), "backend-only".into()),
        ]);
        assert_eq!(
            select(&exports, None, None)?,
            ("http://localhost:9100/v1".into(), "brain".into())
        );
        assert_eq!(
            select(
                &exports,
                Some("http://blade.mesh:9200/v1".into()),
                Some("chosen".into())
            )?,
            ("http://blade.mesh:9200/v1".into(), "chosen".into())
        );
        for value in [
            "",
            "${MIOS_AI_ENDPOINT}",
            "http://localhost:1/v1\n",
            "https://api.openai.com/v1",
            "ftp://localhost/v1",
            "http://secret@localhost/v1",
            "http://localhost/v1?q=1",
        ] {
            assert!(
                select(&exports, Some(value.into()), None).is_err(),
                "{value}"
            );
        }
        assert!(select(&BTreeMap::new(), None, None).is_err());
        Ok(())
    }
    #[test]
    fn projects_only_owned_provider_and_preserves_operator_model_and_mcp() -> Result<(), String> {
        let input = json!({"model":"custom/user-model","mcp":{"custom":{"enabled":true}},"provider":{"custom":{"name":"mine"}},"providers":{"local":{"name":"Local MiOS"},"other":{}}});
        let rendered = opencode(input.clone(), "http://localhost:9200/v1", "chosen")?;
        assert_eq!(
            rendered["provider"]["local"]["options"]["baseURL"],
            "http://localhost:9200/v1"
        );
        assert_eq!(
            rendered["provider"]["local"]["models"]["chosen"]["name"],
            "chosen"
        );
        assert_eq!(rendered["model"], input["model"]);
        assert_eq!(rendered["mcp"], input["mcp"]);
        assert_eq!(rendered["provider"]["custom"], input["provider"]["custom"]);
        assert!(rendered["providers"].get("local").is_none());
        assert!(rendered["providers"].get("other").is_some());
        assert_eq!(
            opencode(rendered.clone(), "http://localhost:9200/v1", "chosen")?,
            rendered
        );
        assert_eq!(
            opencode(
                json!({"model":"local/old"}),
                "http://localhost:9200/v1",
                "chosen"
            )?["model"],
            "local/chosen"
        );
        assert!(opencode(
            json!({"provider":{"local":{"name":"Operator"}}}),
            "http://localhost:9200/v1",
            "chosen"
        )
        .is_err());
        assert!(opencode(json!({"provider":[]}), "http://localhost:9200/v1", "chosen").is_err());
        Ok(())
    }
    #[test]
    fn refuses_wrong_model_empty_and_malformed_catalogs() -> Result<(), String> {
        assert_eq!(
            validate_models(br#"{"data":[{"id":"brain"},{"id":"other"}]}"#, "brain")?,
            2
        );
        for body in [
            br#"{"data":[{"id":"mios-igpu"}]}"#.as_slice(),
            br#"{"data":[]}"#,
            br#"{"models":[{"name":"brain"}]}"#,
            br#"not json"#,
        ] {
            assert!(validate_models(body, "brain").is_err());
        }
        Ok(())
    }
}
