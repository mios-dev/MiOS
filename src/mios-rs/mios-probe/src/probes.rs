// AI-hint: The two probe sets -- build-host readiness and host-install thresholds -- both resolved from mios.toml [preflight].
// AI-related: usr/share/mios/mios.toml, src/mios-rs/mios-probe/src/report.rs, Justfile

use crate::report::{Probe, Report, Verdict};
use std::path::Path;

fn ssot(root: &Path) -> Result<toml::Value, String> {
    let p = root.join("usr/share/mios/mios.toml");
    if !p.is_file() {
        return Err(format!(
            "{} is missing, so no threshold could be read",
            p.display()
        ));
    }
    let text = std::fs::read_to_string(&p)
        .map_err(|e| format!("{} could not be read: {e}", p.display()))?;
    text.parse::<toml::Value>()
        .map_err(|e| format!("{} did not parse: {e}", p.display()))
}

fn cannot_run(why: String) -> Report {
    Report {
        title: String::new(),
        probes: Vec::new(),
        could_not_run: Some(why),
    }
}

fn version(root: &Path) -> String {
    std::fs::read_to_string(root.join("VERSION"))
        .map(|s| s.trim().to_string())
        .unwrap_or_else(|_| "?".to_string())
}

/// Free whole gigabytes, or None when undeterminable. None is never "enough".
/// `df -BG` matches the retired shell probe byte for byte; it rounds up (T-1019).
fn free_gib(path: &Path) -> Option<u64> {
    let out = std::process::Command::new("df")
        .arg("-BG")
        .arg(path)
        .output()
        .ok()?;
    if !out.status.success() {
        return None;
    }
    let text = String::from_utf8_lossy(&out.stdout);
    let line = text.lines().nth(1)?;
    let field = line.split_whitespace().nth(3)?;
    field.trim_end_matches('G').parse().ok()
}

fn on_path(tool: &str) -> bool {
    let Ok(path) = std::env::var("PATH") else {
        return false;
    };
    std::env::split_paths(&path).any(|d| {
        let c = d.join(tool);
        c.is_file() || c.with_extension("exe").is_file()
    })
}

/// Build-host readiness: what `just build` needs before it starts.
/// Output is byte-identical to the shell probe it replaces.
pub fn build(root: &Path) -> Report {
    let cfg = match ssot(root) {
        Ok(v) => v,
        Err(e) => return cannot_run(e),
    };
    let Some(b) = cfg.get("preflight").and_then(|p| p.get("build")) else {
        return cannot_run("mios.toml is missing [preflight.build]".to_string());
    };

    let mut probes = Vec::new();

    let Some(tools) = b.get("required_tools").and_then(|v| v.as_array()) else {
        return cannot_run("[preflight.build].required_tools is missing".to_string());
    };
    for t in tools.iter().filter_map(|v| v.as_str()) {
        let (verdict, msg) = if on_path(t) {
            (Verdict::Ok, format!("{t} found"))
        } else {
            (Verdict::Fail, format!("{t} not found"))
        };
        probes.push(Probe {
            key: format!("tool.{t}"),
            verdict,
            message: msg,
        });
    }

    let Some(min_gb) = b.get("min_disk_free_gb").and_then(|v| v.as_integer()) else {
        return cannot_run("[preflight.build].min_disk_free_gb is missing".to_string());
    };
    match free_gib(root) {
        Some(avail) => {
            let verdict = if avail as i64 >= min_gb {
                Verdict::Ok
            } else {
                Verdict::Warn
            };
            probes.push(Probe {
                key: "disk_free_gb".to_string(),
                verdict,
                message: format!("Disk space: {avail}G available"),
            });
        }
        None => probes.push(Probe {
            key: "disk_free_gb".to_string(),
            // Unknown is not enough. The shell script read a `df` field with no
            // error path, so an unreadable df printed "Disk space: G available"
            // and compared an empty string as zero.
            verdict: Verdict::Fail,
            message: "Disk space: could not be determined".to_string(),
        }),
    }

    let Some(files) = b.get("required_files").and_then(|v| v.as_array()) else {
        return cannot_run("[preflight.build].required_files is missing".to_string());
    };
    for f in files.iter().filter_map(|v| v.as_str()) {
        let (verdict, msg) = if root.join(f).is_file() {
            (Verdict::Ok, format!("{f} present"))
        } else {
            (Verdict::Fail, format!("{f} missing"))
        };
        probes.push(Probe {
            key: format!("file.{f}"),
            verdict,
            message: msg,
        });
    }

    Report {
        title: format!("'MiOS' v{} -- Pre-flight Check", version(root)),
        probes,
        could_not_run: None,
    }
}

/// Host-install thresholds: what a machine needs before MiOS is installed onto
/// it. Each threshold reports NOT APPLICABLE rather than passing on a platform
/// where it cannot be evaluated -- a Windows build number on Linux is not a
/// satisfied requirement.
pub fn host(root: &Path) -> Report {
    let cfg = match ssot(root) {
        Ok(v) => v,
        Err(e) => return cannot_run(e),
    };
    let Some(p) = cfg.get("preflight") else {
        return cannot_run("mios.toml is missing [preflight]".to_string());
    };
    let windows = cfg!(target_os = "windows");
    let mut probes = Vec::new();

    match p.get("min_ram_gb").and_then(|v| v.as_integer()) {
        Some(min) => {
            let got = total_ram_gib();
            match got {
                Some(gb) => probes.push(Probe {
                    key: "min_ram_gb".to_string(),
                    verdict: if gb as i64 >= min {
                        Verdict::Ok
                    } else {
                        Verdict::Fail
                    },
                    message: format!("RAM: {gb}G present, {min}G required"),
                }),
                None => probes.push(Probe {
                    key: "min_ram_gb".to_string(),
                    verdict: Verdict::Fail,
                    message: format!("RAM: could not be determined, {min}G required"),
                }),
            }
        }
        None => return cannot_run("[preflight].min_ram_gb is missing".to_string()),
    }

    match p.get("min_disk_free_gb").and_then(|v| v.as_integer()) {
        Some(min) => match free_gib(root) {
            Some(avail) => probes.push(Probe {
                key: "min_disk_free_gb".to_string(),
                verdict: if avail as i64 >= min {
                    Verdict::Ok
                } else {
                    Verdict::Fail
                },
                message: format!("Disk: {avail}G free, {min}G required"),
            }),
            None => probes.push(Probe {
                key: "min_disk_free_gb".to_string(),
                verdict: Verdict::Fail,
                message: format!("Disk: could not be determined, {min}G required"),
            }),
        },
        None => return cannot_run("[preflight].min_disk_free_gb is missing".to_string()),
    }

    for (key, label) in [
        ("min_windows_build", "Windows build"),
        ("require_virt", "Virtualization"),
        ("require_admin", "Administrator"),
    ] {
        if p.get(key).is_none() {
            return cannot_run(format!("[preflight].{key} is missing"));
        }
        probes.push(Probe {
            key: key.to_string(),
            verdict: if windows {
                Verdict::Warn
            } else {
                Verdict::NotApplicable
            },
            message: if windows {
                format!("{label}: probed by the Windows installer, not by this binary yet")
            } else {
                format!("{label}: not applicable on this platform")
            },
        });
    }

    Report {
        title: format!("'MiOS' v{} -- Host Readiness", version(root)),
        probes,
        could_not_run: None,
    }
}

fn total_ram_gib() -> Option<u64> {
    let text = std::fs::read_to_string("/proc/meminfo").ok()?;
    for line in text.lines() {
        if let Some(rest) = line.strip_prefix("MemTotal:") {
            let kb: u64 = rest.split_whitespace().next()?.parse().ok()?;
            return Some(kb / 1024 / 1024);
        }
    }
    None
}
