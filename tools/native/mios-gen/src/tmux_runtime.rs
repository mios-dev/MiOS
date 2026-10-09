// AI-hint: Native `render-tmux-theme --runtime DIR` -- projects a caller-owned tmux.conf (layered theme + keybindings) and mios.omp.json from ALL SSOT tiers (vendor < host < user), the `--runtime` mode of the deleted tmux_theme.py.
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/tmux_theme.rs, usr/lib/mios/mios_toml.py, usr/libexec/mios/ux/theme_sync.py, etc/profile.d/mios-prompt.sh, usr/libexec/mios/mios-terminal

#![forbid(unsafe_code)]

use crate::tmux_theme::{is_remote_terminal, TmuxThemeEngine};
use std::env;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;

const KEYS_PATH: &str = "usr/share/mios/tmux/mios-keys.tmux.conf";

fn env_nonempty(key: &str) -> Option<String> {
    env::var(key).ok().filter(|v| !v.trim().is_empty())
}

/// Sorted `*.toml` drop-ins of `dir` (systemd `.d` ordering by basename).
fn fragments(dir: &Path) -> Vec<PathBuf> {
    let mut out: Vec<PathBuf> = match fs::read_dir(dir) {
        Ok(rd) => rd
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| p.is_file() && p.extension().map(|x| x == "toml").unwrap_or(false))
            .collect(),
        Err(_) => Vec::new(),
    };
    out.sort_by(|a, b| a.file_name().cmp(&b.file_name()));
    out
}

/// Layer paths, lowest precedence first (mirrors `mios_toml.layer_paths`):
/// tier-major vendor < host < user, each tier's monolith then its `mios.d/*.toml`.
pub fn layer_paths(root: &Path) -> Vec<PathBuf> {
    let toml_root = env_nonempty("MIOS_TOML_ROOT");
    let vendor = env_nonempty("MIOS_VENDOR_TOML")
        .or_else(|| env_nonempty("MIOS_TOML"))
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            if let Some(r) = &toml_root {
                Path::new(r).join("usr/share/mios/mios.toml")
            } else if Path::new("/usr/share/mios/mios.toml").exists() {
                PathBuf::from("/usr/share/mios/mios.toml")
            } else {
                root.join("usr/share/mios/mios.toml")
            }
        });
    let host = PathBuf::from(
        env::var("MIOS_HOST_TOML").unwrap_or_else(|_| "/etc/mios/mios.toml".to_string()),
    );
    let user = env_nonempty("MIOS_USER_TOML")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            let cfg = env_nonempty("XDG_CONFIG_HOME")
                .map(PathBuf::from)
                .or_else(|| {
                    env_nonempty("HOME")
                        .or_else(|| env_nonempty("USERPROFILE"))
                        .map(|h| Path::new(&h).join(".config"))
                })
                .unwrap_or_else(|| PathBuf::from(".config"));
            cfg.join("mios/mios.toml")
        });
    let vendor_d = env_nonempty("MIOS_VENDOR_TOML_D")
        .map(PathBuf::from)
        .unwrap_or_else(|| match &toml_root {
            Some(r) => Path::new(r).join("usr/lib/mios/mios.d"),
            None => PathBuf::from("/usr/lib/mios/mios.d"),
        });
    let host_d = env_nonempty("MIOS_HOST_TOML_D")
        .map(PathBuf::from)
        .unwrap_or_else(|| host.parent().unwrap_or(Path::new("")).join("mios.d"));
    let user_d = env_nonempty("MIOS_USER_TOML_D")
        .map(PathBuf::from)
        .unwrap_or_else(|| user.parent().unwrap_or(Path::new("")).join("mios.d"));

    let mut layers = vec![vendor];
    layers.extend(fragments(&vendor_d));
    layers.push(host);
    layers.extend(fragments(&host_d));
    layers.push(user);
    layers.extend(fragments(&user_d));
    layers
}

/// Recursive merge: later wins; an empty string never overrides a non-empty value below it.
pub fn deep_merge(dst: &mut toml::Value, src: toml::Value) {
    match (dst, src) {
        (toml::Value::Table(d), toml::Value::Table(s)) => {
            for (k, v) in s {
                match d.get_mut(&k) {
                    Some(existing) if existing.is_table() && v.is_table() => {
                        deep_merge(existing, v)
                    }
                    Some(existing) => {
                        let empty = v.as_str().map(|x| x.is_empty()).unwrap_or(false);
                        let below_set = !matches!(existing.as_str(), Some("") | None);
                        if !(empty && below_set) {
                            *existing = v;
                        }
                    }
                    None => {
                        d.insert(k, v);
                    }
                }
            }
        }
        (d, s) => *d = s,
    }
}

/// Full layered SSOT. The vendor tier is mandatory; a missing or unreadable host/user
/// overlay is skipped (a broken overlay must not crash a reader, as in `mios_toml`).
pub fn load_layered(root: &Path) -> Result<toml::Value, String> {
    let layers = layer_paths(root);
    let vendor = &layers[0];
    if !vendor.is_file() {
        return Err(format!("Missing SSOT toml file: {}", vendor.display()));
    }
    let mut merged = toml::Value::Table(toml::map::Map::new());
    for (i, path) in layers.iter().enumerate() {
        if !path.is_file() {
            continue;
        }
        let parsed = fs::read_to_string(path)
            .map_err(|e| e.to_string())
            .and_then(|s| s.parse::<toml::Value>().map_err(|e| e.to_string()));
        match parsed {
            Ok(v) => deep_merge(&mut merged, v),
            Err(e) if i == 0 => {
                return Err(format!(
                    "Failed to load vendor SSOT {}: {}",
                    path.display(),
                    e
                ))
            }
            Err(_) => {}
        }
    }
    Ok(merged)
}

fn exe_name(base: &str) -> String {
    if cfg!(windows) {
        format!("{base}.exe")
    } else {
        base.to_string()
    }
}

fn find_unit_gen(root: &Path) -> Option<PathBuf> {
    let name = exe_name("mios-unit-gen");
    let mut cands: Vec<PathBuf> = Vec::new();
    if let Some(p) = env_nonempty("MIOS_UNIT_GEN") {
        cands.push(PathBuf::from(p));
    }
    if let Ok(me) = env::current_exe() {
        if let Some(dir) = me.parent() {
            cands.push(dir.join(&name));
        }
    }
    for profile in ["release", "debug"] {
        cands.push(root.join("tools/native/target").join(profile).join(&name));
    }
    cands.push(PathBuf::from("/usr/libexec/mios").join(&name));
    cands.into_iter().find(|p| p.is_file())
}

fn find_theme_sync(root: &Path) -> Option<PathBuf> {
    let mut cands: Vec<PathBuf> = Vec::new();
    if let Some(p) = env_nonempty("MIOS_THEME_SYNC") {
        cands.push(PathBuf::from(p));
    }
    cands.push(root.join("usr/libexec/mios/ux/theme_sync.py"));
    cands.push(PathBuf::from("/usr/libexec/mios/ux/theme_sync.py"));
    cands.into_iter().find(|p| p.is_file())
}

/// Create the projection directory 0700, refuse symlinks and (on Linux) directories
/// the caller does not own. `/proc/self` is owned by the process uid, which gives a
/// safe-Rust `getuid()` without `unsafe`.
fn prepare_dir(dir: &Path) -> Result<(), String> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::{DirBuilderExt, MetadataExt, PermissionsExt};
        let mut b = fs::DirBuilder::new();
        b.recursive(true).mode(0o700);
        b.create(dir)
            .map_err(|e| format!("cannot create {}: {e}", dir.display()))?;
        let meta = fs::symlink_metadata(dir).map_err(|e| e.to_string())?;
        if meta.file_type().is_symlink() || !meta.is_dir() {
            return Err("tmux projection directory must be a real directory".to_string());
        }
        if let Ok(me) = fs::metadata("/proc/self") {
            if meta.uid() != me.uid() {
                return Err("tmux projection directory must belong to the caller".to_string());
            }
        }
        let _ = fs::set_permissions(dir, fs::Permissions::from_mode(0o700));
    }
    #[cfg(not(unix))]
    {
        fs::create_dir_all(dir).map_err(|e| format!("cannot create {}: {e}", dir.display()))?;
    }
    Ok(())
}

fn write_atomic(path: &Path, text: &str) -> Result<(), String> {
    let tmp = path.with_extension("tmp-mios");
    {
        let mut f = fs::File::create(&tmp).map_err(|e| format!("{}: {e}", tmp.display()))?;
        f.write_all(text.as_bytes())
            .map_err(|e| format!("{}: {e}", tmp.display()))?;
    }
    fs::rename(&tmp, path).map_err(|e| {
        let _ = fs::remove_file(&tmp);
        format!("{}: {e}", path.display())
    })
}

fn render_keys(root: &Path, dir: &Path, merged: &toml::Value) -> Result<String, String> {
    let kb = merged
        .get("keybindings")
        .ok_or_else(|| "Missing [keybindings] section in layered SSOT".to_string())?;
    let unit_gen = find_unit_gen(root)
        .ok_or_else(|| "mios-unit-gen not found (set MIOS_UNIT_GEN or build it)".to_string())?;
    let src = dir.join(".keybindings.in.json");
    let payload = serde_json::json!({ "keybindings": kb });
    fs::write(&src, payload.to_string()).map_err(|e| format!("{}: {e}", src.display()))?;
    let out = Command::new(&unit_gen)
        .args(["keybindings", "--from-json"])
        .arg(&src)
        .arg("--emit-json")
        .output();
    let _ = fs::remove_file(&src);
    let out = out.map_err(|e| format!("{}: {e}", unit_gen.display()))?;
    if !out.status.success() {
        return Err(format!(
            "mios-unit-gen keybindings failed: {}",
            String::from_utf8_lossy(&out.stderr).trim()
        ));
    }
    let parsed: serde_json::Value = serde_json::from_slice(&out.stdout)
        .map_err(|e| format!("mios-unit-gen keybindings emitted invalid JSON: {e}"))?;
    parsed
        .get(KEYS_PATH)
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .ok_or_else(|| format!("mios-unit-gen keybindings output lacks {KEYS_PATH}"))
}

fn render_prompt(root: &Path) -> Result<String, String> {
    let script = find_theme_sync(root)
        .ok_or_else(|| "theme_sync.py not found (set MIOS_THEME_SYNC)".to_string())?;
    let interpreters: &[&str] = if cfg!(windows) {
        &["python", "python3"]
    } else {
        &["python3", "python"]
    };
    let mut last_err = String::from("no python interpreter found");
    for py in interpreters {
        let mut cmd = Command::new(py);
        cmd.arg(&script).arg("--render-prompt");
        if is_remote_terminal() {
            cmd.arg("--remote");
        }
        match cmd.output() {
            Ok(o) if o.status.success() => {
                return String::from_utf8(o.stdout)
                    .map_err(|e| format!("prompt renderer emitted non-UTF-8: {e}"))
            }
            Ok(o) => {
                return Err(format!(
                    "prompt renderer failed: {}",
                    String::from_utf8_lossy(&o.stderr).trim()
                ))
            }
            Err(e) => last_err = format!("{py}: {e}"),
        }
    }
    Err(last_err)
}

/// Project `tmux.conf` (theme + keybindings) and `mios.omp.json` from all SSOT tiers
/// into `dir`. Nothing is written until every artifact has rendered, so a failed
/// render never leaves a half-projected directory.
pub fn project_runtime(root: &Path, dir: &Path) -> Result<(), String> {
    let merged = load_layered(root)?;
    let theme = TmuxThemeEngine::from_toml(&merged, None, None)?.generate_config()?;
    prepare_dir(dir)?;
    let keys = render_keys(root, dir, &merged)?;
    let omp = render_prompt(root)?;
    let tmux_conf = format!("{theme}\n{keys}");
    write_atomic(&dir.join("mios.omp.json"), &omp)?;
    write_atomic(&dir.join("tmux.conf"), &tmux_conf)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse(s: &str) -> toml::Value {
        s.parse().unwrap()
    }

    #[test]
    fn higher_layer_wins_and_tables_merge() {
        let mut d = parse("[a]\nx = 1\ny = 2\n");
        deep_merge(&mut d, parse("[a]\ny = 3\n[b]\nz = 4\n"));
        assert_eq!(d["a"]["x"].as_integer(), Some(1));
        assert_eq!(d["a"]["y"].as_integer(), Some(3));
        assert_eq!(d["b"]["z"].as_integer(), Some(4));
    }

    #[test]
    fn empty_string_never_overrides_set_value() {
        let mut d = parse("[a]\nk = \"keep\"\nn = \"\"\n");
        deep_merge(&mut d, parse("[a]\nk = \"\"\nn = \"fill\"\n"));
        assert_eq!(d["a"]["k"].as_str(), Some("keep"));
        assert_eq!(d["a"]["n"].as_str(), Some("fill"));
    }
}
