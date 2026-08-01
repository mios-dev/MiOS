// AI-hint: Typed config resolver deserializing mios.toml via Figment into typed models.
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
        if !ver.is_empty() { return ver; }
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

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct SecurityConfig {
    #[serde(default)]
    pub enable_units: Vec<String>,
    #[serde(default)]
    pub cosign: CosignConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct NtpConfig {
    #[serde(default = "default_ntp_servers")]
    pub servers: Vec<String>,
}

fn default_ntp_servers() -> Vec<String> {
    vec!["time.cloudflare.com".into(), "time.google.com".into()]
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct NetworkConfig {
    #[serde(default)]
    pub ntp: NtpConfig,
    #[serde(default)]
    pub ports: std::collections::HashMap<String, u16>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct CosignConfig {
    #[serde(default = "default_policy_mode")]
    pub policy_mode: String,
}

fn default_policy_mode() -> String {
    "insecureAcceptEverything".into()
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct PowerConfig {
    #[serde(default)]
    pub ups: UpsConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct UpsConfig {
    #[serde(default)]
    pub name: String,
    #[serde(default = "default_ups_driver")]
    pub driver: String,
    #[serde(default = "default_ups_port")]
    pub port: String,
    #[serde(default = "default_ups_desc")]
    pub desc: String,
}

fn default_ups_driver() -> String { "usbhid-ups".into() }
fn default_ups_port() -> String { "auto".into() }
fn default_ups_desc() -> String { "MiOS Uninterruptible Power Supply".into() }

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct RepoConfig {
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub baseurl: Option<String>,
    #[serde(default)]
    pub metalink: Option<String>,
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default)]
    pub repo_gpgcheck: bool,
    #[serde(default = "default_rpm_type")]
    pub repo_type: String,
    #[serde(default = "default_true")]
    pub gpgcheck: bool,
}

fn default_true() -> bool { true }

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct ComplianceConfig {
    #[serde(default)]
    pub enabled: bool,
    #[serde(default = "default_compliance_profile")]
    pub profile: String,
    #[serde(default)]
    pub datastream: String,
    #[serde(default = "default_compliance_severity")]
    pub severity_gate: String,
    #[serde(default)]
    pub remediate: bool,
    #[serde(default)]
    pub fetch_remote_resources: bool,
    #[serde(default = "default_compliance_report")]
    pub report_path: String,
}

fn default_compliance_profile() -> String { "standard".into() }
fn default_compliance_severity() -> String { "high".into() }
fn default_compliance_report() -> String { "/usr/share/mios/compliance".into() }

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct MiosConfig {
    #[serde(default)]
    pub meta: MetaConfig,
    #[serde(default)]
    pub identity: IdentityConfig,
    #[serde(default)]
    pub build: BuildConfig,
    #[serde(default)]
    pub security: SecurityConfig,
    #[serde(default)]
    pub network: NetworkConfig,
    #[serde(default)]
    pub power: PowerConfig,
    #[serde(default)]
    pub repos: std::collections::HashMap<String, RepoConfig>,
    #[serde(default)]
    pub compliance: ComplianceConfig,
    #[serde(default)]
    pub packages: std::collections::HashMap<String, PackageSectionConfig>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct PackageSectionConfig {
    #[serde(default)]
    pub pkgs: Vec<String>,
    #[serde(default = "default_true")]
    pub enable: bool,
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
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_deserialize_real_mios_toml() {
        let config = MiosConfig::load_from_path("../../../usr/share/mios/mios.toml")
            .expect("should deserialize real mios.toml");
        assert_eq!(config.identity.username, "mios");
        assert_eq!(config.build.ratchet.max_phase_scripts, 71);
        assert!(!config.build.phases.list.is_empty());
    }
}
