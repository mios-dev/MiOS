<!-- AI-hint: Chapter 57: PowerShell Object Flattening. Records why an object-returning cmdlet reached the model as a BLANK LINE rather than as noise, how a console-less runspace collapses every formatter column to zero width, and the four properties the OAI-03 wrapper has to hold at once: flat text, the caller's own error line numbers, an explicit exit that does not strand the format buffer, and a multi-line script that actually parses on the no-staging fallback. Covers the knobs in mios.toml [powershell] and the two tiers of tests/test-powershell-flatten.sh. -->

# <a name="57_powershell_object_flattening"></a>Chapter 57: PowerShell Object Flattening

> Part VI: The Local AI Plane of the [MiOS manual](../manual.md).

> Path Reference: `/usr/share/doc/mios/manual.md#57_powershell_object_flattening`

#### Overview

The `powershell_run` verb hands a script to `mios-powershell`, which runs it
under `pwsh.exe` with `-NoProfile -NonInteractive` and returns stdout, stderr
and the exit code. That much worked. What did not work was the single most
common thing a Windows script does: emit objects.

#### <a name="57_the_failure_was_silence"></a>57.The Failure Was Silence: The Failure Was Silence

The roadmap entry for this work predicted "unusable serialized noise". The
measured behaviour was worse. A broker has no console, so
`$Host.UI.RawUI.WindowSize.Width` is `-1`. PowerShell's default formatter sizes
every column against that width, every column collapses to zero, and each
object renders as an empty line:

```
$ pwsh -NoProfile -NonInteractive -File t.ps1     # Get-Item x | Select Name, Length
                                                  # (three blank lines)
```

Strings pass through untouched, so the failure is invisible in any test that
prints a string. An agent asking `Get-Service` got exit code 0, an empty
`stdout`, and no error — a silent wrong answer, and one it cannot detect.

#### <a name="57_why_the_obvious_fixes_fail"></a>57.Why the Obvious Fixes Fail: Why the Obvious Fixes Fail

Three approaches fail before the working one:

* **Set the host width.** `$Host.UI.RawUI.BufferSize = ...` throws
  `Operation is not supported on this platform` on a console-less runspace.
* **Override `Out-Default`.** The classic interception trick — defining a
  `function Out-Default` that flattens what the engine implicitly appends to
  every top-level pipeline — is never called from a `-File` script. The engine
  binds the real cmdlet; a script-scope or even a `global:` function is ignored.
* **Wrap the body in `& { … }` inline.** This flattens, but an error record then
  reports the wrapper's line (`& {`) instead of the failing statement, and a
  mid-script `exit` kills the runspace with the formatter's buffer unflushed —
  everything already produced is lost.

#### <a name="57_the_wrapper"></a>57.The Wrapper: The Wrapper That Holds All Four Properties

`mios-powershell` stages the caller's script **verbatim** and invokes it by
path from a wrapper command:

```
$PSStyle.OutputRendering="PlainText"; $FormatEnumerationLimit=16; …
& 'C:\Users\Public\Documents\mios-ps\mios-ps-XXXXXX.ps1' | Out-String -Stream -Width 200
exit ([int]$LASTEXITCODE)
```

Each piece earns its place:

* `Out-String -Stream -Width N` sets the width **explicitly**, so the formatter
  never consults the absent console. `-Stream` emits strings as each format
  group completes rather than buffering the whole run.
* Calling a real script with `&` keeps its own line numbers in error records,
  and its `exit N` returns through `$LASTEXITCODE` instead of terminating the
  runspace — so output produced before the exit still reaches the caller.
* `Set-Location` for `--work-dir` goes in the **wrapper**, never prepended to
  the body; prepending it shifts every line number an error record reports.
* `OutputRendering="PlainText"` strips the ANSI colour sequences PowerShell 7
  wraps error records in, which otherwise arrive as escape noise.
* Trailing column padding is trimmed on the Linux side before the JSON envelope
  is built, because padding is tokens the model pays for and never reads.

Heterogeneous output is one thing the wrapper deliberately does **not** fix:
when objects of different shapes reach one `Format-Table`, the first object
defines the columns and later mismatched objects render as blank rows. That is
PowerShell's own semantics on a real console too, and papering over it would
misrepresent what the script did.

#### <a name="57_the_no_staging_fallback"></a>57.The No-Staging Fallback: The No-Staging Fallback

When `/mnt/c/…` is not writable there is no Windows-visible path to `&`, so the
body becomes an inline scriptblock carried by `-EncodedCommand`. The obvious
alternative, `-Command -`, cannot serve: it reads stdin one line at a time as
if typed, so a multi-line scriptblock never parses. On this path error records
name the wrapper's line rather than the caller's; everything else holds.

#### <a name="57_powershell_configuration"></a>57.PowerShell Configuration: PowerShell Configuration

`mios.toml [powershell]` owns every value: `flatten`, `flatten_width`,
`enumeration_limit`, `plain_text`, `trim_trailing`, `stage_dir`,
`max_script_bytes` and `max_output_bytes`. The staging directory's Windows form
is **derived** from `stage_dir` (`/mnt/c/x` → `C:\x`) rather than tracked as a
second key, so the two cannot drift apart.

#### <a name="57_flattening_tests"></a>57.Flattening Tests: Flattening Tests

`tests/test-powershell-flatten.sh` runs in two tiers. The **stub tier** always
runs: a fake `pwsh` records its argv, and the test asserts the wrapper carries
the Out-String stage, the PlainText setting, the `& '<staged script>'` call
form and the exit propagation — and that `flatten = false` genuinely removes
them, so the knob cannot decay into a no-op. The **live tier** runs against a
real `pwsh` when one is present and proves the behaviour end to end, including
that the unflattened path still produces the blank output the flattening
fixes. With no `pwsh` available the live tier skips loudly, and under
`MIOS_DRIFT_REQUIRE_TOOLS=1` the skip is fatal.
