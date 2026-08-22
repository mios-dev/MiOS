<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### This used to rmtree repo_root/usr/share/doc/mios/manual...

This used to rmtree repo_root/usr/share/doc/mios/manual unconditionally,
derived from repo_root and ignoring --output entirely: pointing --output at
a scratch file still deleted the in-repo directory. That directory is where
AUTHORED manual prose is meant to live, so the tool could destroy
hand-written content that no generator can reproduce. Clean only a stale
split-page directory that sits beside the file we are actually writing, and
never one holding git-tracked files.

<!-- mios-src:448a427d36d9 from tools/generate-manual.py:28-34 -->
