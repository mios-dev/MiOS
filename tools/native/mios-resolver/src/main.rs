// AI-hint: CLI entry point for mios-resolver -- selects an --emit target (shell, powershell, json, install-env) over the merged SSOT.
// AI-related: usr/lib/mios/userenv.sh, automation/lib/globals.ps1, /etc/mios/install.env
use clap::Parser;
use miette::Result;
use mios_resolver::emit_install_env::emit_install_env;
use mios_resolver::emit_json::emit_json;
use mios_resolver::emit_ps::emit_powershell;
use mios_resolver::emit_shell::emit_shell;
use mios_resolver::layers::create_figment;
use mios_resolver::load_model;
use std::path::PathBuf;
use toml::Value;

#[derive(Parser, Debug)]
#[command(name = "mios-resolver")]
#[command(about = "Native compiled SSOT resolver for MiOS")]
struct Args {
    #[arg(long, help = "Validate that mios.toml layers parse cleanly")]
    check_parse: bool,

    #[arg(
        long,
        help = "Emit format (e.g. 'shell', 'powershell', 'ps', 'json', 'install-env')"
    )]
    emit: Option<String>,

    #[arg(long, help = "Repository or root directory path")]
    root: Option<PathBuf>,
}

/// stack_offset = [ports].stack_id * 10000 -- the multi-stack port shift the
/// Python resolver applies in process_val(). Absent stack_id means no shift.
fn stack_offset_of(merged: &Value) -> i32 {
    merged
        .get("ports")
        .and_then(|p| p.get("stack_id"))
        .and_then(|v| {
            v.as_integer()
                .or_else(|| v.as_str().and_then(|s| s.parse::<i64>().ok()))
        })
        .map(|id| id as i32 * 10000)
        .unwrap_or(0)
}

fn main() -> Result<()> {
    let args = Args::parse();
    let root = args.root.as_deref();

    if args.check_parse {
        match load_model(root) {
            Ok(model) => {
                println!(
                    "[mios-resolver] Successfully parsed mios.toml layers. Identity role: {:?}",
                    model.identity.as_ref().and_then(|i| i.role.as_ref())
                );
                Ok(())
            }
            Err(e) => {
                eprintln!("[mios-resolver] Parse error: {:?}", e);
                std::process::exit(1);
            }
        }
    } else if let Some(format) = args.emit {
        let fig = create_figment(root);
        let mut merged = match fig.extract::<Value>() {
            Ok(val) => val,
            Err(e) => {
                eprintln!(
                    "[mios-resolver] Failed to extract merged TOML value: {:?}",
                    e
                );
                std::process::exit(1);
            }
        };

        // Allocate [ports] from [ports.categories] after every layer has merged,
        // so an OEM default or an operator override re-derives live.
        mios_resolver::ports::derive_ports(&mut merged);

        let stack_offset = stack_offset_of(&merged);

        match format.as_str() {
            "shell" => {
                let ref_names = root.map(|r| r.join("usr/share/mios/referenced_names.txt"));
                let output = emit_shell(&merged, stack_offset, ref_names.as_deref());
                print!("{}", output);
                Ok(())
            }
            "powershell" | "ps" => {
                let output = emit_powershell(&merged, stack_offset);
                print!("{}", output);
                Ok(())
            }
            "json" => {
                let output = emit_json(&merged, stack_offset);
                print!("{}", output);
                Ok(())
            }
            "install-env" => {
                let ref_names = root.map(|r| r.join("usr/share/mios/referenced_names.txt"));
                let output = emit_install_env(&merged, stack_offset, ref_names.as_deref());
                print!("{}", output);
                Ok(())
            }
            _ => {
                eprintln!("[mios-resolver] Unsupported emit format: {}", format);
                std::process::exit(1);
            }
        }
    } else {
        println!("[mios-resolver] Native compiled SSOT resolver. Use --check-parse to validate layers or --emit=shell/powershell/json/install-env.");
        Ok(())
    }
}
