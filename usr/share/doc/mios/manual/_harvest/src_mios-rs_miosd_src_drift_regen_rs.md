<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

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
