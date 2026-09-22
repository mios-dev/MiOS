<!-- AI-hint: Manual pages distilled from the source comments of invariants, sanitized, each passage anchored to the comment it came from. -->

# invariants

### This invariant only applies to a booted bootc/MiOS host...

This invariant only applies to a booted bootc/MiOS host with VFIO kargs
baked into the UKI. On a generic devcontainer, Codespace, or CI runner the
file legitimately does not exist: that is a capability absence, not a
defect, so it must SKIP (exit 2) rather than FAIL (exit 1) or silently PASS.

<!-- mios-src:02ca9868d27b from invariants/test_invariant_hw.sh:7-10 -->
