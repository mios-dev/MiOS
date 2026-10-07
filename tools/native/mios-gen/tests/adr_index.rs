// AI-hint: Integration tests for mios-gen adr-index verb -- verifies ADR.md breadcrumb index generation, front-matter parsing, SSOT consistency, --check verification, and negative controls.
// AI-related: tools/native/mios-gen/src/adr_index.rs, usr/share/doc/mios/adr/, docs/design/doc-rust-static-port.md

use std::fs;
use std::process::Command;

fn bin() -> &'static str {
    env!("CARGO_BIN_EXE_mios-gen")
}

fn write_test_ssot(root: &std::path::Path, meta: bool, dotfiles: bool, sha256_in_image: bool) {
    let mios_dir = root.join("usr/share/mios");
    fs::create_dir_all(&mios_dir).unwrap();
    let mut toml = String::new();
    if meta {
        toml.push_str("[meta]\nmios_version = \"0.3.0\"\n\n");
    }
    if dotfiles {
        toml.push_str("[dotfiles]\nregistry = [\"bash\", \"git\"]\n\n");
    }
    if sha256_in_image {
        toml.push_str("[image]\nref = \"ghcr.io/example/core@sha256:1234567890abcdef\"\n\n");
    } else {
        toml.push_str("[image]\nref = \"ghcr.io/example/core:latest\"\n\n");
    }
    fs::write(mios_dir.join("mios.toml"), toml).unwrap();
}

#[test]
fn test_adr_index_render_and_check() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let adr_dir = root.join("usr/share/doc/mios/adr");
    fs::create_dir_all(&adr_dir).unwrap();
    write_test_ssot(root, true, true, false);

    let adr1 = r#"<!-- AI-hint: ADR-0001 -->
---
adr: 0001
title: First Decision
status: accepted
date: 2026-07-12
laws: [1, 7]
ssot_keys: [build.bake, image.sidecars]
---

# 1. Context
First decision details.
"#;
    let adr2 = r#"<!-- AI-hint: ADR-0002 -->
---
adr: 0002
title: Second Decision
status: proposed
date: 2026-08-01
laws: [5]
ssot_keys: []
---

# 1. Context
Second decision details.
"#;
    fs::write(adr_dir.join("0001-first-decision.md"), adr1).unwrap();
    fs::write(adr_dir.join("0002-second-decision.md"), adr2).unwrap();

    // 1. Generation mode
    let out = Command::new(bin())
        .arg("adr-index")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(0));

    let adr_md = root.join("ADR.md");
    assert!(adr_md.is_file());
    let content = fs::read_to_string(&adr_md).unwrap();
    assert!(content.contains("**2 ADRs** (1 accepted)"));
    assert!(content.contains("| 0001 | [First Decision](usr/share/doc/mios/adr/0001-first-decision.md) | accepted | 2026-07-12 | 1, 7 | `build.bake`, `image.sidecars` |"));
    assert!(content.contains("| 0002 | [Second Decision](usr/share/doc/mios/adr/0002-second-decision.md) | proposed | 2026-08-01 | 5 | -- |"));

    // 2. Check mode - clean
    let out = Command::new(bin())
        .arg("adr-index")
        .arg("--root")
        .arg(root)
        .arg("--check")
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.contains("matches the 2 baked ADR(s) and SSOT consistency checks pass"));

    // 3. Check mode - stale after tampering
    fs::write(&adr_md, content + "\n<!-- hand edit -->\n").unwrap();
    let out = Command::new(bin())
        .arg("adr-index")
        .arg("--root")
        .arg(root)
        .arg("--check")
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("is stale -- run tools/generate-adr-index.py"));
}

#[test]
fn test_adr_index_negative_missing_front_matter() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let adr_dir = root.join("usr/share/doc/mios/adr");
    fs::create_dir_all(&adr_dir).unwrap();
    write_test_ssot(root, true, true, false);

    let malformed_adr = r#"# Missing front matter
No YAML front matter here.
"#;
    fs::write(adr_dir.join("0003-malformed.md"), malformed_adr).unwrap();

    let out = Command::new(bin())
        .arg("adr-index")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("VIOLATION: usr/share/doc/mios/adr/0003-malformed.md has no `adr:` front-matter -- add it or rename"));
}

#[test]
fn test_adr_index_negative_ssot_consistency() {
    // 1. Missing meta.mios_version
    {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let adr_dir = root.join("usr/share/doc/mios/adr");
        fs::create_dir_all(&adr_dir).unwrap();
        write_test_ssot(root, false, true, false);
        fs::write(
            adr_dir.join("0001-first.md"),
            "---\nadr: 0001\ntitle: X\nstatus: accepted\n---\n",
        )
        .unwrap();

        let _ = Command::new(bin())
            .arg("adr-index")
            .arg("--root")
            .arg(root)
            .output()
            .unwrap();
        let out = Command::new(bin())
            .arg("adr-index")
            .arg("--root")
            .arg(root)
            .arg("--check")
            .output()
            .unwrap();
        assert_eq!(out.status.code(), Some(1));
        let stderr = String::from_utf8_lossy(&out.stderr);
        assert!(stderr.contains("ADR-0009: mios.toml missing [meta].mios_version SSOT declaration"));
    }

    // 2. Missing dotfiles
    {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let adr_dir = root.join("usr/share/doc/mios/adr");
        fs::create_dir_all(&adr_dir).unwrap();
        write_test_ssot(root, true, false, false);
        fs::write(
            adr_dir.join("0001-first.md"),
            "---\nadr: 0001\ntitle: X\nstatus: accepted\n---\n",
        )
        .unwrap();

        let _ = Command::new(bin())
            .arg("adr-index")
            .arg("--root")
            .arg(root)
            .output()
            .unwrap();
        let out = Command::new(bin())
            .arg("adr-index")
            .arg("--root")
            .arg(root)
            .arg("--check")
            .output()
            .unwrap();
        assert_eq!(out.status.code(), Some(1));
        let stderr = String::from_utf8_lossy(&out.stderr);
        assert!(stderr.contains("ADR-0010: mios.toml missing or empty [dotfiles] table registry"));
    }

    // 3. Hardcoded @sha256: digest in [image]
    {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let adr_dir = root.join("usr/share/doc/mios/adr");
        fs::create_dir_all(&adr_dir).unwrap();
        write_test_ssot(root, true, true, true);
        fs::write(
            adr_dir.join("0001-first.md"),
            "---\nadr: 0001\ntitle: X\nstatus: accepted\n---\n",
        )
        .unwrap();

        let _ = Command::new(bin())
            .arg("adr-index")
            .arg("--root")
            .arg(root)
            .output()
            .unwrap();
        let out = Command::new(bin())
            .arg("adr-index")
            .arg("--root")
            .arg(root)
            .arg("--check")
            .output()
            .unwrap();
        assert_eq!(out.status.code(), Some(1));
        let stderr = String::from_utf8_lossy(&out.stderr);
        assert!(stderr.contains("ADR-0003: hardcoded @sha256 digest found in [image].ref"));
    }

    // 4. Shadow ADR directory outside usr/share/doc/mios/adr
    {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let adr_dir = root.join("usr/share/doc/mios/adr");
        let shadow_dir = root.join("docs/adr");
        fs::create_dir_all(&adr_dir).unwrap();
        fs::create_dir_all(&shadow_dir).unwrap();
        write_test_ssot(root, true, true, false);
        fs::write(
            adr_dir.join("0001-first.md"),
            "---\nadr: 0001\ntitle: X\nstatus: accepted\n---\n",
        )
        .unwrap();
        fs::write(shadow_dir.join("0099-shadow.md"), "# Shadow").unwrap();

        let _ = Command::new(bin())
            .arg("adr-index")
            .arg("--root")
            .arg(root)
            .output()
            .unwrap();
        let out = Command::new(bin())
            .arg("adr-index")
            .arg("--root")
            .arg(root)
            .arg("--check")
            .output()
            .unwrap();
        assert_eq!(out.status.code(), Some(1));
        let stderr = String::from_utf8_lossy(&out.stderr);
        assert!(stderr.contains("shadow ADR namespace found outside usr/share/doc/mios/adr"));
    }
}

#[test]
fn test_adr_index_json_format() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let adr_dir = root.join("usr/share/doc/mios/adr");
    fs::create_dir_all(&adr_dir).unwrap();
    write_test_ssot(root, true, true, false);

    fs::write(
        adr_dir.join("0001-first.md"),
        "---\nadr: 0001\ntitle: X\nstatus: accepted\n---\n",
    )
    .unwrap();

    let out = Command::new(bin())
        .arg("--format")
        .arg("json")
        .arg("adr-index")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&out.stdout);
    let v: serde_json::Value = serde_json::from_str(&stdout).unwrap();
    assert_eq!(v["status"], "clean");
    assert_eq!(v["subcommand"], "adr-index");
    assert_eq!(v["target"], "ADR.md");
    assert_eq!(v["violations"], 0);
}
