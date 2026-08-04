use mios_unit_gen::{render_units, verify_golden_master};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

/// Repo root: MIOS_ROOT when the caller sets it (the build and the drift-gate
/// both do), else relative to the crate, else the working directory. The
/// installed binary has no CARGO_MANIFEST_DIR, so it cannot be the only source.
fn repo_root() -> PathBuf {
    if let Ok(r) = env::var("MIOS_ROOT") {
        if !r.is_empty() {
            return PathBuf::from(r);
        }
    }
    match env::var("CARGO_MANIFEST_DIR") {
        Ok(d) => Path::new(&d).join("../../.."),
        Err(_) => PathBuf::from("."),
    }
}

/// Compare unit bodies on content, not on byte-exactness: line endings differ
/// between a Windows checkout and the Linux build, and a trailing newline is
/// not drift. Anything else is.
fn normalize(s: &str) -> String {
    let mut out: Vec<&str> = s.lines().map(|l| l.trim_end()).collect();
    while out.last().is_some_and(|l| l.is_empty()) {
        out.pop();
    }
    out.join("\n")
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();

    if args.iter().any(|a| a == "--selftest") {
        let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| ".".to_string());
        let root = Path::new(&manifest_dir).join("../../../");
        let systemd_dir = root.join("usr/lib/systemd/system");
        let golden_dir = Path::new(&manifest_dir).join("tests/golden");
        if let Err(e) = verify_golden_master(&systemd_dir, &golden_dir) {
            eprintln!("Selftest failed: {e}");
            std::process::exit(1);
        }
        println!("mios-unit-gen selftest PASSED");
        return Ok(());
    }

    if args.iter().any(|a| a == "--check") {
        // A drift check must COMPARE. The previous implementation rendered the
        // units in memory, printed "check PASSED (rendered N units)" and
        // returned -- it could only fail if rendering itself threw, so it could
        // never detect the one thing it exists to detect: mios.toml [units.*]
        // having drifted from the unit files on disk.
        let root = repo_root();
        let ssot_path = root.join("usr/share/mios/mios.toml");
        let ssot_content = match fs::read_to_string(&ssot_path) {
            Ok(c) => c,
            Err(e) => {
                eprintln!("mios-unit-gen: cannot read {}: {e}", ssot_path.display());
                std::process::exit(1);
            }
        };
        let rendered = match render_units(&ssot_content) {
            Ok(r) => r,
            Err(e) => {
                eprintln!("mios-unit-gen: render error: {e}");
                std::process::exit(1);
            }
        };
        if rendered.is_empty() {
            eprintln!("mios-unit-gen: rendered 0 units from [units.*] -- SSOT empty or unreadable");
            std::process::exit(1);
        }

        let unit_dir = root.join("usr/lib/systemd/system");
        let mut missing = Vec::new();
        let mut drifted = Vec::new();
        for (filename, body) in &rendered {
            let on_disk = unit_dir.join(filename);
            match fs::read_to_string(&on_disk) {
                Err(_) => missing.push(filename.clone()),
                Ok(actual) => {
                    if normalize(&actual) != normalize(body) {
                        drifted.push(filename.clone());
                    }
                }
            }
        }

        if missing.is_empty() && drifted.is_empty() {
            println!(
                "mios-unit-gen check PASSED ({} units match usr/lib/systemd/system)",
                rendered.len()
            );
            return Ok(());
        }
        eprintln!(
            "mios-unit-gen check FAILED: {} rendered, {} missing on disk, {} drifted",
            rendered.len(),
            missing.len(),
            drifted.len()
        );
        for f in missing.iter().take(20) {
            eprintln!("  MISSING  {f}");
        }
        for f in drifted.iter().take(20) {
            eprintln!("  DRIFTED  {f}");
        }
        std::process::exit(1);
    }

    println!("mios-unit-gen binary ready");
    Ok(())
}
