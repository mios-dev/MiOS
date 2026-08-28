// AI-hint: Shell completion generator for mios CLI.
// AI-related: usr/bin/mios

use super::dispatcher::KNOWN_VERBS;

pub struct CompletionGenerator;

impl CompletionGenerator {
    pub fn generate(shell: &str) -> String {
        match shell.to_lowercase().as_str() {
            "bash" => Self::generate_bash(),
            "zsh" => Self::generate_zsh(),
            "fish" => Self::generate_fish(),
            "powershell" | "pwsh" => Self::generate_powershell(),
            _ => Self::generate_bash(),
        }
    }

    fn verbs_space_separated() -> String {
        KNOWN_VERBS
            .iter()
            .map(|(v, _)| *v)
            .collect::<Vec<&str>>()
            .join(" ")
    }

    fn generate_bash() -> String {
        let verbs = Self::verbs_space_separated();
        format!(
            r#"# bash completion for mios
_mios() {{
    local cur prev words cword
    _init_completion || return

    local verbs="{}"

    if [ "$cword" -eq 1 ]; then
        COMPREPLY=( $(compgen -W "$verbs --help --no-tools --tools --generate-completion" -- "$cur") )
        return 0
    fi
}}
complete -F _mios mios
"#,
            verbs
        )
    }

    fn generate_zsh() -> String {
        let verbs = Self::verbs_space_separated();
        format!(
            r#"#compdef mios
_mios() {{
    local -a verbs
    verbs=({})
    _arguments '1: :($verbs)' '*: :_files'
}}
_mios "$@"
"#,
            verbs
        )
    }

    fn generate_fish() -> String {
        let mut out = String::from("# fish completion for mios\n");
        for (v, _) in KNOWN_VERBS {
            out.push_str(&format!(
                "complete -c mios -n '__fish_use_subcommand' -a '{}' -d 'MiOS verb {}'\n",
                v, v
            ));
        }
        out.push_str("complete -c mios -l generate-completion -d 'Generate shell completions'\n");
        out.push_str("complete -c mios -l help -s h -d 'Show help'\n");
        out
    }

    fn generate_powershell() -> String {
        let verbs = Self::verbs_space_separated();
        format!(
            r#"# PowerShell completion for mios
Register-ArgumentCompleter -Native -CommandName mios -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)
    $verbs = @({})
    $verbs | Where-Object {{ $_ -like "$wordToComplete*" }} | ForEach-Object {{
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }}
}}
"#,
            verbs
                .split_whitespace()
                .map(|v| format!("'{}'", v))
                .collect::<Vec<String>>()
                .join(", ")
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_completion_generation() {
        let bash = CompletionGenerator::generate("bash");
        assert!(bash.contains("complete -F _mios mios"));
        assert!(bash.contains("build"));
        assert!(bash.contains("dash"));

        let fish = CompletionGenerator::generate("fish");
        assert!(fish.contains("complete -c mios"));

        let pwsh = CompletionGenerator::generate("pwsh");
        assert!(pwsh.contains("Register-ArgumentCompleter"));
    }
}
