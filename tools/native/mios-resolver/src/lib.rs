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
pub mod layers;
pub mod merge;
pub mod model;
pub mod palette;
pub mod ports;
pub mod walk;

use crate::error::ResolverError;
use crate::model::MiosModel;
use std::path::Path;

pub fn load_model(root_dir: Option<&Path>) -> Result<MiosModel, ResolverError> {
    let fig = layers::create_figment(root_dir);
    fig.extract::<MiosModel>().map_err(|e| ResolverError::TypeShape {
        msg: e.to_string(),
    })
}
