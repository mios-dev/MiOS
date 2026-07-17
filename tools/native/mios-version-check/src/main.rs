use std::fs;
use std::path::{Path, PathBuf};
use std::process;

fn main() {
    // Determine the root directory (default to ".")
    let args: Vec<String> = std::env::args().collect();
    let root_dir = if args.len() > 1 {
        PathBuf::from(&args[1])
    } else {
        PathBuf::from(".")
    };

    // 1. Read VERSION file
    let version_path = root_dir.join("VERSION");
    let version_content = match fs::read_to_string(&version_path) {
        Ok(c) => c.trim().to_string(),
        Err(e) => {
            eprintln!("[mios-version-check] ERROR: Failed to read {:?}: {}", version_path, e);
            process::exit(1);
        }
    };

    // 2. Read mios.toml [meta].mios_version
    let toml_path = root_dir.join("usr/share/mios/mios.toml");
    let toml_content = match fs::read_to_string(&toml_path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("[mios-version-check] ERROR: Failed to read {:?}: {}", toml_path, e);
            process::exit(1);
        }
    };

    // Simple TOML line parse to find [meta].mios_version
    let mut mios_version = None;
    let mut in_meta = false;
    for line in toml_content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with('[') && trimmed.ends_with(']') {
            let section = trimmed[1..trimmed.len() - 1].trim();
            if section == "meta" {
                in_meta = true;
            } else {
                in_meta = false;
            }
        } else if in_meta && trimmed.starts_with("mios_version") {
            if let Some(pos) = trimmed.find('=') {
                let val = trimmed[pos + 1..].trim();
                let val_clean = val.trim_matches('"').trim_matches('\'').trim().to_string();
                mios_version = Some(val_clean);
                break;
            }
        }
    }

    let ssot_version = match mios_version {
        Some(v) => v,
        None => {
            eprintln!("[mios-version-check] ERROR: mios_version not found under [meta] in {:?}", toml_path);
            process::exit(1);
        }
    };

    // 3. Read Containerfile ARG MIOS_VERSION=
    let containerfile_path = root_dir.join("Containerfile");
    let containerfile_content = match fs::read_to_string(&containerfile_path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("[mios-version-check] ERROR: Failed to read {:?}: {}", containerfile_path, e);
            process::exit(1);
        }
    };

    let mut arg_version = None;
    for line in containerfile_content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("ARG") && trimmed.contains("MIOS_VERSION=") {
            if let Some(pos) = trimmed.find('=') {
                let val = trimmed[pos + 1..].trim();
                let val_clean = val.split_whitespace().next().unwrap_or("").to_string();
                arg_version = Some(val_clean);
                break;
            }
        }
    }

    let containerfile_version = match arg_version {
        Some(v) => v,
        None => {
            eprintln!("[mios-version-check] ERROR: ARG MIOS_VERSION not found in {:?}", containerfile_path);
            process::exit(1);
        }
    };

    // 4. Compare all versions
    let mut has_drift = false;
    if version_content != ssot_version {
        eprintln!(
            "[mios-version-check] DRIFT: VERSION file ({}) != mios.toml meta.mios_version ({})",
            version_content, ssot_version
        );
        has_drift = true;
    }
    if containerfile_version != ssot_version {
        eprintln!(
            "[mios-version-check] DRIFT: Containerfile ARG MIOS_VERSION ({}) != mios.toml meta.mios_version ({})",
            containerfile_version, ssot_version
        );
        has_drift = true;
    }

    if has_drift {
        eprintln!("[mios-version-check] FAIL: Version drift detected.");
        process::exit(1);
    }

    println!(
        "[mios-version-check] PASS: All versions match SSOT ({})",
        ssot_version
    );
}
