<!-- AI-hint: Documentation of the ostree content-addressed filesystem used as the bootc storage backend to manage immutable system images, deployments, and the transition path to composefs. -->
# ostree — Content-Addressed Filesystem Tree

> **Why this matters to MiOS:** MiOS is one OS image built two ways at once — an
> immutable bootc/OCI Fedora workstation *and* a local, self-replicating agentic
> AI OS. ostree is the storage backend that makes the *immutable* half real: it
> is how a single OCI image becomes an atomic, content-addressed, rollback-able
> on-disk system. Everything else in MiOS — the AI plane, the desktop, virt,
> cluster — rides on a root that ostree (under bootc, verified by composefs) keeps
> deterministic. This page explains ostree as MiOS actually uses it.

- Project: <https://github.com/ostreedev/ostree>
- Docs: <https://ostreedev.github.io/ostree/>

## Where ostree sits in the whole system

MiOS's lifecycle is: the build pipeline (`Containerfile` + `automation/`) bakes
the repo root (`usr/`, `etc/`, `srv/`, `var/`) into one OCI image → that image is
*also* a bootc image → on a host, `bootc switch`/`upgrade` deploys it and
`bootc rollback` reverts it. ostree is the layer that lets that image land on
disk as discrete, deduplicated, atomically-switchable **deployments** instead of
a mutable filesystem you edit in place.

That is what underwrites the project's promise that you `bootc upgrade` the OS
like a `git pull` and `bootc rollback` it like a Ctrl-Z (Architectural Laws 3–4):
ostree gives bootc a git-shaped object store of filesystem trees, so an upgrade
is "check out a new commit" and a rollback is "point back at the old one." None
of the mutable agent state (pgvector data, AI memory/scratch under `/var`) is in
that store — it persists across upgrades by design (LAW 2), so flipping
deployments never loses the running system's brain.

## Mental model

ostree is a content-addressed object store, like git for filesystem
trees. Each commit references a tree of file objects (deduplicated by
SHA-256). A "deployment" is a hardlinked checkout of a commit into
`/sysroot/ostree/deploy/<stateroot>/deploy/<csum>.<n>`.

| Concept | What it is | Where in MiOS |
| --- | --- | --- |
| Object store | `/sysroot/ostree/repo/objects/` | composefs makes this immutable + fs-verity-verified |
| Refs | named pointers to commits | `bootc switch` rewrites the active ref |
| Deployments | hardlinked checkouts | `bootc status` lists them |
| `/sysroot` | physical root, host-only | mounted read-only (`[sysroot] readonly = true`); never exposed to user space |
| `/var` | mutable subvolume, persistent across upgrades | governed by LAW 2 (NO-MKDIR-IN-VAR); holds the agent's mutable state |
| `/etc` 3-way merge | image-default + previous-state + admin-edits | resolved on every `bootc upgrade` |

## bootc and ostree

bootc currently uses ostree as its storage backend; the two share metadata, so
`bootc` and `ostree admin` describe the same on-disk reality:

- bootc's container-image-as-OS commits to ostree refs under
  `ostree/container/image/<digest>`. The booted MiOS image
  (`ghcr.io/mios-dev/mios:latest`) lands here as an ostree commit.
- bootc kargs are stored in BLS type-1 entries under
  `/boot/loader/entries/`, generated from `/usr/lib/bootc/kargs.d/*.toml`
  + machine-local state
- `ostree admin status` lists the same deployments as `bootc status`,
  with more detail

MiOS never invokes ostree directly to mutate the host — `bootc`
upgrade/switch/rollback is the only sanctioned mutation path. ostree commands
here are for *inspection* and reclaiming disk, not for driving the system.

## How the image is committed (build-time)

The MiOS `Containerfile` finishes the build with two instructions, in this order:

```dockerfile
RUN ostree container commit
# bootc container lint MUST be the final instruction (ARCHITECTURAL LAW 4).
RUN bootc container lint
```

`ostree container commit` normalizes the layered image into the form ostree
expects (canonicalizing `/var`, `/run`, and content metadata) so it deploys
cleanly; `bootc container lint` (LAW 4) then validates the result as a bootable
bootc image and **fails the build** if it isn't. The build also never uses
`--squash-all`: squashing strips the `ostree.final-diffid` metadata and breaks
the Bootc Image Builder (BIB) disk-cutting step downstream.

## composefs — verified read-only `/usr`, today and tomorrow

ostree provides the object store; **composefs** is what makes the checkout of
that store *verified and read-only* at runtime. MiOS layers composefs on top of
ostree via `usr/lib/ostree/prepare-root.conf`:

```ini
[composefs]
enabled = verity      # require fs-verity signatures on every file in /usr
[sysroot]
readonly = true       # the physical root is host-only and immutable
```

With `enabled = verity`, the kernel refuses to boot a composefs image whose
fs-verity digests don't match the expected manifest — tamper-evidence is enforced
at mount time, not trusted after the fact. (`/etc` is left **persistent**, not
transient, so SSH configs, NetworkManager keyfiles, and user preferences survive
reboots — a deliberate workstation choice; LAW 1 USR-OVER-ETC still discourages
putting *static* config there.) See `usr/share/doc/mios/upstream/composefs.md`
for the full layer model.

**Migration path:** `bootc-composefs-native` (in development upstream) will
replace ostree-as-backend with a thin composefs binding. MiOS already gets the
content-addressed, fs-verity-verified read-only `/usr` *today* by enabling
composefs on top of ostree, so that transition is an internal swap of the
storage layer, not a change to the MiOS contract.

## Useful commands

Inspection and slot-reclaim only — never use these to mutate the deployed OS
(that is `bootc`'s job):

```bash
ostree admin status                 # deployments (same set as `bootc status`)
ostree refs                          # all refs in the local repo
ostree log <ref>                     # commit history
ostree show <commit>                 # commit metadata
sudo ostree admin undeploy <index>   # drop a pinned old deployment to free a slot
```

When `/sysroot` is full and a `bootc upgrade` hits the pre-flight free-space
check, `bootc rollback` (clear staged) or `ostree admin undeploy <index>` (drop a
pinned old deployment) reclaims space — see `usr/share/doc/mios/upstream/bootc.md`.

## Cross-refs

- `usr/share/doc/mios/upstream/composefs.md` — the verified read-only `/usr` layer on top of this store
- `usr/share/doc/mios/upstream/bootc.md` — the lifecycle tool that drives ostree deployments
- `usr/share/doc/mios/upstream/rechunk.md` — Day-2 delta optimization (where dedup in the object store pays off)
- `usr/share/doc/mios/concepts/architecture.md` §Pillars (transactional integrity)
