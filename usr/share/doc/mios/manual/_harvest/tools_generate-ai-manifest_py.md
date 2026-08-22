<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Repo-relative paths git tracks, or None when git is...

Repo-relative paths git tracks, or None when git is unavailable.

    The manifests embed a walk of the tree. Walking the FILESYSTEM makes the
    output a function of the developer's working directory -- local scratch
    files, .bak files and untracked notes all land in root-manifest.json -- so
    a manifest generated on a dev box can never match one regenerated on a
    clean CI checkout, and check_ai_manifests_fresh fails forever. Restricting
    the walk to tracked files makes the artifact reproducible anywhere.

<!-- mios-src:28caf1dca73d from tools/generate-ai-manifest.py:33-41 -->
