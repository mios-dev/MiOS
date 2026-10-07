// AI-hint: SSOT Fastfetch configuration generator projecting host hardware, bootc image and AI model specs into JSONC (ADR-0021 gen category).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: usr/share/mios/mios.toml, usr/share/mios/fastfetch/config.jsonc, automation/98-drift-checks.sh

#![forbid(unsafe_code)]

use regex::Regex;
use serde_json::json;
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

/// Persisted, deterministic (`--mock`) render this projector is verified against.
/// `usr/share/mios/fastfetch/config.jsonc` is NOT this generator's output: it is
/// rendered from a template by `mios-dotfiles-render` and intentionally differs.
pub const FASTFETCH_FIXTURE: &str = "tests/golden/fastfetch/mock.jsonc";

#[derive(Debug, Clone)]
pub struct FastfetchEngine {
    pub logo_type: String,
    pub mock: bool,
    pub dry_run: bool,
    #[allow(dead_code)]
    pub palette: BTreeMap<String, String>,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct RenderFastfetchResult {
    pub status: String,
    pub target: Option<PathBuf>,
    pub jsonc_len: usize,
    pub lines_count: usize,
    pub logo_type: String,
    pub mock: bool,
    pub dry_run: bool,
}

impl FastfetchEngine {
    pub fn new(
        doc: Option<&toml::Value>,
        logo_type: Option<&str>,
        mock: bool,
        dry_run: bool,
    ) -> Result<Self, String> {
        let logo = logo_type.unwrap_or("small").to_string();
        if !["small", "auto", "none", "raw"].contains(&logo.as_str()) {
            return Err(format!(
                "Invalid logo_type '{logo}', must be one of: small, auto, none, raw"
            ));
        }

        let mut palette = BTreeMap::new();
        if let Some(doc) = doc {
            if let Some(colors_tbl) = doc.get("colors").and_then(|v| v.as_table()) {
                let hex_re = match Regex::new(r"^#[0-9a-fA-F]{6}$") {
                    Ok(re) => re,
                    Err(e) => return Err(format!("Regex compilation failed: {e}")),
                };
                for (k, v) in colors_tbl {
                    if let Some(s) = v.as_str() {
                        if !hex_re.is_match(s) {
                            return Err(format!("[colors].{k}: expected #rrggbb hex color"));
                        }
                        palette.insert(k.clone(), s.to_string());
                    } else {
                        return Err(format!("[colors].{k}: expected #rrggbb string"));
                    }
                }
            }
        }

        // Fill default palette if missing
        let defaults = [
            ("bg", "#282262"),
            ("fg", "#E7DFD3"),
            ("accent", "#1A407F"),
            ("cursor", "#F35C15"),
            ("success", "#3E7765"),
            ("warning", "#F35C15"),
            ("error", "#DC271B"),
            ("info", "#1A407F"),
            ("muted", "#948E8E"),
            ("subtle", "#B7C9D7"),
        ];
        for (k, v) in defaults {
            palette
                .entry(k.to_string())
                .or_insert_with(|| v.to_string());
        }

        Ok(Self {
            logo_type: logo,
            mock,
            dry_run,
            palette,
        })
    }

    pub fn inspect_system_metadata(&self, root: &Path) -> BTreeMap<String, String> {
        if self.mock {
            let mut map = BTreeMap::new();
            map.insert(
                "os_name".to_string(),
                "MiOS Linux (bootc/OCI workstation)".to_string(),
            );
            map.insert(
                "ai_engine".to_string(),
                "mios-llm-light (llama-swap :8500)".to_string(),
            );
            map.insert(
                "active_model".to_string(),
                "Qwen2.5-Coder-7B-Instruct-GGUF".to_string(),
            );
            map.insert(
                "bootc_image".to_string(),
                "ghcr.io/mios-dev/mios:latest (sha256:7f8a91b2c3d4)".to_string(),
            );
            map.insert("mesh_nodes".to_string(), "1 (Local Node)".to_string());
            map.insert("version".to_string(), "2026.1".to_string());
            return map;
        }

        let mut os_name = "MiOS Linux".to_string();
        let os_rel_paths = [
            PathBuf::from("/etc/os-release"),
            root.join("etc/os-release"),
        ];
        for p in &os_rel_paths {
            if let Ok(content) = fs::read_to_string(p) {
                for line in content.lines() {
                    if let Some(val) = line.strip_prefix("PRETTY_NAME=") {
                        let trimmed = val.trim().trim_matches('"');
                        if !trimmed.is_empty() {
                            os_name = trimmed.to_string();
                            break;
                        }
                    }
                }
                break;
            }
        }

        let mut bootc_img = "ghcr.io/mios-dev/mios:latest".to_string();
        let ver_path = root.join("usr/share/mios/VERSION");
        if let Ok(ver) = fs::read_to_string(&ver_path) {
            let t = ver.trim();
            if !t.is_empty() {
                bootc_img = format!("ghcr.io/mios-dev/mios:{t}");
            }
        }

        let mut map = BTreeMap::new();
        map.insert("os_name".to_string(), os_name);
        map.insert(
            "ai_engine".to_string(),
            "mios-llm-light (llama-swap :8500)".to_string(),
        );
        map.insert(
            "active_model".to_string(),
            "Qwen2.5-Coder-7B-Instruct-GGUF".to_string(),
        );
        map.insert("bootc_image".to_string(), bootc_img);
        map.insert("mesh_nodes".to_string(), "1 (Local Node)".to_string());
        map.insert("version".to_string(), "2026.1".to_string());
        map
    }

    pub fn generate_jsonc(&self, root: &Path) -> Result<String, String> {
        let meta = self.inspect_system_metadata(root);

        let os_name = meta
            .get("os_name")
            .cloned()
            .unwrap_or_else(|| "MiOS Linux".to_string());
        let ai_engine = meta
            .get("ai_engine")
            .cloned()
            .unwrap_or_else(|| "mios-llm-light".to_string());
        let active_model = meta
            .get("active_model")
            .cloned()
            .unwrap_or_else(|| "Qwen2.5-Coder-7B-Instruct".to_string());
        let mesh_nodes = meta
            .get("mesh_nodes")
            .cloned()
            .unwrap_or_else(|| "1".to_string());
        let bootc_image = meta
            .get("bootc_image")
            .cloned()
            .unwrap_or_else(|| "ghcr.io/mios-dev/mios:latest".to_string());

        let config = json!({
            "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
            "logo": {
                "type": self.logo_type,
                "padding": {
                    "top": 1,
                    "left": 2,
                    "right": 2
                }
            },
            "display": {
                "separator": " 󰄾 ",
                "color": {
                    "keys": "blue",
                    "title": "cyan",
                    "separator": "yellow"
                }
            },
            "modules": [
                {"type": "title"},
                {"type": "separator"},
                {"type": "os", "key": "OS", "format": os_name},
                {"type": "host", "key": "Host"},
                {"type": "kernel", "key": "Kernel"},
                {"type": "uptime", "key": "Uptime"},
                {"type": "packages", "key": "Packages"},
                {"type": "shell", "key": "Shell"},
                {"type": "display", "key": "Display"},
                {"type": "wm", "key": "WM"},
                {"type": "cpu", "key": "CPU"},
                {"type": "gpu", "key": "GPU"},
                {"type": "memory", "key": "Memory"},
                {"type": "disk", "key": "Disk"},
                {"type": "break"},
                {"type": "custom", "key": "AI Engine", "format": ai_engine},
                {"type": "custom", "key": "Active Model", "format": active_model},
                {"type": "custom", "key": "Mesh Nodes", "format": mesh_nodes},
                {"type": "custom", "key": "Bootc Image", "format": bootc_image},
                {"type": "break"},
                {"type": "colors", "symbol": "circle"}
            ]
        });

        // Legacy parity: Python `json.dumps(config, indent=2)` escapes every non-ASCII
        // code point as lowercase \uXXXX (UTF-16 surrogate pairs above the BMP) and
        // emits no trailing newline. Structural JSON is ASCII, so escaping the pretty
        // string char-by-char only ever touches string contents.
        serde_json::to_string_pretty(&config)
            .map(|s| escape_non_ascii(&s))
            .map_err(|e| format!("Failed to serialize fastfetch JSONC: {e}"))
    }
}

fn escape_non_ascii(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        if c.is_ascii() {
            out.push(c);
        } else {
            let mut buf = [0u16; 2];
            for unit in c.encode_utf16(&mut buf) {
                out.push_str(&format!("\\u{:04x}", unit));
            }
        }
    }
    out
}

pub fn run_render_fastfetch(
    root: &Path,
    check: bool,
    out: Option<&Path>,
    logo_type: Option<&str>,
    mock: bool,
    dry_run: bool,
) -> Result<RenderFastfetchResult, String> {
    let toml_path = root.join("usr/share/mios/mios.toml");
    if !toml_path.is_file() {
        return Err(format!("Missing SSOT toml file: {}", toml_path.display()));
    }
    let doc_val = {
        let content = fs::read_to_string(&toml_path)
            .map_err(|e| format!("Failed to read {}: {e}", toml_path.display()))?;
        let val: toml::Value = toml::from_str(&content)
            .map_err(|e| format!("Failed to parse {}: {e}", toml_path.display()))?;
        Some(val)
    };

    let engine = FastfetchEngine::new(doc_val.as_ref(), logo_type, mock, dry_run)?;
    let jsonc = engine.generate_jsonc(root)?;
    let lines_count = jsonc.lines().count();
    let jsonc_len = jsonc.len();

    let target_path = out.map(PathBuf::from);

    if check {
        // Peer-lane audit (2026-10-07): without a subject, `--check` used to return
        // success having compared nothing. A check reads and compares a real artifact
        // or it fails; `--mock` only pins the metadata the render is built from.
        let target = target_path.as_ref().ok_or_else(|| {
            "fastfetch --check requires --out <artifact> to verify; nothing was compared"
                .to_string()
        })?;
        if !target.is_file() {
            return Err(format!(
                "fastfetch target does not exist for verification: {}",
                target.display()
            ));
        }
        let existing = fs::read_to_string(target)
            .map_err(|e| format!("Failed to read {}: {e}", target.display()))?;
        let norm_existing = existing.replace("\r\n", "\n");
        let norm_generated = jsonc.replace("\r\n", "\n");
        if norm_existing != norm_generated {
            return Err(format!(
                "fastfetch config drifted from SSOT projection at {}",
                target.display()
            ));
        }
    } else if let Some(target) = &target_path {
        // `--dry-run` is the no-write switch. `--mock` pins metadata only, so an
        // explicit `--out` fixture can be regenerated deterministically.
        if !dry_run {
            if let Some(parent) = target.parent() {
                if !parent.as_os_str().is_empty() && !parent.exists() {
                    fs::create_dir_all(parent).map_err(|e| {
                        format!("Failed to create parent dir {}: {e}", parent.display())
                    })?;
                }
            }
            fs::write(target, &jsonc)
                .map_err(|e| format!("Failed to write {}: {e}", target.display()))?;
        }
    }

    Ok(RenderFastfetchResult {
        status: "success".to_string(),
        target: target_path,
        jsonc_len,
        lines_count,
        logo_type: engine.logo_type,
        mock: engine.mock,
        dry_run: engine.dry_run,
    })
}
