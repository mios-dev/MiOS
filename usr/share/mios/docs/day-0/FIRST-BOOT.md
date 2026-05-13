<!-- FHS: /usr/share/mios/docs/day-0/FIRST-BOOT.md -->

# Day-0: First Boot of MiOS-DEV

The Day-0 first boot is the moment MiOS-DEV becomes a self-contained
build environment. From this point on it can produce any number of
"next MiOS" images.

## What Happens

1. `systemd-firstboot` runs:
   - Hostname → `mios-dev-<short-uuid>`.
   - Generates `/etc/mios/agents/.local_key` (mode 0640).
   - Creates `mios` group; default user is added.
2. `mios-bootstrap.service` (oneshot) runs:
   - Clones the MiOS main repo into the shared root.
   - Runs `just check` to validate invariants (no `system_files/`,
     no `--squash-all` in any phase script, kargs.d TOMLs parse).
3. `mios-kb-reindex.service` (oneshot) populates Qdrant.
4. `mios-agent.target` brings up:
   - `ollama.service` (Quadlet),
   - `qdrant.service` (Quadlet),
   - optionally `localai.service` if `/etc/mios/agents/localai.enabled`.
5. Cockpit lands on :9090 over TLS with the platform CA.

## Verifying

```sh
mios status
# Expect: build target=ready, agent=hermes (ollama), kb=indexed
```

## First-boot ordering diagram

```
systemd-firstboot.service
        │
        ├──► mios-firstboot.service        (user/group, local key)
        │           │
        │           └──► mios-bootstrap.service    (clone, invariants)
        │                       │
        │                       └──► mios-kb-reindex.service
        │
        └──► mios-agent.target
                ├──► ollama.service       (Quadlet)
                ├──► qdrant.service       (Quadlet)
                └──► localai.service      (Quadlet, conditional)
```

`mios-agent.target` requires `mios-kb-reindex.service` to have
succeeded; the target itself is wanted by `multi-user.target`.

## What if Day-0 fails?

- The system still boots to a usable shell.
- `mios doctor` reports the first invariant that failed.
- `journalctl -u mios-firstboot -u mios-bootstrap -u mios-kb-reindex`
  shows phase-script output.
- Re-running is safe: `systemctl start mios-bootstrap.service`.

## Day-0 invariant checks

`just check` (run by `mios-bootstrap.service`) refuses to proceed if
any of the following are observed:

- A path `./system_files/` exists in either repo's view.
- Any file under `usr/libexec/mios/phases/` contains literal
  `--squash-all` or `((` (increment style under `set -e`).
- Any `usr/lib/bootc/kargs.d/*.toml` parses as containing a
  `[kargs]` section header.
- Any kargs source contains `init_on_alloc=1`, `init_on_free=1`,
  `page_alloc.shuffle=1`, or `lockdown=confidentiality`.
- Any dnf repo file under `etc/yum.repos.d/` sets `repo_gpgcheck=1`.
- `/etc/xrdp/xrdp.ini` references `libxvnc.so` or omits `libxup.so`.
- A `cp -a` writing into `/usr/local` is grep-detectable in any phase.
