# Research staging

Use this root-level dotfolder for evidence collection, source snapshots,
comparison matrices, and draft findings that are not yet publication-ready.

Durable reports belong in `docs/research/`. Upstream reference notes intended
to ship with the image belong in `usr/share/doc/mios/upstream/` and must use
primary sources with explicit verification badges.

Research files must identify the run date and scope, distinguish repository
facts from upstream facts, cite primary sources, mark unknown or stale claims,
and contain no secrets, tokens, private URLs, or unredacted credentials.

The separate dotfiles/secrets repository decision is recorded in
`separate-dotfiles-secrets-repository-pattern-2026-09.md`. Its concrete
repository boundary is reflected by `.dotfiles/` and `.secrets/` at the
repository root.
