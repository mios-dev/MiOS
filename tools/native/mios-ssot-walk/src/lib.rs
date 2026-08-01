// AI-hint: Single-sourced mios.toml SSOT-walk logic for resolver-twin and names-registry generators.

pub const EXCLUDED_SECTIONS: &[&str] = &[
    "containers",
    "verbs",
    "recipes",
    "packages",
    "dotfiles",
    "btop",
    "theme",
    "install_phases",
    "messages",
];

pub const WALK_MOSTLY_DEAD: &[&str] =
    &["ai", "image", "bootstrap", "profile", "sandbox", "security"];

pub const WALK_EMIT_KEEP: &[&str] = &[
    "MIOS_AI_BAKE_MODELS",
    "MIOS_AI_DIR",
    "MIOS_AI_EMBED_MODEL",
    "MIOS_AI_ENDPOINT",
    "MIOS_AI_JOURNAL",
    "MIOS_AI_MCP_DIR",
    "MIOS_AI_MEMORY_DIR",
    "MIOS_AI_MODEL",
    "MIOS_AI_MODELS_DIR",
    "MIOS_AI_RAM_FLOOR_GB",
    "MIOS_AI_SCRATCH_DIR",
    "MIOS_IMAGE_NAME",
    "MIOS_IMAGE_REF",
    "MIOS_IMAGE_TAG",
    "MIOS_BOOTSTRAP_MODE",
    "MIOS_PROFILE_FEATURES",
    "MIOS_PROFILE_ROLE",
    "MIOS_SANDBOX_ENABLE",
    "MIOS_SECURITY_ALLOWLIST_HOSTS",
    "MIOS_SECURITY_PROVENANCE_TAINT",
    "MIOS_HEADLESS",
    "MIOS_MONITOR_RUNNING",
    "MIOS_NO_COLOR",
    "MIOS_NO_MONITOR",
];

pub fn is_excluded_section(section: &str) -> bool {
    EXCLUDED_SECTIONS.contains(&section)
}

pub fn is_mostly_dead_section(section: &str) -> bool {
    WALK_MOSTLY_DEAD.contains(&section)
}

pub fn is_emit_keep_var(var_name: &str) -> bool {
    WALK_EMIT_KEEP.contains(&var_name)
}
