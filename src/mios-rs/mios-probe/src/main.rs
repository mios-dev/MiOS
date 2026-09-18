// AI-hint: Entry point for mios-probe, the native host-readiness prober; resolves every threshold from mios.toml rather than from code.
// AI-related: src/mios-rs/mios-probe/src/probes.rs, usr/share/mios/mios.toml, Justfile

#![forbid(unsafe_code)]
#![warn(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

mod probes;
mod report;

use std::process::ExitCode;

/// The gate contract, shared with mios-gate: 0 clean, 1 violations,
/// 2 could-not-run. Never 0 on an input that could not be read.
pub const EXIT_CLEAN: u8 = 0;
pub const EXIT_VIOLATIONS: u8 = 1;
pub const EXIT_CANNOT_RUN: u8 = 2;

const USAGE: &str =
    "usage: mios-probe [build|host] [--root DIR] [--format text|json] [--no-color]\n\
                     build  build-host readiness  (default)\n\
                     host   host-install thresholds\n";

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut set = String::from("build");
    let mut root = std::env::var("MIOS_ROOT")
        .or_else(|_| std::env::var("MIOS_DRIFT_ROOT"))
        .ok();
    let mut json = false;
    let mut color = std::env::var("NO_COLOR").is_err();

    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--root" => {
                i += 1;
                match args.get(i) {
                    Some(v) => root = Some(v.clone()),
                    None => {
                        eprint!("mios-probe: --root needs a directory\n{USAGE}");
                        return ExitCode::from(EXIT_CANNOT_RUN);
                    }
                }
            }
            "--format" => {
                i += 1;
                match args.get(i).map(String::as_str) {
                    Some("json") => json = true,
                    Some("text") => json = false,
                    _ => {
                        eprint!("mios-probe: --format takes text or json\n{USAGE}");
                        return ExitCode::from(EXIT_CANNOT_RUN);
                    }
                }
            }
            "--no-color" => color = false,
            "-h" | "--help" => {
                print!("{USAGE}");
                return ExitCode::from(EXIT_CLEAN);
            }
            other if !other.starts_with('-') => set = other.to_string(),
            other => {
                eprint!("mios-probe: unrecognised argument {other:?}\n{USAGE}");
                return ExitCode::from(EXIT_CANNOT_RUN);
            }
        }
        i += 1;
    }

    // Default to the directory the binary is run from, which for `just
    // preflight` is the repo root.
    let root = std::path::PathBuf::from(root.unwrap_or_else(|| ".".to_string()));

    let report = match set.as_str() {
        "build" => probes::build(&root),
        "host" => probes::host(&root),
        other => {
            eprint!("mios-probe: no such probe set {other:?}\n{USAGE}");
            return ExitCode::from(EXIT_CANNOT_RUN);
        }
    };

    if json {
        println!("{}", report.render_json());
    } else {
        let text = report.render_text(color);
        // The shell script it replaces sent [FAIL] to stderr and the rest to
        // stdout; a combined capture is byte-identical either way.
        if report.code() == EXIT_CLEAN {
            print!("{text}");
        } else {
            eprint!("{text}");
        }
    }
    ExitCode::from(report.code())
}
