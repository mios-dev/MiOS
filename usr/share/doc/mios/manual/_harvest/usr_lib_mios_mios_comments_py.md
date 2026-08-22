<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: The MiOS comment lexer and...

!/usr/bin/env python3
AI-hint: The MiOS comment lexer and classifier -- extracts comment blocks from any source file and decides, deterministically, whether each block STAYs in code or MIGRATEs to documentation. Pure library: holds no policy constants, writes nothing.
AI-related: usr/lib/mios/mios_toml.py, usr/libexec/mios/mios-ai-tag, usr/libexec/mios/mios-manual, docs/agy/doc-generative-documentation.md
AI-functions: lex, classify, Policy, RefIndex, Block, Verdict

<!-- mios-src:5152bcabb1ee from usr/lib/mios/mios_comments.py:1-4 -->

