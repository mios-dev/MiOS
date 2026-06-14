<!-- AI-hint: Documents the dual-repo filesystem topology where two independent .git directories share one working tree (the OS root) and each repo's .gitignore acts as a whitelist isolating its files; explains the GIT_DIR/GIT_WORK_TREE switch, commit isolation, and why this is what lets the immutable bootc image and its cold-start bootstrap evolve as separate but co-located histories.
     AI-related: /usr/share/mios/docs/root-origin/DUAL-WHITELIST.md, /usr/share/mios/docs/root-origin/REPO-IS-ROOT.md, /usr/share/mios/docs/day-0/BOOTSTRAP.md, /usr/share/mios/docs/day-n/SELF-REPLICATION.md, mios-bootstrap, /etc/profile.d/mios-agent.sh -->
<!-- FHS: /usr/share/mios/docs/root-origin/DUAL-WHITELIST.md -->

# Dual `.gitignore`-as-Whitelist Topology

## Purpose and place in the whole system

MiOS is one thing built two ways at once: an **immutable, bootc/OCI-shaped
Fedora workstation** (the whole OS is a single container image you `bootc
upgrade` like a `git pull` and `bootc rollback` like a Ctrl-Z) that is *also* a
**local, self-replicating, agentic AI operating system**. The governing rule
that makes that possible is *the repo root IS the deployed system root* — see
[`REPO-IS-ROOT.md`](REPO-IS-ROOT.md). The `Containerfile` bakes `usr/`, `etc/`,
`srv/`, `var/` exactly where they land on a booted host; editing a file in the
repo *is* editing the OS.

But MiOS is not one repo — it is **two**, and they have to live in the **same**
working tree, because that working tree is the live filesystem of the build host
(`MiOS-DEV`):

- **MiOS** (`mios.git`) — the system FHS overlay that becomes the OCI image:
  the build pipeline, the inference lanes, the agent stack, the desktop, the
  whole OS.
- **mios-bootstrap** (`mios-bootstrap.git`) — the cold-start half: the
  Phase-0/1 logic that clones MiOS into `/`, captures identity, and drives the
  first build. It is *how a bare machine becomes a MiOS build host*, and it must
  be version-controlled separately so it can evolve without touching the OS
  image's history (and ship to a different remote).

This document defines the mechanism that lets those two repositories coexist in
one root without their files, histories, or commits bleeding into each other:
**two independent `.git` directories over one shared working tree, each scoped
by a `.gitignore` written as a whitelist.** It is the source of truth that
[`REPO-IS-ROOT.md`](REPO-IS-ROOT.md) and [`BOOTSTRAP.md`](../day-0/BOOTSTRAP.md)
both defer to for this topology. Audience: anyone editing either repo, writing
phase scripts that commit, or reasoning about the build/bootstrap lifecycle.

## Mechanism

Two repos share one filesystem (the OS root). They are distinguished by their
`.gitignore` files, each of which is a **whitelist** — it ignores everything
*except* the files that "belong" to that repo.

`.gitignore` semantics make this work: `*` ignores everything; lines prefixed
`!` re-include selected paths. MiOS uses **separate `.git` directories under the
same working tree**:

- `/.git`                  → the MiOS repo (the default; plain `git` uses it).
- `/.mios-bootstrap.git`   → the bootstrap repo, invoked with
  `GIT_DIR=/.mios-bootstrap.git GIT_WORK_TREE=/`.

Each `.gitignore` is committed into its respective repo's history. Object
databases are separate; histories are independent; the **working tree is
shared**. This is the same single root pictured in
[`REPO-IS-ROOT.md`](REPO-IS-ROOT.md): `/.git` and `/.mios-bootstrap.git` sit
side by side at the top level, both excluded from composefs's read-only `/usr`
view and from the build's `--exclude=./.git` tar pipeline, so neither leaks into
the baked image.

## What each repo "sees"

- **mios-bootstrap** sees: `bootstrap/`, the top-level docs needed to cold-start
  (`README-BOOTSTRAP.md`, the bootstrap Justfile fragment `Justfile.bootstrap`),
  the `.mios/bootstrap-handoff` marker, and **nothing** under
  `/usr/share/mios/src/` or the rest of the OS overlay.
- **MiOS** sees: everything *except* `bootstrap/` and the bootstrap-only README
  files — i.e. the whole OS image source.

The two whitelists are deliberate inverses: each re-includes only its own files
and explicitly excludes the other's. That is what keeps the MiOS image source
and the bootstrap cold-start logic cleanly separable even though they occupy the
same directories.

## Commit isolation

Because each repo has its own object database, commits to one never appear in
the other's log. Stashes, tags, branches, and remotes are likewise isolated, so
the OS image history and the bootstrap history can be pushed to different
remotes and tagged on different cadences without collision.

## Practical workflow

```sh
# Working on MiOS proper (the OS image source) — the default
git status                                  # uses /.git
git commit -F /tmp/msg

# Switching to bootstrap (same shell, same dir)
export GIT_DIR=/.mios-bootstrap.git GIT_WORK_TREE=/
git status                                  # bootstrap view
git commit -F /tmp/msg
unset GIT_DIR GIT_WORK_TREE
```

Plain `git` (no env override) always operates on the MiOS repo. The bootstrap
repo is reached only by exporting `GIT_DIR`/`GIT_WORK_TREE`; unset them to return
to MiOS.

## Switching helper

The intended safe wrapper is `mios repo use {main|bootstrap}`, which flips the
two scopes without making you remember the env-var pair. Because a child process
*cannot* mutate its parent shell's environment, the helper **prints** the line to
apply rather than applying it directly:

```sh
# main  →   unset GIT_DIR GIT_WORK_TREE
# bootstrap →  export GIT_DIR=/.mios-bootstrap.git GIT_WORK_TREE=/
```

`eval "$(mios repo use bootstrap)"` applies it in the current shell; the
shell helper sourced from `/etc/profile.d/mios-agent.sh` wires this into
interactive sessions. The underlying, always-correct mechanism is the
`GIT_DIR`/`GIT_WORK_TREE` switch shown above — the wrapper is convenience over
that contract, not a replacement for it.

## Why `-F <tempfile>` for commit messages

The `Containerfile` and many phase scripts commit under `set -euo pipefail` in
non-interactive shells, where `-m "<message>"` is fragile when messages contain
quotes, backticks, or `$`. Always use `-F <tempfile>`:

```sh
cat > /tmp/msg <<'EOF'
gen-42: bump kernel, enable composefs fsverity
EOF
git commit -F /tmp/msg
```

This applies to commits in **both** repos — the isolation is about object
stores and histories, not about how messages are passed.

## Example: MiOS repo `.gitignore`

```gitignore
# /.gitignore — MiOS main repo (whitelist)
*

!/.gitignore
!/Containerfile
!/Justfile
!/README.md
!/CHANGELOG.md
!/LICENSE

!/etc/
!/etc/**
!/usr/
!/usr/**
!/var/
!/var/lib/
!/var/lib/mios/
!/var/lib/mios/templates/
!/var/lib/mios/templates/**

# Exclude bootstrap-only paths
/bootstrap/
/README-BOOTSTRAP.md
/Justfile.bootstrap
/.mios-bootstrap.git/

# Exclude transient working-state
/out/
/tmp/
/.cache/
```

## Example: bootstrap repo `.gitignore`

```gitignore
# /.mios-bootstrap.gitignore — bootstrap repo (whitelist)
*

!/.mios-bootstrap.gitignore
!/bootstrap/
!/bootstrap/**
!/README-BOOTSTRAP.md
!/Justfile.bootstrap
!/.mios/
!/.mios/bootstrap-handoff
```

## How this serves the lifecycle

This topology is the seam between the two halves of the MiOS lifecycle:

- **mios-bootstrap** runs first — it clones `mios.git` into `/`, overlays its own
  files (the whitelists keep the two sets distinct in the shared tree), captures
  identity, and hands off to the build (see [`BOOTSTRAP.md`](../day-0/BOOTSTRAP.md)).
- **MiOS** is then the thing the `Containerfile` assembles into the OCI image
  that `bootc switch`/`upgrade` deploys and `bootc rollback` reverts.

Because the OS can rebuild itself from its own source-at-root, the same dual-repo
root is what makes MiOS *self-replicating* (see
[`SELF-REPLICATION.md`](../day-n/SELF-REPLICATION.md)): a running MiOS host holds
both repos, can regenerate the image, and can re-seed a new host — with the
bootstrap history and the OS history kept cleanly apart the whole way through.

These rules are part of why the six Architectural Laws hold (`usr/`-over-`etc/`,
no-mkdir-in-`var/`, bound-images, bootc-container-lint, unified-AI-redirects,
unprivileged-quadlets): a deterministic, single-root source layout is the
precondition for a deterministic, atomic image.
