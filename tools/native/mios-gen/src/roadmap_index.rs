//! AI-hint: Rust native implementation of roadmap-index (ADR-0021, Law 14)
//! Validates workstreams in ROADMAP.md and regenerates TOC, Workstream Index, Status Rollup, and Metrics table.
//! AI-doc: usr/share/doc/mios/manual/tools.md
//! AI-related: usr/share/mios/mios.toml, ROADMAP.md, tools/roadmap-index.py

use regex::Regex;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use std::process::Command;

#[allow(dead_code)]
#[derive(Debug, Default, Clone)]
pub struct WorkstreamMeta {
    pub id: String,
    pub title: String,
    pub status: String,
    pub priority: String,
    pub laws: Vec<i64>,
    pub ssot_keys: Vec<String>,
    pub adr: Vec<i64>,
    pub deps: Vec<String>,
    pub acceptance: String,
    pub theme: String,
    pub part: Option<String>,
}

fn flatten_keys(v: &toml::Value, prefix: &str, set: &mut HashSet<String>) {
    if let toml::Value::Table(t) = v {
        for (k, val) in t {
            let full_key = if prefix.is_empty() {
                k.clone()
            } else {
                format!("{prefix}.{k}")
            };
            set.insert(full_key.clone());
            flatten_keys(val, &full_key, set);
        }
    }
}

pub fn make_anchor(title: &str) -> String {
    let re_link = Regex::new(r"\[([^\]]+)\]\([^)]+\)").unwrap();
    let text = re_link.replace_all(title, "$1");
    let text = text.replace('`', "");
    let mut out = String::new();
    for c in text.to_lowercase().chars() {
        if c.is_alphanumeric() || c == ' ' || c == '-' || c == '_' {
            out.push(c);
        }
    }
    let res = out.trim();
    let re_spaces = Regex::new(r"\s+").unwrap();
    let res = re_spaces.replace_all(res, "-");
    let re_dashes = Regex::new(r"-+").unwrap();
    re_dashes.replace_all(&res, "-").to_string()
}

pub fn parse_simple_yaml(text: &str) -> HashMap<String, String> {
    let mut metadata = HashMap::new();
    let lines: Vec<&str> = text.trim().split('\n').collect();
    let mut in_multiline = false;
    let mut multiline_key = String::new();
    let mut multiline_val = Vec::new();

    for line in lines {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        if in_multiline {
            multiline_val.push(line);
            continue;
        }
        if !line.contains(':') {
            continue;
        }
        let mut parts = line.splitn(2, ':');
        let k = parts.next().unwrap_or("").trim();
        let v = parts.next().unwrap_or("").trim();
        if v == "|" {
            in_multiline = true;
            multiline_key = k.to_string();
            multiline_val.clear();
            continue;
        }
        metadata.insert(k.to_string(), v.to_string());
    }

    if in_multiline && !multiline_key.is_empty() {
        metadata.insert(multiline_key, multiline_val.join("\n"));
    }
    metadata
}

fn parse_bracket_list(v: &str) -> Vec<String> {
    let s = v.trim();
    if s.starts_with('[') && s.ends_with(']') {
        s[1..s.len() - 1]
            .split(',')
            .map(|x| x.trim().trim_matches('"').trim_matches('\'').to_string())
            .filter(|x| !x.is_empty())
            .collect()
    } else {
        Vec::new()
    }
}

fn parse_int_list(v: &str) -> Vec<i64> {
    parse_bracket_list(v)
        .into_iter()
        .filter_map(|x| x.parse::<i64>().ok())
        .collect()
}

fn check_adr_exists(root: &Path, adr_num: i64) -> bool {
    let prefix = format!("{:04}", adr_num);
    let adr_dir = root.join("usr/share/doc/mios/adr");
    if let Ok(entries) = fs::read_dir(adr_dir) {
        for entry in entries.flatten() {
            let name = entry.file_name();
            let name_str = name.to_string_lossy();
            if name_str.starts_with(&format!("{prefix}-")) && name_str.ends_with(".md") {
                return true;
            }
        }
    }
    false
}

fn format_comma(n: usize) -> String {
    let s = n.to_string();
    let mut result = String::new();
    let len = s.len();
    for (i, c) in s.chars().enumerate() {
        if i > 0 && (len - i).is_multiple_of(3) {
            result.push(',');
        }
        result.push(c);
    }
    result
}

pub fn generate_metrics_table(root: &Path) -> Result<String, String> {
    // 1. Tracked files list
    let ls_files = Command::new("git")
        .args(["-C", &root.to_string_lossy(), "ls-files"])
        .output()
        .map_err(|e| format!("git ls-files failed: {e}"))?;
    if !ls_files.status.success() {
        return Err(format!(
            "git ls-files failed with exit code {:?}",
            ls_files.status.code()
        ));
    }
    let ls_stdout = String::from_utf8_lossy(&ls_files.stdout);
    let tracked: Vec<String> = ls_stdout
        .lines()
        .map(|l| l.trim().replace('\\', "/"))
        .filter(|l| !l.is_empty())
        .collect();
    let file_count = tracked.len();

    // 2. ls-files -s -z for exact blob hashes
    let ls_s = Command::new("git")
        .args(["-C", &root.to_string_lossy(), "ls-files", "-s", "-z"])
        .output()
        .map_err(|e| format!("git ls-files -s failed: {e}"))?;
    if !ls_s.status.success() || ls_s.stdout.is_empty() {
        return Err("git ls-files -s failed or empty".to_string());
    }

    let mut oid_of: HashMap<String, String> = HashMap::new();
    let raw = &ls_s.stdout;
    for chunk in raw.split(|&b| b == 0) {
        if chunk.is_empty() {
            continue;
        }
        let s = String::from_utf8_lossy(chunk);
        if let Some((meta, path)) = s.split_once('\t') {
            let parts: Vec<&str> = meta.split_whitespace().collect();
            if parts.len() >= 2 && !path.is_empty() {
                oid_of.insert(path.to_string(), parts[1].to_string());
            }
        }
    }

    // 3. Batch check object sizes
    let mut total_bytes: u64 = 0;
    if !oid_of.is_empty() {
        let mut oids_input = String::new();
        for oid in oid_of.values() {
            oids_input.push_str(oid);
            oids_input.push('\n');
        }

        use std::io::Write;
        let mut child = Command::new("git")
            .args([
                "-C",
                &root.to_string_lossy(),
                "cat-file",
                "--batch-check=%(objectsize)",
            ])
            .stdin(std::process::Stdio::piped())
            .stdout(std::process::Stdio::piped())
            .spawn()
            .map_err(|e| format!("git cat-file --batch-check spawn failed: {e}"))?;

        if let Some(mut stdin) = child.stdin.take() {
            let _ = stdin.write_all(oids_input.as_bytes());
        }
        let out = child
            .wait_with_output()
            .map_err(|e| format!("git cat-file wait failed: {e}"))?;
        let out_str = String::from_utf8_lossy(&out.stdout);
        for line in out_str.lines() {
            if let Ok(bytes) = line.trim().parse::<u64>() {
                total_bytes += bytes;
            }
        }
    }

    // 4. Batch read code files to count lines
    let counted_exts = [".sh", ".py", ".ps1", ".rs"];
    let mut counted: HashMap<&'static str, usize> = HashMap::new();
    for ext in counted_exts {
        counted.insert(ext, 0);
    }

    let mut code: Vec<(&'static str, String)> = Vec::new();
    for f in &tracked {
        let f_lower = f.to_lowercase();
        for ext in counted_exts {
            if f_lower.ends_with(ext) {
                if let Some(oid) = oid_of.get(f) {
                    code.push((ext, oid.clone()));
                }
                break;
            }
        }
    }

    if !code.is_empty() {
        let mut oids_input = String::new();
        for (_, oid) in &code {
            oids_input.push_str(oid);
            oids_input.push('\n');
        }

        use std::io::Write;
        let mut child = Command::new("git")
            .args(["-C", &root.to_string_lossy(), "cat-file", "--batch"])
            .stdin(std::process::Stdio::piped())
            .stdout(std::process::Stdio::piped())
            .spawn()
            .map_err(|e| format!("git cat-file --batch spawn failed: {e}"))?;

        if let Some(mut stdin) = child.stdin.take() {
            let _ = stdin.write_all(oids_input.as_bytes());
        }
        let out = child
            .wait_with_output()
            .map_err(|e| format!("git cat-file --batch wait failed: {e}"))?;
        let blob = out.stdout;

        let mut pos = 0;
        for (ext, _) in &code {
            if pos >= blob.len() {
                break;
            }
            // Find newline terminating the header: <oid> SP <type> SP <size> LF
            let nl = match blob[pos..].iter().position(|&b| b == b'\n') {
                Some(idx) => pos + idx,
                None => break,
            };
            let header = String::from_utf8_lossy(&blob[pos..nl]);
            let h_parts: Vec<&str> = header.split_whitespace().collect();
            if h_parts.len() < 3 {
                break;
            }
            let size: usize = match h_parts[2].parse() {
                Ok(s) => s,
                Err(_) => break,
            };
            let body_start = nl + 1;
            let body_end = body_start + size;
            if body_end > blob.len() {
                break;
            }
            let body = &blob[body_start..body_end];
            let mut nl_count = body.iter().filter(|&&b| b == b'\n').count();
            if !body.is_empty() && !body.ends_with(b"\n") {
                nl_count += 1;
            }
            *counted.get_mut(ext).unwrap() += nl_count;
            // Advance past body and git's trailing newline delimiter
            pos = body_end + 1;
        }
    }

    let sh_l = counted[".sh"];
    let py_l = counted[".py"];
    let ps_l = counted[".ps1"];
    let rs_l = counted[".rs"];

    let size_mb = ((total_bytes as f64) / (1024.0 * 1024.0)).round() as u64;
    let sh_k = (sh_l as f64 / 1000.0).round() as u64;
    let py_k = (py_l as f64 / 1000.0).round() as u64;
    let ps_k = (ps_l as f64 / 1000.0).round() as u64;
    let rs_k = (rs_l as f64 / 1000.0).round() as u64;
    let ratio = if rs_l > 0 {
        (ps_l as f64) / (rs_l as f64)
    } else {
        0.0
    };

    // 5. Drift checks count from automation/98-drift-checks.sh
    let mut drift_count = 0;
    let gate_sh = root.join("automation/98-drift-checks.sh");
    if let Ok(txt) = fs::read_to_string(&gate_sh) {
        if let Some(m_pos) = txt.find("main() {") {
            let rest = &txt[m_pos..];
            let re_check = Regex::new(r"^\s*(check_[a-z0-9_]+)\s*$").unwrap();
            for line in rest.lines() {
                if re_check.is_match(line) {
                    drift_count += 1;
                }
            }
        }
    }

    // 6. Units count
    let mut declared_cnt = 0;
    let mut drift_units_cnt = 0;
    let toml_path = root.join("usr/share/mios/mios.toml");
    if let Ok(txt) = fs::read_to_string(&toml_path) {
        if let Ok(toml_val) = txt.parse::<toml::Value>() {
            if let Some(units) = toml_val.get("units").and_then(|u| u.as_table()) {
                declared_cnt = units.values().filter(|v| v.is_table()).count();
            }
            if let Some(drift) = toml_val
                .get("unit_projection")
                .and_then(|u| u.get("drift"))
                .and_then(|d| d.as_array())
            {
                drift_units_cnt = drift.len();
            }
        }
    }

    let mut shipped_cnt = 0;
    let unit_dir = root.join("usr/lib/systemd/system");
    if unit_dir.is_dir() {
        let mut stack = vec![unit_dir];
        while let Some(dir) = stack.pop() {
            if let Ok(entries) = fs::read_dir(dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.is_dir() {
                        stack.push(path);
                    } else if path.is_file() {
                        shipped_cnt += 1;
                    }
                }
            }
        }
    }

    let faithful_cnt = declared_cnt.saturating_sub(drift_units_cnt);

    let table_lines = [
        "| | Measured | Note |",
        "|---|---:|---|",
        "| Runs on | MiOS-DEV VM / WSL | Bare metal is **untried**; blade/mesh/vfio behaviour is design, not observation. |",
        &format!("| Tracked files | {} | The reading surface. |", format_comma(file_count)),
        &format!("| Tracked size | {} MB | Two vendored assets are most of it. |", size_mb),
        &format!(
            "| Shell / Python / PowerShell / Rust | {}k / {}k / {}k / {}k lines | Law 14 makes Rust the native tier; PowerShell currently outweighs it {:.1}x. |",
            sh_k, py_k, ps_k, rs_k, ratio
        ),
        &format!("| Drift checks | {} | Falsifiability audited per check, not assumed. |", drift_count),
        &format!(
            "| Units reproducing from SSOT | {} faithful of {} | {} registered as drifting: the largest hole in part 1 of the thesis. |",
            faithful_cnt, shipped_cnt, drift_units_cnt
        ),
    ];
    Ok(format!("{}\n", table_lines.join("\n")))
}

pub fn replace_section(
    text: &str,
    start_marker: &str,
    end_marker: &str,
    replacement: &str,
) -> Result<String, String> {
    let start_idx = text
        .find(start_marker)
        .ok_or_else(|| format!("Marker {start_marker} not found"))?;
    let rest = &text[start_idx + start_marker.len()..];
    let end_offset = rest
        .find(end_marker)
        .ok_or_else(|| format!("Marker {end_marker} not found"))?;
    let end_idx = start_idx + start_marker.len() + end_offset;

    Ok(format!(
        "{}{}\n{}{}",
        &text[..start_idx],
        start_marker,
        replacement,
        &text[end_idx..]
    ))
}

pub fn generate_roadmap_index(root: &Path) -> Result<(String, String), (String, i32)> {
    let roadmap_path = root.join("ROADMAP.md");
    if !roadmap_path.is_file() {
        return Err((
            format!("ERROR: ROADMAP.md not found at {}", roadmap_path.display()),
            1,
        ));
    }

    let file_text = fs::read_to_string(&roadmap_path)
        .map_err(|e| (format!("Cannot read ROADMAP.md: {e}"), 1))?;

    // Load SSOT keys from mios.toml
    let toml_path = root.join("usr/share/mios/mios.toml");
    let mut valid_ssot_keys = HashSet::new();
    let toml_data: Option<toml::Value> = if toml_path.is_file() {
        let txt = fs::read_to_string(&toml_path).unwrap_or_default();
        if let Ok(v) = txt.parse::<toml::Value>() {
            flatten_keys(&v, "", &mut valid_ssot_keys);
            Some(v)
        } else {
            None
        }
    } else {
        None
    };

    // Load userenv mappings if present
    let userenv_path = root.join("tools/lib/userenv.sh");
    if userenv_path.is_file() {
        if let Ok(txt) = fs::read_to_string(&userenv_path) {
            let re_userenv = Regex::new(r#"\("([a-zA-Z0-9_.-]+)"\s*,\s*"[A-Z0-9_]+"\)"#).unwrap();
            for caps in re_userenv.captures_iter(&txt) {
                valid_ssot_keys.insert(caps[1].to_string());
            }
        }
    }

    let mut valid_law_ids = HashSet::new();
    if let Some(ref data) = toml_data {
        if let Some(laws) = data
            .get("laws")
            .and_then(|l| l.get("laws"))
            .and_then(|l| l.as_array())
        {
            for law in laws {
                if let Some(id) = law.get("id").and_then(|i| i.as_integer()) {
                    valid_law_ids.insert(id);
                }
            }
        }
    }

    let lines: Vec<&str> = file_text.lines().collect();
    let mut current_part: Option<String> = None;
    let mut workstreams: Vec<WorkstreamMeta> = Vec::new();
    let mut parts_order: Vec<String> = Vec::new();
    let mut part_workstreams: HashMap<String, Vec<WorkstreamMeta>> = HashMap::new();

    let mut idx = 0;
    let re_sep = Regex::new(r"\s+[-—–]+\s+").unwrap();

    while idx < lines.len() {
        let line = lines[idx];
        if line.starts_with("# ") && !line.starts_with("## ") {
            let header_name = line[2..].trim();
            let h_lower = header_name.to_lowercase();
            if !h_lower.starts_with("mios -- master roadmap")
                && !h_lower.starts_with("mios roadmap")
                && !h_lower.starts_with("archived mios roadmap")
                && !h_lower.starts_with("appendix")
            {
                current_part = Some(header_name.to_string());
                if !parts_order.contains(&header_name.to_string()) {
                    parts_order.push(header_name.to_string());
                    part_workstreams.insert(header_name.to_string(), Vec::new());
                }
                idx += 1;
                continue;
            }
        }

        if line.starts_with("## WS-") {
            let header_text = line[2..].trim();
            let mut parts = re_sep.splitn(header_text, 2);
            let ws_id = parts.next().unwrap_or("").trim().to_string();
            let ws_title = parts
                .next()
                .map(|s| s.trim().to_string())
                .unwrap_or_else(|| header_text.to_string());

            let mut frontmatter_text = String::new();
            let mut fm_idx = idx + 1;
            while fm_idx < lines.len() && lines[fm_idx].trim().is_empty() {
                fm_idx += 1;
            }

            if fm_idx < lines.len() && lines[fm_idx].trim().starts_with("<!--") {
                let mut block_lines = Vec::new();
                let first_line = lines[fm_idx].trim();
                if first_line.ends_with("-->") {
                    block_lines.push(&first_line[4..first_line.len() - 3]);
                } else {
                    block_lines.push(&first_line[4..]);
                    let mut cur_idx = fm_idx + 1;
                    while cur_idx < lines.len() {
                        let cur_line = lines[cur_idx];
                        if let Some((before, _)) = cur_line.split_once("-->") {
                            block_lines.push(before);
                            break;
                        } else {
                            block_lines.push(cur_line);
                            cur_idx += 1;
                        }
                    }
                }
                let block_text = block_lines.join("\n");
                if block_text.contains("id:") || block_text.contains("status:") {
                    frontmatter_text = block_text;
                }
            }

            let parsed_yaml = if !frontmatter_text.is_empty() {
                parse_simple_yaml(&frontmatter_text)
            } else {
                HashMap::new()
            };

            let id = parsed_yaml.get("id").cloned().unwrap_or(ws_id);
            let title = parsed_yaml.get("title").cloned().unwrap_or(ws_title);

            let status = if let Some(st) = parsed_yaml.get("status") {
                st.clone()
            } else {
                let mut rest_of_text = String::new();
                let end = std::cmp::min(idx + 15, lines.len());
                for l in &lines[idx..end] {
                    rest_of_text.push_str(l);
                    rest_of_text.push('\n');
                }
                if rest_of_text.contains('✅') || rest_of_text.contains("DONE") {
                    "done".to_string()
                } else if rest_of_text.to_lowercase().contains("active") {
                    "active".to_string()
                } else {
                    "proposed".to_string()
                }
            };

            let priority = parsed_yaml
                .get("priority")
                .cloned()
                .unwrap_or_else(|| "P2".to_string());
            let laws = parsed_yaml
                .get("laws")
                .map(|v| parse_int_list(v))
                .unwrap_or_default();
            let ssot_keys = parsed_yaml
                .get("ssot_keys")
                .map(|v| parse_bracket_list(v))
                .unwrap_or_default();
            let adr = parsed_yaml
                .get("adr")
                .map(|v| parse_int_list(v))
                .unwrap_or_default();
            let deps = parsed_yaml
                .get("deps")
                .map(|v| parse_bracket_list(v))
                .unwrap_or_default();
            let acceptance = parsed_yaml.get("acceptance").cloned().unwrap_or_default();
            let theme = parsed_yaml
                .get("theme")
                .cloned()
                .unwrap_or_else(|| "General".to_string());

            let meta = WorkstreamMeta {
                id,
                title,
                status,
                priority,
                laws,
                ssot_keys,
                adr,
                deps,
                acceptance,
                theme,
                part: current_part.clone(),
            };

            workstreams.push(meta.clone());
            if let Some(ref part) = current_part {
                if let Some(list) = part_workstreams.get_mut(part) {
                    list.push(meta);
                }
            }
        }

        idx += 1;
    }

    // Validation
    let mut validation_errors = Vec::new();
    for ws in &workstreams {
        for law in &ws.laws {
            if !valid_law_ids.is_empty() && !valid_law_ids.contains(law) {
                validation_errors.push(format!("Workstream {} cites invalid Law: {law}", ws.id));
            }
        }
        for adr_num in &ws.adr {
            if !check_adr_exists(root, *adr_num) {
                validation_errors.push(format!(
                    "Workstream {} cites non-existent ADR: {adr_num}",
                    ws.id
                ));
            }
        }
        for key in &ws.ssot_keys {
            if !valid_ssot_keys.contains(key) {
                validation_errors.push(format!(
                    "Workstream {} cites non-existent SSOT key: {key}",
                    ws.id
                ));
            }
        }
    }

    if !validation_errors.is_empty() {
        eprintln!("[roadmap-index] Validation failed:");
        for err in &validation_errors {
            eprintln!("  - {err}");
        }
        return Err(("Roadmap validation failed".to_string(), 2));
    }

    // Generate TOC
    let mut toc_lines = vec!["## Table of Contents".to_string()];
    for part in &parts_order {
        let anchor = make_anchor(part);
        toc_lines.push(format!("- [{part}](#{anchor})"));
    }
    let toc_content = format!("{}\n", toc_lines.join("\n"));

    // Generate Rollup
    let mut rollup_counts: HashMap<&str, usize> = HashMap::new();
    rollup_counts.insert("done", 0);
    rollup_counts.insert("active", 0);
    rollup_counts.insert("proposed", 0);
    rollup_counts.insert("blocked", 0);

    for ws in &workstreams {
        let status = ws.status.to_lowercase();
        match status.as_str() {
            "done" | "active" | "proposed" | "blocked" => {
                *rollup_counts.get_mut(status.as_str()).unwrap() += 1;
            }
            _ => {
                *rollup_counts.get_mut("proposed").unwrap() += 1;
            }
        }
    }
    let done_cnt = rollup_counts["done"];
    let active_cnt = rollup_counts["active"];
    let proposed_cnt = rollup_counts["proposed"];
    let blocked_cnt = rollup_counts["blocked"];

    let rollup_lines = [
        "### Workstream Status Rollup",
        &format!("- **Done**: {done_cnt}"),
        &format!("- **Active**: {active_cnt}"),
        &format!("- **Proposed**: {proposed_cnt}"),
        &format!("- **Blocked**: {blocked_cnt}"),
    ];
    let rollup_content = format!("{}\n", rollup_lines.join("\n"));

    // Generate Index
    let mut index_lines = vec!["### Workstream Index\n".to_string()];
    for part in &parts_order {
        index_lines.push(format!("**{part}**"));
        let ws_list = part_workstreams.get(part).cloned().unwrap_or_default();
        if ws_list.is_empty() {
            index_lines.push("(no workstreams)\n".to_string());
        } else {
            for ws in ws_list {
                let status_suffix = if ws.status.to_lowercase() == "done" {
                    " ✅".to_string()
                } else {
                    format!(" ({})", ws.status.to_lowercase())
                };
                index_lines.push(format!("- `{}` — {}{}", ws.id, ws.title, status_suffix));
            }
            index_lines.push(String::new());
        }
    }
    let index_content = index_lines.join("\n");

    // Generate Metrics
    let metrics_content = generate_metrics_table(root).map_err(|e| (e, 1))?;

    // Perform replacements
    let mut new_text = file_text.clone();
    new_text = replace_section(
        &new_text,
        "<!-- ROADMAP_METRICS_START -->",
        "<!-- ROADMAP_METRICS_END -->",
        &metrics_content,
    )
    .map_err(|e| (format!("ERROR: {e}"), 1))?;

    new_text = replace_section(
        &new_text,
        "<!-- ROADMAP_ROLLUP_START -->",
        "<!-- ROADMAP_ROLLUP_END -->",
        &rollup_content,
    )
    .map_err(|e| (format!("ERROR: {e}"), 1))?;

    new_text = replace_section(
        &new_text,
        "<!-- ROADMAP_INDEX_START -->",
        "<!-- ROADMAP_INDEX_END -->",
        &index_content,
    )
    .map_err(|e| (format!("ERROR: {e}"), 1))?;

    new_text = replace_section(
        &new_text,
        "<!-- ROADMAP_TOC_START -->",
        "<!-- ROADMAP_TOC_END -->",
        &toc_content,
    )
    .map_err(|e| (format!("ERROR: {e}"), 1))?;

    Ok((file_text, new_text))
}

pub fn run_roadmap_index(
    root: &Path,
    check_mode: bool,
    json_format: bool,
) -> Result<(), (String, i32)> {
    let (file_text, new_text) = generate_roadmap_index(root)?;
    let roadmap_path = root.join("ROADMAP.md");

    if check_mode {
        if file_text != new_text {
            if !json_format {
                eprintln!("[roadmap-index] DRIFT detected: ROADMAP.md index is stale");
            }
            return Err(("DRIFT detected: ROADMAP.md index is stale".to_string(), 1));
        }

        if !json_format {
            println!("[roadmap-index] ROADMAP.md index is in sync");
        }
        return Ok(());
    }

    fs::write(&roadmap_path, new_text).map_err(|e| (format!("Cannot write ROADMAP.md: {e}"), 1))?;

    if !json_format {
        println!(
            "[roadmap-index] Successfully regenerated Table of Contents, Index, Metrics, and Rollup in ROADMAP.md"
        );
    }

    Ok(())
}
