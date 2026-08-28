<!-- AI-hint: MiOS architectural documentation: mios-unit-gen.
     AI-related: mios-unit-gen -->

# mios-unit-gen

MiOS Systemd Unit Generator & Golden Master Deviance Oracle.

## Regeneration Workflow

To regenerate golden master snapshots after intentional systemd unit edits:

```bash
python -c "import os, shutil; shutil.rmtree('tools/native/mios-unit-gen/tests/golden', ignore_errors=True); shutil.copytree('usr/lib/systemd/system', 'tools/native/mios-unit-gen/tests/golden')"
cargo test -p mios-unit-gen
```
