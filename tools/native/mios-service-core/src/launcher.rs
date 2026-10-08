// AI-hint: Shared native terminal policy and monitor layouts for Windows and Linux consumers.
// AI-related: usr/share/mios/mios.toml, tools/native/mios-resolver/src/emit_json.rs
use serde_json::Value;

/// One validated terminal policy consumed by Linux and Windows launchers.
pub fn terminal_config(
    config: &Value,
    requested: &str,
    default_action: bool,
) -> Result<[String; 9], String> {
    let identifier = |path: &str, spaces: bool| -> Result<String, String> {
        let value = text(config, path)?;
        if !value
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || c == b'-' || c == b'_' || (spaces && c == b' '))
        {
            return Err(format!("Invalid SSOT tmux identifier {path}"));
        }
        Ok(value)
    };
    let selected = if requested.is_empty() && default_action {
        text(config, "/terminal/default_action")?
    } else {
        requested.into()
    };
    let actions = config
        .pointer("/keybindings/actions")
        .and_then(Value::as_array)
        .ok_or("SSOT keybindings.actions must be an array")?;
    let action = |id: &str, key: &str| -> Result<String, String> {
        let item = actions
            .iter()
            .find(|a| a["id"].as_str() == Some(id))
            .ok_or_else(|| format!("Unknown MiOS terminal action: {id}"))?;
        let value = item[key]
            .as_str()
            .filter(|s| !s.is_empty() && !s.chars().any(char::is_control))
            .ok_or_else(|| format!("Invalid terminal action {id}.{key}"))?;
        Ok(value.into())
    };
    let path = |key: &str| -> Result<String, String> {
        let value = text(config, key)?;
        if !value.starts_with('/') {
            return Err(format!("SSOT {key} must be an absolute guest path"));
        }
        Ok(value)
    };
    Ok([
        identifier("/keybindings/socket_name", false)?,
        identifier("/keybindings/terminal_session", false)?,
        identifier("/mcp/agents/observation/window_name", true)?,
        action("agents", "command")?,
        if selected.is_empty() {
            String::new()
        } else {
            action(&selected, "command")?
        },
        if selected.is_empty() {
            String::new()
        } else {
            action(&selected, "label")?
        },
        selected,
        path("/terminal/start_directory")?,
        path("/terminal/socket_root")?,
    ])
}

pub fn host_tmux_args(config: &Value, config_path: &str) -> Result<Vec<String>, String> {
    if text(config, "/terminal/windows/backend")? != "native-tmux" {
        return Err("Unsupported SSOT terminal.windows.backend".into());
    }
    let socket = text(config, "/terminal/windows/socket_name")?;
    let session = text(config, "/terminal/windows/session_name")?;
    for name in [&socket, &session] {
        if !name
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || c == b'-' || c == b'_')
        {
            return Err("Invalid native Windows tmux namespace".into());
        }
    }
    Ok(vec![
        "-L".into(),
        socket,
        "-f".into(),
        argument(config_path)?,
        "new-session".into(),
        "-A".into(),
        "-s".into(),
        session,
        text(config, "/terminal/windows/shell")?,
    ])
}

pub fn host_tmux_config(config: &Value) -> Result<String, String> {
    let rows = config
        .pointer("/terminal/scrollback_rows")
        .and_then(Value::as_u64)
        .filter(|n| *n > 0)
        .ok_or("Invalid SSOT terminal.scrollback_rows")?;
    let mouse = config
        .pointer("/keybindings/mouse")
        .and_then(Value::as_bool)
        .ok_or("Invalid SSOT keybindings.mouse")?;
    // Keep the operator's other Windows tmux sessions and default server intact.
    Ok(format!("# Generated from layered MiOS SSOT by native Rust.\nset -g history-limit {rows}\nset -g mouse {}\n", if mouse { "on" } else { "off" }))
}

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
pub fn render_monitor(
    config: &Value,
    python: &str,
    script: &str,
    shell: &str,
    portrait: bool,
) -> Result<Vec<String>, String> {
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
    let percent = |key: &str| -> Result<u64, String> {
        config["terminal"]["monitor"][key]
            .as_u64()
            .filter(|v| *v > 0 && *v < 100)
            .ok_or_else(|| format!("Invalid SSOT terminal.monitor.{key}"))
    };
    let landscape_head = percent("split_landscape_head")?;
    let landscape_monitor = percent("split_landscape_monitor")?;
    let portrait_head = percent("split_portrait_head")?;
    let portrait_monitor = percent("split_portrait_monitor")?;
    let worker_split = (percent("worker_split_percent")? as f64 / 100.0).to_string();
    if landscape_head + landscape_monitor != 100 || portrait_head + portrait_monitor != 100 {
        return Err("SSOT monitor split percentages must sum to 100".into());
    }
    let profile = text(config, "/theme/terminal/profile_name")?;
    let scheme = text(config, "/theme/terminal/scheme_name")?;
    let title = text(config, "/terminal/monitor/title")?;
    let shell = argument(shell)?;
    let monitor = vec![argument(python)?, argument(script)?, "--pipeline".into()];
    let pane = |args: &mut Vec<String>, command: &[String], label: &str| {
        args.extend([
            "--profile".into(),
            profile.clone(),
            "--colorScheme".into(),
            scheme.clone(),
            "--title".into(),
            format!("{title}-{label}"),
            "--suppressApplicationTitle".into(),
            "--".into(),
        ]);
        args.extend_from_slice(command);
    };
    let fullscreen = matches!(
        config["theme"]["launch_mode"].as_str(),
        Some("fullscreen" | "focusFullscreen")
    );
    args.push("new-tab".into());
    if portrait && !fullscreen {
        pane(&mut args, &monitor, "monitor");
        args.extend([
            ";".into(),
            "split-pane".into(),
            "-H".into(),
            "-s".into(),
            (portrait_head as f64 / 100.0).to_string(),
        ]);
        pane(&mut args, std::slice::from_ref(&shell), "head");
    } else {
        pane(&mut args, std::slice::from_ref(&shell), "head");
        args.extend([
            ";".into(),
            "split-pane".into(),
            "-V".into(),
            "-s".into(),
            (landscape_monitor as f64 / 100.0).to_string(),
        ]);
        pane(&mut args, &monitor, "monitor");
    }
    if fullscreen {
        for (direction, label) in [("-H", "worker-1"), ("-V", "worker-2")] {
            args.extend([
                ";".into(),
                "split-pane".into(),
                direction.into(),
                "-s".into(),
                worker_split.clone(),
            ]);
            pane(&mut args, std::slice::from_ref(&shell), label);
        }
        args.extend([
            ";".into(),
            "move-focus".into(),
            "up".into(),
            ";".into(),
            "split-pane".into(),
            "-V".into(),
            "-s".into(),
            worker_split,
        ]);
        pane(&mut args, std::slice::from_ref(&shell), "worker-3");
    }
    args.extend([";".into(), "move-focus".into(), "first".into()]);
    Ok(args)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    fn fixture() -> Value {
        json!({"terminal":{"default_action":"ai","start_directory":"/","socket_root":"/tmp","scrollback_rows":9000,
            "windows":{"backend":"native-tmux","socket_name":"host","session_name":"MiOS-WIN","shell":"cmd.exe"},
            "monitor":{"windows_backend":"windows-terminal","window_name":"monitor","title":"Build","cols":80,"rows":20,
                "split_landscape_head":38,"split_landscape_monitor":62,"split_portrait_monitor":62,"split_portrait_head":38,"worker_split_percent":50}},
            "keybindings":{"mouse":true,"socket_name":"guest","terminal_session":"MiOS","actions":[{"id":"agents","command":"mios agents --watch","label":"Agents"},{"id":"ai","command":"mios ai","label":"AI"}]},
            "mcp":{"agents":{"observation":{"window_name":"MiOS Agents"}}},
            "theme":{"launch_mode":"focus","terminal":{"profile_name":"MiOS-WIN","scheme_name":"MiOS"}}})
    }
    #[test]
    fn shared_policy_preserves_host_and_guest_namespaces_and_operator_values() {
        let mut config = fixture();
        assert_eq!(terminal_config(&config, "", true).unwrap()[6], "ai");
        assert_eq!(terminal_config(&config, "", false).unwrap()[4], "");
        config["keybindings"]["socket_name"] = json!("custom-guest");
        config["terminal"]["socket_root"] = json!("/run/user/1000");
        let policy = terminal_config(&config, "agents", false).unwrap();
        assert_eq!(policy[0], "custom-guest");
        assert_eq!(policy[8], "/run/user/1000");
        let host = host_tmux_args(&config, r"C:\Users\user\host.conf").unwrap();
        assert_eq!(host[1], "host");
        assert!(host.contains(&"cmd.exe".into()));
        assert!(!host.contains(&"custom-guest".into()));
        config["keybindings"]["mouse"] = json!(false);
        assert!(host_tmux_config(&config)
            .unwrap()
            .contains("set -g mouse off"));
    }
    #[test]
    fn landscape_portrait_and_fullscreen_keep_existing_panes() {
        let config = fixture();
        let landscape =
            render_monitor(&config, "python.exe", "monitor.py", "cmd.exe", false).unwrap();
        assert_eq!(landscape.iter().filter(|a| *a == "--title").count(), 2);
        assert!(landscape
            .windows(4)
            .any(|w| w == ["split-pane", "-V", "-s", "0.62"]));
        let portrait =
            render_monitor(&config, "python.exe", "monitor.py", "cmd.exe", true).unwrap();
        assert!(portrait
            .windows(4)
            .any(|w| w == ["split-pane", "-H", "-s", "0.38"]));
        let mut config = config;
        config["theme"]["launch_mode"] = json!("fullscreen");
        let full = render_monitor(&config, "python.exe", "monitor.py", "cmd.exe", false).unwrap();
        assert_eq!(full.iter().filter(|a| *a == "--title").count(), 5);
        assert_eq!(full.iter().filter(|a| *a == "monitor.py").count(), 1);
    }
    #[test]
    fn invalid_config_and_command_separators_fail_before_launch() {
        let mut config = fixture();
        assert!(terminal_config(&config, "unknown", false).is_err());
        config["keybindings"]["socket_name"] = json!("bad\nname");
        assert!(terminal_config(&config, "", true).is_err());
        let mut config = fixture();
        config["terminal"]["monitor"]["split_landscape_head"] = json!(99);
        assert!(render_monitor(&config, "python.exe", "monitor.py", "cmd.exe", false).is_err());
        assert!(render_monitor(
            &fixture(),
            "python.exe",
            "monitor.py; new-tab cmd.exe",
            "cmd.exe",
            false
        )
        .is_err());
        config = fixture();
        config["terminal"]["windows"]["socket_name"] = json!("bad socket");
        assert!(host_tmux_args(&config, "host.conf").is_err());
    }
}
