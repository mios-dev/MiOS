// AI-hint: Integration tests for mios-gen egress-firewall verb -- verifies mode rendering, user resolution, and nftables rule syntax.
// AI-related: tools/native/mios-gen/src/main.rs, usr/share/mios/mios.toml, docs/design/doc-rust-static-port.md

use std::fs;
use std::process::Command;

fn bin() -> &'static str {
    env!("CARGO_BIN_EXE_mios-gen")
}

#[test]
fn test_egress_firewall_generation_modes() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let toml_dir = root.join("usr/share/mios");
    fs::create_dir_all(&toml_dir).unwrap();

    let service_dir = root.join("usr/lib/systemd/system");
    fs::create_dir_all(&service_dir).unwrap();
    fs::write(
        service_dir.join("mios-agent-pipe.service"),
        "[Unit]\nDescription=Agent Pipe\n[Service]\nUser=test-agent\nExecStart=/usr/bin/true\n",
    )
    .unwrap();

    // Mode: enforce with IP allowlist
    let toml_content = r#"
[security.egress]
mode = "enforce"
allow = ["1.1.1.1", "2001:db8::1", "8.8.8.8"]
"#;
    fs::write(toml_dir.join("mios.toml"), toml_content).unwrap();

    let out = Command::new(bin())
        .arg("egress-firewall")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(0));

    let nft_path = root.join("usr/share/mios/security/egress.nft");
    assert!(nft_path.is_file());
    let content = fs::read_to_string(&nft_path).unwrap();

    assert!(content.contains("meta skuid != \"test-agent\" accept"));
    assert!(content.contains("ip daddr { 1.1.1.1, 8.8.8.8 } accept"));
    assert!(content.contains("ip6 daddr { 2001:db8::1 } accept"));
    assert!(content.contains("log prefix \"mios-egress-drop \" drop"));
    assert!(
        content.contains("ENFORCE: the agent's non-allowed external egress is logged + DROPPED.")
    );

    // Mode: audit
    let toml_audit = r#"
[security.egress]
mode = "audit"
"#;
    fs::write(toml_dir.join("mios.toml"), toml_audit).unwrap();
    let out = Command::new(bin())
        .arg("egress-firewall")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(0));

    let content_audit = fs::read_to_string(&nft_path).unwrap();
    assert!(content_audit.contains("log prefix \"mios-egress-audit \" accept"));
    assert!(content_audit.contains("AUDIT: the agent's external egress is LOGGED then accepted"));

    // Mode: off
    let toml_off = r#"
[security.egress]
mode = "off"
"#;
    fs::write(toml_dir.join("mios.toml"), toml_off).unwrap();
    let out = Command::new(bin())
        .arg("egress-firewall")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(0));

    let content_off = fs::read_to_string(&nft_path).unwrap();
    assert!(content_off.contains("accept   # mode=off -> no-op even if applied"));
    assert!(content_off.contains("OFF: informational ruleset; applying it changes nothing."));
}

#[test]
fn test_malformed_toml_fails() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let toml_dir = root.join("usr/share/mios");
    fs::create_dir_all(&toml_dir).unwrap();

    let toml_content = "invalid_toml = [unclosed";
    fs::write(toml_dir.join("mios.toml"), toml_content).unwrap();

    let out = Command::new(bin())
        .arg("egress-firewall")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_ne!(out.status.code(), Some(0));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("Failed to parse") || stderr.contains("Error:"));
}

#[test]
fn test_egress_firewall_json_format() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let toml_dir = root.join("usr/share/mios");
    fs::create_dir_all(&toml_dir).unwrap();
    let toml_off = r#"
[security.egress]
mode = "off"
"#;
    fs::write(toml_dir.join("mios.toml"), toml_off).unwrap();
    let out = Command::new(bin())
        .arg("--format")
        .arg("json")
        .arg("egress-firewall")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.contains("\"status\": \"clean\""));
    assert!(stdout.contains("\"subcommand\": \"egress-firewall\""));
}
