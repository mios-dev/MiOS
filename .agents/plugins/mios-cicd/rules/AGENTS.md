# MiOS CI/CD Plugin Rules for Antigravity

Rules applied when the `mios-cicd` plugin is active:
1. Ensure all agent calls route through `MIOS_AI_ENDPOINT` (OpenAI API standard).
2. Maintain the 5 Architectural Invariants: persistent `/var`, UKI signing chain, VirtIO `venus` vs CUDA VFIO, driver-free host GPU passthrough, and Blade vs obfuscated guest.
3. Validate all changes with standing gates: `phase-registry`, `ratchet-direction`, `credential-literals`, `version-literals-ssot`, `signature-policy`, and `ci-suites --check`.
4. Ensure `bash ./tools/sync-generated.sh` runs clean before committing.
