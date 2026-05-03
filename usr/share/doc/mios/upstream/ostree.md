# ostree — Content-Addressed Filesystem Tree

> Used by 'MiOS' as: the storage backend underneath bootc. The
> `Containerfile` ends with `RUN ostree container commit` immediately
> before `bootc container lint`. composefs (next page) is layered on top.

- Project: <https://github.com/ostreedev/ostree>
- Docs: <https://ostreedev.github.io/ostree/>

## Mental model

ostree is a content-addressed object store, like git for filesystem
trees. Each commit references a tree of file objects (deduplicated by
SHA-256). A "deployment" is a hardlinked checkout of a commit into
`/sysroot/ostree/deploy/<stateroot>/deploy/<csum>.<n>`.

| Concept | What it is | Where in 'MiOS' |
| --- | --- | --- |
| Object store | `/sysroot/ostree/repo/objects/` | composefs makes this immutable + verified |
| Refs | named pointers to commits | `bootc switch` rewrites the active ref |
| Deployments | hardlinked checkouts | `bootc status` lists them |
| `/sysroot` | physical root, host-only | never exposed to user space |
| `/var` | mutable subvolume, persistent across upgrades | governed by LAW 2 (NO-MKDIR-IN-VAR) |
| `/etc` 3-way merge | image-default + previous-state + admin-edits | resolved on every `bootc upgrade` |

## bootc and ostree

bootc currently uses ostree as backend. The two share metadata:

- bootc's container-image-as-OS commits to ostree refs under
  `ostree/container/image/<digest>`
- bootc kargs are stored in BLS type-1 entries under
  `/boot/loader/entries/`, generated from `/usr/lib/bootc/kargs.d/*.toml`
  + machine-local state
- `ostree admin status` lists the same deployments as `bootc status`,
  with more detail

## composefs is the migration path

`bootc-composefs-native` (in development) replaces ostree-as-backend with
a thin composefs binding. 'MiOS' already enables composefs *on top of*
ostree via `usr/lib/ostree/prepare-root.conf`, getting the
content-addressed read-only `/usr` mount today.

## Useful commands

```bash
ostree admin status                 # deployments
ostree refs                          # all refs in the local repo
ostree log <ref>                     # commit history
ostree show <commit>                 # commit metadata
sudo ostree admin undeploy <index>   # free a slot
```

## Cross-refs

- `usr/share/doc/mios/upstream/composefs.md`
- `usr/share/doc/mios/upstream/bootc.md`
- `ARCHITECTURE.md` §Pillars (transactional integrity)
