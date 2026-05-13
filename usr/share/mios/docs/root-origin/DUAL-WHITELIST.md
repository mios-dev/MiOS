<!-- FHS: /usr/share/mios/docs/root-origin/DUAL-WHITELIST.md -->

# Dual `.gitignore`-as-Whitelist Topology

Two repos share one filesystem (the OS root). They are distinguished
by their `.gitignore` files, each of which is a **whitelist** —
ignoring everything except the files that "belong" to that repo.

## Mechanism

`.gitignore` semantics: `*` ignores everything; lines prefixed `!`
re-include selected paths. MiOS uses **separate `.git` directories
under the same working tree**:

- `/.git`                  → the MiOS repo
- `/.mios-bootstrap.git`   → the bootstrap repo (invoked with
  `GIT_DIR=/.mios-bootstrap.git GIT_WORK_TREE=/`)

Each `.gitignore` file is committed into its respective repo's
history. Object databases are separate; histories are independent;
working tree is shared.

## What Each Repo "Sees"

- **mios-bootstrap** sees: `bootstrap/`, top-level docs needed to
  cold-start (`README-BOOTSTRAP.md`, the bootstrap Justfile fragment),
  and nothing under `/usr/share/mios/src/`.
- **MiOS** sees: everything except `bootstrap/` and bootstrap-only
  README files.

## Commit Isolation

Because each repo has its own object database, commits to one never
appear in the other's log. Stashes, tags, and remotes are likewise
isolated.

## Practical Workflow

```sh
# Working on MiOS proper
git status                                  # uses /.git
git commit -F /tmp/msg

# Switching to bootstrap (same shell, same dir)
export GIT_DIR=/.mios-bootstrap.git GIT_WORK_TREE=/
git status                                  # bootstrap view
git commit -F /tmp/msg
unset GIT_DIR GIT_WORK_TREE
```

The MiOS `mios` CLI provides `mios repo use main|bootstrap` to flip
this safely.

## Why `-F <tempfile>`

The Containerfile and many phase scripts run under `set -e` and
non-interactive shells; `-m "<message>"` is fragile when messages
contain quotes, backticks, or `$`. Always use `-F <tempfile>`:

```sh
cat > /tmp/msg <<'EOF'
gen-42: bump kernel, enable composefs fsverity
EOF
git commit -F /tmp/msg
```

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

## Switching helper

`/usr/bin/mios` provides `mios repo use {main|bootstrap}` which is
implemented in `/usr/libexec/mios/repo-use`:

```sh
case "$1" in
  main)
    echo "Use: unset GIT_DIR GIT_WORK_TREE"
    ;;
  bootstrap)
    echo "Use: export GIT_DIR=/.mios-bootstrap.git GIT_WORK_TREE=/"
    ;;
esac
```

The script prints the line because it cannot modify the calling
shell's environment directly; users `eval` the output or source the
shell helper at `/etc/profile.d/mios-agent.sh`.
