// AI-hint: Streams the tar layers of an OCI layout (plain, gzip, zstd) and applies the artifact gate's weight rules to every weight file inside them.
// AI-related: src/mios-rs/mios-gate/src/artifact.rs, usr/share/doc/mios/adr/0027-dual-tier-oci-ai-artifacts.md

use crate::artifact::{check_weight_stream, is_weight_name};
use std::fs::File;
use std::io::Read;
use std::path::Path;

enum Codec {
    Plain,
    Gzip,
    Zstd,
}

/// The codec a layer media type names, `None` for a non-tar blob (a config,
/// a raw blob). OCI (`...tar+gzip`), Docker (`...tar.gzip`) and KitOps
/// (`...v1.tar+zstd`) spellings all end in the compression suffix.
fn codec(media_type: &str) -> Option<Result<Codec, ()>> {
    let m = media_type.to_ascii_lowercase();
    if !m.contains("tar") {
        return None;
    }
    Some(if m.ends_with("gzip") {
        Ok(Codec::Gzip)
    } else if m.ends_with("zstd") {
        Ok(Codec::Zstd)
    } else if m.ends_with("tar") {
        Ok(Codec::Plain)
    } else {
        Err(())
    })
}

/// Scans every weight file inside a verified layer blob. A tar layer that
/// cannot be decoded or read is a finding: an unscanned layer is not safe.
pub(crate) fn scan_layer(blob: &Path, media_type: &str, context: &str, findings: &mut Vec<String>) {
    let codec = match codec(media_type) {
        None => return,
        Some(Ok(c)) => c,
        Some(Err(())) => {
            findings.push(format!(
                "{context}: layer media type {media_type:?} uses an unsupported compression, so its contents were not scanned"
            ));
            return;
        }
    };
    let f = match File::open(blob) {
        Ok(f) => f,
        Err(e) => {
            findings.push(format!(
                "{context}: failed to open layer {}: {e}",
                blob.display()
            ));
            return;
        }
    };
    let reader: Box<dyn Read> = match codec {
        Codec::Plain => Box::new(f),
        Codec::Gzip => Box::new(flate2::read::GzDecoder::new(f)),
        Codec::Zstd => match ruzstd::decoding::StreamingDecoder::new(f) {
            Ok(d) => Box::new(d),
            Err(e) => {
                findings.push(format!("{context}: layer is not valid zstd: {e}"));
                return;
            }
        },
    };
    let mut archive = tar::Archive::new(reader);
    let entries = match archive.entries() {
        Ok(entries) => entries,
        Err(e) => {
            findings.push(format!("{context}: layer is not a readable tar: {e}"));
            return;
        }
    };
    for entry in entries {
        let mut entry = match entry {
            Ok(entry) => entry,
            Err(e) => {
                findings.push(format!("{context}: layer tar is truncated or corrupt: {e}"));
                return;
            }
        };
        if !entry.header().entry_type().is_file() {
            continue;
        }
        let path = match entry.path() {
            Ok(p) => p.to_string_lossy().into_owned(),
            Err(_) => continue,
        };
        let name = path.rsplit('/').next().unwrap_or_default().to_string();
        if !is_weight_name(&name) {
            continue;
        }
        let len = entry.size();
        check_weight_stream(
            &format!("{context} {path}"),
            &name,
            len,
            &mut entry,
            findings,
        );
    }
}
