// AI-hint: Build-time tmux fixture and runtime consumers share the native theme engine.
pub use mios_service_core::tmux_theme::{is_remote_terminal, TmuxThemeEngine};
use std::fs;
use std::path::{Path, PathBuf};
pub const GOLDEN: &str = "usr/share/mios/tmux/mios-theme.tmux.conf";

#[allow(dead_code)]
pub struct RenderTmuxThemeResult {
    pub style: String,
    pub status_position: String,
    pub config_lines: usize,
    pub output_path: Option<PathBuf>,
}

pub fn run_render_tmux_theme(
    root: &Path,
    check: bool,
    override_style: Option<&str>,
    override_position: Option<&str>,
    out_path: Option<&Path>,
) -> Result<RenderTmuxThemeResult, String> {
    let toml_path = root.join("usr/share/mios/mios.toml");
    if !toml_path.is_file() {
        return Err(format!("Missing SSOT toml file: {}", toml_path.display()));
    }

    let toml_str = fs::read_to_string(&toml_path)
        .map_err(|e| format!("Failed to read {}: {}", toml_path.display(), e))?;

    let doc: toml::Value = toml_str
        .parse()
        .map_err(|e| format!("Failed to parse {}: {}", toml_path.display(), e))?;

    let engine = TmuxThemeEngine::from_toml(&doc, override_style, override_position)?;
    let rendered = engine.generate_config()?;

    let target_path = if let Some(p) = out_path {
        p.to_path_buf()
    } else {
        root.join(GOLDEN)
    };

    if check {
        if !target_path.is_file() {
            return Err(format!(
                "Target fixture does not exist: {}",
                target_path.display()
            ));
        }

        let disk_content = fs::read_to_string(&target_path)
            .map_err(|e| format!("Failed to read {}: {}", target_path.display(), e))?;

        let disk_norm = disk_content.replace("\r\n", "\n");
        let rendered_norm = rendered.replace("\r\n", "\n");

        if disk_norm != rendered_norm {
            return Err(format!(
                "{}: out of sync with mios.toml [theme.tmux] projection (run 'mios-gen render-tmux-theme')",
                GOLDEN
            ));
        }
    } else {
        if let Some(parent) = target_path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create parent dir {}: {}", parent.display(), e))?;
        }

        fs::write(&target_path, rendered.as_bytes())
            .map_err(|e| format!("Failed to write {}: {}", target_path.display(), e))?;
    }

    let config_lines = rendered.lines().count();

    Ok(RenderTmuxThemeResult {
        style: engine.style,
        status_position: engine.status_position,
        config_lines,
        output_path: Some(target_path),
    })
}
