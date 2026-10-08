// AI-hint: Full SSOT host projection controls: overrides, unsupported fonts, rejected values, and operator-file preservation.
use mios_service_core::{host_tmux, launcher::host_tmux_config_with_font};
use serde_json::{json, Value};
use std::fs;

fn config() -> Value {
    let doc: toml::Value =
        toml::from_str(include_str!("../../../../usr/share/mios/mios.toml")).unwrap();
    serde_json::to_value(doc).unwrap()
}

#[test]
fn renders_real_palette_keys_shell_and_safe_glyph_fallback() {
    let mut config = config();
    config["terminal"]["windows"]["glyph_mode"] = json!("auto");
    let rendered = host_tmux_config_with_font(&config, false).unwrap();
    assert!(rendered.contains(config["colors"]["fg"].as_str().unwrap()));
    assert!(rendered.contains("set -g status-position bottom"));
    assert!(rendered.contains("bind-key h select-pane -L"));
    assert!(rendered.contains("mios.cmd ai"));
    assert!(rendered.contains("mios.cmd agents --watch"));
    assert!(!rendered.contains("/usr/libexec/"));
    assert!(rendered.contains("set -g history-limit 9000"));
    assert!(rendered.contains("set -g default-shell \"cmd.exe\""));
    assert!(
        rendered.is_ascii(),
        "unknown font must not emit private-use glyphs"
    );
    assert!(
        rendered.lines().count() > 55,
        "must render the complete configuration"
    );
}

#[test]
fn changed_operator_values_reach_theme_and_native_shell() {
    let mut config = config();
    config["colors"]["fg"] = json!("#ABCDEF");
    config["theme"]["tmux"]["status_position"] = json!("top");
    config["theme"]["tmux"]["status_interval_s"] = json!(7);
    config["keybindings"]["mouse"] = json!(false);
    config["terminal"]["scrollback_rows"] = json!(1234);
    config["terminal"]["windows"]["shell"] = json!(r"C:\Program Files\PowerShell\7\pwsh.exe");
    let rendered = host_tmux_config_with_font(&config, false).unwrap();
    for expected in [
        "#ABCDEF",
        "set -g status-position top",
        "set -g status-interval 7",
        "set -g mouse off",
        "set -g history-limit 1234",
        r"C:\\Program Files\\PowerShell\\7\\pwsh.exe",
    ] {
        assert!(rendered.contains(expected), "missing override: {expected}");
    }
    config["terminal"]["windows"]["glyph_mode"] = json!("nerd");
    config["theme"]["tmux"]["glyph_mode"] = json!("nerd");
    assert!(host_tmux_config_with_font(&config, true)
        .unwrap()
        .contains(''));
}

#[test]
fn invalid_policy_and_config_injection_fail_before_publication() {
    for (path, value, error) in [
        ("/colors/fg", json!("red"), "colors"),
        ("/theme/tmux/status_interval_s", json!(0), "positive"),
        (
            "/terminal/windows/glyph_mode",
            json!("mystery"),
            "glyph_mode",
        ),
        (
            "/terminal/windows/shell",
            json!("cmd.exe\nrun-shell evil"),
            "argument",
        ),
        ("/keybindings/tmux_prefix", json!("C-\n"), "tmux_prefix"),
    ] {
        let mut config = config();
        *config.pointer_mut(path).unwrap() = value;
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("host.conf");
        fs::write(
            &target,
            "# Generated from layered MiOS SSOT by native Rust.\nprevious",
        )
        .unwrap();
        let old = fs::read(&target).unwrap();
        let failure = host_tmux::stage(&config, &target, &[], false).unwrap_err();
        assert!(failure.contains(error), "{path}: {failure}");
        assert_eq!(fs::read(&target).unwrap(), old);
        assert_eq!(fs::read_dir(tmp.path()).unwrap().count(), 1);
    }
}

#[test]
fn publication_backs_up_owned_legacy_and_preserves_operator_config() {
    let tmp = tempfile::tempdir().unwrap();
    let canonical = tmp.path().join("terminal/host.conf");
    let legacy = tmp.path().join(".tmux.conf");
    let operator = tmp.path().join("operator.conf");
    let old = "# AI-hint: MiOS Windows Native Tmux Configuration\nold theme\n";
    fs::write(&legacy, old).unwrap();
    fs::write(&operator, "# Operator custom settings\nset -g prefix C-a\n").unwrap();
    let reload = host_tmux::stage(
        &config(),
        &canonical,
        &[legacy.clone(), operator.clone()],
        false,
    )
    .unwrap();
    assert!(reload.contains(&legacy));
    assert!(!reload.contains(&operator));
    assert_eq!(fs::read(&canonical).unwrap(), fs::read(&legacy).unwrap());
    assert!(fs::read_to_string(&operator).unwrap().contains("C-a"));
    let backups: Vec<_> = fs::read_dir(tmp.path())
        .unwrap()
        .flatten()
        .filter(|e| e.file_name().to_string_lossy().contains("pre-native"))
        .collect();
    assert_eq!(backups.len(), 1);
    assert_eq!(fs::read_to_string(backups[0].path()).unwrap(), old);
    host_tmux::stage(&config(), &canonical, &[legacy, operator], false).unwrap();
    assert_eq!(
        fs::read_dir(tmp.path()).unwrap().count(),
        4,
        "identical re-stage must not add backups"
    );
}

#[test]
fn non_regular_destination_rejected_before_any_write() {
    let tmp = tempfile::tempdir().unwrap();
    let canonical = tmp.path().join("host.conf");
    let legacy = tmp.path().join("directory.conf");
    fs::create_dir(&legacy).unwrap();
    assert!(host_tmux::stage(&config(), &canonical, &[legacy], false)
        .unwrap_err()
        .contains("non-regular"));
    assert!(!canonical.exists());
}

#[test]
fn console_palette_uses_named_defaults_and_windows_slot_order() {
    let mut config = config();
    config["colors"]["bg"] = json!("#123456");
    config["colors"]["fg"] = json!("#ABCDEF");
    config["colors"]["ansi_4_blue"] = json!("#010203");
    let palette = mios_service_core::launcher::windows_console_palette(&config).unwrap();
    assert_eq!(palette[0], 0x563412);
    assert_eq!(palette[7], 0xEFCDAB);
    assert_eq!(palette[1], 0x030201);
    config["colors"]["ansi_4_blue"] = json!("invalid");
    assert!(
        mios_service_core::launcher::windows_console_palette(&config)
            .unwrap_err()
            .contains("ansi_4_blue")
    );
}
