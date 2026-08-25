// AI-hint: High-performance native Rust drift check runner for MiOS — dispatches drift gates cleanly with timing metrics.
// AI-related: automation/98-drift-checks.sh, src/mios-rs/miosd
use std::env;
use std::process::Command;
use std::time::Instant;

fn run_resolver_check(surface: &str) -> bool {
    let root = env::var("MIOS_ROOT").unwrap_or_else(|_| ".".to_string());
    let bin = format!("{}/tools/native/target/debug/mios-resolver", root);
    let mut cmd = Command::new(&bin);
    cmd.arg(format!("--emit={}", surface));
    println!(
        "[mios-drift-runner] Running resolver equivalence check for surface: {}",
        surface
    );
    match cmd.status() {
        Ok(status) => status.success(),
        Err(_) => false,
    }
}

fn parse_surface(cmd_name: &str) -> Option<&str> {
    if cmd_name.starts_with("check_resolver_") || cmd_name.starts_with("--resolver-") {
        Some(
            cmd_name
                .trim_start_matches("--resolver-")
                .trim_start_matches("check_resolver_"),
        )
    } else {
        None
    }
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let root = env::var("MIOS_ROOT").unwrap_or_else(|_| ".".to_string());

    if let Some(cmd_name) = args.first() {
        if let Some(surface) = parse_surface(cmd_name) {
            let ok = run_resolver_check(surface);
            if ok {
                println!("[mios-drift-runner] Resolver check {} PASSED", surface);
                std::process::exit(0);
            } else {
                eprintln!("[mios-drift-runner] Resolver check {} FAILED", surface);
                std::process::exit(1);
            }
        }
    }

    let use_legacy = env::var("MIOS_DRIFT_LEGACY")
        .map(|v| v == "1" || v == "true")
        .unwrap_or(false);

    if !use_legacy {
        println!("[mios-drift-runner] Dispatching to native miosd drift-check...");
        let start = Instant::now();
        let miosd_bin = format!("{}/src/mios-rs/target/debug/miosd", root);
        let mut cmd = Command::new(&miosd_bin);
        cmd.arg("drift-check");
        cmd.arg("--root").arg(&root);
        for arg in &args {
            cmd.arg(arg);
        }

        if let Ok(status) = cmd.status() {
            if status.success() {
                println!(
                    "[mios-drift-runner] All native miosd drift checks PASSED in {:.2?}",
                    start.elapsed()
                );
                std::process::exit(0);
            }
        }
    }

    let script = format!("{}/automation/98-drift-checks.sh", root);
    println!("[mios-drift-runner] Fallback bash drift check running...");
    let start = Instant::now();

    let mut cmd = Command::new("bash");
    cmd.arg(&script);
    for arg in &args {
        cmd.arg(arg);
    }

    match cmd.status() {
        Ok(status) => {
            let duration = start.elapsed();
            if status.success() {
                println!(
                    "[mios-drift-runner] All drift checks PASSED in {:.2?}",
                    duration
                );
                std::process::exit(0);
            } else {
                eprintln!(
                    "[mios-drift-runner] Drift checks FAILED in {:.2?} (code {})",
                    duration,
                    status.code().unwrap_or(1)
                );
                std::process::exit(status.code().unwrap_or(1));
            }
        }
        Err(e) => {
            eprintln!("[mios-drift-runner] Failed to execute {}: {}", script, e);
            std::process::exit(1);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_surface() {
        assert_eq!(parse_surface("check_resolver_shell"), Some("shell"));
        assert_eq!(parse_surface("--resolver-python"), Some("python"));
        assert_eq!(parse_surface("other_cmd"), None);
    }
}

