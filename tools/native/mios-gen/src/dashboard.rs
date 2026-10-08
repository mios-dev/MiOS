// AI-hint: Native runtime dashboard adapter resolves six-tier SSOT once and renders structured host facts through the shared cross-platform engine.
// AI-related: /usr/share/mios/templates/rust, tools/native/mios-service-core/src/dashboard.rs
use serde_json::Value;
use std::io::Read;
use std::path::Path;
use std::process::Command;
use std::time::Duration;

fn facts(timeout: Duration) -> Result<Value, String> {
    let mut command = Command::new("fastfetch");
    command.args([
        "--config",
        "none",
        "--format",
        "json",
        "--structure",
        "Title:OS:Kernel:Uptime:CPU:GPU:Memory:Swap:Disk:Shell:Host:TerminalFont:DateTime",
    ]);
    let output = mios_service_core::process::output_timeout(&mut command, timeout)?;
    if !output.status.success() {
        return Err(format!(
            "fastfetch exited unsuccessfully: {}",
            String::from_utf8_lossy(&output.stderr)
        ));
    }
    serde_json::from_slice(&output.stdout)
        .map_err(|e| format!("Invalid structured fastfetch facts: {e}"))
}

pub fn run(
    root: &Path,
    resolved_stdin: bool,
    width: Option<usize>,
    no_probe: bool,
    json: bool,
    facts_file: Option<&Path>,
) -> Result<String, String> {
    let doc: Value = if resolved_stdin {
        let mut bytes = Vec::new();
        std::io::stdin()
            .take(8 * 1024 * 1024 + 1)
            .read_to_end(&mut bytes)
            .map_err(|e| format!("Resolver input: {e}"))?;
        if bytes.len() > 8 * 1024 * 1024 {
            return Err("Resolver input exceeds 8 MiB".into());
        }
        let input: Value =
            serde_json::from_slice(&bytes).map_err(|e| format!("Invalid resolver JSON: {e}"))?;
        input
            .get("merged")
            .cloned()
            .ok_or("Native resolver JSON omitted merged SSOT")?
    } else {
        serde_json::to_value(
            mios_resolver::resolve_merged(Some(root), false).map_err(|e| e.to_string())?,
        )
        .map_err(|e| e.to_string())?
    };
    let width = width
        .or_else(|| std::env::var("COLUMNS").ok().and_then(|v| v.parse().ok()))
        .or_else(|| {
            doc["terminal"]["cols"]
                .as_u64()
                .and_then(|v| usize::try_from(v).ok())
        })
        .ok_or("Missing SSOT terminal.cols")?;
    let timeout = mios_service_core::dashboard::milliseconds(&doc, "facts_timeout_ms")?;
    let mut endpoints = mios_service_core::dashboard::catalog(&doc)?;
    if !no_probe {
        mios_service_core::dashboard::probe(
            &mut endpoints,
            mios_service_core::dashboard::milliseconds(&doc, "probe_timeout_ms")?,
        )?;
    }
    let facts = if let Some(path) = facts_file {
        serde_json::from_slice(&std::fs::read(path).map_err(|e| e.to_string())?)
            .map_err(|e| format!("Invalid facts input: {e}"))?
    } else {
        match facts(timeout) {
            Ok(facts) => facts,
            Err(error) => {
                eprintln!("[dashboard] {error}; hardware facts unavailable");
                Value::Array(Vec::new())
            }
        }
    };
    if json {
        // Validate render inputs even for the machine-readable parity surface.
        mios_service_core::dashboard::render(&doc, &facts, &endpoints, width)?;
        serde_json::to_string_pretty(&serde_json::json!({"schema":"mios.dashboard.v1", "metrics":mios_service_core::dashboard::metrics(&doc, &facts)?, "endpoints":endpoints})).map_err(|e| e.to_string())
    } else {
        mios_service_core::dashboard::render(&doc, &facts, &endpoints, width)
    }
}
