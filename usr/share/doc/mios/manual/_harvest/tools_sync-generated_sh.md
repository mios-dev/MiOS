<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Resolve the python MiOS itself provisions. Python is a...

Resolve the python MiOS itself provisions.

Python is a DECLARED MiOS dependency, not something to hope for: mios.toml
[apps.winget].pkgs lists "Python.Python.3.14" under "Critical runtime /
toolchain", so every MiOS host has it globally (dnf python3 on Linux, winget
on Windows), and installation/mios-install.ps1 + Reinstall-MiOSDEV.ps1 already
resolve it at %LOCALAPPDATA%\Programs\Python\Python314\python.exe.

The trap: `command -v python` SUCCEEDS on Windows even when it resolves to the
Microsoft Store alias stub, which prints "Python was not found" and exits. The
old probe (`command -v python3 || PY=python`) therefore set PY to the stub, and
every generator below silently did nothing while sync reported success -- the
tree looked synced while the manifests went stale. So probe by EXECUTING, and
try the MiOS-installed interpreter before bare names.

<!-- mios-src:4cf964f45b77 from tools/sync-generated.sh:8-21 -->

### EVERY renderer resolves through the layered resolver, which...

EVERY renderer resolves through the layered resolver, which honours
MIOS_ROOT / MIOS_TOML* from the environment. On a MiOS host (or the MiOS-DEV
container) those are already exported and point at the INSTALLED system, so
an unpinned run silently renders the installed SSOT into this repo's
artefacts -- which is how globals.ps1 ended up carrying 'MiOS User' and
:8640. Pin every tier to the tree being synced.

<!-- mios-src:7173c25c3b4b from tools/sync-generated.sh:43-48 -->
