// AI-hint: The probe report type and its two renderings: the human lines the shell script printed, and an OpenAI-format structured object.
// AI-related: src/mios-rs/mios-probe/src/main.rs, usr/share/doc/mios/adr/0021-rust-static-binary-consolidation.md

/// What a single probe concluded.
///
/// `NotApplicable` exists so a probe that cannot run on this platform SAYS so.
/// Folding it into `Ok` would be Skip-as-Pass: a Windows-only threshold would
/// read as satisfied on Linux.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    Ok,
    Warn,
    Fail,
    NotApplicable,
}

impl Verdict {
    fn tag(self) -> &'static str {
        match self {
            Verdict::Ok => "ok",
            Verdict::Warn => "warn",
            Verdict::Fail => "fail",
            Verdict::NotApplicable => "not_applicable",
        }
    }
}

pub struct Probe {
    pub key: String,
    pub verdict: Verdict,
    pub message: String,
}

pub struct Report {
    pub title: String,
    pub probes: Vec<Probe>,
    /// Set when the probe set could not run at all -- exit 2, never 0.
    pub could_not_run: Option<String>,
}

const GREEN: &str = "\x1b[0;32m";
const RED: &str = "\x1b[0;31m";
const YELLOW: &str = "\x1b[1;33m";
const NC: &str = "\x1b[0m";

impl Report {
    pub fn failures(&self) -> usize {
        self.probes
            .iter()
            .filter(|p| p.verdict == Verdict::Fail)
            .count()
    }

    pub fn code(&self) -> u8 {
        if self.could_not_run.is_some() {
            crate::EXIT_CANNOT_RUN
        } else if self.failures() > 0 {
            crate::EXIT_VIOLATIONS
        } else {
            crate::EXIT_CLEAN
        }
    }

    /// Byte-identical to the lines the retired shell probe printed, so its
    /// callers and their logs are unchanged by the port.
    pub fn render_text(&self, color: bool) -> String {
        let (g, r, y, n) = if color {
            (GREEN, RED, YELLOW, NC)
        } else {
            ("", "", "", "")
        };
        let mut out = String::new();
        if let Some(why) = &self.could_not_run {
            out.push_str(&format!("{r}[FAIL]{n} {why}\n"));
            return out;
        }
        out.push_str(&format!("{}\n", self.title));
        for p in &self.probes {
            let line = match p.verdict {
                Verdict::Ok => format!("{g}[OK]{n}  {}\n", p.message),
                Verdict::Warn => format!("{y}[WARN]{n} {}\n", p.message),
                Verdict::Fail => format!("{r}[FAIL]{n} {}\n", p.message),
                Verdict::NotApplicable => format!("{y}[N/A]{n}  {}\n", p.message),
            };
            out.push_str(&line);
        }
        let failures = self.failures();
        if failures > 0 {
            out.push('\n');
            out.push_str(&format!(
                "{r}[FAIL]{n} Pre-flight failed with {failures} error(s). Resolve above before building.\n"
            ));
        } else {
            out.push('\n');
            out.push_str(&format!("{g}[OK]{n}  All pre-flight checks passed.\n"));
        }
        out
    }

    /// OpenAI-format structured output, so the agent plane reads a verdict
    /// rather than parsing coloured text.
    pub fn render_json(&self) -> String {
        let probes: Vec<_> = self
            .probes
            .iter()
            .map(|p| {
                serde_json::json!({
                    "key": p.key,
                    "verdict": p.verdict.tag(),
                    "message": p.message,
                })
            })
            .collect();
        let value = serde_json::json!({
            "probe": "preflight",
            "status": if self.could_not_run.is_some() { "could_not_run" }
                      else if self.failures() > 0 { "failed" } else { "ready" },
            "summary": self.could_not_run.clone().unwrap_or_else(|| self.title.clone()),
            "probes": probes,
        });
        serde_json::to_string_pretty(&value).unwrap_or_else(|_| {
            String::from("{\"probe\":\"preflight\",\"status\":\"could_not_run\",\"probes\":[]}")
        })
    }
}
