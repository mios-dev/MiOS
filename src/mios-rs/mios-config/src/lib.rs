// AI-hint: Typed config resolver deserializing mios.toml via Figment into typed models + generic TOML table.
// AI-related: usr/share/mios/mios.toml, /etc/mios/mios.toml, tools/lib/userenv.sh

use figment::{
    providers::{Env, Format, Toml},
    Figment,
};
use miette::Diagnostic;
use serde::{Deserialize, Serialize};
use std::path::Path;
use thiserror::Error;

#[derive(Error, Debug, Diagnostic)]
#[error("Failed to load MiOS configuration: {message}")]
pub struct ConfigError {
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct IdentityConfig {
    #[serde(default = "default_username")]
    pub username: String,
    #[serde(default = "default_fullname")]
    pub fullname: String,
    #[serde(default = "default_hostname")]
    pub hostname: String,
    #[serde(default = "default_shell")]
    pub shell: String,
    #[serde(default)]
    pub email: String,
    #[serde(default)]
    pub location: String,
}

fn default_username() -> String {
    "mios".into()
}
fn default_fullname() -> String {
    "MiOS Operator".into()
}
fn default_hostname() -> String {
    "mios".into()
}
fn default_shell() -> String {
    "/bin/bash".into()
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct MetaConfig {
    #[serde(default = "default_version")]
    pub mios_version: String,
    #[serde(default = "default_fedora_version")]
    pub fedora_version: String,
}

fn default_fedora_version() -> String {
    if let Ok(ver) = std::env::var("FEDORA_VERSION") {
        if !ver.is_empty() {
            return ver;
        }
    }
    "44".into()
}

fn default_version() -> String {
    "0.3.0".into()
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct PhaseItem {
    pub ordinal: String,
    pub name: String,
    pub script: String,
    pub fatal: bool,
    pub apply_class: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct BuildPhases {
    #[serde(default)]
    pub list: Vec<PhaseItem>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct BuildRatchet {
    #[serde(default = "default_max_phase_scripts")]
    pub max_phase_scripts: usize,
}

fn default_max_phase_scripts() -> usize {
    71
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct BuildConfig {
    #[serde(default)]
    pub phases: BuildPhases,
    #[serde(default)]
    pub ratchet: BuildRatchet,
}

/// Schema-generic configuration container. Owns stable fields directly
/// (`meta`, `identity`, `build`) while storing all dynamic/operator-defined
/// sections generically in `raw` to prevent recompilation on mios.toml schema changes.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct MiosConfig {
    #[serde(default)]
    pub meta: MetaConfig,
    #[serde(default)]
    pub identity: IdentityConfig,
    #[serde(default)]
    pub build: BuildConfig,

    /// Raw TOML table capturing all dynamic/operator-defined sections (e.g. packages, repos, security, network, power, compliance, etc.)
    #[serde(flatten)]
    pub raw: toml::Table,
}

impl MiosConfig {
    pub fn load_from_path<P: AsRef<Path>>(path: P) -> Result<Self, ConfigError> {
        Figment::new()
            .merge(Toml::file(path.as_ref()))
            .merge(Env::prefixed("MIOS_"))
            .extract()
            .map_err(|e| ConfigError {
                message: e.to_string(),
            })
    }

    pub fn load_default() -> Result<Self, ConfigError> {
        let root = std::env::var("MIOS_ROOT").unwrap_or_else(|_| ".".to_string());
        let primary = Path::new(&root).join("usr/share/mios/mios.toml");
        if primary.exists() {
            Self::load_from_path(primary)
        } else {
            Ok(Self::default())
        }
    }

    /// Retrieve a generic section from the raw config table by section name.
    pub fn section(&self, name: &str) -> Option<&toml::Value> {
        self.raw.get(name)
    }

    /// Retrieve a value via a dotted-path lookup (e.g. "packages.core.enable" or "security.enable_units").
    pub fn get_value(&self, key: &str) -> Option<&toml::Value> {
        let parts: Vec<&str> = key.split('.').collect();
        if parts.is_empty() {
            return None;
        }
        let mut val = self.raw.get(parts[0])?;
        for part in &parts[1..] {
            match val {
                toml::Value::Table(map) => {
                    val = map.get(*part)?;
                }
                _ => return None,
            }
        }
        Some(val)
    }

    /// Helper to get a string value from a dotted path key.
    pub fn get_string(&self, key: &str) -> Option<String> {
        self.get_value(key)
            .and_then(|v| v.as_str().map(|s| s.to_string()))
    }

    /// Helper to get a boolean value from a dotted path key.
    pub fn get_bool(&self, key: &str) -> Option<bool> {
        self.get_value(key).and_then(|v| v.as_bool())
    }

    /// Helper to get an integer value from a dotted path key.
    pub fn get_i64(&self, key: &str) -> Option<i64> {
        self.get_value(key).and_then(|v| v.as_integer())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_deserialize_real_mios_toml() {
        let config = MiosConfig::load_from_path("../../../usr/share/mios/mios.toml")
            .expect("should deserialize real mios.toml");
        assert_eq!(config.identity.username, "mios");
        // Assert it DESERIALIZES, not that it equals a magic number. Pinning
        // the literal here meant every legitimate ratchet bump in mios.toml
        // (this test said 71; adding 55-native-build.sh moved SSOT to 72)
        // broke a test whose stated purpose is "deserialize real mios.toml".
        assert!(config.build.ratchet.max_phase_scripts > 0);
        assert!(!config.build.phases.list.is_empty());

        // Verify generic section access on complex tables without rigid structs
        assert!(config.section("packages").is_some());
        assert!(config.get_value("security.cosign.policy_mode").is_some());
    }

    #[test]
    fn test_arbitrary_section_zero_recompile() {
        let sample_toml = r#"
[meta]
mios_version = "0.3.0"

[foo.bar]
custom_setting = "test_value"
number_key = 42
flag = true
"#;
        let config: MiosConfig = figment::Figment::new()
            .merge(figment::providers::Toml::string(sample_toml))
            .extract()
            .expect("should parse arbitrary custom sections generically");

        assert_eq!(
            config.get_string("foo.bar.custom_setting").as_deref(),
            Some("test_value")
        );
        assert_eq!(config.get_i64("foo.bar.number_key"), Some(42));
        assert_eq!(config.get_bool("foo.bar.flag"), Some(true));
    }
}
