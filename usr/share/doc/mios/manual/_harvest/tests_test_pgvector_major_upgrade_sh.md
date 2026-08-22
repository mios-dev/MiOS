<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: Verifies...

!/usr/bin/env bash
AI-hint: Verifies mios-pgvector-major-upgrade never destroys an agent datastore -- exercises the no-op, unparseable-tag, downgrade-refusal, missing-old-image and failed-dump paths against a fake data dir with podman stubbed, asserting the cluster survives every one of them, plus the happy path that stashes rather than deletes.
AI-related: usr/libexec/mios/mios-pgvector-major-upgrade, mios-pgvector-major-upgrade.service, mios-pgvector.container

<!-- mios-src:694608b6a74f from tests/test-pgvector-major-upgrade.sh:1-3 -->

