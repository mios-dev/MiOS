// AI-hint: Crate root for mios-resolver -- the native layered mios.toml resolver that subsumes mios_toml.py / userenv.sh / globals.ps1.
// AI-related: usr/lib/mios/mios_toml.py, usr/lib/mios/userenv.sh, tools/native/mios-ssot-walk
pub mod aliases;
pub mod db_overlay;
pub mod emit;
pub mod emit_install_env;
pub mod emit_json;
pub mod emit_ps;
pub mod emit_shell;
pub mod error;
pub mod expand;
pub mod layers;
pub mod merge;
pub mod model;
pub mod palette;
pub mod ports;
pub mod walk;

use crate::error::ResolverError;
use crate::model::MiosModel;
use std::collections::BTreeMap;
use std::path::Path;
use toml::Value;

pub fn load_model(root_dir: Option<&Path>) -> Result<MiosModel, ResolverError> {
    let fig = layers::create_figment(root_dir);
    fig.extract::<MiosModel>()
        .map_err(|e| ResolverError::TypeShape { msg: e.to_string() })
}

/// stack_offset = [ports].stack_id * 10000 -- the multi-stack port shift the
/// Python resolver applies in process_val(). Absent stack_id means no shift.
pub fn stack_offset_of(merged: &Value) -> i64 {
    merged
        .get("ports")
        .and_then(|p| p.get("stack_id"))
        .and_then(|v| {
            v.as_integer()
                .or_else(|| v.as_str().and_then(|s| s.parse::<i64>().ok()))
        })
        .map(|id| id * 10000)
        .unwrap_or(0)
}

/// The merged SSOT every emitter renders: all six tiers, the DB overlay when
/// active or forced, and [ports] derived from [ports.categories] last so an
/// override in any tier re-derives.
pub fn resolve_merged(root_dir: Option<&Path>, db_overlay: bool) -> Result<Value, ResolverError> {
    let mut merged = layers::create_figment(root_dir)
        .extract::<Value>()
        .map_err(|e| ResolverError::TypeShape { msg: e.to_string() })?;
    db_overlay::maybe_apply_db_overlay(&mut merged, db_overlay);
    ports::derive_ports(&mut merged);
    Ok(merged)
}

/// The resolved MIOS_* environment, ${MIOS_*} references expanded -- the same
/// values `mios-resolver --emit=json` prints. Native programs read the SSOT
/// through this at run time instead of carrying their own copies of it.
pub fn resolve_env(root_dir: Option<&Path>) -> Result<BTreeMap<String, String>, ResolverError> {
    let merged = resolve_merged(root_dir, false)?;
    let mut exports = emit::build_exports_map(&merged, stack_offset_of(&merged));
    emit::resolve_cross_references(&mut exports);
    Ok(exports)
}
