// AI-hint: Rust AI-plane linting tool for [agent_pipe] budget keys and recursion/width bounds.
use regex::Regex;
use std::fs;
use std::path::{Path, PathBuf};

pub const BUDGET_KEYS: &[&str] = &[
    "tool_max_iters",
    "replan_max",
    "no_progress_window",
    "max_consecutive_failures",
    "wall_clock_budget_s",
    "reflexion_enable",
    "swarm_max_width",
    "max_dispatch_depth",
    "default_hop_budget",
];

fn key_in_toml_value(val: &toml::Value, target_key: &str) -> bool {
    if let Some(table) = val.as_table() {
        if table.contains_key(target_key) {
            return true;
        }
        for (_k, v) in table {
            if key_in_toml_value(v, target_key) {
                return true;
            }
        }
    }
    false
}

pub fn validate_budgets(
    toml_val: &toml::Value,
    code_contents: &str,
    budget_keys: &[&str],
) -> Result<(), Vec<String>> {
    let agent_pipe = toml_val.get("agent_pipe");
    let dispatch = toml_val.get("dispatch");

    let mut missing = Vec::new();

    for &key in budget_keys {
        let in_agent_pipe = agent_pipe.map_or(false, |v| key_in_toml_value(v, key));
        let in_dispatch = dispatch.map_or(false, |v| key_in_toml_value(v, key));

        if !in_agent_pipe && !in_dispatch {
            missing.push(format!("{} (missing from mios.toml)", key));
            continue;
        }

        let quoted_pattern = format!(r#"['"]{}['"]"#, regex::escape(key));
        let re = Regex::new(&quoted_pattern).unwrap();

        if !re.is_match(code_contents) && !code_contents.contains(key) {
            missing.push(key.to_string());
        }
    }

    if missing.is_empty() {
        Ok(())
    } else {
        Err(missing)
    }
}

fn read_all_python_files(dir: &Path) -> std::io::Result<String> {
    let mut code = String::new();
    if dir.is_dir() {
        for entry in walkdir::WalkDir::new(dir).into_iter().filter_map(|e| e.ok()) {
            let path = entry.path();
            if path.is_file() && path.extension().map_or(false, |ext| ext == "py") {
                if let Ok(c) = fs::read_to_string(path) {
                    code.push_str(&c);
                    code.push('\n');
                }
            }
        }
    }
    Ok(code)
}

fn main() {
    let root_str = std::env::var("MIOS_DRIFT_ROOT")
        .unwrap_or_else(|_| std::env::current_dir().unwrap().to_string_lossy().to_string());
    let root = PathBuf::from(&root_str);

    let toml_path = root.join("usr/share/mios/mios.toml");
    if !toml_path.exists() {
        eprintln!("    Missing mios.toml at {}", toml_path.display());
        std::process::exit(1);
    }

    let toml_content = match fs::read_to_string(&toml_path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("    Failed to read mios.toml: {}", e);
            std::process::exit(1);
        }
    };

    let toml_val: toml::Value = match toml::from_str(&toml_content) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("    Failed to parse mios.toml: {}", e);
            std::process::exit(1);
        }
    };

    let mut search_dir = root.join("usr/lib/mios/agent-pipe");
    if !search_dir.is_dir() {
        search_dir = root.clone();
    }

    let code_contents = match read_all_python_files(&search_dir) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("    Failed to read python code: {}", e);
            std::process::exit(1);
        }
    };

    match validate_budgets(&toml_val, &code_contents, BUDGET_KEYS) {
        Ok(()) => {
            println!("[mios-aiplane-lint] PASS: all [agent_pipe]/[dispatch] budget keys defined and consumed");
            std::process::exit(0);
        }
        Err(missing) => {
            eprintln!(
                "    Missing code consumers or TOML definitions for budget keys: {:?}",
                missing
            );
            std::process::exit(1);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_budgets_pass() {
        let toml_str = r#"
            [agent_pipe]
            tool_max_iters = 15
            replan_max = 5

            [dispatch.autonomy]
            max_dispatch_depth = 2

            [dispatch]
            default_hop_budget = 2
        "#;
        let toml_val: toml::Value = toml::from_str(toml_str).unwrap();
        let code = r#"
            iter_limit = config.get("tool_max_iters", 15)
            max_replan = config.get("replan_max", 5)
            depth = config.get("max_dispatch_depth", 2)
            hop = config.get("default_hop_budget", 2)
        "#;
        let keys = vec!["tool_max_iters", "replan_max", "max_dispatch_depth", "default_hop_budget"];
        assert!(validate_budgets(&toml_val, code, &keys).is_ok());
    }

    #[test]
    fn test_validate_budgets_missing_toml() {
        let toml_str = r#"
            [agent_pipe]
            tool_max_iters = 15
        "#;
        let toml_val: toml::Value = toml::from_str(toml_str).unwrap();
        let code = r#"
            iter_limit = config.get("tool_max_iters", 15)
            max_replan = config.get("replan_max", 5)
        "#;
        let keys = vec!["tool_max_iters", "replan_max"];
        let res = validate_budgets(&toml_val, code, &keys);
        assert!(res.is_err());
        let errs = res.unwrap_err();
        assert_eq!(errs.len(), 1);
        assert!(errs[0].contains("replan_max (missing from mios.toml)"));
    }

    #[test]
    fn test_validate_budgets_missing_code() {
        let toml_str = r#"
            [agent_pipe]
            tool_max_iters = 15
            replan_max = 5
        "#;
        let toml_val: toml::Value = toml::from_str(toml_str).unwrap();
        let code = r#"
            iter_limit = config.get("tool_max_iters", 15)
        "#;
        let keys = vec!["tool_max_iters", "replan_max"];
        let res = validate_budgets(&toml_val, code, &keys);
        assert!(res.is_err());
        let errs = res.unwrap_err();
        assert_eq!(errs.len(), 1);
        assert_eq!(errs[0], "replan_max");
    }
}
