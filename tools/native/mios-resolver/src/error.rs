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

    #[error("Invalid hex color format: '{value}' under [colors].{key}")]
    #[diagnostic(
        code(mios_resolver::invalid_color_hex),
        help("Colors must be valid 6-digit or 3-digit hex strings (e.g. #FFFFFF or #FFF)")
    )]
    InvalidColorHex { key: String, value: String },

    #[error("Invalid non-integer port specification under [ports].{key}: '{value}'")]
    #[diagnostic(
        code(mios_resolver::invalid_port),
        help("Port values must be valid 16-bit unsigned integers between 1 and 65535")
    )]
    InvalidPortValue { key: String, value: String },
}
