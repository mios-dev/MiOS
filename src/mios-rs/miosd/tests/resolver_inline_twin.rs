// AI-hint: Pins that miosd's resolver renders arrays of inline tables byte-equal to mios_toml.py's _toml_inline when built in THIS workspace, whose toml crate lays inline tables out differently (resolver twin, Law 13).
// AI-related: tools/native/mios-resolver/src/walk.rs, usr/lib/mios/mios_toml.py, tools/check-runtime.py

use std::path::Path;
use std::process::Command;

/// Keys out of order, a nested table that is not last, a Windows path: every
/// rule of the inline contract, shaped like [desktop].apps.
const SSOT: &str = r#"apps = [
  { role = "browser", overrides = { B = 2, A = 1 }, id = "org.example.App", remote = "flathub" },
  { path = 'C:\MiOS\bin', tags = ["x", "y"] },
]
"#;

fn rust_render() -> String {
    let v: toml::Value = toml::from_str(SSOT).expect("fixture parses");
    mios_resolver::walk::process_val("desktop.apps", v.get("apps").expect("apps"), 0)
}

#[test]
fn nested_tables_render_last_and_keys_sorted() {
    assert_eq!(
        rust_render(),
        concat!(
            r#"{ id = "org.example.App", remote = "flathub", role = "browser", overrides = { A = 1, B = 2 } },"#,
            r#"{ path = 'C:\MiOS\bin', tags = ["x", "y"] }"#,
        )
    );
}

#[test]
fn equals_the_python_twin() {
    let repo = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..");
    let script = format!(
        "import sys, tomllib; sys.path.insert(0, {lib:?}); import mios_toml; \
         print(mios_toml.process_val('desktop.apps', tomllib.loads(sys.stdin.read())['apps']))",
        lib = repo.join("usr/lib/mios").display().to_string()
    );
    let out = Command::new("python3")
        .args(["-c", &script])
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .spawn()
        .and_then(|mut c| {
            use std::io::Write;
            c.stdin.take().expect("stdin").write_all(SSOT.as_bytes())?;
            c.wait_with_output()
        })
        .expect("python3 runs");
    assert!(out.status.success(), "python twin failed");
    assert_eq!(
        rust_render(),
        String::from_utf8_lossy(&out.stdout).trim_end()
    );
}
