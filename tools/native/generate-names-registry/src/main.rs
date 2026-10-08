// AI-hint: Installed compatibility command; the names projection belongs to mios-gen.
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let root = match std::env::var_os("MIOS_DRIFT_ROOT") {
        Some(path) => std::path::PathBuf::from(path),
        None => std::env::current_dir()?,
    };
    mios_gen::names_registry::run(&root)
}
