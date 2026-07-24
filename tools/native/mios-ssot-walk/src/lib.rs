// AI-hint: Single-sourced mios.toml SSOT-walk logic for resolver-twin and names-registry generators.

pub const EXCLUDED_SECTIONS: &[&str] = &[
    "meta",
    "laws",
];

pub fn is_excluded_section(section: &str) -> bool {
    EXCLUDED_SECTIONS.contains(&section)
}
