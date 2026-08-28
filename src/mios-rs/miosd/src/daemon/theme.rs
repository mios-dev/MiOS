// AI-hint: Theme synchronization watcher checking /etc/mios and /usr/share/mios theme state.
// AI-related: usr/libexec/mios/mios-sync-theme, usr/share/mios/mios.toml

use super::state::ThemeState;
use std::path::{Path, PathBuf};

pub struct ThemeWatcher {
    theme_path: PathBuf,
    last_mod_time: u64,
}

impl Default for ThemeWatcher {
    fn default() -> Self {
        Self::new()
    }
}

impl ThemeWatcher {
    pub fn new() -> Self {
        let root = std::env::var("MIOS_ROOT").unwrap_or_else(|_| ".".to_string());
        let theme_path = Path::new(&root).join("etc/mios/theme.toml");
        Self {
            theme_path,
            last_mod_time: 0,
        }
    }

    pub fn check_theme(&mut self, current_ts: u64) -> ThemeState {
        let mut in_sync = true;
        let mut current_theme = "bibata-modern-classic".to_string();
        let mut cursor_theme = "Bibata-Modern-Classic".to_string();

        if let Ok(metadata) = std::fs::metadata(&self.theme_path) {
            if let Ok(modified) = metadata.modified() {
                if let Ok(dur) = modified.duration_since(std::time::UNIX_EPOCH) {
                    let mtime = dur.as_secs();
                    if self.last_mod_time != 0 && mtime != self.last_mod_time {
                        // Modified recently -> trigger sync state
                        in_sync = true;
                    }
                    self.last_mod_time = mtime;
                }
            }
        }

        // Check environment overrides
        if let Ok(t) = std::env::var("MIOS_THEME") {
            if !t.is_empty() {
                current_theme = t;
            }
        }
        if let Ok(c) = std::env::var("MIOS_CURSOR_THEME") {
            if !c.is_empty() {
                cursor_theme = c;
            }
        }

        ThemeState {
            current_theme,
            cursor_theme,
            last_sync_ts: current_ts,
            in_sync,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_theme_watcher() {
        let mut watcher = ThemeWatcher::new();
        let state = watcher.check_theme(1724688000);
        assert!(!state.current_theme.is_empty());
        assert!(!state.cursor_theme.is_empty());
        assert_eq!(state.last_sync_ts, 1724688000);
    }
}
