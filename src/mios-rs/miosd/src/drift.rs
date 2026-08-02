use regex::Regex;
use std::collections::HashSet;
use std::fs;
use std::path::Path;
use toml::Value;

pub fn run_checks(root: &str, soft: bool) {
    let root_path = Path::new(root);
    let mios_toml_path = root_path.join("usr/share/mios/mios.toml");

    println!("[miosd:drift] Starting drift checks at root: {}", root);

    let mut failed = false;

    if !mios_toml_path.exists() {
        println!(
            "[miosd:drift] ERROR: {} not found.",
            mios_toml_path.display()
        );
        failed = true;
    } else {
        println!(
            "[miosd:drift] [PASS] SSOT found at {}",
            mios_toml_path.display()
        );

        let contents = fs::read_to_string(&mios_toml_path).unwrap_or_default();
        match contents.parse::<Value>() {
            Ok(_) => println!("[miosd:drift] [PASS] SSOT TOML parses successfully"),
            Err(e) => {
                println!("[miosd:drift] [FAIL] SSOT TOML parse error: {}", e);
                failed = true;
            }
        }
    }

    match check_backfill_coverage(root_path) {
        Ok(_) => println!("[miosd:drift] [PASS] check_backfill_coverage"),
        Err(e) => {
            println!("[miosd:drift] [FAIL] check_backfill_coverage:\n{}", e);
            failed = true;
        }
    }

    if failed {
        println!("[miosd:drift] One or more checks failed.");
        if !soft {
            std::process::exit(1);
        }
    } else {
        println!("[miosd:drift] All checks completed successfully.");
    }
}

fn check_backfill_coverage(root_path: &Path) -> Result<(), String> {
    let schema_path = root_path.join("usr/share/mios/postgres/schema-init.sql");
    let backfill_path =
        root_path.join("usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py");

    let schema = fs::read_to_string(&schema_path)
        .map_err(|e| format!("Failed to read schema-init.sql: {}", e))?;
    let backfill = fs::read_to_string(&backfill_path)
        .map_err(|e| format!("Failed to read embed_backfill.py: {}", e))?;

    let table_re =
        Regex::new(r"(?i)CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_.]+)").expect("valid regex");
    // Match the COLUMN TYPE `emb vector(...)`, not the HNSW index operator class
    // `(emb vector_cosine_ops)` -- requiring `(` after `vector` excludes the opclass.
    let emb_re = Regex::new(r"(?i)emb\s+vector\s*\(").expect("valid regex");
    let alter_re = Regex::new(r"(?i)ALTER\s+TABLE\s+([a-zA-Z0-9_]+)\s+ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?emb\s+vector").expect("valid regex");

    let mut emb_tables = HashSet::new();
    let mut current_table = String::new();

    for line in schema.lines() {
        if let Some(caps) = table_re.captures(line) {
            current_table = caps[1].to_string();
        }
        // ALTER TABLE <t> ADD COLUMN ... emb vector -> attribute to <t>, then skip the
        // current_table heuristic below: an ALTER that adds emb to table X while sitting
        // inside table Y's region must NOT falsely tag Y (the domain_verb false positive).
        if let Some(caps) = alter_re.captures(line) {
            let t = caps[1].to_string();
            if !t.contains('.') {
                emb_tables.insert(t);
            }
            continue;
        }
        // Bare "emb vector" column inside a CREATE TABLE body -> current_table. Skip
        // schema-qualified tables (e.g. mios_identity.*): those live in their own schema
        // and are owned by that subsystem, not the public-schema embed_backfill job.
        if emb_re.is_match(line) && !current_table.is_empty() && !current_table.contains('.') {
            emb_tables.insert(current_table.clone());
        }
    }

    let mut mapped_tables = HashSet::new();
    let pk_map_re = Regex::new(r#""([a-zA-Z0-9_]+)"\s*:"#).expect("valid regex");
    let exempt_re = Regex::new(r#""([a-zA-Z0-9_]+)""#).expect("valid regex");

    let mut in_pk_map = false;
    let mut in_exempt = false;

    for line in backfill.lines() {
        if line.contains("PK_MAP = {") {
            in_pk_map = true;
            continue;
        }
        if line.contains("}") && in_pk_map {
            in_pk_map = false;
        }
        if line.contains("_BACKFILL_EXEMPT = [") {
            in_exempt = true;
            continue;
        }
        if line.contains("]") && in_exempt {
            in_exempt = false;
        }

        if in_pk_map {
            if let Some(caps) = pk_map_re.captures(line) {
                mapped_tables.insert(caps[1].to_string());
            }
        }
        if in_exempt {
            if let Some(caps) = exempt_re.captures(line) {
                mapped_tables.insert(caps[1].to_string());
            }
        }
    }

    let mut errors = Vec::new();
    for table in &emb_tables {
        if !mapped_tables.contains(table) {
            errors.push(format!(
                "Table '{}' has 'emb vector' but is not in PK_MAP or _BACKFILL_EXEMPT",
                table
            ));
        }
    }

    if !errors.is_empty() {
        return Err(errors.join("\n"));
    }

    Ok(())
}
