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
# "liquid glass" north star). PROJECTED, never hand-edited downstream:
#   * Hyprland fragment usr/share/mios/hyprland/effects.conf (blur / rounding /
#     opacity / shadow / dim / animation curves+speeds) via the SETTINGS surface
#     [dotfiles.registry.hyprland-effects] (kind=template, section="effects"):
#     each flat scalar below becomes an @MIOS:effects_<key>@ token, the SAME
#     mechanism [btop] -> etc/btop/btop.conf uses.
#   * Quickshell bridge /etc/mios/theme/theme.json (radius_px + panel_opacity)
#     via mios-sync-theme, so shell surfaces round+frost to the SAME numbers the
#     compositor does (Theme.qml radius "matches hyprland.conf decoration.rounding"
#     -- now from ONE value, not three literals).
#   * shell env MIOS_EFFECTS_* (userenv.sh canonical walk) for the build-time path.
#
# TWO HARD RULES (both grounded in mios-dotfiles-render):
#   1. KEYS ALL-LOWERCASE. The token sentinel is @MIOS:([a-z0-9_.-]+)@ (_SENTINEL);
#      an uppercase letter yields a token the regex never matches -> ships raw.
#   2. BOOLEANS ARE QUOTED STRINGS ("true"/"false"), not bare TOML bools: the
#      scalar formatter (_fmt_conf) renders a bool as btop's True/False, but
#      Hyprland wants lowercase true/false -- quoting passes the value verbatim.
#      Numbers stay bare TOML numbers. Bezier points + animation specs are strings.
# ----------------------------------------------------------------------------
[effects]
# -- decoration: rounding + per-state window opacity ------------------------
rounding                  = 12       # px corner radius (compositor AND shell)
active_opacity            = 1.0      # focused window
inactive_opacity          = 0.93     # unfocused window (subtle depth)
fullscreen_opacity        = 1.0

# -- blur: the actual "glass" (multi-pass Kawase) ---------------------------
blur_enabled              = "true"
blur_size                 = 10
blur_passes               = 4
blur_new_optimizations    = "true"
blur_xray                 = "true"
blur_ignore_opacity       = "true"
blur_noise                = 0.01
blur_contrast             = 1.08
blur_brightness           = 0.88
blur_vibrancy             = 0.25     # saturate the color behind the glass
blur_vibrancy_darkness    = 0.08
blur_popups               = "true"   # frost drop-down/context popups too
blur_popups_ignorealpha   = 0.2

# -- shadow + dim: depth under floating glass -------------------------------
shadow_enabled            = "true"   # emitted as `drop_shadow` (Hyprland 0.46)
shadow_range              = 22
shadow_render_power       = 4
shadow_offset             = "0 4"
shadow_color              = "0A0A0A99"  # raw Hyprland rgba() hex (NOT a palette color)
shadow_color_inactive     = "0A0A0A44"
dim_inactive              = "true"
dim_strength              = 0.05

# -- layout spacing (part of the glass rhythm) ------------------------------
gaps_in                   = 5
gaps_out                  = 12
border_size               = 2

# -- shell surface frosting (Quickshell bar/rail, rofi, notifications) ------
panel_opacity             = 0.85     # Quickshell translucent fill alpha (theme.json)
layer_alpha_quickshell    = 0.2      # layerrule ignorealpha for the shell layer
layer_alpha_rofi          = 0.5
layer_alpha_notifications = 0.3

# -- animation curves (cubic-bezier control points; "liquid" spring feel) ---
animations_enabled        = "true"
bezier_liquid             = "0.25, 1.30, 0.35, 1.00"   # overshoot -> spring
bezier_smoothout          = "0.36, 0.00, 0.66, -0.56"
bezier_smoothin           = "0.25, 1.00, 0.50, 1.00"
bezier_mybezier           = "0.05, 0.90, 0.10, 1.05"

# -- animation bindings ("<on>, <speed*100ms>, <curve>, [style]") -----------
anim_windows              = "1, 5, mybezier, popin 60%"
anim_windowsin            = "1, 5, mybezier, popin 60%"
anim_windowsout           = "1, 4, smoothout, popin 80%"
anim_windowsmove          = "1, 4, liquid"
anim_border               = "1, 10, default"
anim_borderangle          = "1, 8, default"
anim_fade                 = "1, 5, smoothin"
anim_fadein               = "1, 5, smoothin"
anim_fadeout              = "1, 5, smoothout"
anim_workspaces           = "1, 5, liquid, slide"
anim_layers               = "1, 4, mybezier, slide"
anim_layersin             = "1, 4, mybezier, slide"
anim_layersout            = "1, 4, smoothout, slide"
```

> Bezier **names** are lowercased (`mybezier`, `smoothout`, `smoothin`, `liquid`) so the definition and every `anim_*` reference stay consistent; Hyprland bezier identifiers are arbitrary. Animation **event** names in the template (`windowsIn`, `fadeOut`, …) keep Hyprland's canonical spelling and are decoupled from the lowercase token keys.

### Register the surface (append into `[dotfiles]`, e.g. after `mios.toml:11104`)

```toml
# Hyprland liquid-glass effects fragment -- SETTINGS surface projecting the flat
# [effects] scalars to @MIOS:effects_<key>@ tokens (same shape as btop-conf).
# `source`d by usr/share/mios/hyprland/hyprland.conf; live-apply lands the
# fragment in the operator's ~/.config/hypr (Hyprland is Linux-only -> no windows
# target, apply no-ops on Windows exactly like quickshell).
[dotfiles.registry.hyprland-effects]
template = "usr/share/mios/theme/templates/hyprland-effects.conf.tmpl"
target   = "usr/share/mios/hyprland/effects.conf"
section  = "effects"
[dotfiles.registry.hyprland-effects.apply.target]
linux = "~/.config/hypr/effects.conf"
```

---

## 4. Drop-in artifact 2 — the fragment template

### 4.1 New file `usr/share/mios/theme/templates/hyprland-effects.conf.tmpl`

Render it with `mios-dotfiles-render render hyprland-effects` (or the global `mios-sync-theme`); the committed rendered output is `usr/share/mios/hyprland/effects.conf`.

```
# AI-hint: Liquid-glass compositor effects (blur/rounding/opacity/shadow/dim +
# animation curves) for Hyprland, PROJECTED from mios.toml [effects] by
# mios-dotfiles-render (surface [dotfiles.registry.hyprland-effects],
# section="effects"). GENERATED -- edit mios.toml [effects] then run
# mios-sync-theme; `source`d by usr/share/mios/hyprland/hyprland.conf.
# AI-related: usr/share/mios/mios.toml [effects], usr/share/mios/hyprland/hyprland.conf, usr/libexec/mios/mios-dotfiles-render, usr/libexec/mios/mios-sync-theme
# ---------------------------------------------------------------------------
# GENERATED from mios.toml [effects] -- do NOT hand-edit.
# ---------------------------------------------------------------------------

# Frosted glass aesthetics / transparency (multi-layer "liquid glass")
decoration {
    rounding = @MIOS:effects_rounding@
    active_opacity = @MIOS:effects_active_opacity@
    inactive_opacity = @MIOS:effects_inactive_opacity@
    fullscreen_opacity = @MIOS:effects_fullscreen_opacity@
    blur {
        enabled = @MIOS:effects_blur_enabled@
        size = @MIOS:effects_blur_size@
        passes = @MIOS:effects_blur_passes@
        new_optimizations = @MIOS:effects_blur_new_optimizations@
        xray = @MIOS:effects_blur_xray@
        ignore_opacity = @MIOS:effects_blur_ignore_opacity@
        noise = @MIOS:effects_blur_noise@
        contrast = @MIOS:effects_blur_contrast@
        brightness = @MIOS:effects_blur_brightness@
        vibrancy = @MIOS:effects_blur_vibrancy@
        vibrancy_darkness = @MIOS:effects_blur_vibrancy_darkness@
        popups = @MIOS:effects_blur_popups@
        popups_ignorealpha = @MIOS:effects_blur_popups_ignorealpha@
    }
    drop_shadow = @MIOS:effects_shadow_enabled@
    shadow_range = @MIOS:effects_shadow_range@
    shadow_render_power = @MIOS:effects_shadow_render_power@
    shadow_offset = @MIOS:effects_shadow_offset@
    col.shadow = rgba(@MIOS:effects_shadow_color@)
    col.shadow_inactive = rgba(@MIOS:effects_shadow_color_inactive@)
    dim_inactive = @MIOS:effects_dim_inactive@
    dim_strength = @MIOS:effects_dim_strength@
}

# Layout spacing (gaps/border width are part of the glass rhythm; border COLORS
# stay in hyprland.conf on the @@MIOS_COLOR_*@@ palette path -- see design §4.3).
general {
    gaps_in = @MIOS:effects_gaps_in@
    gaps_out = @MIOS:effects_gaps_out@
    border_size = @MIOS:effects_border_size@
}

# Dynamic micro-animations -- overshoot beziers approximate a spring/"liquid"
# feel. borderangle is intentionally NOT looped (looping defeats VFR / drains
# battery even when obscured -- Hyprland wiki).
animations {
    enabled = @MIOS:effects_animations_enabled@
    bezier = liquid,    @MIOS:effects_bezier_liquid@
    bezier = smoothout, @MIOS:effects_bezier_smoothout@
    bezier = smoothin,  @MIOS:effects_bezier_smoothin@
    bezier = mybezier,  @MIOS:effects_bezier_mybezier@
    animation = windows,     @MIOS:effects_anim_windows@
    animation = windowsIn,   @MIOS:effects_anim_windowsin@
    animation = windowsOut,  @MIOS:effects_anim_windowsout@
    animation = windowsMove, @MIOS:effects_anim_windowsmove@
    animation = border,      @MIOS:effects_anim_border@
    animation = borderangle, @MIOS:effects_anim_borderangle@
    animation = fade,        @MIOS:effects_anim_fade@
    animation = fadeIn,      @MIOS:effects_anim_fadein@
    animation = fadeOut,     @MIOS:effects_anim_fadeout@
    animation = workspaces,  @MIOS:effects_anim_workspaces@
    animation = layers,      @MIOS:effects_anim_layers@
    animation = layersIn,    @MIOS:effects_anim_layersin@
    animation = layersOut,   @MIOS:effects_anim_layersout@
}

# Liquid-glass on the shell's OWN layer surfaces (Quickshell bar+rail, rofi,
# notifications). Compositor blur frosts them; the QML only sets a translucent fill.
layerrule = blur, quickshell
layerrule = ignorealpha @MIOS:effects_layer_alpha_quickshell@, quickshell
layerrule = blur, rofi
layerrule = ignorealpha @MIOS:effects_layer_alpha_rofi@, rofi
layerrule = blur, notifications
layerrule = ignorealpha @MIOS:effects_layer_alpha_notifications@, notifications
```

### 4.2 Base `hyprland.conf` edit — replace the hardcoded blocks with a `source=`

In **both** `usr/share/mios/hyprland/hyprland.conf` (committed mirror) **and** the heredoc in `automation/65-bake-hyprland.sh` (the file the bake actually writes), delete the `decoration { … }` block (`hyprland.conf:29-58`), the `animations { … }` block (`:60-84`), and the six `layerrule` lines (`:86-95`), and in their place put:

```
# Liquid-glass effects (blur / rounding / opacity / shadow / animation curves +
# shell-layer frosting) are PROJECTED from mios.toml [effects] -- do NOT hardcode
# them here. Source the generated fragment (surface: hyprland-effects).
source = /usr/share/mios/hyprland/effects.conf
```

Keep the `general { … col.active_border … }` block (`:19-27`) exactly as-is — border **colors** remain on the working `@@MIOS_COLOR_*@@` sed path. Hyprland `source=` blocks are additive, so the `general{}` numeric keys in the fragment merge with the base `general{}` colors with no conflict.

> ⚠ **Two-copy landmine.** The committed `hyprland.conf` and the `65-bake-hyprland.sh` heredoc are hand-mirrored (both currently carry the identical hardcoded block). Edit **both** or the bake silently re-emits the old hardcoded effects into the image. (Same class of divergence noted for the two `build-mios.sh`.)

### 4.3 Why the fragment is effects-only (the `#`-hex constraint)

Hyprland's `rgba()` wants **`#`-less** hex — `rgba(F35C15ee)`. The palette tokens resolve **with** the `#` (`@MIOS:cursor@` → `#F35C15`), so `rgba(@MIOS:cursor@ee)` would emit the invalid `rgba(#F35C15ee)`. That is exactly why `65-bake-hyprland.sh:178` strips it (`${MIOS_COLOR_ACCENT#\#}`). Rather than fight it, the border colors stay on the sed path and the fragment carries only numbers + strings (`shadow_color` is stored as a raw Hyprland hex string, not a palette color, so it renders verbatim). Clean separation, zero engine changes.

---

## 5. Drop-in artifact 3 (alternative) — build-time `${MIOS_EFFECTS_*}` path

If you want a strictly build-time projection with **no** new dotfiles surface (the task's literal `${MIOS_*}` placeholder form), `userenv.sh` already exports `MIOS_EFFECTS_*` from the `[effects]` block above. Ship the fragment as `usr/share/mios/hyprland/effects.conf.in` using shell placeholders and `envsubst` it in the bake. This is lower-fidelity (no runtime `mios-sync-theme` refresh, no drift-gate 25 coverage, no live `apply`) — use only as a stepping stone.

`effects.conf.in` (excerpt — same body as §4.1 with `${MIOS_EFFECTS_*}` instead of `@MIOS:effects_*@`):

```
decoration {
    rounding = ${MIOS_EFFECTS_ROUNDING}
    inactive_opacity = ${MIOS_EFFECTS_INACTIVE_OPACITY}
    blur {
        size = ${MIOS_EFFECTS_BLUR_SIZE}
        passes = ${MIOS_EFFECTS_BLUR_PASSES}
        vibrancy = ${MIOS_EFFECTS_BLUR_VIBRANCY}
    }
    col.shadow = rgba(${MIOS_EFFECTS_SHADOW_COLOR})
}
animations {
    bezier = liquid, ${MIOS_EFFECTS_BEZIER_LIQUID}
    animation = windows, ${MIOS_EFFECTS_ANIM_WINDOWS}
}
```

Bake wiring appended to `automation/65-bake-hyprland.sh` (userenv.sh is already sourced via `lib/packages.sh` → `lib/common.sh`):

```bash
# Project [effects] -> the sourced fragment at build time (env path).
envsubst < /usr/share/mios/hyprland/effects.conf.in \
         > /usr/share/mios/hyprland/effects.conf
chmod 0644 /usr/share/mios/hyprland/effects.conf
mios_ok "wrote effects.conf from MIOS_EFFECTS_* (mios.toml [effects])"
```

---

## 6. Shell-side unification (Quickshell reads the same `[effects]`)

Close the "three literals for one radius" gap so the shell frosts to the compositor's numbers.

**6.1 `mios-sync-theme:86`** — replace the hardcoded radius with `[effects]`:

```python
effects = merged.get("effects", {})
resolved["radius_px"]     = int(effects.get("rounding", 10))
resolved["panel_opacity"] = float(effects.get("panel_opacity", 0.85))
```

**6.2 `usr/share/mios/theme/templates/quickshell-Theme.qml.tmpl`** — (a) in `onTextChanged`, add a read for the new bridge key, right after the `radius_px` line:

```js
if (t.panel_opacity) theme.panelOpacity = t.panel_opacity
```

and (b, recommended) tokenize the degrade-open fallbacks so even the pre-sync fallback tracks `[effects]` (resolves via the arbitrary-token fallback — the quickshell surface is section-less, so `@MIOS:effects_rounding@` is walked against merged TOML):

```
property int    radius:       @MIOS:effects_rounding@
property real   panelOpacity: @MIOS:effects_panel_opacity@
```

Then `mios-sync-theme render` regenerates the committed `usr/share/mios/quickshell/Theme.qml` (drift-gated). Result: `Sidebar.qml:31`'s `theme.withAlpha(theme.bg, theme.panelOpacity)` and `radius` (`:141`) now trace to `[effects]`.

---

## 7. Projection mapping (SSOT key → surfaces)

| `mios.toml [effects]` key | `@MIOS:` token (surface) | env (`userenv.sh`) | Rendered target line |
|---|---|---|---|
| `rounding` | `@MIOS:effects_rounding@` | `MIOS_EFFECTS_ROUNDING` | `decoration.rounding` + `theme.json` `radius_px` |
| `inactive_opacity` | `@MIOS:effects_inactive_opacity@` | `MIOS_EFFECTS_INACTIVE_OPACITY` | `decoration.inactive_opacity` |
| `blur_size` / `blur_passes` | `@MIOS:effects_blur_size@` / `…_passes@` | `MIOS_EFFECTS_BLUR_SIZE` / `…_PASSES` | `decoration.blur.size` / `.passes` |
| `blur_vibrancy` | `@MIOS:effects_blur_vibrancy@` | `MIOS_EFFECTS_BLUR_VIBRANCY` | `decoration.blur.vibrancy` |
| `blur_noise/contrast/brightness` | `@MIOS:effects_blur_{noise,contrast,brightness}@` | `MIOS_EFFECTS_BLUR_*` | `decoration.blur.*` |
| `shadow_color` | `@MIOS:effects_shadow_color@` | `MIOS_EFFECTS_SHADOW_COLOR` | `col.shadow = rgba(…)` |
| `dim_strength` | `@MIOS:effects_dim_strength@` | `MIOS_EFFECTS_DIM_STRENGTH` | `decoration.dim_strength` |
| `bezier_liquid` (+3) | `@MIOS:effects_bezier_liquid@` | `MIOS_EFFECTS_BEZIER_LIQUID` | `animations.bezier = liquid, …` |
| `anim_windows` (+12) | `@MIOS:effects_anim_windows@` | `MIOS_EFFECTS_ANIM_WINDOWS` | `animations.animation = windows, …` |
| `layer_alpha_quickshell` (+2) | `@MIOS:effects_layer_alpha_quickshell@` | `MIOS_EFFECTS_LAYER_ALPHA_QUICKSHELL` | `layerrule = ignorealpha …, quickshell` |
| `panel_opacity` | (arbitrary-token in quickshell surface) | `MIOS_EFFECTS_PANEL_OPACITY` | `theme.json` `panel_opacity` → `Theme.qml panelOpacity` |

---

## 8. Sequenced implementation steps

1. **`mios.toml`** — add the `[effects]` block (§3) and the `[dotfiles.registry.hyprland-effects]` entry (§3). Verify the file still parses (`python3 -c "import tomllib,sys; tomllib.load(open('usr/share/mios/mios.toml','rb'))"`) and `wc -l` is unchanged-plus-delta (per the "verify mios.toml before committing" lesson).
2. **Add the template** `usr/share/mios/theme/templates/hyprland-effects.conf.tmpl` (§4.1). It **must** land in the same commit as the registry entry (ORPHAN-TEMPLATE floor, `mios-dotfiles-render:992`).
3. **Render** the committed artifact: `MIOS_THEME_ROOT="$PWD" MIOS_HOST_TOML=/nonexistent MIOS_USER_TOML=/nonexistent python3 usr/libexec/mios/mios-dotfiles-render render hyprland-effects` → produces `usr/share/mios/hyprland/effects.conf`. Commit it.
4. **Base config** — apply the `source=` edit (§4.2) to *both* `usr/share/mios/hyprland/hyprland.conf` and the `65-bake-hyprland.sh` heredoc.
5. **Shell bridge** — apply the `mios-sync-theme` + `quickshell-Theme.qml.tmpl` edits (§6), then `… mios-dotfiles-render render quickshell` to regenerate `Theme.qml`.
6. **Gate locally** — `MIOS_THEME_ROOT="$PWD" MIOS_HOST_TOML=/nonexistent MIOS_USER_TOML=/nonexistent python3 usr/libexec/mios/mios-dotfiles-render check` must PASS (check 25 / index row 28), and re-run the template-conformance check (46 / row 47) for this new `.md` + any new files.
7. **Verify effect parity** — diff the freshly rendered `effects.conf` against the old hardcoded block to confirm the values match (only cosmetic float normalization like `0.010`→`0.01` should differ).
8. **Runtime refresh contract** — confirm `mios-sync-theme` (one command) now refreshes compositor + shell together; `mios dotfiles apply hyprland-effects` lands `~/.config/hypr/effects.conf`.
9. **Law 15 double-repo** — mirror any shared SSOT surface into `mios-bootstrap.git` if it carries a copy of these files; triple-check before committing.

---

## 9. Risks / landmines

- **Boolean formatting** — the single most likely footgun. Bare `blur_enabled = true` → renders `True` → Hyprland parse error. Author booleans as quoted strings (§3). A one-time sanity check: `mios-dotfiles-render render hyprland-effects` then `grep -E '= (True|False)' effects.conf` must return nothing.
- **Uppercase keys** — silently ship un-substituted `@MIOS:effects_Foo@`. Keep every key lowercase.
- **Two-copy divergence** — the `65-bake-hyprland.sh` heredoc (§4.2). Edit both.
- **Hyprland version drift** — `drop_shadow`/`shadow_range` are the 0.46 spelling (baked pin). Hyprland ≥0.49 moved these into a `shadow { }` subcategory; when the baked compositor advances, change the *template* (one file), not the SSOT — the `[effects]` keys are version-agnostic.
- **ORPHAN-TEMPLATE** — template without registry entry reds check 25. Land together.

---

## 10. Net effect

After this change, the operator tunes the entire MiOS liquid-glass look — blur depth, corner radius, window opacity, shadow, and the spring/overshoot animation feel — by editing one `[effects]` table in `mios.toml` (or via the Portal/configurator per ADR-0009), and one command (`mios-sync-theme`) re-projects it to the compositor *and* the shell, drift-gated so no surface can silently diverge. Zero new engine code; it reuses the exact `[btop]`→`btop.conf` settings-surface pattern already in production.
