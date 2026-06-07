# MiOS maturity + release runbook (R14)

Closes the **docs** slice of the R14 maturity-review gaps and documents the
operator-gated steps that close the **signing** and **release** slices. Sourced from
the repo (`Justfile`, `CLAUDE.md`, the T26 naming-refactor plan) — anything an
operator must confirm for their environment is marked **(operator-confirm)**.

## 1. Current maturity state (verified 2026-06-07)

| Gap | Status |
|---|---|
| **tests** | Sibling unit suites under `usr/lib/mios/agent-pipe/test_mios_*.py` — **9 suites / 244 checks green** (sched, evict, hitl, aci, pg, kvfork, codemode, stress, launch). Run: `for t in test_mios_*.py; do python3 "$t"; done`. |
| **docs** | This runbook + `usr/share/doc/mios/` (concepts/reference/guides) + the AIOS/standards plan docs. |
| **headless/server profile** | Done — `usr/share/mios/profile-headless.toml` (no GNOME/remote-desktop; inference stack on). |
| **signing** | **OPEN — operator-gated** (§3). |
| **release (tag + artifacts)** | **OPEN — operator-gated** (§2/§4). |

## 2. Build artifacts (Linux, inside `podman-MiOS-DEV`)

```bash
just preflight        # system prereq check
just build            # OCI image (ends with `bootc container lint` — Law 4)
just verify-images    # smoke-test output/ artifacts
just sbom             # CycloneDX SBOM via syft
# Disk/installer artifacts (need MIOS_USER_PASSWORD_HASH + MIOS_SSH_PUBKEY for qcow2/vhdx):
just iso              # Anaconda installer ISO
just raw / qcow2 / vhdx / wsl2 / all
```

> ⚠️ **Disk hazard (lived 2026-06-07):** a `--no-cache` full image build filled the
> 256 GB **M:** drive and corrupted the dev VM. Do **not** run a no-cache full build
> on the size-capped M: drive; prune (`podman system prune` + `buildah rm --all` +
> `fstrim`) before large builds. Windows host: `.\mios-build-local.ps1`.

## 3. Signing — **(operator-gated; keys are the operator's)**
1. **OCI image signing** (supply-chain): sign the pushed image with the project's
   cosign key — `cosign sign ghcr.io/mios-dev/mios@<digest>` **(operator-confirm key/registry creds)**. bootc can then verify the signature on `bootc upgrade`.
2. **Secure Boot / MOK** (kernel + modules): enroll the project MOK so signed kernel
   modules load under Secure Boot — `mokutil --import <MOK.der>` then reboot to
   confirm enrollment **(operator-confirm: MOK key material + physical/enrollment step)**.

Both require key material only the operator holds; the assistant cannot and must not
fabricate or self-execute them.

## 4. Release (tag + publish) — **(operator-gated)**
```bash
git -C /path/to/mios tag -a vX.Y.Z -m "MiOS vX.Y.Z"
git -C /path/to/mios push origin vX.Y.Z
# then publish the verified, SIGNED image + artifacts to the registry/release
```
Push/publish are outward-facing + use operator credentials → operator executes.

## 5. T26 Phase-3 — global-names migration **(operator-gated)**
The code-side naming refactor (Phases 1–2) is complete (verified: zero rename
targets remain). Phase-3 reconciles the `[services.*]` user/UID SSOT vs reality
(e.g. hermes/agent-pipe → `mios-ai`/850) and is **deferred by design** — its own plan
mandates **additive aliasing first** (keep both, flip canonical later), never in-place
renames of the frozen contract. Closing it needs an **image rebuild + offline
`chown -R` migration** of baked `/var` ownership → operator-gated. See
`usr/share/doc/mios/concepts/naming-refactor-plan.md`.

## 6. Per-change validation gate (every artifact/source edit)
`py_compile` server.py + siblings · run the sibling unit suites · `tomllib` mios.toml
+ kargs · `bash -n` touched scripts · deploy agent-pipe via
`wsl cp .../server.py /usr/lib/mios/agent-pipe/server.py` + `systemctl restart
mios-agent-pipe.service` (import-check before restart). Live changes are reversible
(`.bak` + git).
