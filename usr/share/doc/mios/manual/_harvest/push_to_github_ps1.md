<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Automates the MiOS release pipeline by cloning the bootstrap repo, overlaying staged changes, bumping the VERSION, updating CHANGELOG.md, and pushing to the main branch via GitHub.
AI-related: mios-push
AI-functions: Write-Step, Write-Ok, Write-Warn
============================================================================
push-to-github.ps1  'MiOS' release deliverable (v0.2.2 baseline)
----------------------------------------------------------------------------
Single source of truth for the release pipeline. Per usr/share/mios/ai/INDEX.md 4 + the
/push-version skill, this script is rewritten per release and never split
into push-vX.Y.Z.ps1 siblings.

Behaviour:
  1. Clone github.com/MiOS-DEV/MiOS-bootstrap into a temp directory.
  2. Optionally overlay a staged companion directory (-StagedDir) onto the
     working tree, preserving layout relative to repo root. Files-only
     directories are walked and replaced file by file. Nothing is deleted.
  3. Bump VERSION to -Version (default: read from local VERSION file).
  4. Stamp CHANGELOG.md with a top-of-file release block dated today.
  5. Commit with a structured release message.
  6. Push to main using $env:GH_TOKEN or the configured credential helper.
  7. Print a summary: changed paths, commit SHA, GHCR tag.

This is the deliverable. Humans run it; the agent does not push for you.
============================================================================

<!-- mios-src:07c29ff8db8a from push-to-github.ps1:1-23 -->

