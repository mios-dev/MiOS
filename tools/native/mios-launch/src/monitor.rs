// AI-hint: Render the Windows build monitor command directly from the native merged SSOT.
// AI-related: usr/share/mios/mios.toml, tools/native/mios-resolver/src/emit_json.rs
use serde_json::Value;

fn argument(value: &str) -> Result<String, String> {
    // WT treats semicolons as command separators even without a shell.
    if value.is_empty() || value.chars().any(|c| c.is_control() || c == ';') {
        return Err("Invalid Windows Terminal argument".into());
    }
    Ok(value.into())
}

fn text(config: &Value, path: &str) -> Result<String, String> {
    argument(
        config
            .pointer(path)
            .and_then(Value::as_str)
            .ok_or_else(|| format!("Missing SSOT {path}"))?,
    )
}

/// All policy (backend, window, geometry, profile, theme and mode) comes from
/// the resolver. The caller supplies only the discovered executable/assets.
pub fn render(config: &Value, python: &str, script: &str) -> Result<Vec<String>, String> {
    if text(config, "/terminal/monitor/windows_backend")? != "windows-terminal" {
        return Err("Unsupported SSOT terminal.monitor.windows_backend".into());
    }
    let dimension = |key: &str| {
        config["terminal"]["monitor"][key]
            .as_u64()
            .filter(|n| *n > 0 && *n <= 32767)
            .ok_or_else(|| format!("Invalid SSOT terminal.monitor.{key}"))
    };
    let mut args = vec![
        "-w".into(),
        text(config, "/terminal/monitor/window_name")?,
        "--size".into(),
        format!("{},{}", dimension("cols")?, dimension("rows")?),
    ];
    match text(config, "/theme/launch_mode")?.as_str() {
        "default" => (),
        "focus" => args.push("--focus".into()),
        "maximized" => args.push("--maximized".into()),
        "fullscreen" => args.push("--fullscreen".into()),
        "focusFullscreen" => args.extend(["--fullscreen".into(), "--focus".into()]),
        _ => return Err("Invalid SSOT theme.launch_mode".into()),
    }
    args.extend([
        "new-tab".into(),
        "--profile".into(),
        text(config, "/theme/terminal/profile_name")?,
        "--colorScheme".into(),
        text(config, "/theme/terminal/scheme_name")?,
        "--title".into(),
        text(config, "/terminal/monitor/title")?,
        "--suppressApplicationTitle".into(),
        "--".into(),
        argument(python)?,
        argument(script)?,
        "--pipeline".into(),
    ]);
    Ok(args)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn config() -> Value {
        json!({"terminal":{"monitor":{"windows_backend":"windows-terminal",
            "window_name":"MiOS-Monitor","title":"MiOS Build Monitor","cols":80,"rows":20}},
            "theme":{"launch_mode":"focus","terminal":{"profile_name":"MiOS-WIN","scheme_name":"MiOS"}}})
    }
    #[test]
    fn selections_change_actual_command_without_shell_or_native_tmux() {
        let mut data = config();
        let baseline = render(
            &data,
            r"C:\Program Files\Python\python.exe",
            r"C:\MiOS\mios-mon.py",
        )
        .unwrap();
        assert!(baseline.contains(&"80,20".into()));
        assert_eq!(
            &baseline[baseline.len() - 3..],
            [
                r"C:\Program Files\Python\python.exe",
                r"C:\MiOS\mios-mon.py",
                "--pipeline"
            ]
        );
        data["terminal"]["monitor"]["cols"] = json!(117);
        data["terminal"]["monitor"]["rows"] = json!(35);
        data["theme"]["launch_mode"] = json!("focusFullscreen");
        data["theme"]["terminal"]["profile_name"] = json!("Custom profile");
        let changed = render(&data, "python.exe", "monitor.py").unwrap();
        assert!(changed.contains(&"117,35".into()));
        assert!(changed.contains(&"Custom profile".into()));
        assert!(changed.contains(&"--fullscreen".into()));
        assert!(!changed
            .iter()
            .any(|a| a.contains("tmux") || a.contains("powershell")));
    }
    #[test]
    fn malformed_policy_and_terminal_command_injection_fail_before_spawn() {
        for (path, invalid) in [
            ("/terminal/monitor/windows_backend", json!("tmux.exe")),
            ("/terminal/monitor/cols", json!(0)),
            ("/terminal/monitor/rows", json!("20")),
            ("/theme/launch_mode", json!("bogus")),
            ("/theme/terminal/profile_name", json!("MiOS; new-tab cmd")),
        ] {
            let mut data = config();
            *data.pointer_mut(path).unwrap() = invalid;
            assert!(render(&data, "python.exe", "monitor.py").is_err(), "{path}");
        }
        assert!(render(&config(), "python.exe", "monitor.py; new-tab cmd.exe").is_err());
    }
}
