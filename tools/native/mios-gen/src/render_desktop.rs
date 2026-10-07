// AI-hint: Renders usr/share/applications/*.desktop files from SSOT [ports] and [desktop.launchers] table.
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/main.rs, usr/share/mios/mios.toml, automation/98-drift-checks.sh

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use toml::Value;

const DEFAULT_TOML_PATH: &str = "usr/share/mios/mios.toml";
const APPLICATIONS_DIR: &str = "usr/share/applications";

pub fn load_ssot(root: &Path) -> Result<(BTreeMap<String, i64>, BTreeMap<String, Value>), String> {
    let toml_path = match std::env::var("MIOS_TOML") {
        Ok(v) if !v.trim().is_empty() => PathBuf::from(v.trim()),
        _ => root.join(DEFAULT_TOML_PATH),
    };

    let content = fs::read_to_string(&toml_path)
        .map_err(|e| format!("render-desktop: {} could not be read: {e}", toml_path.display()))?;

    let parsed: Value = content
        .parse()
        .map_err(|e| format!("render-desktop: {} did not parse: {e}", toml_path.display()))?;

    let mut ports = BTreeMap::new();
    if let Some(ports_table) = parsed.get("ports").and_then(|p| p.as_table()) {
        for (k, v) in ports_table {
            if let Some(i) = v.as_integer() {
                ports.insert(k.clone(), i);
            }
        }
    }

    let mut launchers = BTreeMap::new();
    if let Some(desktop) = parsed.get("desktop").and_then(|d| d.as_table()) {
        if let Some(launchers_table) = desktop.get("launchers").and_then(|l| l.as_table()) {
            for (k, v) in launchers_table {
                launchers.insert(k.clone(), v.clone());
            }
        }
    }

    Ok((ports, launchers))
}

pub fn render_launcher(name: &str, cfg_val: &Value, ports: &BTreeMap<String, i64>) -> String {
    let _ = name;
    let cfg = cfg_val.as_table();

    let port_key = cfg
        .and_then(|t| t.get("port_key"))
        .and_then(|v| v.as_str())
        .unwrap_or("");

    let port = if !port_key.is_empty() {
        ports.get(port_key).copied()
    } else {
        None
    };

    let exec_cmd = if let Some(cmd) = cfg.and_then(|t| t.get("exec_cmd")).and_then(|v| v.as_str()) {
        cmd.to_string()
    } else if let Some(p) = port {
        let scheme = cfg
            .and_then(|t| t.get("scheme"))
            .and_then(|v| v.as_str())
            .unwrap_or("http");
        let path = cfg
            .and_then(|t| t.get("path"))
            .and_then(|v| v.as_str())
            .unwrap_or("/");
        format!("xdg-open {scheme}://localhost:{p}{path}")
    } else {
        String::new()
    };

    let comment_raw = cfg
        .and_then(|t| t.get("comment"))
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let comment = if let Some(p) = port {
        comment_raw.replace("{port}", &p.to_string())
    } else {
        comment_raw.to_string()
    };

    let ai_hint_raw = cfg
        .and_then(|t| t.get("ai_hint"))
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let ai_hint = if let Some(p) = port {
        ai_hint_raw.replace("{port}", &p.to_string())
    } else {
        ai_hint_raw.to_string()
    };

    let ai_related_raw = cfg
        .and_then(|t| t.get("ai_related"))
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let ai_related = if ai_related_raw.is_empty() && port.is_some() {
        format!("localhost:{}", port.unwrap())
    } else {
        ai_related_raw.to_string()
    };

    let mut lines = Vec::new();
    if !ai_hint.is_empty() {
        lines.push(format!("# AI-hint: {ai_hint}"));
    }
    if !ai_related.is_empty() {
        lines.push(format!("# AI-related: {ai_related}"));
    }

    lines.push("[Desktop Entry]".to_string());
    lines.push("Type=Application".to_string());
    lines.push("Version=1.0".to_string());

    let title = cfg
        .and_then(|t| t.get("title"))
        .and_then(|v| v.as_str())
        .unwrap_or("");
    lines.push(format!("Name={title}"));

    if let Some(gn) = cfg.and_then(|t| t.get("generic_name")).and_then(|v| v.as_str()) {
        lines.push(format!("GenericName={gn}"));
    }
    if !comment.is_empty() {
        lines.push(format!("Comment={comment}"));
    }
    if !exec_cmd.is_empty() {
        lines.push(format!("Exec={exec_cmd}"));
    }
    if let Some(icon) = cfg.and_then(|t| t.get("icon")).and_then(|v| v.as_str()) {
        lines.push(format!("Icon={icon}"));
    }
    if let Some(cat) = cfg.and_then(|t| t.get("categories")).and_then(|v| v.as_str()) {
        lines.push(format!("Categories={cat}"));
    }
    if let Some(kw) = cfg.and_then(|t| t.get("keywords")).and_then(|v| v.as_str()) {
        lines.push(format!("Keywords={kw}"));
    }

    let terminal = cfg
        .and_then(|t| t.get("terminal"))
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    lines.push(format!("Terminal={terminal}"));

    let startup_notify = cfg
        .and_then(|t| t.get("startup_notify"))
        .and_then(|v| v.as_bool())
        .unwrap_or(true);
    lines.push(format!("StartupNotify={startup_notify}"));

    if let Some(wm) = cfg.and_then(|t| t.get("startup_wm_class")).and_then(|v| v.as_str()) {
        lines.push(format!("StartupWMClass={wm}"));
    }
    if let Some(nd) = cfg.and_then(|t| t.get("no_display")).and_then(|v| v.as_bool()) {
        lines.push(format!("NoDisplay={nd}"));
    }

    if let Some(tc) = cfg.and_then(|t| t.get("trailing_comments")).and_then(|v| v.as_array()) {
        for comment_line in tc {
            if let Some(s) = comment_line.as_str() {
                lines.push(s.to_string());
            }
        }
    }

    let mut out = lines.join("\n");
    out.push('\n');
    out
}

pub fn run_render_desktop(
    root: &Path,
    check: bool,
) -> Result<(String, i32), (String, i32)> {
    let (ports, launchers) = load_ssot(root).map_err(|e| (e, 1))?;
    let apps_dir = root.join(APPLICATIONS_DIR);

    let mut on_disk = Vec::new();
    if apps_dir.is_dir() {
        if let Ok(entries) = fs::read_dir(&apps_dir) {
            for entry in entries.flatten() {
                let name = entry.file_name().to_string_lossy().to_string();
                if name.ends_with(".desktop") {
                    on_disk.push(name);
                }
            }
        }
    }
    on_disk.sort();

    if launchers.is_empty() {
        let msg = format!(
            "[render-desktop] mios.toml [desktop.launchers] is empty or absent, but {} .desktop file(s) ship in usr/share/applications. Nothing would be compared.",
            on_disk.len()
        );
        return Err((msg, 1));
    }

    let mut unmanaged = Vec::new();
    for f in &on_disk {
        let base = &f[..f.len() - 8];
        if !launchers.contains_key(base) {
            unmanaged.push(f.clone());
        }
    }

    if !unmanaged.is_empty() && check {
        let mut lines = Vec::new();
        for f in &unmanaged {
            let base = &f[..f.len() - 8];
            lines.push(format!(
                "[render-desktop] DRIFT: {f} ships but no [desktop.launchers.{base}] declares it"
            ));
        }
        return Err((lines.join("\n"), 1));
    }

    let mut drifted = Vec::new();
    for (name, cfg) in &launchers {
        let rendered = render_launcher(name, cfg, &ports);
        let target_path = apps_dir.join(format!("{name}.desktop"));

        if check {
            if !target_path.is_file() {
                drifted.push(format!("{name}.desktop missing"));
                continue;
            }
            let current = fs::read_to_string(&target_path).unwrap_or_default();
            let current_norm = current.replace("\r\n", "\n");
            let rendered_norm = rendered.replace("\r\n", "\n");
            if current_norm != rendered_norm {
                drifted.push(format!("{name}.desktop content drifted"));
            }
        } else {
            if let Some(parent) = target_path.parent() {
                let _ = fs::create_dir_all(parent);
            }
            if let Err(e) = fs::write(&target_path, rendered.as_bytes()) {
                return Err((format!("render-desktop: write {} failed: {e}", target_path.display()), 1));
            }
        }
    }

    if check {
        if !drifted.is_empty() {
            let mut lines = Vec::new();
            for d in drifted {
                lines.push(format!("[render-desktop] DRIFT: {d}"));
            }
            return Err((lines.join("\n"), 1));
        }
        Ok(("[render-desktop] All .desktop launchers match SSOT".to_string(), 0))
    } else {
        Ok(("[render-desktop] Rendered .desktop launchers from SSOT".to_string(), 0))
    }
}
