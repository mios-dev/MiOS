// AI-hint: Typed model of the mios.toml tables the resolver deserializes ahead of the generic walk.
// AI-related: usr/share/mios/mios.toml
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct IdentityConfig {
    pub username: Option<String>,
    pub hostname: Option<String>,
    pub domain: Option<String>,
    pub email: Option<String>,
    pub role: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct LocaleConfig {
    pub lang: Option<String>,
    pub timezone: Option<String>,
    pub keymap: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PortsConfig {
    pub stack_id: Option<i32>,
    pub vllm: Option<u16>,
    pub sglang: Option<u16>,
    pub searxng: Option<u16>,
    pub crawl4ai: Option<u16>,
    pub firecrawl: Option<u16>,
    pub open_webui: Option<u16>,
    pub guacamole_web: Option<u16>,
    pub pgvector: Option<u16>,
    pub agent_pipe: Option<u16>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ImageConfig {
    pub name: Option<String>,
    pub tag: Option<String>,
    pub base: Option<String>,
    pub sidecars: Option<HashMap<String, String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AiConfig {
    pub model: Option<String>,
    pub embed_model: Option<String>,
    pub endpoint: Option<String>,
    pub ram_floor_gb: Option<u32>,
    pub dir: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct NetworkConfig {
    pub listen_host: Option<String>,
    pub loopback_host: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MiosModel {
    pub identity: Option<IdentityConfig>,
    pub locale: Option<LocaleConfig>,
    pub ports: Option<PortsConfig>,
    pub colors: Option<HashMap<String, String>>,
    pub image: Option<ImageConfig>,
    pub ai: Option<AiConfig>,
    pub network: Option<NetworkConfig>,
    pub env: Option<HashMap<String, String>>,
}
