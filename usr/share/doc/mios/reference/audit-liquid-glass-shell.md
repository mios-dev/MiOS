<!-- AI-hint: Design for the MiOS liquid-glass desktop shell (Apple liquid-glass north star) projected FROM SSOT: adds a flat mios.toml [effects] section (blur/rounding/opacity/shadow/animation-curves) and projects it to a NEW Hyprland fragment usr/share/mios/hyprland/effects.conf via a mios-dotfiles-render SETTINGS surface [dotfiles.registry.hyprland-effects], plus the Quickshell theme.json bridge -- so compositor + shell effects are single-sourced, drift-gated (check 25/index-row 28), and runtime-refreshable via one command. Read before hardcoding any Hyprland decoration/animation value. -->
<!-- AI-related: usr/share/mios/hyprland/hyprland.conf, usr/share/mios/mios.toml [effects] + [dotfiles.registry.hyprland-effects] + [colors], usr/libexec/mios/mios-dotfiles-render, usr/libexec/mios/mios-sync-theme, usr/share/mios/theme/templates/quickshell-Theme.qml.tmpl, usr/share/mios/quickshell/Theme.qml, automation/65-bake-hyprland.sh, tools/lib/userenv.sh, automation/98-drift-checks.sh -->

# MiOS Liquid-Glass Desktop Shell — SSOT Projection Design

**Scope.** Make every Hyprland "liquid-glass" effect (blur, corner rounding, per-state opacity, shadow, dim, and the spring/overshoot animation curves) *derive from `mios.toml`* instead of being hardcoded, using the projection machinery MiOS already ships (`mios-dotfiles-render` + `mios-sync-theme`). Deliverable includes: the exact SSOT keys (`[effects]`), the projection mapping to `hyprland.conf`, and a **drop-in artifact** — a fragment template with placeholders + the `[effects]` block to paste into `mios.toml`. Claude-lane shell; work conceptually **on main**.

---

## 1. Current state (grounded)

### 1.1 The effects are hardcoded in two places

The compositor config `usr/share/mios/hyprland/hyprland.conf` hardcodes the entire glass stack:

- `decoration.rounding = 12` (`hyprland.conf:31`)
- `active_opacity/inactive_opacity/fullscreen_opacity = 1.0 / 0.93 / 1.0` (`:32-34`)
- `blur { size = 10; passes = 4; noise = 0.010; contrast = 1.08; brightness = 0.88; vibrancy = 0.25; vibrancy_darkness = 0.08; ... }` (`:35-49`)
- `drop_shadow`, `shadow_range = 22`, `shadow_render_power = 4`, `col.shadow = rgba(0A0A0A99)`, `dim_inactive`, `dim_strength = 0.05` (`:50-57`)
- 4 `bezier` curves + 13 `animation` bindings (`:65-84`)
- 3 `layerrule = ignorealpha …` shell-surface alphas (`:90-95`)

The **same block is duplicated** inside the build-time generator `automation/65-bake-hyprland.sh:44-110` (a single-quoted heredoc that rewrites `/usr/share/mios/hyprland/hyprland.conf` at bake). **Only the colors are SSOT today**: `col.active_border` / `col.inactive_border` use `@@MIOS_COLOR_*@@` placeholders that `65-bake-hyprland.sh:177-181` substitutes with `sed` from `MIOS_COLOR_*` (exported by `tools/lib/userenv.sh` from `[colors]`). Every *numeric/curve* effect is a magic number in both copies — the exact anti-pattern the SSOT north star forbids.

### 1.2 The projection engine already exists (and how it works)

`usr/libexec/mios/mios-theme-render` is now a deprecation shim (`:8`) delegating to `usr/libexec/mios/mios-dotfiles-render` — the global runtime projector. Mechanics that constrain the design:

- **Token sentinel** `@MIOS:([a-z0-9_.-]+)@` (`mios-dotfiles-render:37`). **Lowercase-only** — an uppercase letter in a token name is never matched, so the key ships un-substituted. ⇒ *every `[effects]` key must be all-lowercase.*
- **SETTINGS surface** (`section = "<name>"`): `_settings()` (`:62-70`) flattens `[section]` scalars to `@MIOS:<section>_<key>@`, formatting each via `_fmt_conf()`. This is exactly how `[btop]` → `etc/btop/btop.conf` works (`[dotfiles.registry.btop-conf]`, `mios.toml:11107`).
- **`_fmt_conf()` renders a bool as btop's `True`/`False`** (`:53-59`) — **NOT** Hyprland's lowercase `true`/`false`. ⇒ *boolean effects must be authored as quoted strings `"true"`/`"false"`* so they pass through verbatim. Numbers stay bare.
- `_settings()` **skips nested tables and arrays** (`:66-68`). ⇒ *`[effects]` must be flat* (no `[effects.blur]` sub-table; bezier control-points as strings, not TOML arrays).
- **Arbitrary-token fallback** `_resolve_arbitrary_token()` (`:107-122`): a token not in the surface's resolved map is walked as a dotted/underscore path against the full merged TOML. This lets a *color* surface (e.g. `quickshell`) still reference `@MIOS:effects_rounding@`.
- **Drift gate**: `check_dotfiles_projection()` (`automation/98-drift-checks.sh:1728`, code-label "(25)", `drift-gate-index.tsv` row **28**) re-renders every surface and fails on any diff. Its **ORPHAN-TEMPLATE completeness floor** (`mios-dotfiles-render:982-994`) fails if a `*.tmpl` in a registered template dir has no `[dotfiles.registry.*]` entry — so the template and the registry block must land together.
- **Surface registry is SSOT** in `mios.toml [dotfiles.registry.*]` (`:11070+`), each entry `template`/`target`/optional `section`/optional `[.apply.target].{linux,windows}`.

### 1.3 The shell side (Quickshell) is half-wired

`usr/share/mios/quickshell/Theme.qml` reads `/etc/mios/theme/theme.json` (written by `mios-sync-theme`) for colors + `radius_px`, but:
- `radius_px` is **hardcoded `10`** in `mios-sync-theme:86` (not read from any effects SSOT), and its own comment admits it only "matches hyprland.conf decoration.rounding" *by hand*.
- `panelOpacity: 0.85` (`Theme.qml:37`, used at `Sidebar.qml:31`) is **never** in `theme.json` — a second unmanaged magic number.

So the shell's rounding/opacity and the compositor's rounding/opacity are *supposed* to agree but are three independent literals. `[effects]` unifies them.

### 1.4 There is no `[effects]` section yet

Confirmed: `grep '^\[effects' mios.toml` → none. `userenv.sh`'s canonical walk (`tools/lib/userenv.sh:192-206`) auto-emits `MIOS_<SECTION>_<KEY>` for any section, so **adding `[effects]` immediately exports `MIOS_EFFECTS_*`** to shell/bake with no code change — the enabler for the bake-time path (§5).

---

## 2. Design: one `[effects]` SSOT, three projections

```
              mios.toml  [effects]   (the ONE source of truth)
                    │
     ┌──────────────┼───────────────────────────────┐
     │              │                                │
 mios-dotfiles-  mios-sync-theme                userenv.sh walk
 render (surface  (theme.json:                  (MIOS_EFFECTS_*)
 hyprland-        radius_px + panel_opacity)          │
 effects)              │                              │
     │                 │                              │
 usr/share/mios/  /etc/mios/theme/theme.json    build-time bake
 hyprland/        → Quickshell Theme.qml         (65-bake-hyprland.sh,
 effects.conf     (bar/rail/rofi frosting)        optional §5 path)
     │
 `source`d by hyprland.conf   ← compositor blur/round/opacity/curves
```

**Primary integration** = a `mios-dotfiles-render` **SETTINGS surface** (`section = "effects"`) rendering a Hyprland fragment `effects.conf`, which the base `hyprland.conf` `source=`s. This is drift-gated (check 25/row 28), runtime-refreshable (`mios-sync-theme`), and live-apply-able (`mios dotfiles apply` → `~/.config/hypr/effects.conf`) — identical to the proven `[btop]` → `btop.conf` surface. Colors stay on their existing `@@MIOS_COLOR_*@@` sed path (Hyprland needs `#`-less hex, which the color tokens don't provide — see §4.3), so the fragment is **effects-only**.

---

## 3. Drop-in artifact 1 — the `[effects]` block for `mios.toml`

Paste this as a new top-level section (recommended location: immediately after `[colors]`, near `mios.toml:8793`, so the whole visual-identity SSOT is contiguous).

```toml
# ----------------------------------------------------------------------------
# [effects] -- SSOT for the liquid-glass compositor + shell effects (Apple

*Note: Findings resolved and verified in active repository implementations.*
