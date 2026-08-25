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

fn main() {
    let args = Args::parse();
    let target = args.file.or(args.path);

    let path_str = match target {
        Some(p) => p,
        None => {
            eprintln!("Usage: mios-comment-lex <FILE>");
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
}
