// AI-hint: Entry dispatcher for mios CLI.
// AI-related: usr/bin/mios

pub mod ai_fallback;
pub mod completions;
pub mod dispatcher;

use ai_fallback::AiFallback;
use completions::CompletionGenerator;
use dispatcher::CliDispatcher;

pub fn print_help() {
    eprintln!(
        "mios -- MiOS binary verb dispatcher + OpenAI agent CLI.\n\n\
        Verbs:\n\
          mios build                           run the MiOS OCI build pipeline\n\
          mios dash                            framed dashboard snapshot (services + telemetry)\n\
          mios mini                            compact framed static dashboard snapshot\n\
          mios mon (or monitor)                unified live TUI for system services and logs\n\
          mios config                          open the HTML configurator in your browser\n\
          mios code                            open code-server in your browser\n\
          mios ai                              open Open WebUI in your browser\n\
          mios ai clear                        wipe chats/jobs/kanban/DBs/RAG clean slate\n\
          mios xbox                            Xbox VM Secure Boot / XML repair\n\
          mios virt                            apply optimized VM config + CPU pinning\n\
          mios vfio                            configure GPU/USB passthrough\n\
          mios vfio-check                      report VFIO / IOMMU binding state\n\
          mios vfio-toggle                     interactive VFIO device selector\n\
          mios tune                            system-wide CPU isolation & latency tuning\n\
          mios summary                         quick ASCII system overview\n\
          mios profile                         interactive hardware/system profiler menu\n\
          mios assess                          comprehensive system capability report\n\
          mios theme                           sync bibata/GTK/Qt themes\n\
          mios dotfiles                        project the SSOT dotfiles to your LIVE HOME\n\
          mios new <type> <name>               scaffold a new file from templates\n\
          mios iommu                           pretty-print hardware IOMMU topology\n\
          mios iommu-groups                    list raw IOMMU groups and devices\n\
          mios env                             inspect layered MIOS_* environment\n\
          mios sync-env                        regenerate install.env from mios.toml\n\
          mios blade                           manage blade roles and activation capabilities\n\
          mios flatpaks                        manage system-wide Flatpaks\n\
          mios user                            initialize user space (dotfiles/XDG)\n\
          mios flight                          flight control hardware profile\n\
          mios models                          manage first-boot large models\n\
          mios update                          perform atomic bootc OS update\n\
          mios check                           run SSOT mios.toml type and schema validator\n\
          mios status                          report unified system and daemon status\n\
          mios logs                            tail unified miosd supervisor logs\n\
          mios backup                          trigger manual snapshot backup\n\
          mios help                            show this help\n\n\
        Options:\n\
          mios --generate-completion <shell>   emit shell completions (bash, zsh, fish, pwsh)\n\
          mios <prompt>                        send prompt to local MIOS_AI_ENDPOINT\n"
    );
}

pub fn dispatch(argv: Vec<String>) -> i32 {
    if argv.len() < 2 {
        print_help();
        return 1;
    }

    let first = &argv[1];

    if first == "-h" || first == "--help" || first == "help" {
        print_help();
        return 0;
    }

    if first == "--generate-completion" || first == "--completion" {
        let shell = argv.get(2).map(|s| s.as_str()).unwrap_or("bash");
        let script = CompletionGenerator::generate(shell);
        print!("{}", script);
        return 0;
    }

    // Special case: ai clear
    if first == "ai" && argv.len() >= 3 && argv[2] == "clear" {
        let clear_bin = "/usr/libexec/mios/mios-ai-clear";
        let resolved = CliDispatcher::resolve_target(clear_bin);
        return CliDispatcher::execute_verb(&[resolved.to_str().unwrap_or(clear_bin)], &argv[3..]);
    }

    if let Some(cmd_spec) = CliDispatcher::find_verb(first) {
        return CliDispatcher::execute_verb(cmd_spec, &argv[2..]);
    }

    // Unrecognized verb -> Treat as prompt for AI Fallback
    let prompt = argv[1..].join(" ");
    AiFallback::execute_prompt(&prompt)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dispatch_help() {
        let rc = dispatch(vec!["mios".into(), "--help".into()]);
        assert_eq!(rc, 0);
    }

    #[test]
    fn test_dispatch_completions() {
        let rc = dispatch(vec![
            "mios".into(),
            "--generate-completion".into(),
            "bash".into(),
        ]);
        assert_eq!(rc, 0);
    }
}
