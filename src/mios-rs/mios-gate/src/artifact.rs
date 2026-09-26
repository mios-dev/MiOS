// AI-hint: Artifact verification gate for mios-gate: validates OCI descriptor closure, non-executing SafeTensors/GGUF headers, and OpenAI SFT/DPO JSONL datasets.
// AI-related: src/mios-rs/mios-gate/src/main.rs, usr/share/doc/mios/adr/0024-dual-tier-oci-ai-artifacts.md, ROADMAP.md (MODELOCI-04)

use crate::Report;
use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};

const CHECK: &str = "artifact";

const SECRET_PATTERNS: [&str; 5] = [
    "ghp_",
    "sk-",
    "BEGIN PRIVATE KEY",
    "BEGIN OPENSSH PRIVATE KEY",
    "password =",
];

fn cannot_run(why: impl Into<String>) -> Report {
    Report {
        check: CHECK.to_string(),
        ok: false,
        could_not_run: Some(why.into()),
        summary: String::new(),
        findings: Vec::new(),
    }
}

/// Checks OpenAI Chat SFT format in `var/lib/mios/training/sft.jsonl`.
fn check_sft(path: &Path, findings: &mut Vec<String>) {
    let content = match std::fs::read_to_string(path) {
        Ok(c) => c,
        Err(e) => {
            findings.push(format!("{}: failed to read SFT dataset: {e}", path.display()));
            return;
        }
    };

    let mut line_count = 0;
    for (idx, line) in content.lines().enumerate() {
        let line_no = idx + 1;
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        line_count += 1;

        // Check secret patterns
        scan_secrets(path, line_no, line, findings);

        // Parse JSON
        let val: serde_json::Value = match serde_json::from_str(trimmed) {
            Ok(v) => v,
            Err(e) => {
                findings.push(format!(
                    "{}:{}: failed to parse JSON: {e}",
                    path.display(),
                    line_no
                ));
                continue;
            }
        };

        // Validate "messages" array
        let Some(messages) = val.get("messages").and_then(|m| m.as_array()) else {
            findings.push(format!(
                "{}:{}: missing or invalid 'messages' array",
                path.display(),
                line_no
            ));
            continue;
        };

        if messages.is_empty() {
            findings.push(format!(
                "{}:{}: 'messages' array is empty",
                path.display(),
                line_no
            ));
            continue;
        }

        let mut has_assistant = false;
        for (m_idx, msg) in messages.iter().enumerate() {
            let Some(role) = msg.get("role").and_then(|r| r.as_str()) else {
                findings.push(format!(
                    "{}:{}: message[{m_idx}] missing string 'role'",
                    path.display(),
                    line_no
                ));
                continue;
            };

            if role != "system" && role != "user" && role != "assistant" {
                findings.push(format!(
                    "{}:{}: message[{m_idx}] invalid role {:?}, must be system, user, or assistant",
                    path.display(),
                    line_no,
                    role
                ));
            }

            let Some(content_str) = msg.get("content").and_then(|c| c.as_str()) else {
                findings.push(format!(
                    "{}:{}: message[{m_idx}] missing string 'content'",
                    path.display(),
                    line_no
                ));
                continue;
            };

            if content_str.trim().is_empty() {
                findings.push(format!(
                    "{}:{}: message[{m_idx}] 'content' is empty",
                    path.display(),
                    line_no
                ));
            }

            if role == "assistant" && !content_str.trim().is_empty() {
                has_assistant = true;
            }
        }

        if !has_assistant {
            findings.push(format!(
                "{}:{}: missing assistant message with non-empty content",
                path.display(),
                line_no
            ));
        }
    }

    if line_count == 0 {
        findings.push(format!("{}: SFT dataset is empty", path.display()));
    }
}

/// Checks OpenAI Preference DPO format in `var/lib/mios/training/dpo.jsonl`.
fn check_dpo(path: &Path, findings: &mut Vec<String>) {
    let content = match std::fs::read_to_string(path) {
        Ok(c) => c,
        Err(e) => {
            findings.push(format!("{}: failed to read DPO dataset: {e}", path.display()));
            return;
        }
    };

    let mut line_count = 0;
    for (idx, line) in content.lines().enumerate() {
        let line_no = idx + 1;
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        line_count += 1;

        // Check secret patterns
        scan_secrets(path, line_no, line, findings);

        // Parse JSON
        let val: serde_json::Value = match serde_json::from_str(trimmed) {
            Ok(v) => v,
            Err(e) => {
                findings.push(format!(
                    "{}:{}: failed to parse JSON: {e}",
                    path.display(),
                    line_no
                ));
                continue;
            }
        };

        // Validate "input" object with non-empty "messages" array
        let Some(input_obj) = val.get("input").and_then(|i| i.as_object()) else {
            findings.push(format!(
                "{}:{}: missing or invalid 'input' object",
                path.display(),
                line_no
            ));
            continue;
        };

        let Some(input_messages) = input_obj.get("messages").and_then(|m| m.as_array()) else {
            findings.push(format!(
                "{}:{}: missing or invalid 'messages' array in 'input'",
                path.display(),
                line_no
            ));
            continue;
        };

        if input_messages.is_empty() {
            findings.push(format!(
                "{}:{}: 'input.messages' array is empty",
                path.display(),
                line_no
            ));
        } else {
            for (m_idx, msg) in input_messages.iter().enumerate() {
                let Some(role) = msg.get("role").and_then(|r| r.as_str()) else {
                    findings.push(format!(
                        "{}:{}: input message[{m_idx}] missing string 'role'",
                        path.display(),
                        line_no
                    ));
                    continue;
                };

                if role != "system" && role != "user" && role != "assistant" {
                    findings.push(format!(
                        "{}:{}: input message[{m_idx}] invalid role {:?}",
                        path.display(),
                        line_no,
                        role
                    ));
                }

                let Some(content_str) = msg.get("content").and_then(|c| c.as_str()) else {
                    findings.push(format!(
                        "{}:{}: input message[{m_idx}] missing string 'content'",
                        path.display(),
                        line_no
                    ));
                    continue;
                };

                if content_str.trim().is_empty() {
                    findings.push(format!(
                        "{}:{}: input message[{m_idx}] 'content' is empty",
                        path.display(),
                        line_no
                    ));
                }
            }
        }

        // Validate "preferred_output"
        let pref = val.get("preferred_output");
        match pref.and_then(|p| p.as_array()) {
            Some(pref_arr) => {
                validate_assistant_messages(path, line_no, "preferred_output", pref_arr, findings);
            }
            None => {
                findings.push(format!(
                    "{}:{}: missing or invalid 'preferred_output' array",
                    path.display(),
                    line_no
                ));
            }
        }

        // Validate "non_preferred_output"
        let non_pref = val.get("non_preferred_output");
        match non_pref.and_then(|np| np.as_array()) {
            Some(non_pref_arr) => {
                validate_assistant_messages(
                    path,
                    line_no,
                    "non_preferred_output",
                    non_pref_arr,
                    findings,
                );
            }
            None => {
                findings.push(format!(
                    "{}:{}: missing or invalid 'non_preferred_output' array",
                    path.display(),
                    line_no
                ));
            }
        }

        // Validate distinct outputs
        if let (Some(p), Some(np)) = (pref, non_pref) {
            if p == np {
                findings.push(format!(
                    "{}:{}: 'preferred_output' and 'non_preferred_output' are identical",
                    path.display(),
                    line_no
                ));
            }
        }
    }

    if line_count == 0 {
        findings.push(format!("{}: DPO dataset is empty", path.display()));
    }
}

/// Validates that an array of messages contains only valid assistant messages with non-empty content.
fn validate_assistant_messages(
    path: &Path,
    line_no: usize,
    field_name: &str,
    messages: &[serde_json::Value],
    findings: &mut Vec<String>,
) {
    if messages.is_empty() {
        findings.push(format!(
            "{}:{}: '{}' array is empty",
            path.display(),
            line_no,
            field_name
        ));
        return;
    }

    for (idx, msg) in messages.iter().enumerate() {
        let Some(role) = msg.get("role").and_then(|r| r.as_str()) else {
            findings.push(format!(
                "{}:{}: {}[{idx}] missing string 'role'",
                path.display(),
                line_no,
                field_name
            ));
            continue;
        };

        if role != "assistant" {
            findings.push(format!(
                "{}:{}: {}[{idx}] invalid role {:?}, expected 'assistant'",
                path.display(),
                line_no,
                field_name,
                role
            ));
        }

        let Some(content_str) = msg.get("content").and_then(|c| c.as_str()) else {
            findings.push(format!(
                "{}:{}: {}[{idx}] missing string 'content'",
                path.display(),
                line_no,
                field_name
            ));
            continue;
        };

        if content_str.trim().is_empty() {
            findings.push(format!(
                "{}:{}: {}[{idx}] 'content' is empty",
                path.display(),
                line_no,
                field_name
            ));
        }
    }
}

/// Scans a text line for high-entropy secrets and private token patterns.
fn scan_secrets(path: &Path, line_no: usize, line: &str, findings: &mut Vec<String>) {
    for pattern in SECRET_PATTERNS {
        if line.contains(pattern) {
            findings.push(format!(
                "{}:{}: forbidden secret or private token pattern detected: {:?}",
                path.display(),
                line_no,
                pattern
            ));
        }
    }
}

/// Scans directories for safe weight deserialization.
fn scan_weights(dir: &Path, findings: &mut Vec<String>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            scan_weights(&path, findings);
        } else if path.is_file() {
            check_weight_file(&path, findings);
        }
    }
}

/// Verifies individual weight file format.
fn check_weight_file(path: &Path, findings: &mut Vec<String>) {
    let file_name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
    let lower = file_name.to_ascii_lowercase();

    // 1. Reject any file ending in .pt, .bin, .pickle, .pkl
    if lower.ends_with(".pt")
        || lower.ends_with(".bin")
        || lower.ends_with(".pickle")
        || lower.ends_with(".pkl")
    {
        findings.push(format!(
            "{}: unsafe weights deserialization format rejected (.pt, .bin, .pickle, .pkl)",
            path.display()
        ));
        return;
    }

    // 2. If .gguf file exists, verify first 4 bytes are b"GGUF"
    if lower.ends_with(".gguf") {
        match File::open(path) {
            Ok(mut f) => {
                let mut magic = [0u8; 4];
                match f.read_exact(&mut magic) {
                    Ok(()) => {
                        if &magic != b"GGUF" {
                            findings.push(format!(
                                "{}: invalid GGUF magic header: expected b\"GGUF\", found {:?}",
                                path.display(),
                                magic
                            ));
                        }
                    }
                    Err(e) => {
                        findings.push(format!(
                            "{}: failed to read GGUF magic header: {e}",
                            path.display()
                        ));
                    }
                }
            }
            Err(e) => {
                findings.push(format!("{}: failed to open GGUF file: {e}", path.display()));
            }
        }
    }

    // 3. If .safetensors file exists, verify file is at least 8 bytes and read 8-byte little-endian header length
    if lower.ends_with(".safetensors") {
        match std::fs::metadata(path) {
            Ok(meta) => {
                let len = meta.len();
                if len < 8 {
                    findings.push(format!(
                        "{}: safetensors file size ({} bytes) is less than 8 bytes",
                        path.display(),
                        len
                    ));
                } else {
                    match File::open(path) {
                        Ok(mut f) => {
                            let mut buf = [0u8; 8];
                            match f.read_exact(&mut buf) {
                                Ok(()) => {
                                    let header_len = u64::from_le_bytes(buf);
                                    if header_len == 0 {
                                        findings.push(format!(
                                            "{}: safetensors header length is 0",
                                            path.display()
                                        ));
                                    } else if header_len > len.saturating_sub(8) {
                                        findings.push(format!(
                                            "{}: safetensors header length ({header_len}) exceeds payload size ({})",
                                            path.display(),
                                            len.saturating_sub(8)
                                        ));
                                    }
                                }
                                Err(e) => {
                                    findings.push(format!(
                                        "{}: failed to read safetensors header: {e}",
                                        path.display()
                                    ));
                                }
                            }
                        }
                        Err(e) => {
                            findings.push(format!(
                                "{}: failed to open safetensors file: {e}",
                                path.display()
                            ));
                        }
                    }
                }
            }
            Err(e) => {
                findings.push(format!("{}: failed to read metadata: {e}", path.display()));
            }
        }
    }
}

/// Recursively discovers OCI layout directories (containing `oci-layout`).
fn find_oci_layout_dirs(root: &Path) -> Vec<PathBuf> {
    let mut layouts = Vec::new();
    if root.join("oci-layout").is_file() {
        layouts.push(root.to_path_buf());
    }
    find_oci_layouts_recursive(root, 0, &mut layouts);
    layouts.sort();
    layouts.dedup();
    layouts
}

fn find_oci_layouts_recursive(dir: &Path, depth: usize, layouts: &mut Vec<PathBuf>) {
    if depth > 4 {
        return;
    }
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let Ok(file_type) = entry.file_type() else {
            continue;
        };
        if file_type.is_dir() {
            let path = entry.path();
            let name = entry.file_name();
            let name_str = name.to_string_lossy();
            if name_str.starts_with('.') || name_str == "target" || name_str == "node_modules" {
                continue;
            }
            if path.join("oci-layout").is_file() {
                layouts.push(path);
            } else {
                find_oci_layouts_recursive(&path, depth + 1, layouts);
            }
        }
    }
}

/// Resolves an OCI digest (e.g. `sha256:<hash>`) to its location in `blobs/<algo>/<hash>`.
fn resolve_blob_path(oci_dir: &Path, digest: &str) -> Option<PathBuf> {
    let (algo, hash) = digest.split_once(':')?;
    if algo.is_empty() || hash.is_empty() {
        return None;
    }
    Some(oci_dir.join("blobs").join(algo).join(hash))
}

/// Verifies a single OCI descriptor's physical blob existence and size.
fn verify_blob_descriptor(
    oci_dir: &Path,
    desc: &serde_json::Value,
    context: &str,
    findings: &mut Vec<String>,
) {
    let Some(digest) = desc.get("digest").and_then(|d| d.as_str()) else {
        findings.push(format!("{context}: missing string 'digest'"));
        return;
    };
    let Some(expected_size) = desc.get("size").and_then(|s| s.as_u64()) else {
        findings.push(format!("{context}: missing integer 'size'"));
        return;
    };
    let Some(blob_path) = resolve_blob_path(oci_dir, digest) else {
        findings.push(format!("{context}: invalid digest format {:?}", digest));
        return;
    };
    if !blob_path.is_file() {
        findings.push(format!(
            "{context}: blob {digest} not found at {}",
            blob_path.display()
        ));
        return;
    }
    match std::fs::metadata(&blob_path) {
        Ok(meta) => {
            if meta.len() != expected_size {
                findings.push(format!(
                    "{context}: blob {digest} size mismatch: expected {expected_size} bytes, found {} bytes",
                    meta.len()
                ));
            }
        }
        Err(e) => {
            findings.push(format!(
                "{context}: failed to read metadata for blob {}: {e}",
                blob_path.display()
            ));
        }
    }
}

/// Validates an OCI image layout directory for Merkle descriptor closure.
fn check_oci_layout(oci_dir: &Path, findings: &mut Vec<String>) {
    let layout_path = oci_dir.join("oci-layout");
    match std::fs::read_to_string(&layout_path) {
        Ok(text) => match serde_json::from_str::<serde_json::Value>(&text) {
            Ok(val) => {
                let version = val.get("imageLayoutVersion").and_then(|v| v.as_str());
                match version {
                    Some(v) if !v.trim().is_empty() => {}
                    Some(_) => findings.push(format!(
                        "{}: 'imageLayoutVersion' is empty",
                        layout_path.display()
                    )),
                    None => findings.push(format!(
                        "{}: missing 'imageLayoutVersion' in oci-layout",
                        layout_path.display()
                    )),
                }
            }
            Err(e) => findings.push(format!(
                "{}: failed to parse oci-layout as JSON: {e}",
                layout_path.display()
            )),
        },
        Err(e) => findings.push(format!(
            "{}: failed to read oci-layout: {e}",
            layout_path.display()
        )),
    }

    let index_path = oci_dir.join("index.json");
    if !index_path.is_file() {
        findings.push(format!(
            "{}: missing index.json in OCI layout",
            oci_dir.display()
        ));
        return;
    }

    let index_val = match std::fs::read_to_string(&index_path) {
        Ok(text) => match serde_json::from_str::<serde_json::Value>(&text) {
            Ok(v) => v,
            Err(e) => {
                findings.push(format!(
                    "{}: failed to parse index.json as JSON: {e}",
                    index_path.display()
                ));
                return;
            }
        },
        Err(e) => {
            findings.push(format!(
                "{}: failed to read index.json: {e}",
                index_path.display()
            ));
            return;
        }
    };

    let manifests = match index_val.get("manifests").and_then(|m| m.as_array()) {
        Some(m) if !m.is_empty() => m,
        Some(_) => {
            findings.push(format!(
                "{}: 'manifests' array is empty in index.json",
                index_path.display()
            ));
            return;
        }
        None => {
            findings.push(format!(
                "{}: missing 'manifests' array in index.json",
                index_path.display()
            ));
            return;
        }
    };

    for (m_idx, manifest_desc) in manifests.iter().enumerate() {
        let Some(digest) = manifest_desc.get("digest").and_then(|d| d.as_str()) else {
            findings.push(format!(
                "{}: manifests[{m_idx}] missing string 'digest'",
                index_path.display()
            ));
            continue;
        };

        let Some(expected_size) = manifest_desc.get("size").and_then(|s| s.as_u64()) else {
            findings.push(format!(
                "{}: manifests[{m_idx}] missing integer 'size'",
                index_path.display()
            ));
            continue;
        };

        let Some(manifest_blob_path) = resolve_blob_path(oci_dir, digest) else {
            findings.push(format!(
                "{}: manifests[{m_idx}] invalid digest format {:?}",
                index_path.display(),
                digest
            ));
            continue;
        };

        if !manifest_blob_path.is_file() {
            findings.push(format!(
                "{}: manifest blob {} not found at {}",
                index_path.display(),
                digest,
                manifest_blob_path.display()
            ));
            continue;
        }

        match std::fs::metadata(&manifest_blob_path) {
            Ok(meta) => {
                if meta.len() != expected_size {
                    findings.push(format!(
                        "{}: manifest blob {} size mismatch: expected {} bytes, found {} bytes",
                        index_path.display(),
                        digest,
                        expected_size,
                        meta.len()
                    ));
                }
            }
            Err(e) => {
                findings.push(format!(
                    "{}: failed to read metadata for manifest blob {}: {e}",
                    index_path.display(),
                    manifest_blob_path.display()
                ));
                continue;
            }
        }

        // Read manifest JSON and verify each layer and config blob
        let manifest_json = match std::fs::read_to_string(&manifest_blob_path) {
            Ok(text) => match serde_json::from_str::<serde_json::Value>(&text) {
                Ok(v) => v,
                Err(e) => {
                    findings.push(format!(
                        "{}: failed to parse manifest JSON at {}: {e}",
                        index_path.display(),
                        manifest_blob_path.display()
                    ));
                    continue;
                }
            },
            Err(e) => {
                findings.push(format!(
                    "{}: failed to read manifest JSON at {}: {e}",
                    index_path.display(),
                    manifest_blob_path.display()
                ));
                continue;
            }
        };

        // Config blob verification
        if let Some(config_desc) = manifest_json.get("config") {
            verify_blob_descriptor(
                oci_dir,
                config_desc,
                &format!("manifest {digest} config"),
                findings,
            );
        }

        // Layer blobs verification
        if let Some(layers) = manifest_json.get("layers").and_then(|l| l.as_array()) {
            for (l_idx, layer_desc) in layers.iter().enumerate() {
                verify_blob_descriptor(
                    oci_dir,
                    layer_desc,
                    &format!("manifest {digest} layer[{l_idx}]"),
                    findings,
                );
            }
        }

        // Nested index manifests verification (if present)
        if let Some(nested_manifests) = manifest_json.get("manifests").and_then(|m| m.as_array()) {
            for (n_idx, n_desc) in nested_manifests.iter().enumerate() {
                verify_blob_descriptor(
                    oci_dir,
                    n_desc,
                    &format!("nested index manifest[{n_idx}]"),
                    findings,
                );
            }
        }
    }
}

pub fn check(root: &Path) -> Report {
    if !root.is_dir() {
        return cannot_run(format!(
            "root directory {} is not a directory",
            root.display()
        ));
    }

    let mut findings = Vec::new();

    // a) OpenAI Chat SFT format validation
    let sft_path = root.join("var/lib/mios/training/sft.jsonl");
    if sft_path.is_file() {
        check_sft(&sft_path, &mut findings);
    } else {
        findings.push(format!(
            "{}: SFT training dataset file is missing",
            sft_path.display()
        ));
    }

    // b) OpenAI Preference DPO format validation
    let dpo_path = root.join("var/lib/mios/training/dpo.jsonl");
    if dpo_path.is_file() {
        check_dpo(&dpo_path, &mut findings);
    } else {
        findings.push(format!(
            "{}: DPO training dataset file is missing",
            dpo_path.display()
        ));
    }

    // c) Non-executing safe weights deserialization
    let training_dir = root.join("var/lib/mios/training");
    if training_dir.is_dir() {
        scan_weights(&training_dir, &mut findings);
    }
    let models_dir = root.join("models");
    if models_dir.is_dir() {
        scan_weights(&models_dir, &mut findings);
    }

    // e) OCI Merkle Descriptor Closure
    let oci_layouts = find_oci_layout_dirs(root);
    for oci_dir in oci_layouts {
        check_oci_layout(&oci_dir, &mut findings);
    }

    let ok = findings.is_empty();
    let summary = if ok {
        "all AI artifacts conform to schema, safe deserialization, and OCI descriptor closure"
            .to_string()
    } else {
        format!("{} artifact violation(s) found", findings.len())
    };

    Report {
        check: CHECK.to_string(),
        ok,
        could_not_run: None,
        summary,
        findings,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn setup_valid_workspace(root: &Path) {
        let training = root.join("var/lib/mios/training");
        std::fs::create_dir_all(&training).unwrap();
        std::fs::write(
            training.join("sft.jsonl"),
            r#"{"messages":[{"role":"system","content":"sys prompt"},{"role":"user","content":"user question"},{"role":"assistant","content":"helpful response"}]}"#,
        )
        .unwrap();
        std::fs::write(
            training.join("dpo.jsonl"),
            r#"{"input":{"messages":[{"role":"system","content":"sys prompt"},{"role":"user","content":"user question"}]},"preferred_output":[{"role":"assistant","content":"preferred response"}],"non_preferred_output":[{"role":"assistant","content":"inferior response"}]}"#,
        )
        .unwrap();
    }

    #[test]
    fn test_clean_training_datasets() {
        let repo_root = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..");
        let report = check(&repo_root);
        assert!(
            report.ok,
            "real repository should pass artifact verification, but findings were:\n{:#?}",
            report.findings
        );
        assert!(report.findings.is_empty());
        assert_eq!(
            report.summary,
            "all AI artifacts conform to schema, safe deserialization, and OCI descriptor closure"
        );
    }

    #[test]
    fn test_sft_missing_messages_fails() {
        let tmp = tempfile::tempdir().unwrap();
        setup_valid_workspace(tmp.path());
        let sft_path = tmp.path().join("var/lib/mios/training/sft.jsonl");
        std::fs::write(&sft_path, r#"{"role":"user","content":"no messages array"}"#).unwrap();
        let report = check(tmp.path());
        assert!(!report.ok);
        assert!(report
            .findings
            .iter()
            .any(|f| f.contains("missing or invalid 'messages' array")));
    }

    #[test]
    fn test_sft_invalid_role_fails() {
        let tmp = tempfile::tempdir().unwrap();
        setup_valid_workspace(tmp.path());
        let sft_path = tmp.path().join("var/lib/mios/training/sft.jsonl");
        std::fs::write(
            &sft_path,
            r#"{"messages":[{"role":"operator","content":"hello"}]}"#,
        )
        .unwrap();
        let report = check(tmp.path());
        assert!(!report.ok);
        assert!(report
            .findings
            .iter()
            .any(|f| f.contains("invalid role")));
    }

    #[test]
    fn test_dpo_identical_outputs_fails() {
        let tmp = tempfile::tempdir().unwrap();
        setup_valid_workspace(tmp.path());
        let dpo_path = tmp.path().join("var/lib/mios/training/dpo.jsonl");
        std::fs::write(
            &dpo_path,
            r#"{"input":{"messages":[{"role":"user","content":"q"}]},"preferred_output":[{"role":"assistant","content":"same answer"}],"non_preferred_output":[{"role":"assistant","content":"same answer"}]}"#,
        )
        .unwrap();
        let report = check(tmp.path());
        assert!(!report.ok);
        assert!(report
            .findings
            .iter()
            .any(|f| f.contains("identical")));
    }

    #[test]
    fn test_pickle_file_rejected() {
        let tmp = tempfile::tempdir().unwrap();
        setup_valid_workspace(tmp.path());
        let models_dir = tmp.path().join("models");
        std::fs::create_dir_all(&models_dir).unwrap();
        std::fs::write(models_dir.join("weights.pickle"), b"pickle bytecode").unwrap();
        let report = check(tmp.path());
        assert!(!report.ok);
        assert!(report
            .findings
            .iter()
            .any(|f| f.contains(".pickle")));
    }

    #[test]
    fn test_secret_token_rejected() {
        let tmp = tempfile::tempdir().unwrap();
        setup_valid_workspace(tmp.path());
        let sft_path = tmp.path().join("var/lib/mios/training/sft.jsonl");
        std::fs::write(
            &sft_path,
            r#"{"messages":[{"role":"user","content":"my token is ghp_1234567890abcdef"},{"role":"assistant","content":"redacted"}]}"#,
        )
        .unwrap();
        let report = check(tmp.path());
        assert!(!report.ok);
        assert!(report
            .findings
            .iter()
            .any(|f| f.contains("forbidden secret or private token")));
    }

    #[test]
    fn test_oci_missing_blob_fails() {
        let tmp = tempfile::tempdir().unwrap();
        setup_valid_workspace(tmp.path());
        let oci_dir = tmp.path().join("artifacts/modelkit");
        std::fs::create_dir_all(&oci_dir).unwrap();
        std::fs::write(
            oci_dir.join("oci-layout"),
            r#"{"imageLayoutVersion": "1.0.0"}"#,
        )
        .unwrap();
        std::fs::write(
            oci_dir.join("index.json"),
            r#"{
                "schemaVersion": 2,
                "manifests": [
                    {
                        "mediaType": "application/vnd.oci.image.manifest.v1+json",
                        "digest": "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                        "size": 123
                    }
                ]
            }"#,
        )
        .unwrap();
        // The blob sha256:ba781... does not exist under oci_dir/blobs/sha256/
        let report = check(tmp.path());
        assert!(!report.ok);
        assert!(report
            .findings
            .iter()
            .any(|f| f.contains("manifest blob") && f.contains("not found")));
    }

    #[test]
    fn test_gguf_validation() {
        let tmp = tempfile::tempdir().unwrap();
        setup_valid_workspace(tmp.path());
        let models_dir = tmp.path().join("models");
        std::fs::create_dir_all(&models_dir).unwrap();

        // Invalid GGUF header
        let bad_gguf = models_dir.join("bad.gguf");
        std::fs::write(&bad_gguf, b"NOPE_NOT_GGUF").unwrap();
        let report = check(tmp.path());
        assert!(!report.ok);
        assert!(report
            .findings
            .iter()
            .any(|f| f.contains("invalid GGUF magic header")));

        // Valid GGUF header
        std::fs::write(&bad_gguf, b"GGUF\x03\x00\x00\x00").unwrap();
        let report2 = check(tmp.path());
        assert!(report2.ok);
    }

    #[test]
    fn test_safetensors_validation() {
        let tmp = tempfile::tempdir().unwrap();
        setup_valid_workspace(tmp.path());
        let models_dir = tmp.path().join("models");
        std::fs::create_dir_all(&models_dir).unwrap();

        // Safetensors too short (< 8 bytes)
        let st = models_dir.join("model.safetensors");
        std::fs::write(&st, b"short").unwrap();
        let report = check(tmp.path());
        assert!(!report.ok);
        assert!(report.findings.iter().any(|f| f.contains("less than 8 bytes")));

        // Valid safetensors: 8 byte header length + JSON header
        let header = b"{}";
        let header_len = (header.len() as u64).to_le_bytes();
        let mut valid_bytes = Vec::new();
        valid_bytes.extend_from_slice(&header_len);
        valid_bytes.extend_from_slice(header);
        std::fs::write(&st, &valid_bytes).unwrap();
        let report2 = check(tmp.path());
        assert!(report2.ok);
    }

    #[test]
    fn test_oci_valid_closure() {
        let tmp = tempfile::tempdir().unwrap();
        setup_valid_workspace(tmp.path());
        let oci_dir = tmp.path().join("artifacts/modelkit");
        let blobs_dir = oci_dir.join("blobs/sha256");
        std::fs::create_dir_all(&blobs_dir).unwrap();

        std::fs::write(
            oci_dir.join("oci-layout"),
            r#"{"imageLayoutVersion": "1.0.0"}"#,
        )
        .unwrap();

        // Layer blob: "dummy layer" (11 bytes)
        let layer_bytes = b"dummy layer";
        let layer_hash = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
        std::fs::write(blobs_dir.join(layer_hash), layer_bytes).unwrap();

        // Config blob: "{}" (2 bytes)
        let cfg_bytes = b"{}";
        let cfg_hash = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789";
        std::fs::write(blobs_dir.join(cfg_hash), cfg_bytes).unwrap();

        // Manifest blob
        let manifest_json = format!(
            r#"{{
                "schemaVersion": 2,
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "config": {{
                    "mediaType": "application/vnd.oci.image.config.v1+json",
                    "digest": "sha256:{cfg_hash}",
                    "size": {}
                }},
                "layers": [
                    {{
                        "mediaType": "application/vnd.oci.image.layer.v1.tar",
                        "digest": "sha256:{layer_hash}",
                        "size": {}
                    }}
                ]
            }}"#,
            cfg_bytes.len(),
            layer_bytes.len()
        );
        let manifest_bytes = manifest_json.as_bytes();
        let manifest_hash = "1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff";
        std::fs::write(blobs_dir.join(manifest_hash), manifest_bytes).unwrap();

        // index.json
        let index_json = format!(
            r#"{{
                "schemaVersion": 2,
                "manifests": [
                    {{
                        "mediaType": "application/vnd.oci.image.manifest.v1+json",
                        "digest": "sha256:{manifest_hash}",
                        "size": {}
                    }}
                ]
            }}"#,
            manifest_bytes.len()
        );
        std::fs::write(oci_dir.join("index.json"), index_json).unwrap();

        let report = check(tmp.path());
        assert!(report.ok, "findings: {:#?}", report.findings);
    }
}
