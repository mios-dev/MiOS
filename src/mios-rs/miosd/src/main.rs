// AI-hint: Entry point for the MiOS daemon native workspace (WS-LANG)
// AI-related: Containerfile, automation/98-drift-checks.sh

mod drift;

// AI-related: Containerfile, automation/98-drift-checks.sh

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "miosd")]
#[command(about = "MiOS native daemon and toolbox", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Run structural drift checks across the repository
    DriftCheck {
        /// Optional root directory to check
        #[arg(long)]
        root: Option<String>,
        /// Advisory mode (exit 0 on failure)
        #[arg(long)]
        soft: bool,
    },
    /// Scaffold a new file from a template
    Scaffold {
        /// Type of the template
        template_type: String,
        /// Name of the new file
        name: String,
    },
}

fn main() {
    let cli = Cli::parse();

    match &cli.command {
        Commands::DriftCheck { root, soft } => {
            let root_dir = root.as_deref().unwrap_or(".");
            drift::run_checks(root_dir, *soft);
        }
        Commands::Scaffold { template_type, name } => {
            println!("[miosd] Scaffolding {} as {}...", template_type, name);
            // TODO: Fold mios-new Python logic into this Rust command.
            println!("[miosd] (Stub) Scaffolding complete.");
        }
    }
}
