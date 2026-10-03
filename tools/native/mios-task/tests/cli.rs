// AI-hint: Integration tests for mios-task -- every check of ADR-0028 with its planted negative (dropped record, edited frozen slice, duplicate id, second store, hand-edited TASKS.md, bad override), on a sandbox migrated from fixtures with the real schema.
// AI-related: tools/native/mios-task/src/cli.rs, tools/native/mios-task/tests/fixtures/, /usr/lib/mios/schemas/task-record.schema.json
// AI-functions: bare, sandbox, run, migrate_args, plant_line, py, set_overrides

use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

const BIN: &str = env!("CARGO_BIN_EXE_mios-task");

fn manifest() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn fixture(name: &str) -> PathBuf {
    manifest().join("tests/fixtures").join(name)
}

/// The one schema: the repo's own, never a copy.
fn schema_src() -> PathBuf {
    manifest().join("../../../usr/lib/mios/schemas/task-record.schema.json")
}

struct Out {
    code: i32,
    text: String,
}

fn run(root: &Path, args: &[&str]) -> Out {
    let o = Command::new(BIN)
        .args(args)
        .arg("--root")
        .arg(root)
        .output()
        .expect("run mios-task");
    Out {
        code: o.status.code().unwrap_or(-1),
        text: format!(
            "{}{}",
            String::from_utf8_lossy(&o.stdout),
            String::from_utf8_lossy(&o.stderr)
        ),
    }
}

const TOML: &str = "[tasks.store]\npath   = \"tasks.jsonl\"\nschema = \"usr/lib/mios/schemas/task-record.schema.json\"\ndoc    = \"TASKS.md\"\nretired = [\"TASKS.jsonl\", \".devloop/tasks.jsonl\", \"AGY-TASKS.md\"]\n";

/// A repo root with the SSOT table and schema, and nothing else.
fn bare(name: &str) -> PathBuf {
    let d = PathBuf::from(env!("CARGO_TARGET_TMPDIR")).join(format!("mios-task-{name}"));
    let _ = fs::remove_dir_all(&d);
    fs::create_dir_all(d.join("usr/share/mios")).unwrap();
    fs::create_dir_all(d.join("usr/lib/mios/schemas")).unwrap();
    fs::write(d.join("usr/share/mios/mios.toml"), TOML).unwrap();
    fs::copy(
        schema_src(),
        d.join("usr/lib/mios/schemas/task-record.schema.json"),
    )
    .unwrap();
    d
}

fn migrate_args<'a>(
    store: &'a str,
    lane: &'a str,
    cls: &'a str,
    out: &'a str,
    rep: &'a str,
) -> Vec<&'a str> {
    vec![
        "migrate-canonical",
        "--store",
        store,
        "--lane",
        lane,
        "--classification",
        cls,
        "--out",
        out,
        "--report",
        rep,
        "--lane-origin",
        "MiOS:.devloop/tasks.jsonl",
    ]
}

/// The [tasks.store] keys a migration report implies: the migrated count, identity digest and frozen digests.
fn frozen_toml(rep: &Value) -> String {
    let mut s = format!("migrated = {}\n", rep["out_lines"]);
    if let Some(d) = rep["migrated_sha256"].as_str() {
        s.push_str(&format!("migrated_sha256 = \"{d}\"\n"));
    }
    s.push_str("frozen = [\n");
    for f in rep["frozen"].as_array().unwrap() {
        s.push_str(&format!(
            "  {{ source = {}, bytes = {}, sha256 = {} }},\n",
            f["source"], f["bytes"], f["sha256"]
        ));
    }
    s + "]\n"
}

/// A sandbox holding the fixture migration as tasks.jsonl plus its render: a green tree.
fn sandbox(name: &str) -> PathBuf {
    sandbox_from(name, &fixture("lane.jsonl"))
}

/// The fixture migration with `lane` as the lane file.
fn sandbox_from(name: &str, lane: &Path) -> PathBuf {
    let d = bare(name);
    let (s, l, c) = (
        fixture("store.v1.jsonl"),
        lane.to_path_buf(),
        fixture("classification.json"),
    );
    let (out, rep) = (d.join("tasks.jsonl"), d.join("report.json"));
    let o = run(
        &d,
        &migrate_args(
            s.to_str().unwrap(),
            l.to_str().unwrap(),
            c.to_str().unwrap(),
            out.to_str().unwrap(),
            rep.to_str().unwrap(),
        ),
    );
    assert_eq!(o.code, 0, "{}", o.text);
    let r: Value = serde_json::from_str(&fs::read_to_string(&rep).unwrap()).unwrap();
    fs::remove_file(&rep).unwrap();
    fs::write(
        d.join("usr/share/mios/mios.toml"),
        format!("{TOML}{}", frozen_toml(&r)),
    )
    .unwrap();
    assert_eq!(run(&d, &["fmt"]).code, 0);
    let r = run(&d, &["render"]);
    assert_eq!(r.code, 0, "{}", r.text);
    let c = run(&d, &["check"]);
    assert_eq!(c.code, 0, "the fixture tree must start green: {}", c.text);
    d
}

fn records(d: &Path) -> Vec<Value> {
    fs::read_to_string(d.join("tasks.jsonl"))
        .unwrap()
        .lines()
        .map(|l| serde_json::from_str(l).unwrap())
        .collect()
}

fn get(d: &Path, id: &str) -> Value {
    records(d)
        .into_iter()
        .find(|r| r["id"] == id)
        .unwrap_or_else(|| panic!("no {id}"))
}

/// Rewrite the line of `id` through `f` the way the dev-loop toolkit writes it (Python separators).
fn plant_line(d: &Path, id: &str, f: impl Fn(&mut Value)) {
    let p = d.join("tasks.jsonl");
    let t = fs::read_to_string(&p).unwrap();
    let out: Vec<String> = t
        .lines()
        .map(|l| {
            let mut v: Value = serde_json::from_str(l).unwrap();
            if v["id"] == id {
                f(&mut v);
                py(&v)
            } else {
                l.to_string()
            }
        })
        .collect();
    fs::write(&p, out.join("\n") + "\n").unwrap();
}

/// Python json.dumps(v, ensure_ascii=False) for the values these tests write.
fn py(v: &Value) -> String {
    let mut s = String::new();
    let mut in_str = false;
    let mut esc = false;
    for c in serde_json::to_string(v).unwrap().chars() {
        s.push(c);
        if in_str {
            if esc {
                esc = false;
            } else if c == '\\' {
                esc = true;
            } else if c == '"' {
                in_str = false;
            }
            continue;
        }
        match c {
            '"' => in_str = true,
            ',' | ':' => s.push(' '),
            _ => {}
        }
    }
    s
}

fn bytes(p: &Path) -> Vec<u8> {
    fs::read(p).unwrap()
}

/// Replace everything between the override markers with `lines`.
fn set_overrides(d: &Path, lines: &[&str]) {
    let p = d.join("TASKS.md");
    let t = fs::read_to_string(&p).unwrap();
    let b = t.find("<!-- overrides:begin -->\n").unwrap() + "<!-- overrides:begin -->\n".len();
    let e = t.find("<!-- overrides:end -->").unwrap();
    let mut body = String::new();
    for l in lines {
        body.push_str(l);
        body.push('\n');
    }
    fs::write(&p, format!("{}{}{}", &t[..b], body, &t[e..])).unwrap();
}

#[test]
fn migration_counts_both_ways_and_keeps_ids_statuses_text_and_lane_claims() {
    let d = bare("migrate");
    let (s, l, c) = (
        fixture("store.v1.jsonl"),
        fixture("lane.jsonl"),
        fixture("classification.json"),
    );
    let (out, rep) = (d.join("tasks.jsonl"), d.join("report.json"));
    let mut args = migrate_args(
        s.to_str().unwrap(),
        l.to_str().unwrap(),
        c.to_str().unwrap(),
        out.to_str().unwrap(),
        rep.to_str().unwrap(),
    );
    args.push("--dry-run");
    let o = run(&d, &args);
    assert_eq!(o.code, 0, "{}", o.text);
    assert!(!out.exists(), "a dry run writes only the report");
    let r: Value = serde_json::from_str(&fs::read_to_string(&rep).unwrap()).unwrap();
    assert_eq!(
        (
            r["store_in"].as_u64(),
            r["kept"].as_u64(),
            r["excluded_toolkit"].as_u64(),
            r["excluded_devloop_origin"].as_u64()
        ),
        (Some(12), Some(10), Some(1), Some(1))
    );
    assert_eq!(
        (
            r["lane_in"].as_u64(),
            r["merged_into_store"].as_u64(),
            r["lane_only"].as_u64(),
            r["out_lines"].as_u64()
        ),
        (Some(3), Some(2), Some(1), Some(11))
    );
    assert!(r["balance"]
        .as_object()
        .unwrap()
        .values()
        .all(|b| b == true));
    assert_eq!(
        r["store_key_map"].as_object().unwrap().len(),
        12,
        "every store key maps exactly once"
    );
    assert_eq!(
        r["changed_status"],
        json!([]),
        "a store record keeps its status word"
    );

    let d = sandbox("migrated");
    let store: Vec<Value> = fs::read_to_string(fixture("store.v1.jsonl"))
        .unwrap()
        .lines()
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();
    // Both ways: every kept store key is one record with its id (or '#n' form) and status, and back.
    let recs = records(&d);
    for s in &store {
        let key = s["key"].as_str().unwrap();
        let hit: Vec<&Value> = recs
            .iter()
            .filter(|r| r["provenance"]["key"] == key)
            .collect();
        if key.starts_with("-dev-loop:") {
            assert!(hit.is_empty(), "{key} is toolkit work and stays out");
            continue;
        }
        assert_eq!(hit.len(), 1, "{key}");
        assert!(
            hit[0]["id"] == s["id"] || hit[0]["provenance"]["aliases"][0] == s["id"],
            "{key}"
        );
        if s["origin"] != "MiOS:.devloop/tasks.jsonl" {
            assert_eq!(hit[0]["status"], s["status"], "{key}");
        }
    }
    assert_eq!(
        recs.iter()
            .filter(|r| r["provenance"]["classification"] != "lane")
            .count(),
        10
    );
    let t50 = get(&d, "T-050");
    assert_eq!(
        (t50["owner"].as_str(), t50["status"].as_str()),
        (Some("lane-b"), Some("in_progress")),
        "a lane claim survives"
    );
    assert_eq!(t50["provenance"]["owner_raw"], Value::Null);
    let t60 = get(&d, "T-060#2");
    assert_eq!(
        (t60["owner"].as_str(), t60["status"].as_str()),
        (Some("lane-b"), Some("completed"))
    );
    assert_eq!(t60["provenance"]["aliases"], json!(["T-060"]));
    assert_eq!(get(&d, "T-070")["depends_on"], json!(["T-060#2"]));
    assert_eq!(get(&d, "T-070")["provenance"]["classification"], "lane");
    assert_eq!(get(&d, "T-031#2")["status"], "cancelled");
    let code = get(&d, "CODE-01");
    assert_eq!(
        (
            code["type"].as_str(),
            code["provenance"]["type_raw"].as_str()
        ),
        (Some("task"), Some("roadmap_item"))
    );
    assert!(get(&d, "AGY-503..AGY-510")["verification_evidence"]
        .as_str()
        .unwrap()
        .starts_with("migrated from MiOS:AGY-TASKS.md"));
    let agy9 = get(&d, "AGY-9");
    assert_eq!(agy9["provenance"]["classification"], "mios-classified");
    assert_eq!(
        agy9["provenance"]["sources"][0]["file"], "-dev-loop:.devloop/tasks.jsonl",
        "a MiOS record only the toolkit held keeps its toolkit bytes"
    );
    assert!(get(&d, "T-050")["provenance"]["sources"]
        .as_array()
        .unwrap()
        .iter()
        .all(|s| s["file"] == "MiOS:.devloop/tasks.jsonl"));
    // Text: every MiOS list rebuilds byte for byte, the lane file included.
    let o = run(&d, &["source", "MiOS:.devloop/tasks.jsonl"]);
    assert_eq!(o.code, 0, "{}", o.text);
    assert_eq!(o.text, fs::read_to_string(fixture("lane.jsonl")).unwrap());
    let o = run(&d, &["source", "MiOS:TASKS.md"]);
    assert!(
        o.code == 0 && o.text.starts_with("## T-001 -- First"),
        "{}",
        o.text
    );
}

#[test]
fn migration_refuses_unknown_keys_collisions_unknown_words_and_a_stale_store() {
    let d = bare("migrate-neg");
    let (out, rep) = (d.join("o.jsonl"), d.join("r.json"));
    let (o, r) = (out.to_str().unwrap(), rep.to_str().unwrap());
    // Each plant is derived from a good fixture, so the fixtures stay three files.
    let plant = |name: &str, from: &str, f: &dyn Fn(String) -> String| -> PathBuf {
        let p = d.join(name);
        fs::write(&p, f(fs::read_to_string(fixture(from)).unwrap())).unwrap();
        p
    };
    let unknown_key = plant("cls.unknown.json", "classification.json", &|_| {
        "[{\"key\": \"T-999\", \"class\": \"mios\", \"why\": \"planted: not in the store\"}]".into()
    });
    let collision = plant("lane.collision.jsonl", "lane.jsonl", &|t| {
        let mut v: Value = serde_json::from_str(t.lines().nth(2).unwrap()).unwrap();
        v["id"] = "T-002".into();
        v["title"] = "planted: a different task under a store id".into();
        format!("{t}{}\n", py(&v))
    });
    let bad_status = plant("store.bad.jsonl", "store.v1.jsonl", &|t| {
        // The first pending record is T-002.
        t.replacen("\"status\":\"pending\"", "\"status\":\"frobnicated\"", 1)
    });
    let stale = plant("lane.stale.jsonl", "lane.jsonl", &|t| {
        t.replace("\"owner\": \"lane-b\"", "\"owner\": \"lane-c\"")
    });
    let (cls, lane, store) = (
        fixture("classification.json"),
        fixture("lane.jsonl"),
        fixture("store.v1.jsonl"),
    );
    let cases = [
        (&store, &lane, &unknown_key, "T-999"),
        (&store, &collision, &cls, "lane-only id T-002 collides"),
        (&bad_status, &lane, &cls, "T-002: unknown status"),
        (
            &store,
            &stale,
            &cls,
            "the store is stale against the lane file",
        ),
    ];
    for (s, l, c, want) in cases {
        let x = run(
            &d,
            &migrate_args(
                s.to_str().unwrap(),
                l.to_str().unwrap(),
                c.to_str().unwrap(),
                o,
                r,
            ),
        );
        assert_eq!(x.code, 1, "{want}: {}", x.text);
        assert!(x.text.contains(want), "{want}: {}", x.text);
        assert!(
            !out.exists() && !rep.exists(),
            "a refused migration writes nothing"
        );
    }
}

#[test]
fn a_dropped_record_fails_and_is_named() {
    let d = sandbox("drop");
    let p = d.join("tasks.jsonl");
    let t = fs::read_to_string(&p).unwrap();
    let kept: Vec<&str> = t
        .lines()
        .filter(|l| !l.starts_with("{\"id\": \"T-031\","))
        .collect();
    assert_eq!(kept.len() + 1, t.lines().count());
    fs::write(&p, kept.join("\n") + "\n").unwrap();
    run(&d, &["render"]);
    let o = run(&d, &["check"]);
    assert_eq!(o.code, 1, "{}", o.text);
    assert!(
        o.text
            .contains("MiOS:TASKS.md: bytes 87..112 are missing -- record T-031 was dropped"),
        "{}",
        o.text
    );
    assert!(
        o.text
            .contains("holds 10 migrated record(s) but [tasks.store].migrated is 11 -- a migrated record was dropped"),
        "{}",
        o.text
    );
}

#[test]
fn an_edited_frozen_slice_fails_and_is_named() {
    let d = sandbox("edit-frozen");
    plant_line(&d, "CODE-01", |v| {
        v["provenance"]["sources"][0]["text"] = "### CODE-01 rewritten history\n".into()
    });
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1
            && o.text
                .contains("MiOS:ROADMAP.md: the slice CODE-01 owns at offset 0 was edited"),
        "{}",
        o.text
    );
    assert_eq!(
        run(&d, &["source", "MiOS:ROADMAP.md"]).code,
        1,
        "source refuses to rebuild edited history"
    );
    // A slice outside the frozen lists keeps its digest too.
    let d = sandbox("edit-toolkit-slice");
    plant_line(&d, "AGY-9", |v| {
        v["provenance"]["sources"][0]["text"] = "{}\n".into()
    });
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1
            && o.text.contains(
                "-dev-loop:.devloop/tasks.jsonl: the slice AGY-9 owns at offset 3 was edited"
            ),
        "{}",
        o.text
    );
}

#[test]
fn schema_is_strict() {
    let d = sandbox("strict");
    plant_line(&d, "T-001", |v| {
        v["bogus"] = 1.into();
    });
    let o = run(&d, &["check"]);
    assert_eq!(o.code, 1);
    assert!(
        o.text.contains("T-001: additional property bogus"),
        "{}",
        o.text
    );
}

#[test]
fn ids_are_unique() {
    let d = sandbox("dup");
    let p = d.join("tasks.jsonl");
    let t = fs::read_to_string(&p).unwrap();
    let mut v: Value = serde_json::from_str(t.lines().nth(1).unwrap()).unwrap();
    v["provenance"] = Value::Null;
    v["acceptance_criteria"] = json!(["x"]);
    v["verification"]["positive_cmd"] = "true".into();
    v["verification"]["negative_control_cmd"] = "false".into();
    fs::write(&p, format!("{t}{}\n", py(&v))).unwrap();
    let o = run(&d, &["check"]);
    assert_eq!(o.code, 1);
    assert!(o.text.contains("duplicate id T-002"), "{}", o.text);
}

#[test]
fn depends_on_resolves_and_is_acyclic() {
    let d = sandbox("deps");
    plant_line(&d, "T-002", |v| v["depends_on"] = json!(["T-999999"]));
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1 && o.text.contains("T-002: depends_on unknown T-999999"),
        "{}",
        o.text
    );
    let d = sandbox("cycle");
    plant_line(&d, "T-002", |v| v["depends_on"] = json!(["T-031"]));
    plant_line(&d, "T-031", |v| v["depends_on"] = json!(["T-002"]));
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1 && o.text.contains("depends_on cycle among [T-002, T-031]"),
        "{}",
        o.text
    );
}

#[test]
fn completed_requires_evidence() {
    let d = sandbox("evidence");
    plant_line(&d, "T-001", |v| v["verification_evidence"] = "".into());
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1
            && o.text
                .contains("T-001: completed without verification_evidence"),
        "{}",
        o.text
    );
}

#[test]
fn a_born_record_must_be_falsifiable() {
    let d = sandbox("born");
    let o = run(
        &d,
        &[
            "add",
            "--id",
            "T-900",
            "--title",
            "born here",
            "--ac",
            "WHEN x THE SYSTEM SHALL y",
            "--positive",
            "true",
            "--negative",
            "false",
        ],
    );
    assert_eq!(o.code, 0, "{}", o.text);
    assert_eq!(run(&d, &["check"]).code, 0);
    plant_line(&d, "T-900", |v| {
        v["verification"]["negative_control_cmd"] = Value::Null
    });
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1
            && o.text
                .contains("T-900: record born in tasks.jsonl lacks a negative control"),
        "{}",
        o.text
    );
    let o = run(
        &d,
        &[
            "add",
            "--id",
            "T-901",
            "--title",
            "no controls",
            "--ac",
            "x",
        ],
    );
    assert_eq!(
        o.code, 64,
        "add refuses a record without both controls: {}",
        o.text
    );
}

#[test]
fn a_toolkit_shaped_record_is_made_canonical_by_fmt() {
    // The dev-loop toolkit's `tasks add` writes fewer keys; fmt fills the rest and check then passes.
    let d = sandbox("toolkit-add");
    let p = d.join("tasks.jsonl");
    let t = fs::read_to_string(&p).unwrap();
    let rec = json!({"id": "T-950", "type": "task", "title": "added by the toolkit", "status": "pending",
        "owner": "", "epic": "", "goal": "", "depends_on": [], "acceptance_criteria": ["WHEN a THE SYSTEM SHALL b"],
        "verification": {"positive_cmd": "true", "negative_control_cmd": "false", "negative_expect": "exit 1"},
        "verification_evidence": "", "links": [], "notes": "", "created": "2026-10-03"});
    fs::write(&p, format!("{t}{}\n", py(&rec))).unwrap();
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1 && o.text.contains("T-950: missing required provenance"),
        "{}",
        o.text
    );
    assert_eq!(run(&d, &["fmt"]).code, 0);
    assert_eq!(run(&d, &["render"]).code, 0);
    let o = run(&d, &["check"]);
    assert_eq!(o.code, 0, "{}", o.text);
}

#[test]
fn status_words_and_serialization_are_canonical() {
    let d = sandbox("canon");
    plant_line(&d, "T-002", |v| v["status"] = "done".into());
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1
            && o.text
                .contains("legacy status word \"done\" on disk -- run mios-task fmt"),
        "{}",
        o.text
    );
    assert_eq!(run(&d, &["fmt", "--check"]).code, 1);
    let d = sandbox("compact");
    let p = d.join("tasks.jsonl");
    let t = fs::read_to_string(&p).unwrap();
    let mut lines: Vec<String> = t.lines().map(str::to_string).collect();
    let v: Value = serde_json::from_str(&lines[1]).unwrap();
    lines[1] = serde_json::to_string(&v).unwrap();
    fs::write(&p, lines.join("\n") + "\n").unwrap();
    let o = run(&d, &["fmt", "--check"]);
    assert!(
        o.code == 1
            && o.text
                .contains("tasks.jsonl:2 (T-002): not canonical -- run mios-task fmt"),
        "{}",
        o.text
    );
    assert_eq!(run(&d, &["fmt"]).code, 0);
    assert_eq!(
        run(&d, &["check"]).code,
        0,
        "fmt restores the canonical bytes"
    );
}

#[test]
fn a_dialect_marker_is_not_a_task() {
    let d = sandbox("marker");
    let p = d.join("tasks.jsonl");
    let t = fs::read_to_string(&p).unwrap();
    fs::write(&p, format!("{{\"_dialect\": \"openai\"}}\n{t}")).unwrap();
    let o = run(&d, &["check"]);
    assert_eq!(o.code, 0, "{}", o.text);
    assert_eq!(run(&d, &["claim", "T-002", "lane-x"]).code, 0);
    assert!(fs::read_to_string(&p)
        .unwrap()
        .starts_with("{\"_dialect\": \"openai\"}\n"));
    assert_eq!(get_after_marker(&d, "T-002")["owner"], "lane-x");
    fs::write(&p, format!("{{\"_dialect\": \"legacy\"}}\n{t}")).unwrap();
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1 && o.text.contains("dialect marker"),
        "{}",
        o.text
    );
}

fn get_after_marker(d: &Path, id: &str) -> Value {
    fs::read_to_string(d.join("tasks.jsonl"))
        .unwrap()
        .lines()
        .map(|l| serde_json::from_str::<Value>(l).unwrap())
        .find(|r| r["id"] == id)
        .unwrap()
}

#[test]
fn tasks_md_is_a_regenerated_projection() {
    let d = sandbox("render-diff");
    let p = d.join("TASKS.md");
    let t = fs::read_to_string(&p).unwrap();
    assert!(
        t.starts_with("# TASKS\n"),
        "the toolkit's banner comes first"
    );
    fs::write(&p, t.replace("`T-001` First", "`T-001` First, hand-edited")).unwrap();
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1
            && o.text.contains("differs from the render of tasks.jsonl")
            && o.text.contains("`T-001` First, hand-edited"),
        "{}",
        o.text
    );
    assert_eq!(run(&d, &["render"]).code, 0);
    assert_eq!(run(&d, &["check"]).code, 0);
    assert_eq!(bytes(&p), t.into_bytes(), "render is byte-deterministic");
    // A TASKS.md that lost the banner is foreign to the toolkit: its overrides would be ignored there.
    let t = fs::read_to_string(&p).unwrap();
    fs::write(&p, t.replacen("# TASKS\n", "# Tasks\n", 1)).unwrap();
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1 && o.text.contains("does not open with the '# TASKS' banner"),
        "{}",
        o.text
    );
}

#[test]
fn overrides_validate_and_apply() {
    let d = sandbox("overrides");
    set_overrides(
        &d,
        &[
            "<!-- operator: ship T-002 first -->",
            "{\"id\": \"T-002\", \"priority\": \"P0\"}",
            "- {\"id\": \"T-031\", \"status\": \"blocked\", \"owner\": \"operator\"}",
        ],
    );
    assert_eq!(run(&d, &["render"]).code, 0);
    let o = run(&d, &["check"]);
    assert_eq!(o.code, 0, "{}", o.text);
    let md = fs::read_to_string(d.join("TASKS.md")).unwrap();
    assert!(
        md.contains("<!-- operator: ship T-002 first -->"),
        "kept verbatim"
    );
    assert!(md.contains("P0 [override]"), "{md}");
    assert!(
        md.contains("incomplete [override] · owner operator [override]"),
        "a legacy word applies as the canonical one: {md}"
    );
    assert_eq!(
        get(&d, "T-002")["priority"],
        "P2",
        "overrides never touch tasks.jsonl"
    );
    let o = run(&d, &["ready", "--json"]);
    assert!(
        !o.text.contains("\"T-031\""),
        "ready reads the overridden status: {}",
        o.text
    );
    // T-031 is also the former id of T-031#2, so an edit by it names the task exactly.
    let o = run(&d, &["claim", "T-031", "lane-b", "--exact"]);
    assert_eq!(
        o.code, 2,
        "claim compares against the overridden owner: {}",
        o.text
    );

    let bad = [
        (
            "{\"id\": \"T-404\", \"priority\": \"P0\"}",
            "override for unknown task \"T-404\"",
        ),
        (
            "{\"id\": \"T-002\", \"bogus\": 1}",
            "T-002: bogus is not a task record field",
        ),
        (
            "{\"id\": \"T-002\", \"provenance\": null}",
            "T-002.provenance cannot be overridden",
        ),
        (
            "{\"id\": \"T-002\", \"status\": \"finished\"}",
            "is not in the enum",
        ),
        (
            "{\"id\": \"T-002\", \"depends_on\": [\"T-404\"]}",
            "T-002: depends_on unknown T-404",
        ),
        ("{\"id\": \"T-002\"}", "override of T-002 sets no field"),
        ("{\"priority\": \"P0\"}", "override needs an \"id\""),
        ("{not json", "override line is not a JSON object"),
    ];
    for (line, want) in bad {
        let d = sandbox("overrides-bad");
        set_overrides(&d, &[line]);
        let o = run(&d, &["check"]);
        assert!(
            o.code == 1 && o.text.contains(want) && o.text.contains("TASKS.md:"),
            "{want}: {}",
            o.text
        );
    }
    // A valid override with no re-render fails the render diff.
    let d = sandbox("overrides-stale");
    set_overrides(&d, &["{\"id\": \"T-002\", \"priority\": \"P0\"}"]);
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1 && o.text.contains("differs from the render"),
        "{}",
        o.text
    );
    // A missing end marker.
    let d = sandbox("overrides-marker");
    let p = d.join("TASKS.md");
    let t = fs::read_to_string(&p)
        .unwrap()
        .replace("<!-- overrides:end -->\n", "");
    fs::write(&p, t).unwrap();
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1 && o.text.contains("end marker appears 0 time(s)"),
        "{}",
        o.text
    );
    assert_eq!(
        run(&d, &["render"]).code,
        1,
        "render refuses to clobber a broken block"
    );
}

#[test]
fn ready_and_next() {
    let d = sandbox("ready");
    let o = run(&d, &["ready", "--json"]);
    assert!(o.text.contains("\"T-002\""), "{}", o.text);
    assert!(
        o.text.contains("\"T-070\"")
            && !o.text.contains("\"T-050\"")
            && !o.text.contains("\"T-031#2\""),
        "pending with every dependency completed; nothing in progress or cancelled: {}",
        o.text
    );
    plant_line(&d, "T-060#2", |v| v["status"] = "pending".into());
    let o = run(&d, &["ready", "--json"]);
    assert!(
        !o.text.contains("\"T-070\""),
        "T-070 waits on T-060#2: {}",
        o.text
    );
    let o = run(&d, &["next", "--limit", "1"]);
    assert!(
        o.text.contains("(+") && o.text.contains("more)"),
        "{}",
        o.text
    );
}

#[test]
fn claim_is_compare_and_set() {
    let d = sandbox("claim");
    let o = run(&d, &["claim", "T-002", "lane-b"]);
    assert_eq!(o.code, 0, "{}", o.text);
    assert_eq!(get(&d, "T-002")["owner"], "lane-b");
    assert_eq!(run(&d, &["check"]).code, 0, "claim re-renders TASKS.md");
    let before = bytes(&d.join("tasks.jsonl"));
    let o = run(&d, &["claim", "T-050", "claude-code"]);
    assert!(
        o.code == 2 && o.text.contains("owned by lane-b"),
        "{}",
        o.text
    );
    assert_eq!(
        bytes(&d.join("tasks.jsonl")),
        before,
        "a lost claim leaves the file untouched"
    );
    assert_eq!(run(&d, &["release", "T-050", "claude-code"]).code, 2);
    assert_eq!(run(&d, &["release", "T-002", "lane-b"]).code, 0);
    assert_eq!(get(&d, "T-002")["owner"], "");
    let o = run(&d, &["set", "T-002", "--status", "done"]);
    assert_eq!(
        o.code, 1,
        "completed without evidence is refused: {}",
        o.text
    );
    let o = run(
        &d,
        &[
            "set",
            "T-002",
            "--status",
            "done",
            "--evidence",
            "positive ok; negative fails",
        ],
    );
    assert_eq!(o.code, 0, "{}", o.text);
    assert_eq!(
        get(&d, "T-002")["status"],
        "completed",
        "a legacy word is stored canonically"
    );
    assert_eq!(run(&d, &["check"]).code, 0);
}

#[test]
fn a_second_or_retired_store_fails() {
    let d = sandbox("retired");
    fs::create_dir_all(d.join(".devloop")).unwrap();
    fs::write(d.join(".devloop/tasks.jsonl"), "").unwrap();
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1
            && o.text
                .contains("retired task store present: .devloop/tasks.jsonl"),
        "{}",
        o.text
    );
    fs::remove_file(d.join(".devloop/tasks.jsonl")).unwrap();
    fs::write(d.join("AGY-TASKS.md"), "## AGY-1 edited again\n").unwrap();
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1 && o.text.contains("retired task store present: AGY-TASKS.md"),
        "{}",
        o.text
    );
    fs::remove_file(d.join("AGY-TASKS.md")).unwrap();
    fs::create_dir_all(d.join("docs")).unwrap();
    fs::write(d.join("docs/Tasks.JSONL"), "").unwrap();
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1
            && o.text
                .contains("second task store present: docs/Tasks.JSONL"),
        "{}",
        o.text
    );
    fs::remove_file(d.join("docs/Tasks.JSONL")).unwrap();
    // The old store's name: on a case-folding filesystem it is the canonical file itself, never a plant.
    fs::write(d.join("TASKS.jsonl"), "").unwrap();
    let o = run(&d, &["check"]);
    let case_sensitive = fs::read_dir(&d)
        .unwrap()
        .flatten()
        .filter(|e| {
            e.file_name()
                .to_string_lossy()
                .eq_ignore_ascii_case("tasks.jsonl")
        })
        .count()
        == 2;
    if case_sensitive {
        assert!(
            o.code == 1 && o.text.contains("retired task store present: TASKS.jsonl"),
            "{}",
            o.text
        );
    }
}

#[test]
fn the_check_reads_no_sibling_checkout() {
    // A root with nothing beside it (no -dev-loop, no mios-micro) validates, renders and answers queries.
    let d = sandbox("alone");
    assert!(!d.join("../-dev-loop").exists() && !d.join("../mios-micro").exists());
    assert_eq!(run(&d, &["check"]).code, 0);
    assert_eq!(run(&d, &["render"]).code, 0);
    assert_eq!(run(&d, &["next", "--json"]).code, 0);
    assert_eq!(
        run(&d, &["source", "mios-micro:ROADMAP.md"]).code,
        1,
        "never a frozen list here"
    );
}

#[test]
fn coordination_hygiene() {
    let d = sandbox("hygiene");
    assert_eq!(run(&d, &["check", "--only", "hygiene"]).code, 0);
    plant_line(&d, "T-002", |v| {
        v["notes"] = "C:\\Users\\x\\AppData\\Local\\Temp\\run".into()
    });
    let o = run(&d, &["check", "--only", "hygiene"]);
    assert!(
        o.code == 1
            && o.text
                .contains("T-002: notes contains an AppData/Temp path"),
        "{}",
        o.text
    );
    let d = sandbox("hygiene-override");
    set_overrides(
        &d,
        &["{\"id\": \"T-002\", \"notes\": \"see 123e4567-e89b-12d3-a456-426614174000\"}"],
    );
    let o = run(&d, &["check", "--only", "hygiene"]);
    assert!(
        o.code == 1
            && o.text
                .contains("override line contains an AppData/Temp path or session id"),
        "{}",
        o.text
    );
}

#[test]
fn the_ssot_table_carries_only_known_keys() {
    let d = sandbox("ssot");
    let p = d.join("usr/share/mios/mios.toml");
    let t = fs::read_to_string(&p).unwrap();
    fs::write(
        &p,
        format!("{t}sources = [ {{ repo = \"elsewhere\", path = \"x\" }} ]\n"),
    )
    .unwrap();
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1 && o.text.contains("[tasks.store] carries 'sources'"),
        "{}",
        o.text
    );
}

#[test]
fn fold_bakes_an_override_and_drops_its_line() {
    let d = sandbox("fold");
    set_overrides(
        &d,
        &[
            "{\"id\": \"T-002\", \"priority\": \"P0\"}",
            "{\"id\": \"T-001\", \"size\": \"L\"}",
        ],
    );
    assert_eq!(run(&d, &["render"]).code, 0);
    let o = run(&d, &["overrides", "fold", "T-002"]);
    assert_eq!(o.code, 0, "{}", o.text);
    assert_eq!(get(&d, "T-002")["priority"], "P0");
    let md = fs::read_to_string(d.join("TASKS.md")).unwrap();
    assert!(
        !md.contains("{\"id\": \"T-002\"") && md.contains("{\"id\": \"T-001\""),
        "only T-002's line goes"
    );
    assert_eq!(run(&d, &["check"]).code, 0);
}

#[test]
fn an_archived_dependency_stays_out_of_depends_on() {
    // The toolkit moves an edge to archived_dependencies when it archives the target; it is history, not a block.
    let lane = PathBuf::from(env!("CARGO_TARGET_TMPDIR")).join("lane.archived.jsonl");
    let t = fs::read_to_string(fixture("lane.jsonl")).unwrap();
    let planted: Vec<String> = t
        .lines()
        .map(|l| {
            let mut v: Value = serde_json::from_str(l).unwrap();
            if v["id"] == "T-070" {
                v["archived_dependencies"] = json!(["T-050"]);
                py(&v)
            } else {
                l.to_string()
            }
        })
        .collect();
    fs::write(&lane, planted.join("\n") + "\n").unwrap();
    let d = sandbox_from("archived-deps", &lane);
    let t70 = get(&d, "T-070");
    assert_eq!(t70["depends_on"], json!(["T-060#2"]), "{t70}");
    assert!(
        t70["related"]
            .as_array()
            .unwrap()
            .contains(&json!({"id": "T-050", "type": "archived"})),
        "{t70}"
    );
    // Put the archived edge back into depends_on: check names it from the frozen lane line.
    plant_line(&d, "T-070", |v| {
        v["depends_on"] = json!(["T-060#2", "T-050"]);
    });
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1
            && o.text.contains(
                "T-070: depends_on T-050 is an edge the lane file archived (archived_dependencies)"
            ),
        "{}",
        o.text
    );
}

#[test]
fn the_migrated_identity_is_frozen() {
    // a. A count-keeping swap: AGY-9 (no frozen slice) replaced by a slice-less record.
    let d = sandbox("swap");
    let p = d.join("tasks.jsonl");
    let t = fs::read_to_string(&p).unwrap();
    let mut lines: Vec<String> = t
        .lines()
        .filter(|l| !l.starts_with("{\"id\": \"AGY-9\","))
        .map(str::to_string)
        .collect();
    let mut forged: Value = serde_json::from_str(
        t.lines()
            .find(|l| l.starts_with("{\"id\": \"AGY-9\","))
            .unwrap(),
    )
    .unwrap();
    forged["id"] = "T-777".into();
    forged["provenance"]["key"] = "T-777".into();
    forged["provenance"]["sources"] = json!([]);
    lines.push(py(&forged));
    fs::write(&p, lines.join("\n") + "\n").unwrap();
    run(&d, &["render"]);
    let o = run(&d, &["check"]);
    assert_eq!(o.code, 1, "{}", o.text);
    assert!(
        o.text
            .contains("T-777: a migrated record with no provenance.sources"),
        "{}",
        o.text
    );
    assert!(
        o.text.contains("[tasks.store].migrated_sha256"),
        "{}",
        o.text
    );
    // b. The only record of a lane rename loses it.
    let d = sandbox("aliases");
    plant_line(&d, "T-060#2", |v| v["provenance"]["aliases"] = json!([]));
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1
            && o.text
                .contains("T-060#2: a renamed id whose provenance.aliases does not name T-060")
            && o.text.contains("[tasks.store].migrated_sha256"),
        "{}",
        o.text
    );
    // c. A rewritten provenance key.
    let d = sandbox("key");
    plant_line(&d, "T-002", |v| {
        v["provenance"]["key"] = "T-002-forged".into()
    });
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1 && o.text.contains("[tasks.store].migrated_sha256"),
        "{}",
        o.text
    );
    // d. A kept record's toolkit slices stripped.
    let d = sandbox("strip");
    plant_line(&d, "AGY-9", |v| v["provenance"]["sources"] = json!([]));
    let o = run(&d, &["check"]);
    assert!(
        o.code == 1
            && o.text
                .contains("AGY-9: a migrated record with no provenance.sources")
            && o.text.contains("[tasks.store].migrated_sha256"),
        "{}",
        o.text
    );
}

#[test]
fn a_former_id_is_resolved_or_refused_never_silently_retargeted() {
    let d = sandbox("alias-set");
    let before = bytes(&d.join("tasks.jsonl"));
    // T-060 is a task, and also the lane id T-060#2 answered to before the migration.
    for args in [
        &["set", "T-060", "--owner", "x"][..],
        &["claim", "T-060", "lane-x"][..],
    ] {
        let o = run(&d, args);
        assert!(
            o.code == 1 && o.text.contains("T-060 is ambiguous") && o.text.contains("T-060#2"),
            "{args:?}: {}",
            o.text
        );
        assert_eq!(
            bytes(&d.join("tasks.jsonl")),
            before,
            "a refusal writes nothing"
        );
    }
    let o = run(&d, &["set", "T-060", "--owner", "x", "--exact"]);
    assert_eq!(o.code, 0, "{}", o.text);
    assert_eq!(get(&d, "T-060")["owner"], "x");
    assert_eq!(get(&d, "T-060#2")["owner"], "lane-b");
    // check names every such id, so a toolkit edit by the old id is a known hazard, not a silent one.
    let o = run(&d, &["check"]);
    assert!(
        o.code == 0
            && o.text
                .contains("note: T-060 names task T-060 and is a former id of T-060#2"),
        "{}",
        o.text
    );
}

#[test]
fn a_carriage_return_is_refused_and_named() {
    let d = sandbox("crlf");
    let p = d.join("tasks.jsonl");
    let t = fs::read_to_string(&p).unwrap();
    fs::write(&p, t.replacen('\n', "\r\n", 1)).unwrap();
    let before = bytes(&p);
    for args in [&["check"][..], &["fmt", "--check"][..]] {
        let o = run(&d, args);
        assert!(
            o.code == 1 && o.text.contains("tasks.jsonl:1") && o.text.contains("carriage return"),
            "{args:?}: {}",
            o.text
        );
    }
    let o = run(&d, &["set", "T-002", "--owner", "x"]);
    assert!(
        o.code == 1 && o.text.contains("carriage return"),
        "set must not strip it silently: {}",
        o.text
    );
    assert_eq!(bytes(&p), before);
    assert_eq!(run(&d, &["fmt"]).code, 0, "fmt is the repair");
    assert!(!fs::read_to_string(&p).unwrap().contains('\r'));
    assert_eq!(run(&d, &["check"]).code, 0);
}
