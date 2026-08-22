<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### render-globals.py -- generate BOTH globals resolvers from...

render-globals.py -- generate BOTH globals resolvers from the SSOT.

automation/lib/globals.sh and globals.ps1 used to be two divergent hand-typed
registries (~200 literals each) kept in step with mios.toml only by drift
checks. They are now generated in full, directly, under their original names --
every consumer that sources/dot-sources them is untouched, and there is no
`.generated` sidecar and no shim layer.

Only ONE thing cannot be a constant: the version, which is read from a file at
run time. That logic is emitted as a preamble from this generator, so it still
lives in exactly one place.

Usage:
    tools/render-globals.py           # write both resolvers
    tools/render-globals.py --check   # exit 1 if either has drifted

<!-- mios-src:a14177eaae8b from tools/render-globals.py:3-18 -->

### Assign-if-unset. Prefer the idiomatic `: "${VAR:=value}"`...

Assign-if-unset.

    Prefer the idiomatic `: "${VAR:=value}"` -- several drift checks parse that
    exact shape out of this file. It is unusable when the value contains `}`
    (message templates carry `{placeholder}`), which would close the expansion
    early and make the file a syntax error; those fall back to
    `[ -n "${VAR+x}" ] ||`, which has identical already-set-wins semantics.

<!-- mios-src:e7e3421e3913 from tools/render-globals.py:232-239 -->

### The word in `"${VAR:=word}"` is still quote-processed, so a...

The word in `"${VAR:=word}"` is still quote-processed, so a lone ' or "
inside it (e.g. "the operator's phone") starts an unterminated quote.
Only take the idiomatic form when the value is free of every metacharacter.

<!-- mios-src:ea6d3604444b from tools/render-globals.py:241-243 -->
