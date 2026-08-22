<!-- AI-hint: Chapter 56: Persistent Shell Sessions. Explains the SHELL-01 substrate that lets cwd, environment and history survive across agent turns. Covers the BEGIN/END nonce framing and the two spoofing properties it buys, why the marker is printed in two pieces, why the PTY echo and prompt must be silenced at the source, why tmux history-limit has to arrive through a config file, and the session-key rules that stop one chat reading another's shell. -->

# <a name="56_persistent_shell_sessions"></a>Chapter 56: Persistent Shell Sessions

> Part VI: The Local AI Plane of the [MiOS manual](../manual.md).

> Path Reference: `/usr/share/doc/mios/manual.md#56_persistent_shell_sessions`

#### Overview

Every shell call used to discard `cwd`, `env` and history, so an agent had to
re-establish its working state on every turn and could not run any workflow
whose steps depend on each other. SHELL-01 adds a bounded, reapable persistent
shell: one tmux session per chat, so

```
run_in_shell "cd /tmp && export FOO=bar"
run_in_shell "echo $PWD $FOO"      →  /tmp bar
```

The pure protocol is `usr/lib/mios/agent-pipe/mios_pipe/routing/pty.py` — no
subprocess, no tmux, no filesystem, so every branch is isolation-tested. The
runner `usr/libexec/mios/mios-shell-session` supplies the I/O. It ships **off**
(`[shell_session].enable = false`): a long-lived shell is state the agent
accumulates, and that should be a deliberate choice.

#### <a name="56_the_nonce_framing"></a>56.The Nonce Framing: The Nonce Framing

A command is sent wrapped between two sentinels carrying a per-command
128-bit nonce:

```
printf '%s%s\n' "__MIOS_PTY__" "<nonce>-BEGIN"
<the command>
printf '%s%s\n' "__MIOS_PTY__" "<nonce> $? $PWD"
```

The END marker is what reports completion, exit status and cwd. Two properties
follow, and both are tested:

* **Output cannot forge completion.** The nonce is minted per command and never
  appears in the command text, so a command that prints a marker-shaped line —
  or replays an older marker — does not read as *this* command finishing. Only a
  marker carrying the expected nonce counts.
* **Replayed scrollback cannot end a command early.** The *last* END marker for
  the nonce wins.

The BEGIN sentinel is not decoration: it bounds the body exactly, so the result
is the command's own output rather than a pane transcript trimmed by guesswork.

#### <a name="56_what_only_running_it_revealed"></a>56.What Only Running It Revealed: What Only Running It Revealed

The pure tests all passed against a protocol with three defects that only a real
tmux session exposed. Each is now fixed at the source and worth stating, because
each is the kind of thing that looks fine in a unit test forever.

**The marker matched its own echo.** A PTY echoes what is typed into it, so the
pane contained the framing line *before* the command ran. Searching for the
assembled marker found that echo, and the first command back reported a null
exit code — parsed out of the literal text `$?`. Printing the marker in **two
pieces** (`printf '%s%s'`) means the echoed line never contains an assembled
marker while the output line does.

**A command that killed the shell hung until the timeout.** `exit 42` ends the
session; `capture-pane` then fails forever and the poll loop spun for the full
budget. The loop now checks whether the session still exists when a capture
fails, and returns in a fraction of a second.

**Long output lost its head.** `capture-pane` can only return what the pane still
holds, and tmux keeps 2000 lines by default — so a 5,000-line command came back
tail-only, defeating the head-and-tail elision. `history-limit` cannot fix this
after the fact: tmux applies it only to panes created *after* it is set, and
`set-option -g` before the first session fails outright because no server exists
yet. It has to arrive as a **config file** passed with `tmux -f` on every
invocation.

The echo and the prompt are silenced at the source too — `stty -echo` and an
empty `PS1` on session creation — so a captured result is output, not a
transcript of the terminal.

#### <a name="56_session_isolation"></a>56.Session Isolation: Session Isolation

`session_key` turns an arbitrary chat id into a tmux name: unsafe characters
collapse to `-`, the result is prefixed so a MiOS session can never collide with
an operator's own tmux session, and it is length-capped. Two details matter more
than they look:

* A traversal or metacharacter id (`../../etc/passwd`, `a; rm -rf /`) cannot
  escape the namespace, and `session_path` inherits the same proofing.
* Length-capping **alone would let two long ids collide**, and one chat reading
  another's `cwd` and environment is precisely the risk this substrate
  introduces. A truncated key keeps a digest tail.

Output is bounded through the existing ACI normalizer — head and tail kept with
an elision marker between them — rather than raw-truncated. Idle sessions are
reaped by `mios-shell-session-gc.timer`; the reaper treats unparseable
bookkeeping as *not idle*, so a session is never killed on a bad timestamp.

#### <a name="56_shell_session_configuration"></a>56.Shell Session Configuration: Shell Session Configuration

| Key | Default | Meaning |
|---|---|---|
| `enable` | `false` | run the substrate at all |
| `socket_name` | `mios` | tmux `-L` namespace, off an operator's default socket |
| `state_dir` | `/var/lib/mios/shell-sessions` | per-session activity stamps + the generated tmux.conf |
| `idle_s` | `1800` | reap after this long with no command |
| `max_sessions` | `8` | hard cap on concurrent shells |
| `timeout_s` | `120` | per-command wall clock |
| `max_output_chars` / `max_output_lines` | `24000` / `400` | ACI elision budget |
| `history_limit` | `50000` | pane scrollback, so long output keeps its head |

The verb is `[verbs.shell_session]`, model name `run_in_shell`, permission
`write`, sandbox profile `baseline` — so it projects to the MCP, OpenAI and A2A
surfaces with no new dispatch code.
