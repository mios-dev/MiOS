<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash AI-hint: Force-reindexes all files in every OWUI...

!/bin/bash
AI-hint: Force-reindexes all files in every OWUI knowledge collection by cycling through /api/v1/knowledge/{id}/file/add endpoints to bypass metadata-only updates and trigger full chunking/embedding.
AI-related: /usr/libexec/mios/mios-knowledge-search, mios-knowledge-search, localhost (port key `open_webui`)

<!-- mios-src:12971b9b3441 from automation/support/force-revectorize.sh:1-3 -->

