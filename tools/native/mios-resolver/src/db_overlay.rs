// AI-hint: Reserved DB-authoritative overlay hook -- inert unless MIOS_ACCOUNTS_DB_BACKED is enabled.
// AI-related: usr/share/mios/mios.toml, docs/agy/doc-postgresos-accounts.md
use toml::Value;

pub fn is_db_authoritative() -> bool {
    // By default, DB mode is inert unless MIOS_ACCOUNTS_DB_BACKED is enabled in environment or DB
    std::env::var("MIOS_ACCOUNTS_DB_BACKED")
        .map(|v| v == "true" || v == "1")
        .unwrap_or(false)
}

pub fn maybe_apply_db_overlay(_dst: &mut Value) {
    if !is_db_authoritative() {
    }
    // Reserved hook for DB overlay execution if enabled
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_db_authoritative_default() {
        assert!(!is_db_authoritative());
    }
}
