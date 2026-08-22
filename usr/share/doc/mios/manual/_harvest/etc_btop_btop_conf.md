<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: GENERATED btop config -- do NOT hand-edit. Projected from the mios.toml [btop] SSOT by mios-theme-render (surface "btop-conf" -> etc/btop/btop.conf), the SAME way [colors] projects into themes/mios.theme. Edit mios.toml [btop] and re-run mios-sync-theme to refresh. UNIFIED Linux+Windows: the Windows bootstrap (install-host-tools.ps1) stages THIS rendered artifact to M:\MiOS\btop, so both platforms derive from one source instead of two divergent hand-copies.
AI-related: usr/libexec/mios/mios-theme-render, usr/libexec/mios/mios-sync-theme, usr/share/mios/mios.toml, etc/profile.d/mios-btop.sh
? Config file for btop v. 1.4.x -- MiOS preset (80x20 portal)

Operator: "btop can run if a preset can fit the dimensions provided -- just
need a profile preset (make it match the entire MiOS themes and color
palette)". This preset trims the default config to fit the 80x20 MiOS
canonical terminal size and packs cpu/mem/proc into the smallest layout
that still shows meaningful info.

<!-- mios-src:3a9945d888b4 from etc/btop/btop.conf:1-9 -->

### Presets accessible via `p` 0-9 inside btop. Format...

Presets accessible via `p` 0-9 inside btop. Format: <boxes>:<mode>:<theme>
where mode = 0 (full) or 1 (compact).

Slot 4 (proc only) is the MiOS default; mios-btop.sh launches
`btop -p 4` on plain invocation.

  0  cpu compact
  1  cpu full
  2  cpu+mem compact
  3  cpu+mem full
  4  proc only             <- canonical launch via `btop -p 4`
  5  cpu+mem+net+proc full

<!-- mios-src:2add1ac7df9c from etc/btop/btop.conf:16-27 -->

### Boxes shown at launch -- matches preset 4 (proc only) so...

Boxes shown at launch -- matches preset 4 (proc only) so plain
`btop` invocations (without -p) still render the operator's
canonical view.

<!-- mios-src:abbc7ef8a3a1 from etc/btop/btop.conf:46-48 -->

### Update time in milliseconds. Operator

Update time in milliseconds. Operator: "not 500ms update speed" -- the
displayed value was 2000ms. Lock to 500ms here so btop refreshes 2x/sec
on the dev VM out of the box.

<!-- mios-src:77fe03ac20f8 from etc/btop/btop.conf:51-53 -->
