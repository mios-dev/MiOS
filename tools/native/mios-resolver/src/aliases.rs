// AI-hint: Legacy MIOS_* alias map -- ordered dotted-path to alias table mirroring get_aliases(), including the [ports] dual-alias forms.
// AI-related: usr/lib/mios/mios_toml.py, usr/share/mios/referenced_names.txt
pub fn get_aliases(dotted_path: &str) -> Vec<String> {
    let mut aliases = Vec::new();

    if let Some(rest) = dotted_path.strip_prefix("ai.vllm.") {
        let suffix = rest.to_uppercase().replace('.', "_").replace('-', "_");
        if suffix == "V1_ENGINE" {
            aliases.push("MIOS_VLLM_USE_V1".into());
        } else {
            aliases.push(format!("MIOS_VLLM_{}", suffix));
        }
    } else if let Some(rest) = dotted_path.strip_prefix("ai.sglang.") {
        let suffix = rest.to_uppercase().replace('.', "_").replace('-', "_");
        if suffix == "UNIFIED_RADIX_TREE" {
            aliases.push("MIOS_SGLANG_ENABLE_UNIFIED_RADIX_TREE".into());
        } else if suffix == "HIERARCHICAL_CACHE" {
            aliases.push("MIOS_SGLANG_ENABLE_HIERARCHICAL_CACHE".into());
        } else {
            aliases.push(format!("MIOS_SGLANG_{}", suffix));
        }
    } else if dotted_path == "identity.username" {
        aliases.push("MIOS_USER".into());
        aliases.push("MIOS_DEFAULT_USER".into());
    } else if dotted_path == "identity.fullname" {
        aliases.push("MIOS_USER_FULLNAME".into());
    } else if dotted_path == "identity.hostname" {
        aliases.push("MIOS_HOSTNAME".into());
        aliases.push("MIOS_DEFAULT_HOST".into());
    } else if dotted_path == "identity.shell" {
        aliases.push("MIOS_USER_SHELL".into());
        aliases.push("MIOS_DEFAULT_SHELL".into());
    } else if dotted_path == "identity.groups" {
        aliases.push("MIOS_USER_GROUPS".into());
        aliases.push("MIOS_DEFAULT_GROUPS".into());
    } else if dotted_path == "identity.default_password" {
        aliases.push("MIOS_DEFAULT_PASSWORD".into());
    } else if dotted_path == "accounts.db_backed" {
        aliases.push("MIOS_ACCOUNTS_DB_BACKED".into());
    } else if dotted_path == "locale.timezone" {
        aliases.push("MIOS_TIMEZONE".into());
        aliases.push("MIOS_DEFAULT_TIMEZONE".into());
    } else if dotted_path == "locale.keyboard_layout" {
        aliases.push("MIOS_KEYBOARD".into());
        aliases.push("MIOS_DEFAULT_KEYBOARD".into());
    } else if dotted_path == "locale.language" {
        aliases.push("MIOS_LOCALE".into());
        aliases.push("MIOS_DEFAULT_LOCALE".into());
    } else if dotted_path == "auth.ssh_key_action" {
        aliases.push("MIOS_SSH_KEY_ACTION".into());
    } else if dotted_path == "auth.password_policy" {
        aliases.push("MIOS_PASSWORD_POLICY".into());
    } else if dotted_path == "network.firewalld_default_zone" {
        aliases.push("MIOS_FIREWALLD_ZONE".into());
    } else if let Some(rest) = dotted_path.strip_prefix("portal.") {
        let suffix = rest.to_uppercase().replace('.', "_").replace('-', "_");
        if suffix == "PUBLIC_HOST" {
            aliases.push("MIOS_PUBLIC_HOST".into());
        } else {
            aliases.push(format!("MIOS_PORTAL_{}", suffix));
        }
    } else if let Some(rest) = dotted_path.strip_prefix("a2a.") {
        let name = rest.to_uppercase().replace('.', "_");
        if name == "DISCOVER_PORT" {
            aliases.push("MIOS_A2A_DISCOVER_PORT".into());
        } else if name == "PUBLIC_DOMAIN" {
            aliases.push("MIOS_PUBLIC_DOMAIN".into());
        } else {
            aliases.push(format!("MIOS_A2A_{}", name));
        }
    } else if dotted_path == "agents.hermes.endpoint" {
        aliases.push("MIOS_HERMES_WORKER_ENDPOINT".into());
    } else if dotted_path.starts_with("ai.") && !dotted_path.starts_with("ai.vllm.") && !dotted_path.starts_with("ai.sglang.") {
        let suffix = dotted_path["ai.".len()..].to_uppercase().replace('.', "_").replace('-', "_");
        if suffix == "API_KEY" || suffix == "KEY" {
            aliases.push("MIOS_AI_KEY".into());
        } else if suffix == "EMBED_MODEL" {
            aliases.push("MIOS_VERB_EMBED_MODEL".into());
        } else if suffix == "STACK_MODEL" {
            aliases.push("MIOS_STACK_MODEL".into());
        } else if suffix == "CHAT_VISION_MODEL" {
            aliases.push("MIOS_AGENT_PIPE_VISION_MODEL".into());
        } else if suffix == "AGENT_VENV" {
            aliases.push("MIOS_HERMES_VENV".into());
        } else if suffix == "AGENT_INSTALL_DIR" {
            aliases.push("MIOS_HERMES_DIR".into());
        } else if suffix == "MICRO_MODEL" {
            aliases.push("MIOS_MICRO_MODEL".into());
        } else if suffix == "MICRO_ENDPOINT" {
            aliases.push("MIOS_MICRO_ENDPOINT".into());
        } else if suffix == "OPENCODE_GATEWAY_WORKDIR" {
            aliases.push("MIOS_OPENCODE_WORKDIR".into());
        } else if suffix == "OPENCODE_GATEWAY_TIMEOUT_S" {
            aliases.push("MIOS_OPENCODE_TIMEOUT_S".into());
        } else if suffix.starts_with("OPENCODE_") {
            aliases.push(format!("MIOS_{}", suffix));
        } else if suffix == "ENDPOINT" || suffix == "MODEL" {
            aliases.push(format!("MIOS_AI_{}", suffix));
            aliases.push(format!("MIOS_{}", suffix));
        } else if matches!(
            suffix.as_str(),
            "SYSTEM_PROMPT_FILE"
                | "TOKENIZER_BACKEND"
                | "TOKENIZER_ENCODING"
                | "TOKENIZER_CACHE_DIR"
                | "TOKENIZER_PATH"
                | "HERMES_AGENT_REPO"
                | "HERMES_AGENT_REF"
                | "HERMES_BACKEND_URL"
                | "MCP_REGISTRY"
        ) {
            aliases.push(format!("MIOS_{}", suffix));
        }
    } else if let Some(rest) = dotted_path.strip_prefix("build.") {
        let name = rest.to_uppercase().replace('.', "_");
        if matches!(name.as_str(), "LOCAL_TAG" | "AI_RAM_FLOOR_GB" | "RECHUNK_MAX_LAYERS") {
            aliases.push(format!("MIOS_{}", name));
        } else {
            aliases.push(format!("MIOS_BUILD_{}", name));
        }
    } else if let Some(rest) = dotted_path.strip_prefix("code_mode.") {
        let name = rest.to_uppercase();
        aliases.push(format!("MIOS_CODEMODE_{}", name));
    } else if let Some(rest) = dotted_path.strip_prefix("colors.") {
        let name = rest.to_uppercase();
        if name.starts_with("ANSI_") {
            aliases.push(format!("MIOS_{}", name));
        } else {
            aliases.push(format!("MIOS_COLOR_{}", name));
        }
    } else if let Some(rest) = dotted_path.strip_prefix("frontier.") {
        let name = rest.to_uppercase();
        if name == "STREAM_TO_REASONING" {
            aliases.push("MIOS_A2O_STREAM_REASONING".into());
        } else {
            aliases.push(format!("MIOS_A2O_{}", name));
        }
    } else if let Some(rest) = dotted_path.strip_prefix("paths.") {
        let name = rest.to_uppercase();
        if name == "MIOS_TOML" {
            aliases.push("MIOS_TOML".into());
        } else if name == "WSL_FIRSTBOOT_DONE" {
            aliases.push("MIOS_WSLBOOT_DONE".into());
        } else if name == "LAUNCHER_SOCKET" || name == "MIOS_LAUNCHER_SOCKET" {
            aliases.push("MIOS_LAUNCHER_SOCKET".into());
        } else {
            aliases.push(format!("MIOS_{}", name));
        }
    } else if dotted_path.starts_with("pgvector.") || dotted_path.starts_with("pg.") {
        let prefix_len = if dotted_path.starts_with("pgvector.") { "pgvector.".len() } else { "pg.".len() };
        let name = dotted_path[prefix_len..].to_uppercase();
        if name == "DB_BACKEND" {
            aliases.push("MIOS_DB_BACKEND".into());
        } else if name == "RLS_ENABLE" {
            aliases.push("MIOS_DB_RLS_ENABLE".into());
        } else {
            aliases.push(format!("MIOS_PG_{}", name));
            aliases.push(format!("MIOS_PGVECTOR_{}", name));
        }
    } else if dotted_path.starts_with("routing.") && !dotted_path.starts_with("routing.domains.") {
        let name = dotted_path["routing.".len()..].to_uppercase().replace('.', "_");
        aliases.push(format!("MIOS_{}", name));
    } else if dotted_path == "polish.timeout_seconds" {
        aliases.push("MIOS_POLISH_TIMEOUT_S".into());
    } else if dotted_path == "refine.timeout_seconds" {
        aliases.push("MIOS_REFINE_TIMEOUT_S".into());
    } else if dotted_path == "security.fapolicyd_observe.enable" {
        aliases.push("MIOS_FAPOLICYD_OBSERVE_ENABLE".into());
    } else if dotted_path == "uki.verity_uki_build" {
        aliases.push("MIOS_UKI_VERITY_BUILD".into());
    } else if let Some(rest) = dotted_path.strip_prefix("verity.") {
        let name = rest.to_uppercase();
        aliases.push(format!("MIOS_{}", name));
    } else if dotted_path == "user.hostname" {
        aliases.push("MIOS_HOSTNAME".into());
    } else if dotted_path == "user.name" {
        aliases.push("MIOS_USER_FULLNAME".into());
    } else if dotted_path == "flatpaks.install" {
        aliases.push("MIOS_FLATPAKS".into());
    } else if let Some(rest) = dotted_path.strip_prefix("llamacpp.") {
        let name = rest.to_uppercase();
        if name == "CPU_NODE_THREADS" {
            aliases.push("MIOS_CPU_NODE_THREADS".into());
        } else {
            aliases.push(format!("MIOS_LLAMACPP_{}", name));
        }
    } else if dotted_path == "meta.mios_version" {
        aliases.push("MIOS_VERSION".into());
    } else if let Some(rest) = dotted_path.strip_prefix("network.quadlet.") {
        let name = rest.to_uppercase();
        if name == "CORE_GATEWAY" {
            aliases.push("MIOS_CORE_NET_GATEWAY".into());
        } else if name == "CORE_SUBNET" {
            aliases.push("MIOS_CORE_NET_SUBNET".into());
        } else if name == "NETWORK" {
            aliases.push("MIOS_QUADLET_NETWORK".into());
        } else if name == "SUBNET" {
            aliases.push("MIOS_QUADLET_SUBNET".into());
        }
    } else if dotted_path == "fs_watcher.watch_dirs" {
        aliases.push("MIOS_FS_WATCHER_DIRS".into());
    } else if let Some(rest) = dotted_path.strip_prefix("ports.") {
        let name = rest.to_uppercase().replace('.', "_").replace('-', "_");
        let canon = if name == "GUACAMOLE_WEB" { "GUACAMOLE" } else { &name };
        aliases.push(format!("MIOS_PORT_{}", canon));
        aliases.push(format!("MIOS_{}_PORT", canon));
    } else if let Some(rest) = dotted_path.strip_prefix("image.sidecars.") {
        let name = rest.to_uppercase().replace('.', "_").replace('-', "_");
        if name.ends_with("_VERSION") {
            let base = &name[..name.len() - "_VERSION".len()];
            aliases.push(format!("MIOS_{}_VERSION", base));
        } else {
            aliases.push(format!("MIOS_{}_IMAGE", name));
            aliases.push(format!("MIOS_{}_VERSION", name));
        }
    } else if let Some(rest) = dotted_path.strip_prefix("services.") {
        let parts: Vec<&str> = rest.split('.').collect();
        if parts.len() >= 2 {
            let service = parts[0].to_uppercase().replace('-', "_");
            let key = parts[1..].join("_").to_uppercase().replace('-', "_");
            if service == "WEBTOOLS" {
                if matches!(key.as_str(), "USER" | "UID" | "GID") {
                    aliases.push(format!("MIOS_WEBTOOLS_{}", key));
                } else if key == "CDP_URL" {
                    aliases.push("MIOS_CRAWL_CDP_URL".into());
                } else if key == "CAMOUFOX" {
                    aliases.push("MIOS_CRAWL_CAMOUFOX".into());
                } else if key == "MIN_CHARS" {
                    aliases.push("MIOS_CRAWL_MIN_CHARS".into());
                } else if key.starts_with("FIRECRAWL_") || key.starts_with("CRAWL4AI_") {
                    aliases.push(format!("MIOS_{}", key));
                }
            } else {
                aliases.push(format!("MIOS_{}_{}", service, key));
            }
        }
    } else if let Some(rest) = dotted_path.strip_prefix("storage.cephfs.") {
        let key = rest.to_uppercase().replace('.', "_").replace('-', "_");
        if key == "XDG_CACHE_HOME_OVERRIDE" {
            aliases.push("MIOS_XDG_CACHE_LOCAL_PATH".into());
        } else {
            aliases.push(format!("MIOS_CEPHFS_{}", key));
        }
    } else if let Some(rest) = dotted_path.strip_prefix("wsl2.") {
        let key = rest.to_uppercase().replace('.', "_").replace('-', "_");
        if key == "DESKTOP_COMPAT_GDK_BACKEND" {
            aliases.push("MIOS_WSLG_GDK_BACKEND".into());
        } else if key == "DESKTOP_COMPAT_MOZ_WAYLAND" {
            aliases.push("MIOS_WSLG_MOZ_WAYLAND".into());
        } else if key == "DESKTOP_COMPAT_QT_PLATFORM" {
            aliases.push("MIOS_WSLG_QT_PLATFORM".into());
        } else if key == "DEV_VM_QUADLET_NETWORK_MODE" {
            aliases.push("MIOS_QUADLET_DEV_NETWORK_MODE".into());
        } else {
            aliases.push(format!("MIOS_WSL2_{}", key));
        }
    } else if dotted_path.starts_with("converge.") {
        // No legacy alias
    } else if dotted_path.starts_with("image.") && !dotted_path.starts_with("image.sidecars.") {
        let key = dotted_path["image.".len()..].to_uppercase().replace('.', "_").replace('-', "_");
        if key == "BRANCH" {
            aliases.push("MIOS_BRANCH".into());
        } else if key == "BASE" {
            aliases.push("MIOS_BASE_IMAGE".into());
        } else if key == "BIB" {
            aliases.push("MIOS_BIB_IMAGE".into());
        } else if key == "LOCAL_TAG" {
            aliases.push("MIOS_LOCAL_TAG".into());
        } else if matches!(key.as_str(), "REF" | "NAME" | "TAG") {
            aliases.push(format!("MIOS_IMAGE_{}", key));
        }
    } else if let Some(rest) = dotted_path.strip_prefix("desktop.") {
        let key = rest.to_uppercase().replace('.', "_").replace('-', "_");
        if key == "COLOR_SCHEME" {
            aliases.push("MIOS_COLOR_SCHEME".into());
        } else if key == "FLATPAKS" {
            aliases.push("MIOS_FLATPAKS".into());
        } else if key == "SESSION" {
            aliases.push(format!("MIOS_DESKTOP_{}", key));
        }
    } else if let Some(rest) = dotted_path.strip_prefix("bootstrap.dev_vm.") {
        let key = rest.to_uppercase().replace('.', "_").replace('-', "_");
        if key == "MACHINE_NAME" {
            aliases.push("MIOS_BUILDER_DISTRO".into());
        } else if key == "WSL_DISTRO" {
            aliases.push("MIOS_WSL_DISTRO".into());
        } else if key == "DISK_SIZE_GB" {
            aliases.push("MIOS_DEV_VM_DISK_GB".into());
        } else if key == "GPU_PASSTHROUGH" {
            aliases.push("MIOS_DEV_VM_GPU".into());
        } else if key == "HOST_RESERVE_CPU_PCT" {
            aliases.push("MIOS_DEV_VM_CPU_RESERVE_PCT".into());
        } else if key == "HOST_RESERVE_CPU_MIN" {
            aliases.push("MIOS_DEV_VM_CPU_RESERVE_MIN".into());
        } else if key == "HOST_RESERVE_MEMORY_PCT" {
            aliases.push("MIOS_DEV_VM_MEMORY_RESERVE_PCT".into());
        } else if key == "HOST_RESERVE_MEMORY_GB" {
            aliases.push("MIOS_DEV_VM_MEMORY_RESERVE_GB".into());
        } else if key == "HOST_RESERVE_DISK_GB" {
            aliases.push("MIOS_DEV_VM_DISK_RESERVE_GB".into());
        } else if matches!(key.as_str(), "BASE_IMAGE" | "CPUS" | "MEMORY_MB") {
            aliases.push(format!("MIOS_DEV_VM_{}", key));
        }
    } else if let Some(rest) = dotted_path.strip_prefix("bootstrap.host_storage.") {
        let key = rest.to_uppercase().replace('.', "_").replace('-', "_");
        if key == "SHRINK_MB" {
            aliases.push("MIOS_DATA_DISK_MB".into());
        } else if key == "DRIVE_LETTER" {
            aliases.push("MIOS_DATA_DISK_LETTER".into());
        }
    } else if dotted_path.starts_with("bootstrap.")
        && !dotted_path.starts_with("bootstrap.dev_vm.")
        && !dotted_path.starts_with("bootstrap.host_storage.")
    {
        let key = dotted_path["bootstrap.".len()..].to_uppercase().replace('.', "_").replace('-', "_");
        if key == "MIOS_REPO" {
            aliases.push("MIOS_REPO_URL".into());
        } else if key == "BOOTSTRAP_REPO" {
            aliases.push("MIOS_BOOTSTRAP_REPO_URL".into());
        } else if key == "MODE" {
            aliases.push(format!("MIOS_BOOTSTRAP_{}", key));
        }
    } else if let Some(rest) = dotted_path.strip_prefix("reliability.") {
        let key = rest.to_uppercase().replace('.', "_").replace('-', "_");
        aliases.push(format!("MIOS_RELIABILITY_{}", key));
    } else if let Some(rest) = dotted_path.strip_prefix("routing.") {
        let key = rest.to_uppercase().replace('.', "_").replace('-', "_");
        aliases.push(format!("MIOS_ROUTING_{}", key));
        if key.starts_with("LAUNCH_") {
            aliases.push(format!("MIOS_{}", key));
        }
    } else if dotted_path.starts_with("mios-find.") || dotted_path.starts_with("mios_find.") {
        let prefix_len = if dotted_path.starts_with("mios-find.") { "mios-find.".len() } else { "mios_find.".len() };
        let key = dotted_path[prefix_len..].to_uppercase().replace('.', "_").replace('-', "_");
        aliases.push(format!("MIOS_FIND_{}", key));
    }

    aliases
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_identity_aliases() {
        assert_eq!(get_aliases("identity.username"), vec!["MIOS_USER", "MIOS_DEFAULT_USER"]);
        assert_eq!(get_aliases("identity.hostname"), vec!["MIOS_HOSTNAME", "MIOS_DEFAULT_HOST"]);
    }

    #[test]
    fn test_ports_dual_alias() {
        assert_eq!(get_aliases("ports.vllm"), vec!["MIOS_PORT_VLLM", "MIOS_VLLM_PORT"]);
        assert_eq!(get_aliases("ports.guacamole_web"), vec!["MIOS_PORT_GUACAMOLE", "MIOS_GUACAMOLE_PORT"]);
    }

    #[test]
    fn test_image_sidecars_aliases() {
        assert_eq!(get_aliases("image.sidecars.vllm"), vec!["MIOS_VLLM_IMAGE", "MIOS_VLLM_VERSION"]);
        assert_eq!(get_aliases("image.sidecars.k3s_version"), vec!["MIOS_K3S_VERSION"]);
    }
}
