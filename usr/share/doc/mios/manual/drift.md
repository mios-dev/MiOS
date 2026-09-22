<!-- AI-hint: Manual pages distilled from the source comments of drift, sanitized, each passage anchored to the comment it came from. -->

# drift

### Re-render a projection whose generator is a SHELL renderer...

Re-render a projection whose generator is a SHELL renderer and diff it against
what is committed.

`regen_and_diff` above only suits generators that implement `--check` and
report drift through their exit code. The chrony/nut/kargs/composefs
projections have no such mode: `automation/NN-*-render.sh` WRITE their output.
Six checks in this registry were therefore wired to Python generators that do
not exist in the tree (`generate-kargs.py`, `generate-chrony-conf.py`, ...),
and because a missing generator yields `Verdict::Skip`, they never ran and
never said so.

This renders into a scratch directory seeded with the committed artifact,
then compares -- the same shape as the bash gate's kargs check.

<!-- mios-src:888eee4c1089 from src/mios-rs/miosd/src/drift/regen.rs:81-93 -->
### T-1045. This used to stat the Justfile and return Pass("BIB...

T-1045. This used to stat the Justfile and return Pass("BIB single
config invariant verified") without opening it. Ported from the bash
twin: every config/artifacts/*.toml must parse, and every recipe that
invokes bootc-image-builder must mount EXACTLY ONE /config.toml --
two mounts and the second silently wins.

<!-- mios-src:6cf4514751aa from src/mios-rs/miosd/src/drift/deploy.rs:92-96 -->

### T-1045. This used to stat two files and return Pass("Deploy...

T-1045. This used to stat two files and return Pass("Deploy plane
verified"). Stating that a file EXISTS is not verifying what is in
it. Ported from the bash twin's content assertions -- and unlike the
twin, an absent subject FAILS here rather than printing a WARNING and
carrying on, because these are tracked deliverables.

<!-- mios-src:28142d12570b from src/mios-rs/miosd/src/drift/deploy.rs:214-218 -->

### T-1043. This used to test `p.exists()` and then return...

T-1043. This used to test `p.exists()` and then return
Pass("Law enforcers resolution validated clean") -- a claim about a
file it never opened. Touching ctx.root to BUILD a path is not
reading the tree, which is why two successive stub detectors let it
through. CLAUDE.md calls [laws] the canonical registry; this now
checks it.

<!-- mios-src:3e7a6484feac from src/mios-rs/miosd/src/drift/laws.rs:17-22 -->

### `process:` is a real scheme, not a malformed entry: Law...

`process:` is a real scheme, not a malformed entry: Law 15's
triple-check-before-acting cannot be gated, only followed. It
still has to SAY something, which the emptiness test above covers.

<!-- mios-src:62909a3e7822 from src/mios-rs/miosd/src/drift/laws.rs:93-95 -->

### T-1045. This used to test whether a DEBUG BUILD of the...

T-1045. This used to test whether a DEBUG BUILD of the generator
existed and, if so, return Pass("Names registry projection matches
SSOT") -- without running it and without comparing anything. If the
binary was absent it skipped instead, so on an ordinary tree the
check was silent and on a developer's tree it lied. Both halves of
Skip-as-Pass in one function.

The projection is produced by tools/generate-names-registry.py, the
same generator sync-generated.sh runs, so regenerate and diff it the
way every other projection check already does.
The generator has no --check mode and the tooling-Python ratchet has
no room to add one (T-1044), so compare in Rust: snapshot, render,
diff, restore.

<!-- mios-src:e329f7bbba21 from src/mios-rs/miosd/src/drift/names.rs:19-31 -->

### T-1043. This used to read ctx.in_image for the early skip...

T-1043. This used to read ctx.in_image for the early skip above and
then return a constant Pass -- "ordinals verified dense" about a tree
it never opened. Naming the parameter `ctx` was the only thing that
made it look implemented. Ported from the bash twin's three assertions.

<!-- mios-src:3980a58c9a9e from src/mios-rs/miosd/src/drift/numbering.rs:20-23 -->

### T-1045. This function is named regen_and_diff and it does...

T-1045. This function is named regen_and_diff and it does not diff: it
runs the generator and then asserts the target EXISTS. That is only sound
when the generator itself compares, i.e. when --check is passed and its
exit status is the verdict. Called without it the generator WRITES --
erasing the very drift the check is looking for, and mutating the tree
from inside a read-only gate. Refuse rather than mislead.

<!-- mios-src:b2bbad5618f1 from src/mios-rs/miosd/src/drift/regen.rs:17-22 -->
