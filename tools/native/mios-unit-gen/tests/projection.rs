// AI-hint: Tests systemd unit projection against the shipped units in usr/lib/systemd/system.

//! The projection contract: `[units.*]` in the SSOT must RENDER the units the
//! tree ships. What replaced `golden_master.rs`, which diffed
//! `usr/lib/systemd/system` against `tests/golden/` -- a byte copy of that same
//! tree. It could only fail when someone forgot to update the copy, which is
//! what eventually happened, and it never once called the renderer.

use mios_unit_gen::{
    drift_register, project, project_deployment, render_blade_dropins, render_blade_karg,
    render_uki_cmdline, DeploymentKind, BLADE_KARG, UKI_CMDLINE,
};
use std::fs;
use std::path::{Path, PathBuf};

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn ssot() -> String {
    std::fs::read_to_string(root().join("usr/share/mios/mios.toml")).expect("SSOT is readable")
}

#[test]
fn test_declared_units_render_or_are_registered() {
    let p = project(&root()).expect("projection runs");
    let register = drift_register(&ssot()).expect("register parses");

    let unexpected: Vec<&String> = p.drifted.iter().filter(|f| !register.contains(f)).collect();
    assert!(
        unexpected.is_empty(),
        "[units.*] no longer renders these units, and they are not in \
         [unit_projection].drift -- either fix the declaration or register the debt: {unexpected:#?}"
    );
}

#[test]
fn test_the_register_only_shrinks() {
    let p = project(&root()).expect("projection runs");
    let register = drift_register(&ssot()).expect("register parses");

    let stale: Vec<&String> = register.iter().filter(|f| !p.drifted.contains(f)).collect();
    assert!(
        stale.is_empty(),
        "these units render faithfully now -- drop them from [unit_projection].drift. \
         A register that keeps entries it no longer needs stops measuring the debt \
         and starts hiding the next one: {stale:#?}"
    );
}

#[test]
fn test_every_declared_unit_exists_on_disk() {
    let p = project(&root()).expect("projection runs");
    assert!(
        p.missing.is_empty(),
        "[units.*] declares units the tree does not ship: {:#?}",
        p.missing
    );
}

/// The gate must not be able to pass over an empty set. `[units.*]` covering
/// nothing would make every other assertion here vacuously true.
#[test]
fn test_the_projection_is_not_empty() {
    let p = project(&root()).expect("projection runs");
    let declared = p.faithful.len() + p.drifted.len() + p.missing.len();
    assert!(declared > 0, "[units.*] declares no units at all");
    assert!(
        !p.faithful.is_empty(),
        "not one declared unit renders faithfully -- the renderer is broken, not the SSOT"
    );
}

#[test]
fn test_undeclared_unit_inventory_includes_only_top_level_units() {
    let temp = tempfile::tempdir().unwrap();
    write_fixture(
        temp.path(),
        "usr/share/mios/mios.toml",
        "[units.\"declared.service\".Service]\nExecStart = \"/bin/true\"\n",
    );
    write_fixture(
        temp.path(),
        "usr/lib/systemd/system/declared.service",
        "[Service]\nExecStart=/bin/true\n",
    );
    let names = [
        "authored.mount",
        "authored.service",
        "authored.slice",
        "authored.socket",
        "authored.target",
        "authored.timer",
        "authored.path",
    ];
    for name in names {
        write_fixture(
            temp.path(),
            &format!("usr/lib/systemd/system/{name}"),
            "authored\n",
        );
    }
    write_fixture(
        temp.path(),
        "usr/lib/systemd/system/ignored.conf",
        "not a unit\n",
    );
    write_fixture(
        temp.path(),
        "usr/lib/systemd/system/nested/ignored.service",
        "not top level\n",
    );
    let projection = project(temp.path()).unwrap();
    let mut expected = names.map(str::to_owned).to_vec();
    expected.sort();
    assert_eq!(projection.undeclared, expected);
    assert_eq!(projection.faithful, ["declared.service"]);
    assert!(projection.missing.is_empty());
}

fn blade_ssot(kind: &str) -> String {
    format!("[blade]\ntype = {kind:?}\n[blade.archetypes]\nhybrid = []\nendpoint = []\n")
}

#[test]
fn blade_karg_is_a_single_bare_array_and_marks_its_producer() {
    let body = render_blade_karg(&blade_ssot("endpoint")).unwrap();
    let doc: toml::Value = body.parse().unwrap();
    assert_eq!(doc.as_table().unwrap().len(), 1);
    assert_eq!(
        doc["kargs"].as_array().unwrap(),
        &[toml::Value::String("mios.blade=endpoint".into())]
    );
    assert!(body.contains("DO NOT EDIT"));
    assert!(body.contains("mios-unit-gen blade-karg"));
}

#[test]
fn blade_karg_rejects_empty_missing_or_undeclared_type() {
    for input in [
        "".to_owned(),
        "[blade.archetypes]\nhybrid = []\n".to_owned(),
        blade_ssot(""),
        blade_ssot("   "),
        blade_ssot("nosucharchetype"),
    ] {
        assert!(render_blade_karg(&input).is_err(), "accepted {input:?}");
    }
}

#[test]
fn committed_blade_karg_matches_ssot_and_reader_contract() {
    let body = render_blade_karg(&ssot()).unwrap();
    assert_eq!(
        fs::read_to_string(root().join(BLADE_KARG))
            .unwrap()
            .replace("\r\n", "\n"),
        body
    );
    let doc: toml::Value = ssot().parse().unwrap();
    assert!(body.contains(&format!(
        "mios.blade={}",
        doc["blade"]["type"].as_str().unwrap()
    )));
    let resolver = fs::read_to_string(root().join("usr/lib/mios/blade.sh")).unwrap();
    assert!(resolver.contains("_cmdline_tok mios.blade"));
    assert!(resolver.contains("\"${key}=\"*)"));
    assert!(
        fs::read_to_string(root().join("usr/libexec/mios/role-apply"))
            .unwrap()
            .contains("blade.sh")
    );
}

#[test]
fn capability_projection_preserves_selectors_tolerations_and_and_rules() {
    let input = "[blade.requires]\nzed = [\" gpu-serving \", \"service-plane\", \"\"]\nalpha = \"controller\"\nempty = []\n";
    let out = render_blade_dropins(input).unwrap();
    assert_eq!(out.len(), 5);
    assert!(out["usr/share/mios/dropins/blade-gpu-serving.conf"]
        .contains("ConditionPathExists=/etc/mios/blade.d/gpu-serving"));
    let yaml = &out["usr/share/mios/dropins/k3s-node-selectors.yaml"];
    assert!(yaml.find("  alpha:").unwrap() < yaml.find("  zed:").unwrap());
    assert!(yaml.contains("mios.capability/gpu-serving: \"true\""));
    assert!(yaml.contains("key: \"mios.capability/service-plane\"\n        operator: \"Exists\"\n        effect: \"NoSchedule\""));
    let rules = &out["usr/share/mios/dropins/pcs-location-rules.pcs"];
    assert!(rules.contains(
        "zed rule score=100 mios-cap-gpu-serving eq true and mios-cap-service-plane eq true"
    ));
    assert!(!rules.contains("location empty"));
}

#[test]
fn capability_projection_rejects_paths_and_non_string_values() {
    for input in [
        "[blade.requires]\nx = [42]",
        "[blade.requires]\nx = false",
        "[blade.requires]\nx = [\"../../outside\"]",
    ] {
        assert!(render_blade_dropins(input).is_err(), "accepted {input:?}");
    }
}

fn write_fixture(root: &Path, relative: &str, body: &str) {
    let path = root.join(relative);
    fs::create_dir_all(path.parent().unwrap()).unwrap();
    fs::write(path, body).unwrap();
}

#[test]
fn deployment_check_names_mutated_and_missing_files_without_writing() {
    let temp = tempfile::tempdir().unwrap();
    write_fixture(
        temp.path(),
        "usr/share/mios/mios.toml",
        &blade_ssot("endpoint"),
    );
    assert_eq!(
        project_deployment(temp.path(), DeploymentKind::BladeKarg, false, None).unwrap(),
        1
    );
    project_deployment(temp.path(), DeploymentKind::BladeKarg, true, None).unwrap();
    write_fixture(temp.path(), BLADE_KARG, "kargs = [\"mios.blade=wrong\"]\n");
    let err = project_deployment(temp.path(), DeploymentKind::BladeKarg, true, None)
        .unwrap_err()
        .to_string();
    assert!(err.contains(BLADE_KARG) && err.contains("drifted"), "{err}");
    assert!(fs::read_to_string(temp.path().join(BLADE_KARG))
        .unwrap()
        .contains("wrong"));
    fs::remove_file(temp.path().join(BLADE_KARG)).unwrap();
    let err = project_deployment(temp.path(), DeploymentKind::BladeKarg, true, None)
        .unwrap_err()
        .to_string();
    assert!(
        err.contains(BLADE_KARG) && err.contains("cannot read"),
        "{err}"
    );
}

#[test]
fn deployment_output_root_and_ssot_input_are_independent() {
    let input = tempfile::tempdir().unwrap();
    let output = tempfile::tempdir().unwrap();
    write_fixture(
        input.path(),
        "choice.toml",
        "[blade.requires]\nx = [\"controller\"]\n",
    );
    let path = input.path().join("choice.toml");
    assert_eq!(
        project_deployment(
            output.path(),
            DeploymentKind::BladeDropins,
            false,
            Some(&path)
        )
        .unwrap(),
        3
    );
    project_deployment(
        output.path(),
        DeploymentKind::BladeDropins,
        true,
        Some(&path),
    )
    .unwrap();
    assert!(!input.path().join("usr/share/mios/dropins").exists());
}

#[test]
fn uki_cmdline_preserves_filename_and_token_order_including_duplicates() {
    let temp = tempfile::tempdir().unwrap();
    write_fixture(
        temp.path(),
        "usr/lib/bootc/kargs.d/20-role.toml",
        "kargs = [\"mios.blade=endpoint\", \"quiet\"]\n",
    );
    write_fixture(
        temp.path(),
        "usr/lib/bootc/kargs.d/01-base.toml",
        "kargs = [\"quiet\", \"mios.blade=hybrid\"]\n",
    );
    write_fixture(temp.path(), "usr/lib/bootc/kargs.d/ignored.txt", "not toml");
    assert_eq!(
        render_uki_cmdline(temp.path()).unwrap(),
        "quiet mios.blade=hybrid mios.blade=endpoint quiet\n"
    );
    project_deployment(temp.path(), DeploymentKind::UkiCmdline, false, None).unwrap();
    project_deployment(temp.path(), DeploymentKind::UkiCmdline, true, None).unwrap();
}

#[test]
fn invalid_uki_input_never_erases_the_existing_cmdline() {
    let temp = tempfile::tempdir().unwrap();
    write_fixture(temp.path(), UKI_CMDLINE, "known-good\n");
    for input in ["kargs = [", "kargs = false", "kargs = [42]"] {
        write_fixture(temp.path(), "usr/lib/bootc/kargs.d/01-bad.toml", input);
        let err = project_deployment(temp.path(), DeploymentKind::UkiCmdline, false, None)
            .unwrap_err()
            .to_string();
        assert!(err.contains("01-bad.toml"), "{err}");
        assert_eq!(
            fs::read_to_string(temp.path().join(UKI_CMDLINE)).unwrap(),
            "known-good\n"
        );
    }
}

#[test]
fn deployment_cli_writes_then_checks_the_requested_root() {
    let temp = tempfile::tempdir().unwrap();
    write_fixture(
        temp.path(),
        "usr/share/mios/mios.toml",
        &blade_ssot("endpoint"),
    );
    let invoke = |check: bool| {
        let mut cmd = std::process::Command::new(env!("CARGO_BIN_EXE_mios-unit-gen"));
        cmd.args(["blade-karg", "--root"]).arg(temp.path());
        if check {
            cmd.arg("--check");
        }
        cmd.output().unwrap()
    };
    assert!(invoke(false).status.success());
    assert!(invoke(true).status.success());
    write_fixture(temp.path(), BLADE_KARG, "corrupt\n");
    let result = invoke(true);
    assert!(!result.status.success());
    assert!(String::from_utf8_lossy(&result.stderr).contains(BLADE_KARG));
}

#[test]
fn deployment_cli_advertises_modes_and_rejects_incomplete_options() {
    let binary = env!("CARGO_BIN_EXE_mios-unit-gen");
    let advertised = std::process::Command::new(binary)
        .arg("--list-projections")
        .output()
        .unwrap();
    assert!(advertised.status.success());
    assert_eq!(
        String::from_utf8(advertised.stdout).unwrap(),
        "blade-dropins\nblade-karg\nuki-cmdline\n"
    );
    let temp = tempfile::tempdir().unwrap();
    for options in [vec!["--root"], vec!["--toml", "--check"], vec!["--unknown"]] {
        let result = std::process::Command::new(binary)
            .arg("blade-karg")
            .args(&options)
            .current_dir(temp.path())
            .output()
            .unwrap();
        assert!(!result.status.success(), "accepted {options:?}");
        assert!(String::from_utf8_lossy(&result.stderr).contains(options[0]));
        assert!(!temp.path().join(BLADE_KARG).exists());
    }
}
