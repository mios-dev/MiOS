# GEMINI.md

> Read by Gemini CLI on entry into this repo. Redirector stub.
> Canonical agent prompt: `/usr/share/mios/ai/system.md`.

## Behavior contract

1. Load `/usr/share/mios/ai/system.md` first.
2. Apply `/etc/mios/ai/system-prompt.md` as host-local override if present.
3. This file carries Gemini CLI-specific deltas only.

If `/usr/share/mios/ai/system.md` is unreachable, fall back to
`/system-prompt.md` in the repo root.

## Tool-specific deltas (Gemini CLI only)

- **Sandbox model:** Gemini CLI typically operates from the working directory
  as the sandbox root. On a MiOS-DEV host, `cwd` should be `/`. Do NOT treat
  `/` as a "dangerous" path to avoid; it is the canonical repo root.
- **Tool calls:** Use `read_file`, `list_directory`, `glob`, `search_file_content`
  for read-only inspection. `write_file`, `replace`, `run_shell_command` are
  mutating — confirm with the user before each invocation that touches a
  whitelisted overlay path or the live system.
- **Memory:** `/memory add` and `/memory show` write to
  `/var/lib/mios/ai/memory/gemini-cli/`. The format must conform to
  `/usr/share/mios/ai/system.md` §12 (one fact per record, file:line citation,
  immutable, supersedes-by-reference).
- **YOLO mode:** Even when `--yolo` is enabled, never `git push`, `bootc upgrade`,
  `dnf install`, or destructive shell commands without explicit operator turn.

## Sanitization reminder

Per `/usr/share/mios/ai/system.md` §6, all persisted artifacts are sanitized.
Specifically for Gemini CLI: do not write the strings "Gemini", "Google",
"Bard", "DeepMind", or any vendor brand into pushed paths. Vendor brands stay
in your runtime context only; persisted artifacts are vendor-neutral.
