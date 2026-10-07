// AI-hint: Integration tests for mios-gen pipeline-index verb -- verifies TSV generation, NN space bounds, uniqueness, and --check verification.
// AI-related: tools/native/mios-gen/src/pipeline_index.rs, docs/design/doc-rust-static-port.md

use std::fs;
use std::process::Command;

fn bin() -> &'static str {
    env!("CARGO_BIN_EXE_mios-gen")
}

#[test]
fn test_pipeline_index_render_and_check() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let auto_dir = root.join("automation");
    let ref_dir = root.join("usr/share/mios/reference");
    let ssot_dir = root.join("usr/share/mios");
    fs::create_dir_all(&auto_dir).unwrap();
    fs::create_dir_all(&ref_dir).unwrap();
    fs::create_dir_all(&ssot_dir).unwrap();

    fs::write(
        ssot_dir.join("mios.toml"),
        "[pipeline.space]\nmin = 0\nmax = 99\n[pipeline.invariants]\nprefix_unique = true\n",
    )
    .unwrap();

    let s01 =
        "#!/usr/bin/env bash\n# AI-hint: test hint\n# First stage description\necho stage 01\n";
    let s02 = "#!/usr/bin/env bash\n# Second stage description\necho stage 02\n";
    fs::write(auto_dir.join("01-first.sh"), s01).unwrap();
    fs::write(auto_dir.join("02-second.sh"), s02).unwrap();

    // 1. Generation mode
    let out = Command::new(bin())
        .arg("pipeline-index")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(0));

    let tsv_path = ref_dir.join("pipeline-index.tsv");
    assert!(tsv_path.is_file());
    let content = fs::read_to_string(&tsv_path).unwrap();
    let expected = "# NN\tkind\tname\tfile\toneline\n01\tscript\tfirst\tautomation/01-first.sh\tFirst stage description\n02\tscript\tsecond\tautomation/02-second.sh\tSecond stage description\n";
    assert_eq!(content, expected);

    // 2. Check mode - clean
    let out = Command::new(bin())
        .arg("pipeline-index")
        .arg("--root")
        .arg(root)
        .arg("--check")
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.contains("PASS: pipeline-index.tsv is in sync."));

    // 3. Check mode - tampered
    fs::write(&tsv_path, "# tampered\n").unwrap();
    let out = Command::new(bin())
        .arg("pipeline-index")
        .arg("--root")
        .arg(root)
        .arg("--check")
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("out of sync with automation scripts"));
}

#[test]
fn test_duplicate_nn_prefix_fails() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let auto_dir = root.join("automation");
    fs::create_dir_all(&auto_dir).unwrap();

    fs::write(auto_dir.join("01-first.sh"), "#!/bin/bash\n# desc\n").unwrap();
    fs::write(auto_dir.join("01-duplicate.sh"), "#!/bin/bash\n# desc2\n").unwrap();

    let out = Command::new(bin())
        .arg("pipeline-index")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("Duplicate NN prefix found: 01"));
}
