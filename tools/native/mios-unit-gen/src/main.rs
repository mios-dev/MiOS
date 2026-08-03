use mios_unit_gen::{render_units, verify_golden_master};
use std::env;
use std::fs;
use std::path::Path;

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
        let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| ".".to_string());
        let root = Path::new(&manifest_dir).join("../../../");
        let ssot_path = root.join("usr/share/mios/mios.toml");
        let ssot_content = fs::read_to_string(&ssot_path).unwrap_or_default();
        match render_units(&ssot_content) {
            Ok(rendered) => {
                println!(
                    "mios-unit-gen check PASSED (rendered {} units)",
                    rendered.len()
                );
                return Ok(());
            }
            Err(e) => {
                eprintln!("Check error: {e}");
                std::process::exit(1);
            }
        }
    }

    println!("mios-unit-gen binary ready");
    Ok(())
}
