// AI-hint: Projects etc/mios/ai/config.json (the OpenAI-client connection config) from [ai] endpoint/agent_model/embed_model and [ports], so it cannot drift to a retired port.
// AI-related: usr/share/mios/mios.toml, etc/mios/ai/config.json, automation/98-drift-checks.sh, tools/sync-generated.sh

#![forbid(unsafe_code)]
#![warn(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

use std::path::{Path, PathBuf};
use std::process::ExitCode;

const SSOT: &str = "usr/share/mios/mios.toml";
const OUTPUT: &str = "etc/mios/ai/config.json";

const USAGE: &str = "usage: mios-ai-config [--root DIR] [--check]\n";

fn die(msg: &str) -> ExitCode {
    eprintln!("mios-ai-config: {msg}");
    ExitCode::from(2)
}

#[derive(Debug, PartialEq)]
struct AiConfig {
    base_url: String,
    default_model: String,
    embed_model: String,
}

/// JSON string escaping for the handful of characters a TOML string can carry
/// that JSON cannot carry verbatim.
fn json_str(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// The shape the existing consumers read: four keys, one line. `api_key` is
/// always empty -- a credential never comes from the vendor SSOT (Law 11); the
/// agent surface reads its bearer from /etc/mios/hermes/api.env instead.
fn render(cfg: &AiConfig) -> String {
    format!(
        "{{\"base_url\":{},\"default_model\":{},\"embed_model\":{},\"api_key\":\"\"}}\n",
        json_str(&cfg.base_url),
        json_str(&cfg.default_model),
        json_str(&cfg.embed_model)
    )
}

/// Expands every `${MIOS_PORT_<KEY>}` against [ports].<key>. Any other
/// placeholder, or a port key [ports] does not declare, is refused: a literal
/// `${...}` in a URL a client dials is a broken config, not a default.
fn expand_ports(s: &str, ports: &toml::value::Table) -> Result<String, String> {
    let mut out = String::with_capacity(s.len());
    let mut rest = s;
    while let Some(start) = rest.find("${") {
        out.push_str(&rest[..start]);
        let after = &rest[start + 2..];
        let end = after
            .find('}')
            .ok_or_else(|| format!("unterminated placeholder in '{s}'"))?;
        let name = &after[..end];
        let key = name
            .strip_prefix("MIOS_PORT_")
            .ok_or_else(|| format!("placeholder ${{{name}}} in '{s}' is not a [ports] reference"))?
            .to_ascii_lowercase();
        let port = ports
            .get(&key)
            .and_then(|v| v.as_integer())
            .ok_or_else(|| {
                format!("[ports].{key} (from ${{{name}}}) is not declared as an integer")
            })?;
        out.push_str(&port.to_string());
        rest = &after[end + 1..];
    }
    out.push_str(rest);
    Ok(out)
}

fn str_key(ai: &toml::Value, key: &str) -> Result<String, String> {
    let v = ai
        .get(key)
        .and_then(|v| v.as_str())
        .ok_or_else(|| format!("[ai].{key} is missing or not a string"))?
        .trim()
        .to_string();
    if v.is_empty() {
        return Err(format!(
            "[ai].{key} is empty -- refusing to project a config no client can use"
        ));
    }
    Ok(v)
}

fn read_config(root: &Path) -> Result<AiConfig, String> {
    let path = root.join(SSOT);
    let text = std::fs::read_to_string(&path)
        .map_err(|e| format!("{SSOT} could not be read ({e}) -- nothing was projected"))?;
    let doc: toml::Value = text
        .parse()
        .map_err(|e| format!("{SSOT} did not parse ({e}) -- nothing was projected"))?;
    let ai = doc
        .get("ai")
        .ok_or_else(|| format!("{SSOT} has no [ai] -- nothing was projected"))?;
    let ports = doc
        .get("ports")
        .and_then(|p| p.as_table())
        .ok_or_else(|| format!("{SSOT} has no [ports] -- nothing was projected"))?;

    let base_url = expand_ports(&str_key(ai, "endpoint")?, ports)?;
    Ok(AiConfig {
        base_url,
        default_model: str_key(ai, "agent_model")?,
        embed_model: str_key(ai, "embed_model")?,
    })
}

fn main() -> ExitCode {
    let mut root = PathBuf::from(".");
    let mut check = false;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--root" => match args.next() {
                Some(v) => root = PathBuf::from(v),
                None => return die("--root needs a directory"),
            },
            "--check" => check = true,
            "-h" | "--help" => {
                print!("{USAGE}");
                return ExitCode::SUCCESS;
            }
            other => return die(&format!("unknown argument '{other}'\n{USAGE}")),
        }
    }

    let cfg = match read_config(&root) {
        Ok(c) => c,
        Err(e) => return die(&e),
    };
    let want = render(&cfg);
    let out = root.join(OUTPUT);

    if check {
        let have = match std::fs::read_to_string(&out) {
            Ok(s) => s,
            Err(e) => {
                eprintln!(
                    "mios-ai-config: {OUTPUT} is missing or unreadable ({e}) -- regenerate it"
                );
                return ExitCode::from(1);
            }
        };
        if have == want {
            println!(
                "mios-ai-config: OK: {OUTPUT} matches [ai] + [ports] (base_url {})",
                cfg.base_url
            );
            return ExitCode::SUCCESS;
        }
        eprintln!(
            "mios-ai-config: {OUTPUT} differs from its projection -- it was hand-edited, \
             or the SSOT moved and it was not regenerated"
        );
        eprintln!("mios-ai-config:   have: {}", have.trim_end());
        eprintln!("mios-ai-config:   want: {}", want.trim_end());
        return ExitCode::from(1);
    }

    if let Some(parent) = out.parent() {
        if let Err(e) = std::fs::create_dir_all(parent) {
            return die(&format!("{} could not be created ({e})", parent.display()));
        }
    }
    if let Err(e) = std::fs::write(&out, &want) {
        return die(&format!("{OUTPUT} could not be written ({e})"));
    }
    println!(
        "mios-ai-config: projected {OUTPUT} (base_url {})",
        cfg.base_url
    );
    ExitCode::SUCCESS
}

#[cfg(test)]
// Fixture setup panics on failure by design; the crate-level bans exist
// to keep the production paths from doing that.
#[allow(clippy::unwrap_used, clippy::expect_used)]
mod tests {
    use super::*;
    use std::fs;

    fn root_with(ssot: &str) -> tempfile::TempDir {
        let d = tempfile::tempdir().expect("tempdir");
        fs::create_dir_all(d.path().join("usr/share/mios")).expect("mkdir");
        fs::write(d.path().join(SSOT), ssot).expect("write ssot");
        d
    }

    const GOOD: &str = "[ai]\nendpoint = \"http://localhost:${MIOS_PORT_AGENT_PIPE}/v1\"\n\
                        agent_model = \"MiOS AI\"\nembed_model = \"nomic-embed-text\"\n\
                        [ports]\nagent_pipe = 8700\n";

    #[test]
    fn a_good_ssot_projects_the_current_port() {
        let d = root_with(GOOD);
        let c = read_config(d.path()).expect("must read");
        assert_eq!("http://localhost:8700/v1", c.base_url);
        assert_eq!("MiOS AI", c.default_model);
        assert_eq!("nomic-embed-text", c.embed_model);
    }

    #[test]
    fn render_keeps_the_consumer_shape_and_never_carries_a_key() {
        let out = render(&AiConfig {
            base_url: "http://localhost:8700/v1".into(),
            default_model: "MiOS AI".into(),
            embed_model: "nomic-embed-text".into(),
        });
        assert_eq!(
            "{\"base_url\":\"http://localhost:8700/v1\",\"default_model\":\"MiOS AI\",\
             \"embed_model\":\"nomic-embed-text\",\"api_key\":\"\"}\n",
            out
        );
    }

    #[test]
    fn render_escapes_json_specials() {
        let out = render(&AiConfig {
            base_url: "u".into(),
            default_model: "a\"b\\c".into(),
            embed_model: "e".into(),
        });
        assert!(out.contains("\"a\\\"b\\\\c\""), "{out}");
    }

    #[test]
    fn a_port_key_ports_does_not_declare_is_refused() {
        let d = root_with(
            "[ai]\nendpoint = \"http://localhost:${MIOS_PORT_NOPE}/v1\"\n\
             agent_model = \"m\"\nembed_model = \"e\"\n[ports]\nagent_pipe = 1\n",
        );
        let e = read_config(d.path()).expect_err("must refuse");
        assert!(e.contains("[ports].nope"), "{e}");
    }

    #[test]
    fn a_non_port_placeholder_is_refused() {
        let d = root_with(
            "[ai]\nendpoint = \"http://${HOST}/v1\"\nagent_model = \"m\"\n\
             embed_model = \"e\"\n[ports]\n",
        );
        let e = read_config(d.path()).expect_err("must refuse");
        assert!(e.contains("not a [ports] reference"), "{e}");
    }

    #[test]
    fn an_empty_model_is_refused() {
        let d = root_with(
            "[ai]\nendpoint = \"http://h/v1\"\nagent_model = \"\"\nembed_model = \"e\"\n[ports]\n",
        );
        let e = read_config(d.path()).expect_err("must refuse");
        assert!(e.contains("agent_model is empty"), "{e}");
    }

    /// Absent is not clean: a missing table is cannot-run, never a pass.
    #[test]
    fn a_missing_ai_table_cannot_run() {
        let d = root_with("[ports]\nagent_pipe = 1\n");
        let e = read_config(d.path()).expect_err("must refuse");
        assert!(e.contains("no [ai]"), "{e}");
    }

    #[test]
    fn an_absent_ssot_cannot_run() {
        let d = tempfile::tempdir().expect("tempdir");
        let e = read_config(d.path()).expect_err("must refuse");
        assert!(e.contains("could not be read"), "{e}");
    }
}
