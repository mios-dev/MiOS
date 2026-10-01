// AI-hint: Library entry point for the mios-node edge micro-node daemon.
// AI-related: src/mios-rs/mios-node/src/main.rs, src/mios-rs/mios-node/src/node.rs, tools/native/mios-resolver/src/lib.rs
//! MiOS ("My OS" / "MyOS") Distributed Edge Micro-Node Library

pub mod ble;
pub mod buffer_pool;
pub mod capabilities;
pub mod cgroups;
pub mod crypto;
pub mod executor;
pub mod hardware;
pub mod heartbeat;
pub mod net;
pub mod node;
pub mod overlay;
pub mod protocol;
pub mod scheduler;
pub mod state_sync;
pub mod watchdog;

/// Runtime SSOT lookup -- process environment first, then the layered
/// mios.toml through mios-resolver; no value is compiled in.
pub mod ssot {
    // The node's ports and endpoints are SSOT values. The unit passes them as
    // Environment=; an unset or empty variable falls back to the resolved
    // six-tier mios.toml, and a name neither provides is an error that names it.

    use anyhow::{anyhow, Result};
    use std::collections::BTreeMap;
    use std::sync::OnceLock;

    static RESOLVED: OnceLock<BTreeMap<String, String>> = OnceLock::new();

    /// `name` from `env`, else from `resolved`; empty strings count as unset.
    pub fn lookup_in(
        name: &str,
        env: impl Fn(&str) -> Option<String>,
        resolved: &BTreeMap<String, String>,
    ) -> Option<String> {
        env(name)
            .filter(|v| !v.is_empty())
            .or_else(|| resolved.get(name).filter(|v| !v.is_empty()).cloned())
    }

    fn resolved() -> &'static BTreeMap<String, String> {
        RESOLVED.get_or_init(|| mios_resolver::resolve_env(None).unwrap_or_default())
    }

    pub fn get(name: &str) -> Option<String> {
        lookup_in(name, |n| std::env::var(n).ok(), resolved())
    }

    pub fn require(name: &str) -> Result<String> {
        get(name)
            .ok_or_else(|| anyhow!("{name} is unset and the layered mios.toml does not resolve it"))
    }

    pub fn require_port(name: &str) -> Result<u16> {
        let raw = require(name)?;
        raw.parse::<u16>()
            .map_err(|_| anyhow!("{name}='{raw}' is not a port"))
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        fn ssot() -> BTreeMap<String, String> {
            BTreeMap::from([("MIOS_PORT_NODE".to_string(), "8650".to_string())])
        }

        #[test]
        fn environment_wins_over_the_resolved_ssot() {
            let env = |_: &str| Some("9100".to_string());
            assert_eq!(
                lookup_in("MIOS_PORT_NODE", env, &ssot()).as_deref(),
                Some("9100")
            );
        }

        #[test]
        fn empty_environment_falls_back_to_the_ssot() {
            let env = |_: &str| Some(String::new());
            assert_eq!(
                lookup_in("MIOS_PORT_NODE", env, &ssot()).as_deref(),
                Some("8650")
            );
        }

        #[test]
        fn a_name_nothing_provides_is_none() {
            assert_eq!(lookup_in("MIOS_PORT_MISSING", |_| None, &ssot()), None);
        }
    }
}
