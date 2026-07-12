<!-- AI-hint: Plan to provision large AI models at FULL FIRST BOOT instead of baking them into the build-time OCI image, keeping the image lean and avoiding the bound-images bake layer-commit ceiling (build exit 125). -->
# Plan: large AI models at FULL FIRST BOOT (not build-time bake)

**Operator directive (2026-06-19):** *"JUST PLAN TO ADD MORE LARGE AI MODELS FULL
FIRST BOOT INSTEAD"* — for the OCI build `exit 125` (bound-images bake layer commit
ceiling). Rather than shrink/split the build-time bake or grow the build disk,
**move large-model provisioning OUT of the build and INTO first boot.** This keeps
the build-time image lean (no giant model/lane layer → no buildah large-layer
commit failure) and lets us add MORE / LARGER models without ever touching the
build's layer-size ceiling.

## Why this fixes exit 125
The `exit 125` is buildah failing to commit a multi-GB layer (the >15-image /
large-weight bake; Containerfile:206-208 history). If the big weights + heavy-lane
container images are **not baked at build time**, that layer never exists → the
build stays small + reproducible. The cost moves to a one-time first-boot fetch
(network + disk on the target), which is where unbounded model size belongs.

## Design
1. **Build-time = lean.** Bake ONLY the always-on light essentials (or nothing):
   keep `MIOS_LLAMACPP_BAKE_MODELS` minimal/empty; do NOT bind+bake the heavy-lane
   container images (SGLang/vLLM, multi-GB each) — mark them first-boot-provisioned.
   Law 3 (BOUND-IMAGES) still holds for the SMALL/essential images; large weights
   are data, not bound container images.
2. **First-boot provisioner** (`mios-models-firstboot.service`, `After=network-online`,
   `ConditionPathExists=!<sentinel>`): reads the model set from SSOT
   `mios.toml [ai.firstboot_models]` (a NEW list: name, source GGUF URL / HF repo,
   sha, target lane) and downloads each into the model store
   (`/var/lib/mios/llamacpp/models` — already the llama-swap models dir) with
   resume + checksum + a progress log. Writes the sentinel on success so it runs
   ONCE. Idempotent + re-runnable (`mios models sync`).
3. **Lane readiness gating** (already present): the lanes use `ConditionPathExists`
   on baked weights — extend so a lane stays inert until its first-boot weight
   lands, then `systemctl start` it. llama-swap hot-loads on first request, so a
   model present in the dir is served with no rebuild.
4. **Heavy-lane container images** (SGLang/vLLM): pull at first boot into the
   additional store (`mios-bound-images-firstboot`, the same pull logic as the
   build-time bake but on the running host where layer size is irrelevant) instead
   of the build-time bound-images bake. The build only binds+bakes the lean set.
5. **SSOT + UI:** new `[ai.firstboot_models]` flows through `userenv.sh` +
   `install.env` + the configurator HTML so the operator adds models by editing
   mios.toml (no rebuild). `mios models {list,sync,add,rm}` CLI.

## Migration / phases
- **P0 (unblocks the build):** move the heavy-lane container images + any large
  baked weight OUT of the build-time bake; add the first-boot provisioner that
  pulls/downloads them. Build goes green (lean image).
- **P1:** `[ai.firstboot_models]` SSOT + `mios models` CLI + configurator entry.
- **P2:** resume/checksum/progress + a Portal "model provisioning" status tile.
- **P3:** optional pre-seed (a `mios models cache` that pre-downloads to a USB/
  local mirror for air-gapped first boots).

## Trade-off (state honestly)
First boot is SLOWER + needs network (or a local mirror) the first time. Mitigate
with P3 (pre-seed) + a clear first-boot progress UI. The build, in exchange, is
small, fast, reproducible, and never hits the layer-commit ceiling — and model
size becomes unbounded.

## Status
PLAN ONLY (operator said "just plan"). The split-bake mitigation
(`usr/libexec/mios/mios-bake-bound-images`, written this session) is the
ALTERNATIVE if build-time baking is ever kept — left uncommitted/available. The
recommended path is this first-boot provisioning.
