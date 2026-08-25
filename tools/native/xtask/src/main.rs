// AI-hint: xtask binary entry point for mios build-resolver and regen commands.
// AI-related: tools/native/Cargo.toml, automation/98-drift-checks.sh
use std::env;
use std::process::Command;

fn parse_task(args: &[String]) -> &str {
    args.first().map(|s| s.as_str()).unwrap_or("help")
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let task = parse_task(&args);

    match task {
        "build-resolver" => {
            println!("[xtask] Building mios-resolver in release mode...");
            let status = Command::new("cargo")
                .args(["build", "--release", "-p", "mios-resolver"])
                .status()
                .expect("Failed to execute cargo build");
            if !status.success() {
                std::process::exit(1);
            }
            println!("[xtask] mios-resolver build complete.");
        }
        "regen" => {
            println!("[xtask] Regenerating SSOT projections...");
            let status = Command::new("cargo")
                .args(["run", "-p", "mios-resolver", "--", "--emit=shell"])
                .status()
                .expect("Failed to execute cargo run");
            if !status.success() {
                std::process::exit(1);
            }
            println!("[xtask] Regeneration complete.");
        }
        _ => {
            println!("Usage: cargo xtask <build-resolver|regen>");
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_task() {
        assert_eq!(parse_task(&[]), "help");
        assert_eq!(parse_task(&["build-resolver".to_string()]), "build-resolver");
        assert_eq!(parse_task(&["regen".to_string()]), "regen");
        assert_eq!(parse_task(&["unknown".to_string()]), "unknown");
    }
}

