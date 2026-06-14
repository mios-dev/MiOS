<!-- AI-hint: Documentation for the composefs subsystem, detailing the integration of overlayfs, EROFS, and fs-verity to provide a verified, deduplicated, read-only root filesystem that anchors MiOS's image-mode integrity. -->
# composefs — Verifiable Read-Only Root

> **Where this fits in MiOS.** MiOS is one image built two ways at once: an
> immutable, bootc/OCI-shaped Fedora workstation *and* a local, self-replicating
> agentic AI OS. composefs is the integrity floor under that whole. It makes the
> shipped `/usr` (GNOME/Wayland, the GPU/virt stack, and the entire local agent
> plane — agent-pipe, MiOS-Hermes, the `mios-llm-*` inference lanes, the
> `mios-pgvector` datastore) a kernel-verified, content-addressed, read-only
> mount. The build pipeline produces an OCI image; ostree stores it; composefs
> verifies it at mount time; `bootc upgrade`/`rollback` carry it forward. If a
> byte of `/usr` were tampered with on disk, the kernel refuses it before user
> space (and the agent stack) ever sees it.
>
> Enabled in MiOS via `usr/lib/ostree/prepare-root.conf`. See the canonical FHS
> + filesystem-layout reference in
> `usr/share/doc/mios/concepts/architecture.md` §Filesystem-layout.

## What it is

composefs combines **overlayfs + EROFS + fs-verity** to produce a
read-only mount whose every file is independently verified by the
kernel. Backing files live in a content-addressed object store
(deduplicated, sharable across deployments — in MiOS, the ostree repo
under `/sysroot/ostree/repo/objects/`).

- Project: <https://github.com/containers/composefs> (alt mirror: <https://github.com/composefs/composefs>)
- v1.0.0 release (stable on-disk format): <https://github.com/composefs/composefs/releases/tag/v1.0.0>

## How the layers fit

```
┌────────────────────────────────────┐
│ overlayfs (ephemeral writable upper │   ← top, never persists
│   for tools that must write to a    │
│   read-only mount at runtime)       │
├────────────────────────────────────┤
│ EROFS image (synthesized by         │   ← read-only middle layer
│   mkcomposefs from manifest +       │
│   metacopy xattrs → backing files)  │
├────────────────────────────────────┤
│ fs-verity-protected backing files   │   ← content-addressed leaves
│   in the ostree object store        │
└────────────────────────────────────┘
```

`mount.composefs` validates each backing file's fs-verity digest before
exposing it. Tampering on disk produces an `EIO`, not silent corruption.

## MiOS enable shape

`usr/lib/ostree/prepare-root.conf`:

```ini
[composefs]
enabled = verity     # require fs-verity signatures on every file in /usr
                     # (tamper-evident root; stronger than `enabled = yes`)

[sysroot]
readonly = true      # the physical /sysroot is read-only

[etc]
# /etc is left PERSISTENT (NOT transient). transient = yes would make /etc a
# tmpfs that is forgotten on reboot — too aggressive for a workstation (it
# would drop persistent SSH configs, NetworkManager keyfiles, user prefs).
```

Notes on `enabled = verity`:

- The `ucore-hci` base image is built with fs-verity digests. Setting
  `verity` makes MiOS **refuse to boot** a composefs image whose digests
  don't match the expected manifest — the core tenet of image-mode
  integrity, and the on-disk enforcement of Architectural Law 3
  (BOUND-IMAGES) at the filesystem level.
- `verity` requires **ext4 or btrfs** at install time (xfs does not
  support fs-verity). If first boot fails with a `composefs: verity
  mismatch`, either install onto ext4/btrfs or temporarily drop to
  `enabled = yes` while the filesystem is investigated. MiOS does **not**
  ship the fallback; the supported path is to stay on the signed image.

Effects on the FHS layout:

- `/usr` — content-addressed, deduplicated, fs-verity-verified, read-only.
  This is where the whole shipped system lives, including the agent plane.
  LAW 1 (USR-OVER-ETC) puts static config in `/usr/lib/<component>.d/`.
- `/etc` — persistent; written each boot from the image's `/etc` plus
  persisted admin overrides via bootc's **3-way merge** (image default +
  previous state + admin edits) on every `bootc upgrade`. LAW 1
  discourages treating it as anything but the admin-override surface.
- `/var` — mutable and persistent across upgrades; every runtime write
  goes here, with each path declared via `usr/lib/tmpfiles.d/*.conf`
  (LAW 2, NO-MKDIR-IN-VAR) rather than created at build time.

## Why MiOS uses it

- **Trusted boot for an autonomous system.** MiOS runs a local agent
  stack that acts on the machine. composefs guarantees the code that
  stack runs from (`/usr`) is exactly the bytes that were built and
  signed — any disk-level tampering is detected by fs-verity before the
  file is exposed to user space.
- **Efficient Day-2 deltas.** Identical files across image versions are
  stored once; `bootc upgrade` only fetches the deltas. This pairs with
  rechunk's deterministic 67-layer split
  (`bootc-base-imagectl rechunk --max-layers 67`) to keep upgrade
  transfers small — the same "boot it, `bootc upgrade` it like a
  `git pull`, `bootc rollback` it like a Ctrl-Z" lifecycle MiOS is built
  around.
- **No write amplification.** Applying an upgrade hardlinks unchanged
  files; only changed files consume new blocks.

## Cross-refs

- `usr/share/doc/mios/upstream/ostree.md` — the content-addressed store composefs verifies (and the `bootc-composefs-native` migration path)
- `usr/share/doc/mios/upstream/rechunk.md` — the 67-layer Day-2 delta optimization
- `usr/share/doc/mios/upstream/bootc.md` — the image lifecycle that deploys/upgrades/rolls back this mount
- `usr/share/doc/mios/concepts/architecture.md` §Filesystem-layout — canonical FHS 3.0 + bootc disposition (`/usr` read-only composefs, `/etc` 3-way merge, `/var` LAW 2)
