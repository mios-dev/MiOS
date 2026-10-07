// AI-hint: Integration tests for mios-gen metal-vs-hosted verb (T-1010, AGY-1089).
// AI-related: tools/native/mios-gen/src/metal_vs_hosted.rs, usr/share/doc/mios/reference/metal-vs-hosted.md, docs/design/doc-rust-static-port.md

use std::fs;
use std::process::Command;

fn bin() -> &'static str {
    env!("CARGO_BIN_EXE_mios-gen")
}

fn write_synthetic_ssot(root: &std::path::Path) {
    let mios_dir = root.join("usr/share/mios");
    fs::create_dir_all(&mios_dir).unwrap();

    let toml = r#"
[blade.hardware]
min_interfaces = 1
min_ap_capable = 0
max_radios = 1

[blade.cluster]
k3s_servers = 3
control_plane_ha = true
localhost_hosts = 3

[blade.fencing]
method = "sbd"
diskless = true

[blade.storage]
replication = "all"
at_rest = "dmcrypt"

[blade.uplink]
failover = ["local", "peer"]

[blade.mesh]
blocks_boot = false
federate = "native"

[blade.archetypes]
endpoint = []
hybrid = ["service-plane", "gpu-serving", "controller"]

[blade.requires]
mios-llm-light = ["service-plane"]
mios-pgvector = ["service-plane"]
mios-hermes = ["service-plane"]
mios-k3s = ["controller", "service-plane"]

[blade.seat_side]
seat_side = ["mios-agent-pipe", "hermes-dashboard"]

[blade.planes.ai]
owner = "either"
role = "the OpenAI-compatible front door and the lanes behind it"
markers = []
wired_by = "usr/share/containers/systemd/mios-llm-light.container"

[blade.planes.router]
owner = "mini"
role = "the uplink"
markers = ["firewalld"]
wired_by = "usr/lib/sysctl.d/99-mios-vmhost.conf"

[greenboot]
critical_services = ["agent-pipe", "llm-light"]
blade_reachability_critical = false

[greenboot.probe.agent_pipe]
unit = "mios-agent-pipe.service"

[greenboot.probe.llm_light]
unit = "mios-llm-light.service"

[packages.core]
pkgs = ["firewalld"]

[llamacpp]
bake_models = "test-model.gguf = example/test:model.gguf"

[ai.vllm]
bake_model = ""
enable = false
"#;
    fs::write(mios_dir.join("mios.toml"), toml).unwrap();
}

#[test]
fn test_metal_vs_hosted_render_and_check() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    write_synthetic_ssot(root);

    // 1. Generate the file
    let out = Command::new(bin())
        .arg("metal-vs-hosted")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must run mios-gen");
    assert_eq!(out.status.code(), Some(0));

    let doc_path = root.join("usr/share/doc/mios/reference/metal-vs-hosted.md");
    assert!(doc_path.exists());
    let doc_content = fs::read_to_string(&doc_path).unwrap();
    assert!(doc_content.contains("# MiOS-Metal vs hosted MiOS — the products, then the modes"));
    assert!(doc_content.contains("## Part 1 — the two products"));
    assert!(doc_content.contains("## Part 2 — the two modes"));

    // 2. Run --check mode on identical file
    let check_out = Command::new(bin())
        .arg("metal-vs-hosted")
        .arg("--root")
        .arg(root)
        .arg("--check")
        .output()
        .expect("must run mios-gen --check");
    assert_eq!(check_out.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&check_out.stdout);
    assert!(stdout.contains("matches the SSOT"));

    // 3. Plant defect (drift)
    fs::write(&doc_path, "tampered content\n").unwrap();
    let drift_out = Command::new(bin())
        .arg("metal-vs-hosted")
        .arg("--root")
        .arg(root)
        .arg("--check")
        .output()
        .expect("must run mios-gen --check");
    assert_eq!(drift_out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&drift_out.stderr);
    assert!(stderr.contains("has drifted from the SSOT"));
}

#[test]
fn test_metal_vs_hosted_json_format() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    write_synthetic_ssot(root);

    let out = Command::new(bin())
        .arg("--format")
        .arg("json")
        .arg("metal-vs-hosted")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must run mios-gen");
    assert_eq!(out.status.code(), Some(0));

    let stdout = String::from_utf8_lossy(&out.stdout);
    let v: serde_json::Value = serde_json::from_str(&stdout).unwrap();
    assert_eq!(v["status"], "clean");
    assert_eq!(v["subcommand"], "metal-vs-hosted");
    assert_eq!(v["target"], "usr/share/doc/mios/reference/metal-vs-hosted.md");
    assert_eq!(v["violations"], 0);
}

#[test]
fn test_metal_vs_hosted_negative_missing_ssot() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();

    let out = Command::new(bin())
        .arg("metal-vs-hosted")
        .arg("--root")
        .arg(root)
        .arg("--check")
        .output()
        .expect("must run mios-gen --check");
    assert_eq!(out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("cannot read the SSOT"));
}
