<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### etc/profile.d/* loads in alphabetical order, so this script...

/etc/profile.d/* loads in alphabetical order, so this script runs
BEFORE mios-env.sh (c < e). Eagerly load /etc/mios/install.env (the
bootstrap-staged export of mios.toml values) so MIOS_COLOR_* /
MIOS_ANSI_* are available below. Bootstrap writes [colors] keys
into install.env via userenv.sh's slot map; if the file is missing
(pre-bootstrap host) we fall back to the hardcoded defaults via
the ${VAR:-default} expansions below.

<!-- mios-src:4d378d3d73d9 from etc/profile.d/mios-colors.sh:8-14 -->
