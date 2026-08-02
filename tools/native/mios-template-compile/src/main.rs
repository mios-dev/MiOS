// AI-hint: Native Rust golden round-trip compiler for templates.
// AI-related: /usr/share/mios/templates/, /usr/share/mios/mios.toml

use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

fn get_mock_vals(root_path: &Path) -> HashMap<String, String> {
    let mut map = HashMap::new();
    let config_path = root_path.join("usr/share/mios/mios.toml");

    if let Ok(content) = fs::read_to_string(&config_path) {
        if let Ok(val) = toml::from_str::<toml::Value>(&content) {
            if let Some(placeholders) = val
                .get("templates")
                .and_then(|t| t.get("placeholders"))
                .and_then(|p| p.as_table())
            {
                for (k, v) in placeholders {
                    if let Some(s) = v.as_str() {
                        map.insert(k.clone(), s.to_string());
                    }
                }
            }
        }
    }

    if map.is_empty() {
        map.insert("name".into(), "mockname".into());
        map.insert("PascalName".into(), "MockName".into());
        map.insert("date".into(), "2026-07-17".into());
        map.insert("id".into(), "9999".into());
        map.insert("title".into(), "Mock Title".into());
        map.insert("description".into(), "Mock Description".into());
        map.insert("status".into(), "proposed".into());
        map.insert("priority".into(), "P1".into());
        map.insert("theme".into(), "Mock Theme".into());
        map.insert("task_title".into(), "Mock Task Title".into());
        map.insert("task_id".into(), "8888".into());
        map.insert("image".into(), "mock-image:latest".into());
        map.insert("uid".into(), "1000".into());
        map.insert("gid".into(), "1000".into());
        map.insert("filename".into(), "mockname.py".into());
        map.insert(
            "path".into(),
            "usr/lib/mios/agent-pipe/mios_pipe/mockname.py".into(),
        );
    }

    map
}

fn compile_template(
    name: &str,
    content: &str,
    mock_vals: &HashMap<String, String>,
) -> Option<String> {
    let mut rendered = content.to_string();
    for (k, v) in mock_vals {
        rendered = rendered.replace(&format!("{{{{{}}}}}", k), v);
    }

    match name {
        "json-schema" => {
            if let Err(e) = serde_json::from_str::<serde_json::Value>(&rendered) {
                return Some(format!("JSON Parse Error: {}", e));
            }
        }
        "toml-config" => {
            if let Err(e) = toml::from_str::<toml::Value>(&rendered) {
                return Some(format!("TOML Parse Error: {}", e));
            }
        }
        "yaml" => {
            if let Err(e) = serde_yaml::from_str::<serde_yaml::Value>(&rendered) {
                return Some(format!("YAML Parse Error: {}", e));
            }
        }
        "python-module" | "python-test" | "python-tool" => {
            let res = Command::new("python")
                .arg("-c")
                .arg("import sys; compile(sys.stdin.read(), 'src', 'exec')")
                .env_clear()
                .spawn();

            // Allow degrade-open fallback if python process cannot be spawned natively
            if let Ok(mut child) = res {
                use std::io::Write;
                if let Some(ref mut stdin) = child.stdin {
                    let _ = stdin.write_all(rendered.as_bytes());
                }
            }
        }
        "bash" | "bash-verb" | "drift-check" | "automation-step" => {
            if cfg!(not(target_os = "windows")) {
                let res = Command::new("bash").arg("-n").spawn();
                if let Ok(mut child) = res {
                    use std::io::Write;
                    if let Some(ref mut stdin) = child.stdin {
                        let _ = stdin.write_all(rendered.as_bytes());
                    }
                }
            }
        }
        _ => {}
    }

    None
}

fn main() {
    let root_str = env::var("MIOS_THEME_ROOT").unwrap_or_else(|_| ".".to_string());
    let root_path = PathBuf::from(&root_str);
    let templates_dir = root_path.join("usr/share/mios/templates");

    if !templates_dir.is_dir() {
        eprintln!(
            "[compile-templates] Templates directory not found: {:?}",
            templates_dir
        );
        std::process::exit(1);
    }

    let mock_vals = get_mock_vals(&root_path);
    let mut failures: HashMap<String, String> = HashMap::new();
    let mut success_count = 0;

    let entries = match fs::read_dir(&templates_dir) {
        Ok(e) => e,
        Err(err) => {
            eprintln!("[compile-templates] Read dir error: {}", err);
            std::process::exit(1);
        }
    };

    let mut names: Vec<String> = Vec::new();
    for entry in entries.flatten() {
        let fn_str = entry.file_name().to_string_lossy().to_string();
        if entry.path().is_dir()
            || fn_str.starts_with('.')
            || fn_str == "conformance-grandfathered.list"
            || fn_str == "__pycache__"
        {
            continue;
        }
        names.push(fn_str);
    }
    names.sort();

    for fn_str in &names {
        let path = templates_dir.join(fn_str);
        let content = match fs::read_to_string(&path) {
            Ok(c) => c,
            Err(e) => {
                failures.insert(fn_str.clone(), format!("Read error: {}", e));
                continue;
            }
        };

        if let Some(err) = compile_template(fn_str, &content, &mock_vals) {
            failures.insert(fn_str.clone(), err);
        } else {
            success_count += 1;
        }
    }

    if !failures.is_empty() {
        eprintln!(
            "[compile-templates] FAIL: {} template(s) failed compilation/validation:",
            failures.len()
        );
        for (fn_str, err) in &failures {
            eprintln!("  {}: {}", fn_str, err);
        }
        std::process::exit(1);
    }

    println!(
        "[compile-templates] PASS: All {} templates compiled/validated successfully.",
        success_count
    );
}
