# WS-7 — Verity-rooted UKI + fapolicyd execution whitelist

> Status: scaffolded 2026-06-04, **DEFAULT-OFF / OBSERVE-ONLY**. Companion:
> `aios-implementation-plan.md` (Appendix B · WS-7), `upstream/bootc.md`,
> `upstream/composefs.md`, `coderun-sandbox.md`.

## TL;DR — the one rule

**fapolicyd ships in PERMISSIVE (observe) mode and the verity UKI is a build
ARTIFACT that is never made the active boot entry by default.** Enforce-mode
fapolicyd on an incomplete whitelist, or a mis-signed / `verity.require` UKI,
**bricks boot** — and on an immutable composefs root there is no easy in-place
recovery once the deny has cut the recovery shell. Promotion to enforce is a
deliberate, rollback-tested operator step. Nothing in this scaffold flips it.

## What this scaffold ships

| File | Role | Default posture |
|---|---|---|
| `usr/lib/fapolicyd/mios-ws7-permissive.conf` | fapolicyd config drop-in, `permissive = 1` | observe; not applied unless gated on |
| `usr/lib/fapolicyd/rules.d/80-mios-agent-codegen.rules` | exec carve-out for the sandboxed agent codegen | inert until enforce |
| `usr/lib/bootc/kargs.d/32-mios-ws7-uki.toml` | boot posture kargs | only `fapolicyd.permissive=1` active; enforce/lockdown/verity.require **commented** |
| `automation/lib/ws7-uki-fapolicyd-build.sh` | gated build step (observe install + verity UKI build) | no-op unless SSOT flags true; **not** a numbered pipeline step, so `build.sh` never auto-runs it |
| `usr/share/mios/mios.toml` (shared_edits) | SSOT flags `[security.fapolicyd_observe].enable`, `[uki].verity_uki_build` | both `false` |

### SSOT knobs (mios.toml, both default `false`)

```toml
[security.fapolicyd_observe]
enable = false   # install the permissive/observe drop-in + codegen carve-out

[uki]
verity_uki_build = false   # build the verity-rooted UKI artifact (ukify)
```

These flow `mios.toml -> tools/lib/userenv.sh (MIOS_FAPOLICYD_OBSERVE_ENABLE /
MIOS_UKI_VERITY_BUILD) -> the build step`. The build step ALSO reads them
directly from the resolved TOML via its `_ws7_scalar` helper, so it is correct
whether or not `userenv.sh` ran.

### The codegen carve-out

fapolicyd enforce mode would deny the agent's *legitimate* model-generated code
from executing — even though that code only ever runs inside the coderun
sandbox (rootless podman, `Network=none`, `DropCapability=ALL`, seccomp,
writable `/work`+`/tmp` only; see `coderun-sandbox.md`). `80-mios-agent-codegen.rules`
re-permits exec **scoped to the sandbox roots only** (resolved from
`mios.toml [paths].coderun_workspace_root` / `.coderun_snapshots_root` /
`ai_scratch_dir`, rendered by the build step). It is numbered `80-` so it is
evaluated **before** the `90-mios-deny.rules` deny-by-default block (rules.d is
read lexicographically, first match wins). It is inert while permissive.

## Promotion procedure: permissive → enforce (operator-gated)

Do this **only** in a dedicated image-build + boot-test session, never as part
of the "everything on" flip. Have a known-good prior bootc deployment staged
so `bootc rollback` is a one-command recovery.

1. **Enable observe.** Set `[security.fapolicyd_observe].enable = true` in
   `/etc/mios/mios.toml`, run the gated build step (or wire it on per the
   shared_edit below), rebuild + deploy. fapolicyd now LOGS would-be denials
   and blocks nothing.

2. **Collect the would-deny log.** Run the box through a full week of real
   workloads (every service start, every agent turn, every coderun dry-run).
   Read what fapolicyd *would* have denied:
   ```bash
   journalctl -u fapolicyd | grep -E 'dec=deny'
   # or the richer report:
   fapolicyd-cli --dump-cache | less
   ```

3. **Close the gaps in the whitelist, NOT by re-broadening.** For each
   legitimate path fapolicyd flagged, add a targeted
   `allow perm=execute path=/exact/path : all` to a new `rules.d/` file (do
   **not** widen the `uid=0` catch-all in `etc/fapolicyd/fapolicyd.rules`).
   Re-build, re-deploy, repeat step 2 until the would-deny log is empty across
   a full workload cycle (including a fresh boot, a `bootc upgrade`, an agent
   coderun, and a podman pull).

4. **Build + sign the verity UKI (optional, separate gate).** Set
   `[uki].verity_uki_build = true`. The build step runs `ukify build` measuring
   the composefs fs-verity digest. The artifact lands at
   `/usr/lib/modules/<kver>/mios-verity.efi` — **unsigned and not installed**.
   Sign it with a MOK already enrolled in the firmware, install it as a boot
   entry, and **boot-test it with the old entry still selectable**. Confirm a
   `bootc rollback` works before removing the fallback entry.

5. **Flip enforce — last, and only after 2–4 pass clean.** Uncomment the
   relevant kargs in `32-mios-ws7-uki.toml` (`fapolicyd.permissive=0`, and only
   if the signed UKI booted, `lockdown=confidentiality` / `rootflags=verity.require`),
   set `etc/fapolicyd/fapolicyd.conf` `permissive = 0`, rebuild, deploy.
   **Boot-test immediately.** If the box does not come up, `bootc rollback`
   from the bootloader to the prior (permissive) deployment.

6. **Verify enforce + the carve-out together.** Confirm services + the agent
   stack run, AND confirm a coderun dry-run still executes (the carve-out
   holds), AND confirm an arbitrary script dropped under `/home` or `/tmp`
   outside the sandbox is denied:
   ```bash
   echo 'echo nope' > /tmp/x.sh; chmod +x /tmp/x.sh; /tmp/x.sh   # should be denied
   ```

## Rollback / panic

- From the bootloader: pick the previous deployment (bootc keeps it staged).
- `bootc rollback` then reboot.
- Emergency disable without rebuilding: append `fapolicyd.permissive=1` (or
  `systemd.mask=fapolicyd.service`) at the bootloader edit prompt for one boot,
  then fix the rules and redeploy.

## Why default-off is deliberate, not incomplete

Per `aios-implementation-plan.md` §Appendix B, WS-7 is the single place where
"default on, debug live" is the wrong order. Everything here is reviewed and in
tree so the carve-out + observe posture already exist before anyone considers
enforce — but the brick-capable flips stay commented/`false` until the
procedure above passes on the actual image.
