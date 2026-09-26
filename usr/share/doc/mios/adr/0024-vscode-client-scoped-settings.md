<!-- AI-hint: ADR-0024 partitions the VS Code SSOT by mios.toml [dotfiles.vscode]: devcontainer.json / *.code-workspace blocks get only client-portable keys, settings FILES the full profile; sync-dotfiles.py prunes, check_dotfiles_projection gates. -->
<!-- AI-related: usr/share/mios/mios.toml [dotfiles.vscode], .dotfiles/vscode/settings.json, tools/sync-dotfiles.py, usr/libexec/mios/mios-dotfiles-render, automation/98-drift-checks.sh check_dotfiles_projection, tests/drift-gate-negatives.sh test_dotfiles_projection, .devcontainer/devcontainer.json, .devcontainer/artifact-builder/devcontainer.json, mios.code-workspace, .devcontainer/mios-ecosystem.code-workspace, usr/share/doc/mios/adr/0010-ssot-as-system-dotfiles.md -->
---
adr: 0024
title: VS Code settings are partitioned by the client that applies them
status: proposed
date: 2026-09-25
deciders: [operator, ai-pair]
tags: [dotfiles, vscode, codespaces, devcontainer, ssot, projection, drift-gate]
laws: [7, 8, 9, 15]
ssot_keys: [dotfiles.vscode]
related_ws: [WS-DOTFILES]
supersedes: []
superseded_by: []
---

# ADR-0024: VS Code settings are partitioned by the client that applies them

## Status

proposed — 2026-09-25. Amends ADR-0010 (SSOT-as-system-dotfiles), whose VS Code
projection stays in force; this record narrows WHAT reaches one class of its
surfaces. Agents propose, the operator accepts: the code, the gate and the
negative control landed with this record so the decision can be judged on a
green tree, not on a plan.

## Context

ADR-0010 made `.dotfiles/vscode/settings.json` the one VS Code SSOT and
`tools/sync-dotfiles.py` its projector. The projector had two output classes it
treated as one:

- **byte copies** — settings FILES a client reads from disk
  (`etc/skel/.config/Code/User/settings.json`, the code-server seed, the
  `~/.vscode-server/data/*/settings.json` HOME targets);
- **API-applied blocks** — the `customizations.vscode.settings` object of each
  `devcontainer.json` and the `settings` object of each `*.code-workspace`,
  merged in place (`JSON_MERGE_PROJECTIONS`).

The trigger: a GitHub Codespace for MiOS opened in the browser reports
`Unable to write to Workspace Settings because window.customTitleBarVisibility
is not a registered configuration.` The mechanism, read in the VS Code source
(`src/vs/workbench/services/configuration/common/configurationEditing.ts`): a
write through the configuration API first checks the key against
`configurationService.keys().default` and throws `ERROR_UNKNOWN_KEY` on a miss;
a second check refuses any APPLICATION- or MACHINE-scoped key at a Workspace
target ("This setting can be written only into User settings"). Neither check
runs on a settings file read from disk, where an unknown key only warns. The
registry differs per client: `window.titleBarStyle`,
`window.customTitleBarVisibility`, `window.dialogStyle` and `window.zoomLevel`
are registered only in `src/vs/workbench/electron-browser/desktop.contribution.ts`,
which `workbench.desktop.main.ts` alone imports, so the web workbench
(vscode.dev, github.dev, a browser Codespace, code-server) has no registration
for them; `vscode_custom_css.imports` is contributed by an extension that is
`extensionKind: ["ui"]` with no `browser` entry, which a web extension host
never loads. Three of the four `window.*` keys are APPLICATION-scoped as well,
so a Workspace-target write of them was refused on the desktop client too:
they never had an effect from those surfaces on any client.

Two further defects sat in the same block. The merge was additive only (SSOT
keys win, surface-only keys survive), so a key removed from the SSOT lingered
in every surface with nothing to say so. And the SSOT carried keys no current
client or extension registers at all: `workbench.panel.alignment` (runtime
state, never a setting), `vscode_custom_css.policy` (removed from the
extension), `podman.socketPath`/`podman.systemSocketPath` (no extension
registers them; `redhat.vscode-podman` does not exist on the marketplace or
open-vsx) and `docker.dockerPath`/`docker.environment` (renamed by Container
Tools to `containers.containerCommand`/`containers.environment`).

Law 7 forbids the fix that first comes to mind, a literal list of keys in the
projector; Law 8 requires the surfaces to stay regenerate-and-diff gated; Law 9
forbids a second SSOT for the same keys; Law 15 requires the same rule in
`mios-bootstrap.git`, whose `.devcontainer/devcontainer.json` carries the same
block.

## Decision

1. **The partition is SSOT-authored: `mios.toml [dotfiles.vscode]`.** It names
   `desktop_only_keys` (each with the upstream file that registers it),
   `user_only_keys` (registered on every client, APPLICATION-scoped, so refused
   at a Workspace target everywhere), `unregistered_keys` (keys no client or
   extension registers; gone from the SSOT files, and named here so the prune
   evicts them from every surface), `client_portable_surfaces` (this
   repository's API-applied surfaces, repo-relative) and
   `bootstrap_client_portable_surfaces` (the same kind of surface in
   `mios-bootstrap.git`). No key list lives in code.

2. **The rule.** A surface VS Code applies THROUGH ITS CONFIGURATION API on
   whichever client connects gets only the client-portable subset of the SSOT.
   A settings FILE keeps the full desktop profile, because a file with an
   unknown key warns and never throws. The settings object's location is a
   property of the file type (`customizations.vscode.settings` in a
   `devcontainer.json`, `settings` in a `*.code-workspace`), not a per-file
   literal.

3. **The merge prunes.** `tools/sync-dotfiles.py` merges the portable subset
   and REMOVES every partitioned key already present on a client-portable
   surface; surface-only keys still survive. `--check` diffs each surface
   against that projection and reports one line per file and key, in both
   directions: a partitioned key present, and a portable key missing or stale.
   A key that leaves `desktop_only_keys` while the surfaces still lack it is
   therefore red, not silently portable again. `--client-surfaces` restricts a
   run to the tracked, gated surfaces (the byte copies under `etc/skel` are
   gitignored and cannot be gated in a fresh clone). The SSOT itself carrying
   an `unregistered_keys` member is refused at the source.

4. **The gate has both halves.** `mios-dotfiles-render check` (what
   `check_dotfiles_projection` runs, and what a deployed host ships) refuses
   any partitioned key on a client-portable surface, naming file and key;
   `check_dotfiles_projection` then runs `tools/sync-dotfiles.py --check
   --client-surfaces` for the diff. `tests/drift-gate-negatives.sh
   test_dotfiles_projection` plants both failures (a desktop-only key put back
   on a surface; a key dropped from the SSOT list) and requires the gate to go
   red naming them, then green after byte-identical restoration.

## Rationale

- **Law 8, completed rather than bent.** The surfaces stay derived and
  drift-gated; the projection just stopped being a superset. A prune is the
  missing half of a merge: without it, "SSOT wins" cannot express "SSOT no
  longer says this".
- **Law 7 / Law 9.** One partition table, referenced by name from the projector
  and the render tool; the settings content stays in the one settings file. The
  upstream evidence travels as a trailing comment on each key, so the next
  reader can re-check a classification against the VS Code tree instead of
  trusting the list.
- **Nothing is lost that ever worked.** The desktop title-bar and dialog keys
  are APPLICATION-scoped: a workspace or devcontainer block could never set them
  on any client. They keep working exactly where they always did, the User
  settings file, which the byte copies and the HOME targets still carry.
- **Check-Without-Diff is designed out.** A scan that only looks for the listed
  keys on the surfaces passes when a key leaves the list; the diff against the
  projection catches that case, and the negative control plants it.

## Alternatives considered

- **Keep one block and accept the toast.** Rejected: whether the writer stops
  at the first refused key is unverified, so every later setting in the block
  may silently not apply; and three of the keys never applied from there anyway.
- **A literal desktop-only list in `sync-dotfiles.py`.** Rejected (Law 7); a
  list in code is also invisible to the Portal (ADR-0009) and to the render
  tool that ships in the image.
- **Two SSOT files, one per client.** Rejected (Law 9): every portable key
  would be stated twice and could drift between the two.
- **A second `[dotfiles.registry.*]` kind.** Rejected for now: the registry
  projects one template to one target; these surfaces are hand-authored files
  with a MiOS-owned subtree, which is `sync-dotfiles.py`'s job. The partition
  is data the registry could consume later.

## Consequences

Positive:
- A browser Codespace applies the devcontainer block without an unregistered
  key in it; a key removed from the SSOT leaves every surface on the next sync;
  `--check` says which file and which key, both ways.
- Dead keys are gone from the SSOT and every copy; the Container Tools
  replacements (`containers.containerCommand`, `containers.environment`) reach
  every surface, and the surfaces list `ms-azuretools.vscode-containers` (the
  extension that registers them) in place of the pack id and the nonexistent
  `redhat.vscode-podman`.

Costs and open points (honest):
- The desktop title-bar/dialog customisation now travels only with the User
  settings file (dotfiles, skel, Settings Sync), not with the repository. That
  is where it already had to live.
- The Custom CSS terminal styling cannot load in a web client through the
  extension; code-server keeps `mios-vscode-custom-css patch`.
- Where the Codespaces writer targets (the error names the Workspace target;
  GitHub's documentation says the Remote scope) and whether it aborts at the
  first refused key are unverified. Extension-contributed keys
  (`containers.*`, `python.defaultInterpreterPath`) are registered only once
  their extension is; if the browser client still reports one after a rebuild,
  it belongs in `[dotfiles.vscode]` too.
- A browser client cannot be exercised from the build host, so the fix is
  proven by the gate and the negative controls, not by a Codespace session.

## Implementation

- `usr/share/mios/mios.toml` — `[dotfiles.vscode]` beside `[dotfiles]`
  (`desktop_only_keys`, `user_only_keys`, `unregistered_keys`,
  `client_portable_surfaces`, `bootstrap_client_portable_surfaces`).
- `.dotfiles/vscode/settings.json`, `.dotfiles/code-server/settings.json` —
  unregistered keys deleted; `docker.*` renamed to `containers.*`.
- `tools/sync-dotfiles.py` — reads the partition through `mios_toml`, derives
  the surfaces and their settings path from the SSOT, merges the portable
  subset, prunes, and reports per file and key; `--client-surfaces`;
  temp-file + rename writes; `MIOS_ROOT` / `MIOS_BOOTSTRAP_ROOT` roots.
- `usr/libexec/mios/mios-dotfiles-render` — `check` refuses a partitioned key
  on a client-portable surface.
- `automation/98-drift-checks.sh check_dotfiles_projection` — the second leg.
- `tests/drift-gate-negatives.sh test_dotfiles_projection` — both plants.
- The API-applied surfaces in both repositories, re-projected; extension lists
  aligned with the keys they carry.
- `usr/libexec/mios/mios-vscode-custom-css`, `usr/share/doc/mios/manual/ch16-ide-custom-css.md`,
  `.dotfiles/README.md` — the same partition, stated where a reader meets it.

## References

- ADR-0010 (SSOT-as-system-dotfiles) — the projection this record amends:
  `0010-ssot-as-system-dotfiles.md`.
- ADR-0009 (Unified config surface) — `[dotfiles.vscode]` is Portal-editable
  like every other `mios.toml` table.
- VS Code: `src/vs/workbench/services/configuration/common/configurationEditing.ts`
  (unknown-key and scope checks), `src/vs/workbench/electron-browser/desktop.contribution.ts`
  (desktop-only registrations), `src/vs/workbench/workbench.desktop.main.ts` and
  `workbench.web.main.ts` (which entry point imports it),
  `src/vs/workbench/browser/workbench.contribution.ts` (`window.menuBarVisibility`,
  APPLICATION scope), `src/vs/workbench/browser/layout.ts` (panel alignment is
  runtime state).
- VS Code web extensions guide: an extension with only a `main` entry is not a
  web extension and is ignored by the web extension host.
- Container Tools (`ms-azuretools.vscode-containers`) manifest:
  `containers.containerCommand`, `containers.environment`.
- MiOS Laws 7/8/9/15: `usr/share/mios/mios.toml [laws]`.
