// AI-hint: Native Windows tmux publication preserves operator configurations and backs up owned legacy projections.
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

const HEADER: &str = "# Generated from layered MiOS SSOT by native Rust.";

fn owned(text: &str) -> bool {
    text.starts_with(HEADER)
        || text.starts_with("# AI-hint: MiOS Windows Native Tmux Configuration")
}

fn publish(path: &Path, bytes: &[u8]) -> Result<(), String> {
    let parent = path.parent().ok_or("tmux projection has no parent")?;
    fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    let pending = parent.join(format!(".mios-tmux-{}.tmp", std::process::id()));
    let result = (|| {
        let mut file = OpenOptions::new().write(true).create_new(true).open(&pending)
            .map_err(|e| format!("{}: {e}", pending.display()))?;
        file.write_all(bytes).and_then(|_| file.sync_all()).map_err(|e| e.to_string())?;
        fs::rename(&pending, path).map_err(|e| format!("{}: {e}", path.display()))
    })();
    if result.is_err() { let _ = fs::remove_file(&pending); }
    result
}

/// Render before publication. Replace legacy copies only when absent or marked
/// as MiOS-owned; save their exact old bytes before replacing them.
/// Returns the paths of pre-existing owned files, used to scope live reloads.
pub fn stage(config: &serde_json::Value, canonical: &Path, legacy: &[PathBuf], font_verified: bool)
    -> Result<Vec<PathBuf>, String>
{
    let rendered = crate::launcher::host_tmux_config_with_font(config, font_verified)?;
    let mut previous = Vec::new();
    for path in std::iter::once(canonical).chain(legacy.iter().map(PathBuf::as_path)) {
        match fs::symlink_metadata(path) {
            Ok(meta) if !meta.is_file() || meta.file_type().is_symlink() => return Err(format!("{}: refusing non-regular tmux projection", path.display())),
            Ok(_) => {
                let bytes = fs::read(path).map_err(|e| format!("{}: {e}", path.display()))?;
                let managed = std::str::from_utf8(&bytes).map(owned).unwrap_or(false);
                if path == canonical && !managed { return Err(format!("{}: canonical tmux projection is not MiOS-owned", path.display())); }
                previous.push((path.to_path_buf(), Some(bytes), managed));
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => previous.push((path.to_path_buf(), None, false)),
            Err(e) => return Err(format!("{}: {e}", path.display())),
        }
    }
    let mut reload = Vec::new();
    for (path, bytes, managed) in previous {
        if bytes.is_some() && !managed { continue; }
        if managed { reload.push(path.clone()); }
        if bytes.as_deref() == Some(rendered.as_bytes()) { continue; }
        if let Some(bytes) = bytes {
            let stamp = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map_err(|e| e.to_string())?.as_nanos();
            let backup = path.with_file_name(format!("{}.pre-native-{stamp}", path.file_name().ok_or("tmux filename missing")?.to_string_lossy()));
            let mut file = OpenOptions::new().write(true).create_new(true).open(&backup).map_err(|e| e.to_string())?;
            file.write_all(&bytes).and_then(|_| file.sync_all()).map_err(|e| e.to_string())?;
        }
        publish(&path, rendered.as_bytes())?;
    }
    Ok(reload)
}
