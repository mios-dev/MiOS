<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Windows PowerShell 5.1 -- which is what runs the install...

Windows PowerShell 5.1 -- which is what runs the install path on a stock
Windows box -- reads a BOM-less file as ANSI, not UTF-8. Any .ps1 carrying
non-ASCII (the box-drawing run separators, arrows and accented text MiOS
prints) therefore MUST ship a UTF-8 BOM or its output is mojibake. This is the
same convention tools/render-globals.py already writes with (utf-8-sig).
Pure-ASCII scripts need no BOM and must not carry a pointless one.

<!-- mios-src:62f7b82da080 from automation/98-drift-checks.sh:6777-6782 -->
