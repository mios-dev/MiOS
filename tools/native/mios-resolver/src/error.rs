// AI-hint: Resolver error surface -- thiserror enum with miette diagnostics so a bad layer or value points at its mios.toml source.
// AI-related: usr/share/mios/mios.toml
use miette::Diagnostic;
use thiserror::Error;

#[derive(Error, Debug, Diagnostic)]
pub enum ResolverError {
    #[error("Failed to parse TOML layer at {path}: {source}")]
    #[diagnostic(
        code(mios_resolver::layer_parse),
        help("Check TOML syntax in layer file")
    )]
    LayerParse {
        path: String,
        #[source]
        source: toml::de::Error,
    },

    #[error("Type shape or schema mismatch: {msg}")]
    #[diagnostic(code(mios_resolver::type_shape))]
    TypeShape { msg: String },

    #[error("Missing expected configuration layer: {path}")]
    #[diagnostic(code(mios_resolver::missing_layer))]
    MissingLayer { path: String },
}
