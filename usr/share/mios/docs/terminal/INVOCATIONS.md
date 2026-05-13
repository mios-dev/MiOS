<!-- FHS: /usr/share/mios/docs/terminal/INVOCATIONS.md -->

# Terminal Invocation Grammar (`mios *` and `@*`)

## `mios` — Canonical CLI

```
mios [global-opts] <subcommand> [args...]

Subcommands:
  ask <prompt...>        Ask Hermes a question (alias: @).
  build [target]         Run Justfile target; default 'build'.
  status                 Show build, agent, kb, bootc, GPU status.
  agent <subcommand>     Manage agents:
    agent list             List installed agents.
    agent tools            Show tool schemas for active agent.
    agent endpoint         Show / set discovered endpoint.
    agent model            Show / set active model.
  repo <subcommand>      Manage the dual repos:
    repo use main|bootstrap
    repo status
    repo commit <message-file>
  kargs                  Print effective kernel args + kargs.d sources.
  packages <q>           Grep PACKAGES.md.
  bootc <subcommand>     Thin wrapper around 'bootc' (status, upgrade, switch).
  doctor                 Run invariant checks.
  help [subcommand]
```

## `@` — Shell-Position-Free Invocation

- **As widget**: at any prompt position, typing `@hello world<Enter>`
  invokes Hermes with `hello world`. Bash uses a `READLINE_LINE`
  rewrite via `bind -x`; zsh uses a ZLE widget. See
  `/etc/profile.d/mios-agent.sh`.
- **As binary**: `/usr/bin/@` is a real executable. Pipes work:

  ```sh
  cat error.log | @ "summarize this"
  ```

- **Escape hatch**: `\@foo` (leading backslash) is passed to the
  shell literally. The widget honors quoting: `'@foo'` is literal.

## Examples

```sh
mios ask "why did my build fail at phase 32?"
@why did the build fail
@ "produce a kargs.d snippet to add console=ttyS0"
mios build bib-qcow2
mios status --json | jq .agent
mios agent endpoint set http://ollama.lab:11434/v1
mios repo use bootstrap && mios repo status
```

## Quoting and special characters

| Input               | Effect                                        |
|---------------------|-----------------------------------------------|
| `@foo bar`          | Hermes called with `foo bar`.                 |
| `@'foo $X bar'`     | Hermes called with `foo $X bar` (literal).    |
| `@"foo $X bar"`     | Variable expansion happens, then Hermes.      |
| `\@foo`             | Shell literal (no widget rewrite).            |
| `echo @foo`         | `echo` runs; `@foo` is its argument.          |
| `cmd | @ "Q"`       | Pipes stdin into Hermes as context.           |
| `@@`                | Reserved — invokes default agent's `--help`.  |

## TTY vs non-TTY

- TTY → streaming SSE, ANSI colorized.
- Non-TTY (pipe / `>`) → buffered final response, no ANSI.

## Exit codes

| Code | Meaning                                     |
|------|---------------------------------------------|
| 0    | Success.                                    |
| 2    | Usage error (bad subcommand / missing arg). |
| 4    | No reachable endpoint.                      |
| 5    | Model unavailable on chosen endpoint.       |
| 6    | Tool execution failed.                      |
| 130  | SIGINT during stream (Ctrl-C).              |
