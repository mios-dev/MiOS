// AI-hint: High-performance native Rust drift check runner for MiOS — dispatches drift gates cleanly with timing metrics.
// AI-related: automation/98-drift-checks.sh, tools/native/Cargo.toml
use std::env;
use std::process::Command;
use std::time::Instant;

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let root = env::var("MIOS_ROOT").unwrap_or_else(|_| ".".to_string());
    let script = format!("{}/automation/98-drift-checks.sh", root);

    println!("[mios-drift-runner] Native drift-check runner starting...");
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
