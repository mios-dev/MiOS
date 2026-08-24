<!-- AI-hint: The measured state of the MiOS deploy plane: what installs, what does not, and the root causes behind each. -->
<!-- AI-related: AGY-TASKS.md, installation/, usr/share/mios/ventoy/ -->

# MiOS Deploy Plane â Hardening Plan

Sources: deploy-plane audit (`wbq3zes03`, 111 findings / 26 confirmed gaps, 14 agents), gate-suite audit (`w5ih2smtv`, 202 checks, 13 agents). Every claim below that is not attributed to those audits was re-run in `C:\MiOS` at `24217fb1` and the command is named.

---

## 1. Verdict

**The medium boots, and it does not install MiOS.** The one path that would install the real bootc image â `usr/share/mios/ventoy/mios-oci-install.ks` â `tools/install.sh` â `bootc install to-disk --source-imgref oci-archive:` â is completely written and completely unreachable: nothing copies the kickstart to the partition its own boot entry names (`grep -rn mios-oci-install.ks` over `*.sh|*.ps1|*.cfg|*.py|Justfile` returns exactly two hits outside worktrees, both *references* in menu text, zero copiers), the menu that would offer it (`cat/loopback.cfg`) is read by nothing, and the menu that Ventoy actually loads (`mios-bootstrap/cat/resources/ventoy/ventoy_grub.cfg`) has no MiOS entry at all. What does run on bare metal is `mios-kickstart.cfg`, which installs stock Fedora and then applies an FHS overlay â a different product from the immutable image the project ships. Around that hole sits a consistent second defect: the deploy plane reports success it did not perform. `automation/install-fhs.sh` resolves `REPO_ROOT` to `automation/`, finds no `usr etc var srv` there, applies nothing and prints `[OK] MiOS system installer complete`; `installation/stage-mios-repo.sh` prints `DONE. Boot the USB -> Install MiOS...` and exits 0 with both payloads missing; `just verify-images` returns success over zero artifacts and `just publish` depends on it; `/etc/greenboot/check/required.d/15-composefs-verity.sh` prints `ERROR: composefs requested but not active` and then `exit 0`. And the published image has no Day-2 update path whatsoever â `automation/50-uupd-installer.sh` unconditionally `systemctl disable bootc-fetch-apply-updates.timer`, then only *warns* if `uupd.timer` is absent, and the audit confirmed in `ghcr.io/mios-dev/mios:latest` that `rpm -q uupd` fails and no update timer is enabled. Nothing in either publisher exercises any of it: `grep -c just .github/workflows/mios-ci.yml .forgejo/workflows/build-mios.yml` = **0, 0**. The deploy plane is roughly a complete set of correct parts with the wires between them missing, sitting behind gates that are green because they measure the wrong thing.

---

## 2. Gaps ranked by what they cost a deployer

Each root cause is stated once, with the surfaces it appears on. Evidence class is marked per group.

### RC-1 â No supported path installs MiOS onto bare metal
*Cost: total. This is the product.* â **Confirmed by a second agent** (survey:installers + verify:installers, survey:media + verify:media; re-verified here).

The bootc leg (Path B) is broken in four independent places, each sufficient on its own:
- The kickstart is never staged. `installation/stage-mios-repo.sh` creates `$REPO_MP/ventoy/` and writes exactly one file into it, `mios-loopback.cfg` (`:151-157`); it never touches `usr/share/mios/ventoy/`. The `.ks` reaches a stick only buried inside the `git archive HEAD` dump at `$REPO_MP/repos/MiOS/...` (`:192`), where Anaconda's `inst.ks=hd:LABEL=MiOS-Repo:/ventoy/mios-oci-install.ks` will not find it.
- The menu that would offer Path B is dangling. `cat/loopback.cfg` (35 lines, `@@REPO_LABEL@@` placeholders) has no reader; `stage-mios-repo.sh:72-96` carries a hand-maintained second copy of the same three `menuentry` blocks, and the AI-hint on the dead file tells maintainers to edit *that* one.
- The rendered copy lands where Ventoy cannot read it: `$REPO_MP/ventoy/mios-loopback.cfg` is on the MiOS-Repo partition, not Ventoy's first partition, and under a filename Ventoy does not load.
- The menu Ventoy *does* load, `ventoy_grub.cfg` (xcopied by `MiOS-Cat.bat:550`), chainloads Fedora-Server, MiOS-Xbox, MiOS_PE and SystemRescue. No MiOS.iso, no bootc entry.

The FHS leg (Path A) is what actually runs, and `mios-kickstart.cfg:97` falls back to `git clone --depth 1 https://github.com/mios-dev/mios-bootstrap.git` â a network call in what is documented as the offline path.

The stager has no caller. `grep -rn stage-mios-repo` returns only docs, `AGY-TASKS.md`, the corpus TSV and a comment in `cat/loopback.cfg`.

The staging verb that should produce the payload is a mock: `mios-bootstrap/cat/lib/cat.sh:68-69` is `echo "Saving localhost/mios:latest..."` followed by a commented-out `podman save`; `:71-72` are bare echoes for models and mirrors; `MiOS-Cat.psm1:78-79` is the byte-twin. The real chain exists â `Justfile:299-302` runs the `podman save --format oci-archive`, and two real copiers stage it â the verb is simply not joined to it. Note a detail the audit surfaced and I confirmed against both files: even uncommented, `cat.sh` writes to `$dataDir/images/mios-latest.tar` (**MiOS-Data**), while `tools/install.sh:12` defaults to `/mnt/mios-repo/mios-latest.tar` (**MiOS-Repo**). Uncommenting alone still misses.

### RC-2 â The published image has no way to update itself
*Cost: every deployed machine is frozen at install time, silently.* â **Confirmed by a second agent** (verify:updater ran inside `ghcr.io/mios-dev/mios:latest`).

`automation/50-uupd-installer.sh` disables `bootc-fetch-apply-updates.timer` and `rpm-ostreed-automatic.timer` unconditionally, calls `install_packages "updater"`, then `mios_warn "Uupd.timer not present"` if the unit is missing. Four silent-skip layers stack: the repo is skip-if-unavailable, `install_packages_strict` also passes `--skip-unavailable` (`automation/lib/packages.sh:181-190`), the script warns instead of dying, and `mios.toml:10159` declares the phase `fatal = false`. In the published image: `rpm -q uupd` â not installed; no `uupd.timer`; `bootc-fetch-apply-updates.timer` â **disabled**; the enabled-timer set contains nothing that updates the OS.

The verb makes it worse rather than compensating. `[verbs.update]` has `description`/`surface` and **no `cmd`** â and `check_verb_backends` (`98-drift-checks.sh:1472`) only walks `[verbs.*].cmd`, so a verb with no backend is invisible to the gate by construction. In an interactive shell, `etc/profile.d/mios-verbs.sh:95-101` routes `update` to `mios pull`, a `git reset --hard` of a Windows drive. In any non-interactive context, `mios-verbs.sh:3` (`[ -n "${PS1:-}" ] || return 0`) means `/usr/bin/mios` handles it â and its `KNOWN_VERBS` (`:317-348`, 31 entries, verified) has no `update` and no `pull`, so the string `update` is sent to the Hermes agent as an LLM prompt. `usr/bin/mios-update` is a correct `bootc upgrade --check/--apply/--rollback` wrapper that nothing calls.

### RC-3 â Build artifacts land where the consumers do not look
*Cost: the medium cannot be assembled even when the image builds.* â **Confirmed by a second agent** (verify:media, re-verified here against `Justfile`).

Three consumers disagree about one output path, and all three are wrong under bootc-image-builder's per-type layout:
- `iso:` (`Justfile:234-247`) mounts `./build/iso:/output`.
- `usb-installer:` (`:313`) globs `build/*.iso build/bootiso/*.iso` and `exit 1`s on empty.
- `verify-images` (`:337`) globs `build/*.iso build/bootiso/*.iso build/qcow2/*.qcow2 build/vhd*/*.vhd*`.
- `stage-mios-repo.sh:167` globs `$BUILD/iso/*.iso $BUILD/bootiso/*.iso $BUILD/usb-installer/*.iso`.

`all:` (`:304`) lists `usb-installer`, so a multi-hour `just all` dies at a rename step. `verify-images` ends `[ "$fail" -eq 0 ]` â with zero matches that is exit 0, and `publish: all verify-images` runs behind it. And `usb-installer` builds no medium in any case: its body is `mkdir -p`, a `cp -p` loop and three `echo` lines about `dd`. No Ventoy, no partitioning, no label, no oci-archive, no repo, no models. `[deploy.formats.usb-installer]` in the SSOT already says `status='partial'`, but its `summary` promises "a Ventoy USB or NVMe carrying the image, the repository and the models, installing with no network".

### RC-4 â One surface, two repos, divergent copies; the SSOT blesses the divergence
*Cost: the operator's default entry point is a different program from the one that works.* â **Confirmed by a second agent** (verify:installers; both bugs re-verified here).

`installation/mios-install.{sh,ps1}`, `install.sh`, `install.ps1`, `installation/mios-common.sh` and `installation/README.md` are all in `[bootstrap.sync].not_mirrored`, so `tools/sync-bootstrap.py` never compares them. Result: mios.git's guided installer is 403 lines; mios-bootstrap's is 1713, and the real `do_install_core` is at `mios-bootstrap/installation/mios-install.sh:1548`.

- `cat/` in mios.git contains exactly one file, `loopback.cfg` â which makes `[[ ! -d "$CAT_DIR" ]]` false and therefore *disables* the working `../mios-bootstrap/cat` fallback. `flash` and `live` hard-error on a repo whose sibling has the backend one directory away.
- `installation/mios-install.ps1:14-15` computes `$script:CatBat` and references it nowhere else; `:163` hardcodes `Join-Path $PSScriptRoot 'MiOS-Cat.bat'`, absent from mios.git. `flash|live|xbox|provision|test-vm` all resolve to files that do not exist â and the "type ERASE" confirmation runs at `:254`, *before* target resolution at `:268`.
- Root `install.sh` is a `MIOS_INSTALLER_ROLE=root-overlay-redirector` pointing at `build-mios.sh`, which exists in neither repo's root (`ls build-mios.*` â only `build-mios.ps1`). `UNIFY.md:130-133`'s rationale for the divergence describes a shape neither repo currently has.
- `automation/install-fhs.sh:19` sets `REPO_ROOT` to the script's own directory (`automation/`), so its overlay loop never executes; it also prints `bootc switch ghcr.io/MiOS-DEV/mios:latest` at `:10` where GHCR paths must be lowercase and the SSOT says `ghcr.io/mios-dev/mios:latest`.
- **The mode-swallow is upstream.** In `mios-bootstrap/installation/mios-install.sh`, `TYPE=""` (`:118`), the arg loop's lenient `*)` branch (`:134-144`) shunts a positional `bootc` into `PASSTHROUGH` and `break`s, and `:1605` dispatches `do_install_core "${TYPE:-fhs}"`. `_install_core bootc` therefore still runs **fhs** there. mios.git's copy was fixed at `24217fb1` (`:330` now reads `"${TYPE:-${PASSTHROUGH[0]:-fhs}}"`); mios-bootstrap was not.

### RC-5 â The gates certify all of the above
*Cost: nobody would look.* â **Split evidence, see below.**

Confirmed by a second agent:
- `check_offline_install_invariant` (`:4599`) asserts `grep -q '\--transport oci-archive' tools/install.sh` with no comment filter. That string occurs **only** on line 3, inside the AI-hint. The real command at `:77` has no `--transport` flag. The verifier gutted the installer to `echo "I install nothing at all."; exit 0` and the gate printed *verified clean*; deleting the file entirely also returned 0 (`:4589-4591`).
- `check_repo_partition_label_ssot` (`:4668`) â re-read here â resolves the label as `grep -A 5 '\[cat\.repo_partition\]' â¦ || echo "MiOS-Repo"` under `set -euo pipefail`, so when the SSOT table is gone `grep` returns 1, the fallback fires, and the gate compares consumers against a **hardcoded literal**. Rename the table and the gate stays green. It also never inspects `mios-oci-install.ks` or `cat/loopback.cfg`, both of which carry the label.
- `src/mios-rs/miosd/src/drift/deploy.rs` is 82 lines and all six `run(&self, _ctx)` bodies are a single `Verdict::Pass(...)` â `InstallerRolesCheck`, `OfflineInstallCheck`, `BIBConfigCheck`, `DeployPlaneCheck`, `OCIArchivePathCheck`, `Win11VMTemplateCheck`, all registered at `mod.rs:297-302`. The harness meant to reconcile bash and Rust, `tests/drift-parity.sh` (27 lines, read here), runs both with `|| true`, greps the Rust log, deletes both logs and prints `Parity check completed successfully`. It never compares them.
- `just iso` has no `MIOS_USER_PASSWORD_HASH` guard while `qcow2` (`:251`) and `vhdx` (`:267`) do; `:237` seds with `${MIOS_USER_PASSWORD_HASH:-}`, yielding `user --name=mios --groups=wheel,render,video --iscrypted --password=` and a malformed `sshkey` line. `check_replaceme_mount_substitution` tests only whether the recipe *contains* `sed`, which it does.

From the gate audit (202 checks: 120 effective, 16 claimed unfailable, 66 inconclusive):
- **Confirmed unable to fail, still open: 2.** `check_bake_budget` (high) â the SSOT `runner_disk_budget_gb` appears only inside the *failure message*; the sole live assertion is a hardcoded `[[ "$count" -gt 30 ]]` over TSV row count. 12 mutations including budgetâ1, budgetâ0, 321-image bake list and a 20.7 TB TSV all returned 0. The clean tree already violates the stated property: `bound-images.tsv` lines 13-14 are the ~20 GB sglang and ~27 GB vllm images against a declared 40 GB budget, and the gate prints "within SSOT limit". `check_package_registry` (medium) â flipping the documented SSOT switch `[ai].package_registry = false â true` with no `registry.json` anywhere returns 0, because nothing bridges the key to the `MIOS_PACKAGE_REGISTRY` env var the gate reads.
- **Confirmed unable to fail, repaired this run: 2.** `check_clevis_luks` and `check_no_duplicate_value_key`, both with SSOT-side negative tests proven to fail against the pre-repair gate. The residual `[security.luks]` vs `[security.disk_encryption]` contradiction is explicitly *not* fixed and needs its own change.
- **Overturned: 3.** `check_hummingbird` and `check_cargo_deny` can fail, but only on file presence â `cargo deny` is invoked nowhere in the repo (`grep -rn 'cargo deny|cargo-deny'` = zero), so a gutted, empty or invalid `deny.toml` is indistinguishable from the real one. `check_db_seed_coverage` is technically failable but effectively broken: `:5294`'s `"kv_sections = [k for k in data.keys()" not in seed_code and â¦` short-circuits for every section, and â the important part â `tests/drift-gate-negatives.sh:1715` **secretly sabotages the seeder with a `sed` so the test passes**. Removing only that line makes the test die: `Check_db_seed_coverage passed despite unseeded section in mios.toml`. The negative test manufactures the proof.

**Reported but unverified â say so plainly:**
- Three of six verify agents (`verify:repair`, `verify:offline`, `verify:gates`) and the `name-research` and `hardening-plan` agents all died on a session limit. The **repair, offline and gates lenses were never independently confirmed**, and worse, their survey findings are not in the result artifact at all â only 401-character `resultPreview` strings survived. Their content contributed to the 111/64-broken headline and is otherwise unrecoverable from this file. Anything about repair tooling, the offline dependency set, or the 16-gate deploy cluster below should be treated as one agent's unrefuted claim, not as a finding.
- Of the 16 gates *claimed* unfailable, 4 were adjudicated and 3 overturned; **9 were never refuted** because `refute:slice-3` and `refute:slice-4` died. Only two of those nine names survive in the artifact: **`check_no_hardcode`** (claimed: appending a date-in-comment to `usr/lib/mios/agent-pipe/mios_pipe/auth.py`, exactly what its violation text forbids, left it green) and **`check_unit_security`** (claimed: stripping `NoNewPrivileges`/`ProtectSystem`/`ProtectHome`/`PrivateTmp` from `hermes-dashboard.service` left it green). The other seven names are lost.
- **The identities of the 66 inconclusive gates were not preserved** â the `synthesize` agent died before writing them. Only the count survives. Re-deriving the list is itself a task.
- One structural fact I did verify, because it explains how the unfailable gates stay unfailable: `[testing].negative_coverage_exempt.exempt` has **55 entries** (`tomllib`, verified), and it contains `check_no_hardcode`, `check_unit_security`, `check_package_registry`, `check_hummingbird`, `check_greenboot` and `check_greenboot_enablement` â i.e. an exemption list that excuses precisely the gates most suspected of being unfailable. 157 test functions cover 202 gates.

### RC-6 â Health checks that cannot fail, on a rollback nobody has watched
*Cost: a bad update is not caught, and the rollback that would save it is unobserved.* â **Confirmed by a second agent** (verify:updater, in-image; `15-` and `50-` re-read here).

`50-mios-core.sh` is `command -v miosd || { echo "Miosd not found, skipping"; exit 0; }`. The binary ships only at `/usr/libexec/mios/miosd`, which is not on PATH, and `greenboot-healthcheck.service` sets no PATH override â so the required check is a no-op today. If PATH were "fixed" it would fail every boot: `miosd greenboot` is not among the 19 subcommands the shipped binary advertises. `15-composefs-verity.sh` detects `composefs requested but not active`, prints ERROR, and falls through to `exit 0`; `/usr/lib/ostree/prepare-root.conf` is present in the published image with `enabled = verity`, so this branch is live, not skipped. Greenboot rollback itself is `implemented-unexercised`: inside a container `greenboot health-check` prints `Container environment detected; skipping reboot and rollback handling`, `/boot/grub2/grubenv` does not exist, `grep -rn rollback tests/` returns zero, and the two registered greenboot gates check only service names and unit existence. Ordering hazard: `required.d` runs lexically and greenboot aborts at the first failure, so `10-mios-composefs.sh` failing means `15-` and `50-` never run.

### RC-7 â The medium can ship an empty root-equivalent credential
Covered under RC-5. Ranked last only because it requires the ISO to build at all, which RC-3 currently prevents.

---

## 3. Hardening plan, in dependency order

Each step: **what changes / what proves it / what would make it a FALSE pass**.

**H0. Repair the gates that cover the deploy plane, before touching the deploy plane.**
*Changes:* `check_offline_install_invariant` asserts on comment-stripped executable text and treats a missing `tools/install.sh` as a violation; `check_repo_partition_label_ssot` reads `[cat.repo_partition].label` with `tomllib` and treats a missing key as a violation, never a default, and extends its consumer set to `mios-oci-install.ks` and `cat/loopback.cfg`; `check_bake_budget` sums real per-image sizes and compares to the SSOT budget; `check_package_registry` derives its flag from `[ai].package_registry`; `check_db_seed_coverage` imports the seeder's own selection function; `deploy.rs`'s six stubs either implement the check or return `Verdict::Skip`; `drift-parity.sh` compares the two outputs and exits non-zero on disagreement.
*Proves it:* for each gate, four exit codes captured with `$?` directly â clean-before=0, mutated-before=0 (the defect reproduced), clean-after=0, mutated-after=1 â plus a negative test in `tests/drift-gate-negatives.sh` that is *run against the un-repaired gate* and observed to fail there.
*FALSE pass:* adding the negative test without ever running it against the old gate; mutating the tool instead of the SSOT (the `check_db_seed_coverage` sabotage pattern); accepting `Skip` as coverage; counting a green full-suite run as proof when `check_docs_ratchet` is already red at HEAD, which masks polarity changes.

**H1. One artifact output directory, derived from the SSOT, with all four consumers reading it.** Depends on H0 (`check_build_artifacts_output_dir` must be able to fail first).
*Changes:* a single `[deploy].build_output_dir` (and per-type subdir convention) projected into the `Justfile` recipes, `verify-images`, `stage-mios-repo.sh` and `build-mios.ps1`; `verify-images` fails on an empty artifact set.
*Proves it:* build one ISO, then `just usb-installer` and `just verify-images` both find it; delete every artifact and `verify-images` exits 1 with "0 artifacts".
*FALSE pass:* adding `build/iso/*.iso` to each glob by hand â that is four hand-maintained copies of one fact, which is the defect. Also false: running `verify-images` on a tree that happens to contain a stale qcow2.

**H2. Stage the Path-B payload set, and make the stager fail when it cannot.** Depends on H1.
*Changes:* `stage-mios-repo.sh` copies `usr/share/mios/ventoy/mios-oci-install.ks` to `$REPO_MP/ventoy/`, stages `mios-latest.tar` to `$REPO_MP/` (the location `tools/install.sh:12` defaults to), and exits non-zero â not with a `WARN` â when the tar or the ISO is absent.
*Proves it:* run the stager with `MIOS_STAGE_REPOS=0` against empty mount points and observe exit 1; run it with both artifacts present and assert `find $REPO_MP -type f` contains `ventoy/mios-oci-install.ks` and `mios-latest.tar`.
*FALSE pass:* the current behaviour â two WARNs and `DONE. Boot the USB -> Install MiOS`, exit 0. Also false: satisfying the check via the `git archive HEAD` copy at `repos/MiOS/usr/share/mios/ventoy/`, which Anaconda cannot reach.

**H3. Make the immutable-install entry reachable from the menu Ventoy loads.** Depends on H2.
*Changes:* one rendered menu, generated from the SSOT labels, written to the Ventoy partition under the filename Ventoy reads, with a bootc entry; `cat/loopback.cfg` and the inline `render_loopback()` heredoc collapse into that one generator.
*Proves it:* build a Ventoy-formatted disk image, boot it under QEMU/OVMF, and observe the "Install MiOS (Immutable bootcâ¦)" entry under F6. **Untestable from a text tool without that VM** â nothing short of booting it is proof.
*FALSE pass:* asserting the file exists at the right path. File presence is not menu presence; the current `ventoy_grub.cfg` is present, correct and has no MiOS entry.

**H4. Restore a real installer core to mios.git, or make its copy delegate.** Independent of H1âH3.
*Changes:* either port `do_install_core` from `mios-bootstrap/installation/mios-install.sh:1548`, or delete mios.git's copy and have the entry point exec the bootstrap one; remove the touched paths from `[bootstrap.sync].not_mirrored` so the two are compared.
*Proves it:* `_install_core bootc` on a scratch host changes the host (bootc deployment present) or exits non-zero; `_install_core fhs` writes the overlay. Both observed on a machine, not a dry run.
*FALSE pass:* a dry-run that resolves a command string. `24217fb1` already made the stub fail loudly; a task is not done because the failure message is nicer.

**H5. Fix the mode-swallow in mios-bootstrap.** Independent.
*Changes:* `mios-install.sh:1605` uses the positional mode; `_install_core bootc` runs bootc.
*Proves it:* `bash installation/mios-install.sh _install_core bootc --dry-run` prints a bootc plan, and `_install_core fhs` prints an fhs plan, and the two differ.
*FALSE pass:* checking only that `--type bootc` works. The bug is the *positional* form, which is what the dispatch at `:218` generates.

**H6. Join the MiOS-Cat stage verb to the real `podman save` chain.** Depends on H1, H2.
*Changes:* `cat/lib/cat.sh` and `MiOS-Cat.psm1` invoke the real archive producer and write to the MiOS-Repo path `tools/install.sh` reads; the `echo "Fetching models..."` lines either fetch or are deleted; the `>= 128` disk threshold reads `[cat.data_partition].min_disk_gb`.
*Proves it:* after `stage`, `sha256sum` of the file on the stick equals `sha256sum build/oci-archive/mios-<version>.tar`.
*FALSE pass:* uncommenting the `podman save` line. It writes to `MiOS-Data/images/`, and the installer reads `/mnt/mios-repo/mios-latest.tar`.

**H7. Prove an offline bare-metal install, once.** Depends on H2, H3, H4, H6.
*Proves it:* a machine (or a VM with no NIC attached â not merely unconfigured) boots the medium, installs, reboots, and reports the MiOS release and the bootc labels.
*FALSE pass:* a booted medium; a VM with a NIC present but DHCP unconfigured; an install that ends up as Fedora-plus-overlay via `mios-kickstart.cfg` rather than the carried image.

**H8. Restore a Day-2 update path.** Independent, and the highest-value step for already-deployed machines.
*Changes:* `50-uupd-installer.sh` fails when neither `uupd.timer` nor `bootc-fetch-apply-updates.timer` will be enabled, and does not disable the fallback until the replacement is present; `mios.toml:10159` `fatal = true`; a gate asserts that the *built image* has exactly one enabled OS-update timer.
*Proves it:* `podman run --rm <image> systemctl is-enabled uupd.timer` (or the bootc timer) returns `enabled`; deleting `uupd` from `[packages.updater]` turns the build red.
*FALSE pass:* asserting `[packages.updater]` lists `uupd`. The SSOT already says that and the package is not in the image â `install_packages_strict` passes `--skip-unavailable` too, so "strict" is not strict.

**H9. Make `mios update` reach bootc on every surface.** Depends on H8.
*Changes:* `[verbs.update]` gets a `cmd` pointing at `/usr/bin/mios-update`; `KNOWN_VERBS` in `/usr/bin/mios` gains `update` and `rollback`; `check_verb_backends` treats a `cmd`-less verb as a violation rather than skipping it.
*Proves it:* `bash -lc 'mios update --check'` and `sh -c 'mios update --check'` both reach `bootc upgrade --check`; removing the `cmd` key turns the gate red.
*FALSE pass:* testing only in an interactive shell. `mios-verbs.sh:3` returns early without `PS1`, and the non-interactive path currently ships the word "update" to an LLM.

**H10. Make the greenboot required checks capable of failing.** Independent of H8.
*Changes:* `15-composefs-verity.sh` exits 1 on `composefs requested but not active`; `50-mios-core.sh` either resolves the absolute `/usr/libexec/mios/miosd` path *and* a `greenboot` subcommand exists, or the file is removed â shipping a required check that no-ops is worse than shipping none.
*Proves it:* in a container with a stub `fsverity` and no composefs mount, `15-` exits 1 (the audit's fixture, which currently exits 0); `50-` either runs a real health check or is absent from `required.d`.
*FALSE pass:* adding `exit 1` and confirming the script still returns 0 on a healthy host. The healthy path was never the question.

**H11. Observe one greenboot rollback.** Depends on H10.
*Proves it:* on real hardware or a UEFI VM with a boot counter, deploy an image whose required check fails, and observe the second boot land on the previous deployment with `boot_counter` consumed.
*FALSE pass:* any assertion made inside a container. `systemd-detect-virt --container` â `wsl` makes greenboot skip rollback handling by design; a green run there proves nothing about rollback.

**H12. Guard the ISO credential.** Depends on H1.
*Changes:* `just iso` gets the same `[ -z "${MIOS_USER_PASSWORD_HASH:-}" ] && exit 1` guard as `qcow2` and `vhdx`; `check_replaceme_mount_substitution` asserts the substituted value is non-empty rather than asserting `sed` appears.
*Proves it:* `MIOS_USER_PASSWORD_HASH= just iso` exits 1 before invoking BIB; the gate goes red when the guard is removed.
*FALSE pass:* the existing check â the recipe contains `sed -e`, so it passes regardless of whether anything was substituted.

**H13. Adjudicate the 66 inconclusive gates and the 9 unrefuted CANNOT_FAIL claims.** Depends on H0.
*Changes:* re-derive the inconclusive list (it was lost with the synthesize agent), mutate each gate's own SSOT input, record the four exit codes, and land a negative test for every gate that lacks one. Then empty `[testing].negative_coverage_exempt.exempt` â 55 entries â or justify each remaining one in the SSOT with a reason a reader can check.
*Proves it:* a per-gate table of four exit codes, mutation described, with `mutated-before=0, mutated-after=1` for every repaired gate.
*FALSE pass:* counting gates that "ran and printed passed"; treating an exemption as coverage; reporting a count of tests rather than a count of tests observed to fail against a broken gate.

**H14. Reconcile the two `[cat]` tables and the two `MiOS-Cat.bat` copies, then rename.** Depends on H0 (specifically `check_repo_partition_label_ssot`).
*Proves it:* the two SSOT tables agree key-for-key; the two `.bat` files are one file or one is deleted; then the rename lands atomically and `tools/check-variant-registry.py` goes red on a half-done rename (it demonstrably does â mutating either half returns exit 1).
*FALSE pass:* renaming while `check_repo_partition_label_ssot` still substitutes `MiOS-Repo` for a missing SSOT key â it will report green through the entire operation, which is exactly what it did in the naming research's shadow-root reproduction.

---
