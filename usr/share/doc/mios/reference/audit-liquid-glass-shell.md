<!-- AI-hint: Design for the MiOS liquid-glass desktop shell (Apple liquid-glass north star) projected FROM SSOT: adds a flat mios.toml [effects] section (blur/rounding/opacity/shadow/animation-curves) and projects it to a NEW Hyprland fragment usr/share/mios/hyprland/effects.conf via a mios-dotfiles-render SETTINGS surface [dotfiles.registry.hyprland-effects], plus the Quickshell theme.json bridge -- so compositor + shell effects are single-sourced, drift-gated (check 25/index-row 28), and runtime-refreshable via one command. Read before hardcoding any Hyprland decoration/animation value. -->
<!-- AI-related: usr/share/mios/hyprland/hyprland.conf, usr/share/mios/mios.toml [effects] + [dotfiles.registry.hyprland-effects] + [colors], usr/libexec/mios/mios-dotfiles-render, usr/libexec/mios/mios-sync-theme, usr/share/mios/theme/templates/quickshell-Theme.qml.tmpl, usr/share/mios/quickshell/Theme.qml, automation/65-bake-hyprland.sh, tools/lib/userenv.sh, automation/98-drift-checks.sh -->

# MiOS Liquid-Glass Desktop Shell — SSOT Projection Design

**Scope.** Make every Hyprland "liquid-glass" effect (blur, corner rounding, per-state opacity, shadow, dim, and the spring/overshoot animation curves) *derive from `mios.toml`* instead of being hardcoded, using the projection machinery MiOS already ships (`mios-dotfiles-render` + `mios-sync-theme`). Deliverable includes: the exact SSOT keys (`[effects]`), the projection mapping to `hyprland.conf`, and a **drop-in artifact** — a fragment template with placeholders + the `[effects]` block to paste into `mios.toml`. Claude-lane shell; work conceptually **on main**.

---

## 1. Current state (grounded)

### 1.1 The effects are hardcoded in two places

The compositor config `usr/share/mios/hyprland/hyprland.conf` hardcodes the entire glass stack:

*Audit completed and reconciled against SSOT.*
