<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Strip INHERITED MIOS_* before running the bash twin. The...

Strip INHERITED MIOS_* before running the bash twin. The comparison asks
"what does userenv.sh resolve from SSOT?", but bash reports every MIOS_*
in its environment -- so any ambient var the TOML side has no key for
shows up as a mismatch. CI sets MIOS_DRIFT_REQUIRE_TOOLS=1 as a workflow
knob, which failed the check with:
  Var MIOS_DRIFT_REQUIRE_TOOLS: Toml resolved '', Bash resolved '1'
Keep only the tier pointers the resolver needs to find the SSOT layers.

<!-- mios-src:568191b44c9c from tools/check-resolver-twin.py:40-46 -->
