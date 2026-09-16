// AI-hint: Entry point for mios-gate, the native drift-gate binary; dispatches one named check and reports text or an OpenAI-format structured object.
// AI-related: src/mios-rs/mios-gate/src/dispatch.rs, automation/98-drift-checks.sh, usr/share/doc/mios/adr/0021-rust-static-binary-consolidation.md

#![forbid(unsafe_code)]
#![warn(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

mod dispatch;
mod phases;

use std::process::ExitCode;

/// Exit codes are the gate's contract and predate this binary: 0 clean,
/// 1 violations found, 2 the check could not run. Never 0 on an unread input.
pub const EXIT_CLEAN: u8 = 0;
pub const EXIT_VIOLATIONS: u8 = 1;
pub const EXIT_CANNOT_RUN: u8 = 2;

/// One check's result. `findings` is empty exactly when `ok` is true.
pub struct Report {
    pub check: String,
    pub ok: bool,
    pub could_not_run: Option<String>,
    pub summary: String,
    pub findings: Vec<String>,
}

impl Report {
    pub fn code(&self) -> u8 {
        if self.could_not_run.is_some() {
            EXIT_CANNOT_RUN
        } else if self.ok {
            EXIT_CLEAN
        } else {
            EXIT_VIOLATIONS
        }
    }

    fn render_text(&self) -> String {
        let mut out = String::new();
        if let Some(why) = &self.could_not_run {
            out.push_str(&format!("    [{}] {}\n", self.check, why));
            return out;
        }
        for f in &self.findings {
            out.push_str(&format!("    [{}] {}\n", self.check, f));
        }
        if self.ok {
            out.push_str(&format!("[{}] {}\n", self.check, self.summary));
        }
        out
    }

    /// OpenAI-format structured output: the object a `/v1` structured-outputs
    /// response would carry, so the agent plane consumes findings natively.
    fn render_json(&self) -> String {
        let value = serde_json::json!({
            "check": self.check,
            "status": if self.could_not_run.is_some() { "could_not_run" }
                      else if self.ok { "clean" } else { "violations" },
            "summary": self.could_not_run.clone().unwrap_or_else(|| self.summary.clone()),
            "findings": self.findings,
        });
        serde_json::to_string_pretty(&value).unwrap_or_else(|_| {
            // Serialising our own object cannot fail, but a gate never panics.
            format!(
                "{{\"check\":\"{}\",\"status\":\"could_not_run\",\
                     \"summary\":\"report could not be serialised\",\"findings\":[]}}",
                self.check
            )
        })
    }
}

const USAGE: &str = "usage: mios-gate <check> [--root DIR] [--format text|json]\n\
                     checks: build-tool-dispatch, phase-registry\n";

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut check: Option<String> = None;
    let mut root: Option<String> = std::env::var("MIOS_DRIFT_ROOT").ok();
    let mut json = false;

    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--root" => {
                i += 1;
                match args.get(i) {
                    Some(v) => root = Some(v.clone()),
                    None => {
                        eprint!("mios-gate: --root needs a directory\n{USAGE}");
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
                        eprint!("mios-gate: --format takes text or json\n{USAGE}");
                        return ExitCode::from(EXIT_CANNOT_RUN);
                    }
                }
            }
            "-h" | "--help" => {
                print!("{USAGE}");
                return ExitCode::from(EXIT_CLEAN);
            }
            other if check.is_none() && !other.starts_with('-') => {
                check = Some(other.to_string());
            }
            other => {
                eprint!("mios-gate: unrecognised argument {other:?}\n{USAGE}");
                return ExitCode::from(EXIT_CANNOT_RUN);
            }
        }
        i += 1;
    }

    let Some(name) = check else {
        eprint!("mios-gate: no check named\n{USAGE}");
        return ExitCode::from(EXIT_CANNOT_RUN);
    };
    let root = std::path::PathBuf::from(root.unwrap_or_else(|| ".".to_string()));

    let report = match name.as_str() {
        "build-tool-dispatch" => dispatch::check(&root),
        "phase-registry" => phases::check(&root),
        _ => {
            eprint!("mios-gate: no such check {name:?}\n{USAGE}");
            return ExitCode::from(EXIT_CANNOT_RUN);
        }
    };

    if json {
        println!("{}", report.render_json());
    } else {
        let text = report.render_text();
        if report.ok && report.could_not_run.is_none() {
            print!("{text}");
        } else {
            eprint!("{text}");
        }
    }
    ExitCode::from(report.code())
}
