// AI-hint: Dynamic SSOT resolution from usr/share/mios/mios.toml and environment overrides.
// AI-related: usr/share/mios/mios.toml, tools/native/mios-resolver

use std::path::{Path, PathBuf};

pub const FORBIDDEN_CLOUD_URLS: &[&str] = &[
    "api.openai.com",
    "generativelanguage.googleapis.com",
    "api.anthropic.com",
];

#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    #[error("SSOT file not found: {0}")]
    NotFound(String),

    #[error("Failed to parse SSOT TOML: {0}")]
    ParseError(String),

    #[error("Missing required SSOT key: {0}")]
    MissingKey(String),

    #[error("Invalid port value for key '{key}': {value}")]
    InvalidPort { key: String, value: String },

    #[error("Forbidden vendor cloud endpoint detected in violation of Law 5: {0}")]
    ForbiddenCloudEndpoint(String),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

/// Asserts that a URL does not reference prohibited vendor cloud APIs (Law 5).
pub fn validate_no_cloud_endpoints(url: &str) -> Result<(), ConfigError> {
    for forbidden in FORBIDDEN_CLOUD_URLS {
        if url.contains(forbidden) {
            return Err(ConfigError::ForbiddenCloudEndpoint(forbidden.to_string()));
        }
    }
    Ok(())
}

/// Discovers the path to `usr/share/mios/mios.toml` using environment variables and search heuristics.
pub fn find_ssot_path() -> Result<PathBuf, ConfigError> {
    if let Ok(p) = std::env::var("MIOS_SSOT_PATH") {
        let path = PathBuf::from(p);
        if path.is_file() {
            return Ok(path);
        }
    }
    if let Ok(root) = std::env::var("MIOS_ROOT") {
        let path = PathBuf::from(root).join("usr/share/mios/mios.toml");
        if path.is_file() {
            return Ok(path);
        }
    }
    let fhs = Path::new("/usr/share/mios/mios.toml");
    if fhs.is_file() {
        return Ok(fhs.to_path_buf());
    }
    if let Ok(cwd) = std::env::current_dir() {
        let mut cur = cwd.as_path();
        loop {
            let candidate = cur.join("usr/share/mios/mios.toml");
            if candidate.is_file() {
                return Ok(candidate);
            }
            match cur.parent() {
                Some(p) => cur = p,
                None => break,
            }
        }
    }
    if let Ok(exe) = std::env::current_exe() {
        let mut cur = exe.as_path();
        while let Some(parent) = cur.parent() {
            let candidate = parent.join("usr/share/mios/mios.toml");
            if candidate.is_file() {
                return Ok(candidate);
            }
            cur = parent;
        }
    }
    let win_fallback = Path::new(r"C:\MiOS\usr\share\mios\mios.toml");
    if win_fallback.is_file() {
        return Ok(win_fallback.to_path_buf());
    }
    Err(ConfigError::NotFound(
        "usr/share/mios/mios.toml not found".into(),
    ))
}

/// Loads and parses the raw SSOT TOML table.
pub fn load_ssot_table() -> Result<toml::Table, ConfigError> {
    let path = find_ssot_path()?;
    let content = std::fs::read_to_string(&path)
        .map_err(|e| ConfigError::NotFound(format!("{}: {}", path.display(), e)))?;
    content
        .parse::<toml::Table>()
        .map_err(|e| ConfigError::ParseError(e.to_string()))
}

/// Resolves a typed port (1..=65535) dynamically from environment or `[ports]` SSOT table.
pub fn require_port(key: &str) -> Result<u16, ConfigError> {
    // 1. Environment variable override (e.g. MIOS_PORT_NODE or MIOS_PORT_HEADSCALE)
    let env_var_name = if key.starts_with("MIOS_PORT_") {
        key.to_string()
    } else {
        format!(
            "MIOS_PORT_{}",
            key.to_uppercase().replace(['.', '-'], "_")
        )
    };
    if let Ok(val) = std::env::var(&env_var_name) {
        if !val.trim().is_empty() {
            let parsed: i64 = val.trim().parse().map_err(|_| ConfigError::InvalidPort {
                key: key.to_string(),
                value: val.clone(),
            })?;
            if (1..=65535).contains(&parsed) {
                return Ok(parsed as u16);
            } else {
                return Err(ConfigError::InvalidPort {
                    key: key.to_string(),
                    value: val,
                });
            }
        }
    }

    // 2. Read from mios.toml [ports]
    let table = load_ssot_table()?;
    let ports = table
        .get("ports")
        .and_then(|v| v.as_table())
        .ok_or_else(|| ConfigError::MissingKey("ports".into()))?;

    let lookup_key = key
        .trim_start_matches("MIOS_PORT_")
        .trim_start_matches("ports.")
        .to_lowercase()
        .replace('-', "_");

    let val = ports.get(&lookup_key).or_else(|| ports.get(key));

    let raw_port = match val {
        Some(toml::Value::Integer(i)) => *i,
        Some(toml::Value::String(s)) => s.parse::<i64>().map_err(|_| ConfigError::InvalidPort {
            key: key.to_string(),
            value: s.clone(),
        })?,
        Some(other) => {
            return Err(ConfigError::InvalidPort {
                key: key.to_string(),
                value: other.to_string(),
            });
        }
        None => {
            return Err(ConfigError::MissingKey(key.to_string()));
        }
    };

    let stack_id = ports
        .get("stack_id")
        .and_then(|v| v.as_integer())
        .unwrap_or(0);
    let effective_port = raw_port + (stack_id * 10000);

    if !(1..=65535).contains(&effective_port) {
        return Err(ConfigError::InvalidPort {
            key: key.to_string(),
            value: effective_port.to_string(),
        });
    }

    Ok(effective_port as u16)
}

/// Resolves a string configuration value from environment or dotted TOML path.
pub fn require_str(key: &str) -> Result<String, ConfigError> {
    let env_var = format!(
        "MIOS_{}",
        key.to_uppercase().replace(['.', '-'], "_")
    );
    if let Ok(v) = std::env::var(&env_var) {
        if !v.is_empty() {
            return Ok(v);
        }
    }
    if let Ok(v) = std::env::var(key) {
        if !v.is_empty() {
            return Ok(v);
        }
    }

    let table = load_ssot_table()?;
    let parts: Vec<&str> = key.split('.').collect();
    let mut current: &toml::Value = &toml::Value::Table(table);

    for part in parts {
        match current {
            toml::Value::Table(t) => {
                current = t
                    .get(part)
                    .ok_or_else(|| ConfigError::MissingKey(key.to_string()))?;
            }
            _ => return Err(ConfigError::MissingKey(key.to_string())),
        }
    }

    match current {
        toml::Value::String(s) => Ok(s.clone()),
        other => Ok(other.to_string()),
    }
}

/// Resolves the unified local AI endpoint, strictly enforcing Law 5.
pub fn resolve_ai_endpoint() -> Result<String, ConfigError> {
    if let Ok(ep) = std::env::var("MIOS_AI_ENDPOINT") {
        if !ep.trim().is_empty() {
            validate_no_cloud_endpoints(&ep)?;
            return Ok(ep.trim().to_string());
        }
    }
    let port = require_port("llm_light").unwrap_or(8500);
    let endpoint = format!("http://127.0.0.1:{port}/v1");
    validate_no_cloud_endpoints(&endpoint)?;
    Ok(endpoint)
}

/// Resolves a general endpoint, ensuring zero cloud URLs.
pub fn resolve_endpoint(key: &str) -> Result<String, ConfigError> {
    if key == "ai" || key == "MIOS_AI_ENDPOINT" {
        return resolve_ai_endpoint();
    }
    let endpoint = require_str(key)?;
    validate_no_cloud_endpoints(&endpoint)?;
    Ok(endpoint)
}
