// AI-hint: Native comment lexer for MiOS -- hot-path Rust lexer matching mios_comments.py.
use clap::Parser;
use regex::Regex;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;

#[derive(Parser, Debug)]
#[command(author, version, about = "Native comment lexer for MiOS", long_about = None)]
struct Args {
    /// File to lex
    #[arg(short, long)]
    file: Option<String>,

    /// Positional file argument
    path: Option<String>,

    /// Check that git diff against base revision modifies comments only
    #[arg(long)]
    check_diff: Option<Option<String>>,

    /// Compare two files directly to prove identical non-comment token streams
    #[arg(long, num_args = 2)]
    diff_files: Option<Vec<String>>,
}

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct Block {
    pub path: String,
    pub start_line: usize,
    pub end_line: usize,
    pub kind: String,
    pub style: String,
    pub text: String,
    pub norm: String,
    pub sha12: String,
    pub lines: usize,
    pub words: usize,
    pub attach: String,
    pub anchor_code: String,
    pub in_header_block: bool,
    #[serde(default)]
    pub cls: String,
    #[serde(default)]
    pub reason: String,
    #[serde(default)]
    pub stale: bool,
    #[serde(default, rename = "as_")]
    pub as_: String,
}

fn style_for(path: &str) -> &'static str {
    let lower = path.to_lowercase();
    if lower.ends_with(".py")
        || lower.ends_with(".sh")
        || lower.ends_with(".bash")
        || lower.ends_with(".toml")
        || lower.ends_with(".yml")
        || lower.ends_with(".yaml")
        || lower.ends_with(".ps1")
        || lower.ends_with(".psm1")
        || lower.ends_with(".service")
        || lower.ends_with(".container")
        || lower.ends_with(".timer")
        || lower.ends_with(".socket")
        || lower.ends_with(".target")
        || lower.ends_with(".conf")
        || lower.ends_with(".nft")
        || lower.ends_with(".cfg")
    {
        "#"
    } else if lower.ends_with(".rs")
        || lower.ends_with(".go")
        || lower.ends_with(".c")
        || lower.ends_with(".h")
        || lower.ends_with(".cs")
        || lower.ends_with(".ts")
        || lower.ends_with(".js")
        || lower.ends_with(".tsx")
        || lower.ends_with(".mjs")
    {
        "//"
    } else if lower.ends_with(".md") || lower.ends_with(".html") || lower.ends_with(".xml") {
        "<!--"
    } else {
        "#"
    }
}

fn strip_line(line: &str) -> String {
    let re_marker = Regex::new(r"^\s*(?:#+|//+|;+|--|<!--|\*|/\*)\s?").unwrap();
    let re_end = Regex::new(r"\s*(?:-->|\*/)\s*$").unwrap();
    let s1 = re_marker.replace(line, "");
    let s2 = re_end.replace(&s1, "");
    s2.trim_end().to_string()
}

/// Where a block sits: grouped so make_block stays inside clippy's
/// seven-argument limit without suppressing the lint.
struct Span<'a> {
    path: &'a str,
    start: usize,
    end: usize,
}

fn make_block(
    at: Span<'_>,
    kind: &str,
    style: &str,
    body_lines: &[String],
    attach: &str,
    anchor: &str,
    in_header: bool,
) -> Block {
    let text = body_lines.join("\n");
    let ws_re = Regex::new(r"\s+").unwrap();
    let norm = ws_re
        .replace_all(&text.to_lowercase(), " ")
        .trim()
        .to_string();

    let mut hasher = Sha256::new();
    hasher.update(norm.as_bytes());
    let hash_hex = format!("{:x}", hasher.finalize());
    let sha12 = hash_hex[..12].to_string();

    let word_re = Regex::new(r"[A-Za-z0-9_][A-Za-z0-9_./:-]*").unwrap();
    let words = word_re.find_iter(&text).count();

    Block {
        path: at.path.to_string(),
        start_line: at.start,
        end_line: at.end,
        kind: kind.to_string(),
        style: style.to_string(),
        text,
        norm,
        sha12,
        lines: body_lines.len(),
        words,
        attach: attach.to_string(),
        anchor_code: anchor.to_string(),
        in_header_block: in_header,
        cls: String::new(),
        reason: String::new(),
        stale: false,
        as_: String::new(),
    }
}

fn lex_generic(path: &str, src: &str, style: &str) -> Vec<Block> {
    let mut out = Vec::new();
    let lines: Vec<&str> = src.lines().collect();
    let mut run: Vec<String> = Vec::new();
    let mut run_start = 0;
    let mut in_block = false;
    let mut block_start = 0;
    let mut block_lines: Vec<String> = Vec::new();

    let marker_re = Regex::new(r"^\s*(?:#+|//+|;+|--|<!--|\*|/\*)\s?").unwrap();

    let flush = |out: &mut Vec<Block>, run: &mut Vec<String>, start: usize, end: usize| {
        if !run.is_empty() {
            let text = run.join("\n");
            let attach = if start <= 3 { "file-header" } else { "orphan" };
            let in_header = start <= 3 || text.contains("AI-hint");
            out.push(make_block(
                Span { path, start, end },
                "blockcomment",
                style,
                run,
                attach,
                "",
                in_header,
            ));
            run.clear();
        }
    };

    for (idx, &raw) in lines.iter().enumerate() {
        let i = idx + 1;
        let s = raw.trim();

        if style == "<!--" {
            if !in_block && s.starts_with("<!--") {
                in_block = true;
                block_start = i;
                block_lines = vec![strip_line(raw)];
                if s.contains("-->") {
                    in_block = false;
                    let in_hdr = i <= 3 || raw.contains("AI-hint");
                    out.push(make_block(
                        Span {
                            path,
                            start: block_start,
                            end: i,
                        },
                        "blockcomment",
                        style,
                        &block_lines,
                        if i <= 3 { "file-header" } else { "orphan" },
                        "",
                        in_hdr,
                    ));
                }
                continue;
            }
            if in_block {
                block_lines.push(strip_line(raw));
                if s.contains("-->") {
                    in_block = false;
                    let in_hdr =
                        block_start <= 3 || block_lines.iter().any(|x| x.contains("AI-hint"));
                    out.push(make_block(
                        Span {
                            path,
                            start: block_start,
                            end: i,
                        },
                        "blockcomment",
                        style,
                        &block_lines,
                        if block_start <= 3 {
                            "file-header"
                        } else {
                            "orphan"
                        },
                        "",
                        in_hdr,
                    ));
                }
                continue;
            }
            continue;
        }

        if !s.is_empty() && marker_re.is_match(raw) && raw.trim_start().starts_with(style) {
            if run.is_empty() {
                run_start = i;
            }
            run.push(strip_line(raw));
            continue;
        }

        if (style == "#" || style == "//")
            && raw.contains(style)
            && !raw.trim_start().starts_with(style)
        {
            if let Some(pos) = raw.find(style) {
                if pos > 0 && !raw[..pos].trim().is_empty() {
                    flush(&mut out, &mut run, run_start, i - 1);
                    out.push(make_block(
                        Span {
                            path,
                            start: i,
                            end: i,
                        },
                        "inline",
                        style,
                        &[strip_line(&raw[pos..])],
                        "inline",
                        raw[..pos].trim(),
                        false,
                    ));
                    continue;
                }
            }
        }

        flush(&mut out, &mut run, run_start, if i > 0 { i - 1 } else { 0 });
    }
    flush(&mut out, &mut run, run_start, lines.len());

    out
}

pub fn lex_file(path: &str) -> Vec<Block> {
    let content = match fs::read_to_string(path) {
        Ok(c) => c,
        Err(_) => return Vec::new(),
    };
    let src = content.replace("\r\n", "\n");
    let style = style_for(path);
    lex_generic(path, &src, style)
}

/// Strips comments and docstrings from source text, returning normalized non-comment lines.
pub fn strip_non_code(path: &str, src: &str) -> Vec<String> {
    let lower = path.to_lowercase();
    let is_py = lower.ends_with(".py");
    let is_rs = lower.ends_with(".rs")
        || lower.ends_with(".go")
        || lower.ends_with(".c")
        || lower.ends_with(".h")
        || lower.ends_with(".cs")
        || lower.ends_with(".ts")
        || lower.ends_with(".js");
    let is_md = lower.ends_with(".md") || lower.ends_with(".html");

    let style = style_for(path);
    let lines: Vec<&str> = src.lines().collect();
    let mut out: Vec<String> = Vec::new();
    let mut in_multiline_comment = false;
    let mut in_py_docstring = false;
    let mut py_docstring_delim = "";

    for (idx, &line) in lines.iter().enumerate() {
        let trimmed = line.trim();

        // Python docstrings
        if is_py {
            if in_py_docstring {
                if trimmed.contains(py_docstring_delim) {
                    in_py_docstring = false;
                }
                continue;
            }
            if let Some(rest) = trimmed.strip_prefix("\"\"\"") {
                if !rest.is_empty() && !rest.contains("\"\"\"") {
                    in_py_docstring = true;
                    py_docstring_delim = "\"\"\"";
                }
                continue;
            } else if let Some(rest) = trimmed.strip_prefix("'''") {
                if !rest.is_empty() && !rest.contains("'''") {
                    in_py_docstring = true;
                    py_docstring_delim = "'''";
                }
                continue;
            }
        }

        // HTML / Markdown <!-- -->
        if is_md || style == "<!--" {
            if in_multiline_comment {
                if trimmed.contains("-->") {
                    in_multiline_comment = false;
                }
                continue;
            }
            if trimmed.starts_with("<!--") {
                if !trimmed.contains("-->") {
                    in_multiline_comment = true;
                }
                continue;
            }
        }

        // C / Rust style /* */
        if is_rs {
            if in_multiline_comment {
                if trimmed.contains("*/") {
                    in_multiline_comment = false;
                }
                continue;
            }
            if trimmed.starts_with("/*") {
                if !trimmed.contains("*/") {
                    in_multiline_comment = true;
                }
                continue;
            }
        }

        // Full line comment
        if trimmed.starts_with(style) {
            // Keep shebang line
            if idx == 0 && trimmed.starts_with("#!") {
                out.push(line.trim_end().to_string());
            }
            continue;
        }

        if trimmed.is_empty() {
            continue;
        }

        // Inline comment stripping
        if (style == "#" || style == "//") && line.contains(style) {
            let mut in_quote = false;
            let mut quote_char = ' ';
            let mut cut_pos = None;
            let chars: Vec<char> = line.chars().collect();
            let mut i = 0;
            while i < chars.len() {
                let c = chars[i];
                if (c == '"' || c == '\'') && (i == 0 || chars[i - 1] != '\\') {
                    if in_quote && c == quote_char {
                        in_quote = false;
                    } else if !in_quote {
                        in_quote = true;
                        quote_char = c;
                    }
                } else if !in_quote {
                    let hash = style == "#" && c == '#';
                    let slashes =
                        style == "//" && c == '/' && i + 1 < chars.len() && chars[i + 1] == '/';
                    if hash || slashes {
                        cut_pos = Some(i);
                        break;
                    }
                }
                i += 1;
            }
            if let Some(pos) = cut_pos {
                let code_part = line[..pos].trim_end();
                if !code_part.trim().is_empty() {
                    out.push(code_part.to_string());
                }
                continue;
            }
        }

        out.push(line.trim_end().to_string());
    }
    out
}

/// Checks whether the diff between old_src and new_src modifies comments only.
pub fn is_comment_only_diff(path: &str, old_src: &str, new_src: &str) -> (bool, Option<String>) {
    let old_tokens = strip_non_code(path, old_src);
    let new_tokens = strip_non_code(path, new_src);

    if old_tokens == new_tokens {
        return (true, None);
    }

    let max_len = old_tokens.len().max(new_tokens.len());
    for i in 0..max_len {
        let old_line = old_tokens.get(i).map(|s| s.as_str()).unwrap_or("<EOF>");
        let new_line = new_tokens.get(i).map(|s| s.as_str()).unwrap_or("<EOF>");
        if old_line != new_line {
            return (
                false,
                Some(format!(
                    "line {}: expected {:?}, found {:?}",
                    i + 1,
                    old_line,
                    new_line
                )),
            );
        }
    }
    (
        false,
        Some("non-comment token stream length mismatch".to_string()),
    )
}

/// Runs comment-only diff check against git base ref.
pub fn check_git_diff(root: &str, base: &str) -> (bool, Vec<String>) {
    let output = match std::process::Command::new("git")
        .arg("-C")
        .arg(root)
        .arg("diff")
        .arg("--name-only")
        .arg(base)
        .output()
    {
        Ok(o) => o,
        Err(e) => return (false, vec![format!("failed to run git diff: {}", e)]),
    };

    if !output.status.success() {
        return (
            false,
            vec![format!(
                "git diff failed: {}",
                String::from_utf8_lossy(&output.stderr)
            )],
        );
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let files: Vec<&str> = stdout
        .lines()
        .map(|l| l.trim())
        .filter(|l| !l.is_empty())
        .collect();
    if files.is_empty() {
        return (true, Vec::new());
    }

    let mut violations = Vec::new();
    for file in files {
        let old_cmd = std::process::Command::new("git")
            .arg("-C")
            .arg(root)
            .arg("show")
            .arg(format!("{}:{}", base, file))
            .output();

        let old_content = match old_cmd {
            Ok(o) if o.status.success() => String::from_utf8_lossy(&o.stdout).to_string(),
            _ => continue, // New untracked or deleted file
        };

        let file_path = std::path::Path::new(root).join(file);
        let new_content = match fs::read_to_string(&file_path) {
            Ok(c) => c,
            Err(_) => continue,
        };

        let (ok, reason) = is_comment_only_diff(file, &old_content, &new_content);
        if !ok {
            violations.push(format!(
                "{}: modified executable code outside comments ({})",
                file,
                reason.unwrap_or_default()
            ));
        }
    }

    (violations.is_empty(), violations)
}

fn main() {
    let args = Args::parse();

    if let Some(ref diff_files) = args.diff_files {
        if diff_files.len() != 2 {
            eprintln!("Usage: mios-comment-lex --diff-files <FILE_A> <FILE_B>");
            std::process::exit(1);
        }
        let src_a = fs::read_to_string(&diff_files[0]).unwrap_or_default();
        let src_b = fs::read_to_string(&diff_files[1]).unwrap_or_default();
        let (ok, reason) = is_comment_only_diff(&diff_files[0], &src_a, &src_b);
        if ok {
            println!("[mios-comment-lex] diff-files clean: comment-only diff holds");
            std::process::exit(0);
        } else {
            eprintln!(
                "[mios-comment-lex] diff-files VIOLATION: {}",
                reason.unwrap_or_default()
            );
            std::process::exit(1);
        }
    }

    if let Some(ref base_opt) = args.check_diff {
        let base = base_opt.as_deref().unwrap_or("main");
        let (ok, violations) = check_git_diff(".", base);
        if ok {
            println!(
                "[mios-comment-lex] comment-only diff clean against {}",
                base
            );
            std::process::exit(0);
        } else {
            for v in &violations {
                eprintln!("[mios-comment-lex] VIOLATION: {}", v);
            }
            std::process::exit(1);
        }
    }

    let target = args.file.or(args.path);
    let path_str = match target {
        Some(p) => p,
        None => {
            eprintln!(
                "Usage: mios-comment-lex <FILE> | --check-diff [BASE] | --diff-files <A> <B>"
            );
            std::process::exit(1);
        }
    };

    let blocks = lex_file(&path_str);
    let json = serde_json::to_string_pretty(&blocks).unwrap();
    println!("{}", json);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_style_for() {
        assert_eq!(style_for("foo.py"), "#");
        assert_eq!(style_for("bar.rs"), "//");
        assert_eq!(style_for("baz.md"), "<!--");
    }

    #[test]
    fn test_strip_line() {
        assert_eq!(strip_line("# Hello world"), "Hello world");
        assert_eq!(strip_line("// Test line"), "Test line");
        assert_eq!(strip_line("<!-- Comment -->"), "Comment");
    }

    #[test]
    fn test_lex_generic() {
        let src = "# Header comment\n# Second line\n\nfn main() {}\n";
        let blocks = lex_generic("test.py", src, "#");
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].start_line, 1);
        assert_eq!(blocks[0].end_line, 2);
        assert_eq!(blocks[0].lines, 2);
    }

    #[test]
    fn test_comment_only_diff_positive_control() {
        let old_py = "#!/usr/bin/env python3\n# AI-hint: old hint\ndef foo():\n    \"\"\"Old doc.\"\"\"\n    return 42 # inline comment\n";
        let new_py = "#!/usr/bin/env python3\n# AI-hint: updated new hint\ndef foo():\n    \"\"\"New updated docstring.\"\"\"\n    return 42 # changed inline comment\n";
        let (ok, reason) = is_comment_only_diff("test.py", old_py, new_py);
        assert!(ok, "Expected positive control to pass: {:?}", reason);
    }

    #[test]
    fn test_comment_only_diff_negative_control_runtime_edit() {
        let old_py = "#!/usr/bin/env python3\ndef foo():\n    return 42\n";
        let new_py = "#!/usr/bin/env python3\n# AI-hint: added hint\ndef foo():\n    return 43\n";
        let (ok, reason) = is_comment_only_diff("test.py", old_py, new_py);
        assert!(
            !ok,
            "Expected negative control to fail when runtime code changes"
        );
        assert!(reason.unwrap().contains("return 42"));
    }
}
