<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Declares the persistent /home/coder volume for the mios-agents super-container (agy/claude logins + war-room state survive container restarts). Law 2 (NO-MKDIR-IN-VAR): the /var path is declared here, never written at build time.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md

<!-- mios-src:eb9fe332a267 from usr/lib/tmpfiles.d/mios-agents.conf:1-2 -->

### AI-hint

AI-hint: Defines systemd tmpfiles for Ceph orchestration, ensuring critical directories like /var/lib/ceph/crash/posted exist to prevent ceph-crash.service startup warnings and ensure proper storage path availability.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md

<!-- mios-src:634e1243b62b from usr/lib/tmpfiles.d/mios-ceph.conf:1-2 -->

### AI-hint

AI-hint: Defines filesystem permissions and ownership for the mios-crawl4ai service's working directory and Camoufox/crawl4ai cache locations to ensure the FastAPI service (uid 824) can persist state and browser assets.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md

<!-- mios-src:edca36662a68 from usr/lib/tmpfiles.d/mios-crawl4ai.conf:1-2 -->

### AI-hint

AI-hint: Defines filesystem permissions and setgid bits for mios-cron-director state and prompt storage, ensuring the mios-ai daemon and launcher-broker can share and access per-minute deduplication data and prompt text.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md

<!-- mios-src:3217f5899e41 from usr/lib/tmpfiles.d/mios-cron-director.conf:1-2 -->

### AI-hint

AI-hint: Defines filesystem permissions and ownership for the Forgejo Runner's persistent state directory (/srv/mios/forge-runner) and the build-output sentinel directory (/var/lib/mios/forge-runner) used by mios-bootc-switch.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md
Persistent runner state: registration record, workflow caches, job
logs. The runner image's entrypoint persists /data/.runner here so
subsequent starts skip re-registration.

<!-- mios-src:1160e039286c from usr/lib/tmpfiles.d/mios-forge-runner.conf:1-5 -->

### AI-hint

AI-hint: Defines filesystem paths, permissions, and ownership for the Forgejo service (SQLite DB, logs, and config overrides) to ensure correct runtime state and access for the mios-forge user.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md
Container's /data mount target. Holds the SQLite DB, repository bytes,
attachments, avatars, search index. /srv is the FHS-3.0 location for data.
Owned by user 1000 (mios) mode 0775.

<!-- mios-src:6faf025a2675 from usr/lib/tmpfiles.d/mios-forge.conf:1-5 -->

### AI-hint

AI-hint: Defines filesystem permissions and directory structures for FreeIPA, certmonger, and SSSD components to ensure proper runtime access and security for identity management.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md
-- certmonger ---------------------------------------------------------------

<!-- mios-src:7e7141d02190 from usr/lib/tmpfiles.d/mios-freeipa.conf:1-3 -->

### AI-hint

AI-hint: Defines systemd-tmpfiles for GPU runtime directories, CDI paths, and NVIDIA container toolkit configurations to ensure persistent mount points and environment files for GPU acceleration. 'MiOS' v0.2.4 -- GPU runtime directories.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md

<!-- mios-src:72ed803dde1a from usr/lib/tmpfiles.d/mios-gpu.conf:1-2 -->

### AI-hint

AI-hint: tmpfiles.d that creates the /var/lib/mios parent state dir (0755 root:root); the grd/gnome-remote-desktop var dir is intentionally NOT declared here (upstream's grd tmpfiles owns /var/lib/gnome-remote-desktop).
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md

<!-- mios-src:0432b413225e from usr/lib/tmpfiles.d/mios-grd.conf:1-2 -->

### AI-hint

AI-hint: Defines filesystem permissions and ownership for the mios-hermes-browser directory and profile, ensuring the mios-ai user can write launch logs and access the CDP Chrome profile to prevent service crash-loops.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md

<!-- mios-src:fcc7fe18070d from usr/lib/tmpfiles.d/mios-hermes-browser.conf:1-2 -->

### AI-hint

AI-hint: Declares the Hermes WORKER (:8643) runtime directory and its dedicated CDP browser profile, owned by the mios-ai service user, so the second isolated gateway instance has its own HERMES_HOME (separate pid/lock/state/DBs/config)...
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md

<!-- mios-src:133450529685 from usr/lib/tmpfiles.d/mios-hermes-worker.conf:1-2 -->

### AI-hint

AI-hint: Defines systemd-tmpfiles directory permissions and initial content for core infrastructure components including Cockpit, Libvirt, K3s, Ceph, and MiOS-specific configuration skeletons.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md
-- Cockpit ------------------------------------------------------------------

<!-- mios-src:a3e3bcd374be from usr/lib/tmpfiles.d/mios-infra.conf:1-3 -->

### AI-hint

AI-hint: Defines the persistent directory structure and initial manifest copy operations for the K3s cluster in /var/lib/rancher, ensuring the container runtime and storage drivers are correctly initialized at boot.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md

<!-- mios-src:fdfdad596ead from usr/lib/tmpfiles.d/mios-k3s.conf:1-2 -->

### AI-hint

AI-hint: Defines the /run/mios-launcher directory with 1777 permissions and mios ownership to provide a dedicated, persistent runtime path for the mios-launcher broker and hermes-agent to share sockets and tempfiles.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md

<!-- mios-src:aaad258832c3 from usr/lib/tmpfiles.d/mios-launcher.conf:1-2 -->

### AI-hint

AI-hint: Defines the directory structure and permissions for agent identity keys, ensuring public keys are accessible to the mios-ai group for cross-agent verification while restricting private keys.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md
Group=mios-ai (gid 850) -- every AI agent can resolve another
agent's public key without world-read. USER/SYSTEM/AI separation:
pubkeys narrowed from 0644 world-read to 0640 group-read on the
AI bucket. Per-agent private keys stay 0600 sysuser-owned.

<!-- mios-src:9481f2af15af from usr/lib/tmpfiles.d/mios-passports.conf:1-6 -->

### AI-hint

AI-hint: Defines filesystem permissions and ownership for SearXNG configuration and cache directories, ensuring the uwsgi worker (UID 818) has write access to the cache and the settings.yml file is correctly provisioned.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md

<!-- mios-src:acd5cb34b4f6 from usr/lib/tmpfiles.d/mios-searxng.conf:1-2 -->

### AI-hint

AI-hint: Defines systemd-tmpfiles symlinks to map mios-shell-verbs from /usr/libexec/mios/ to /usr/local/bin/ and /usr/local/sbin/ to ensure consistent tool availability across all user PATH configurations.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md
format: L+ <link> - - - - <target>
  L+  = symlink, replacing if already present (idempotent across builds)

<!-- mios-src:fe115f53a58d from usr/lib/tmpfiles.d/mios-shim-links.conf:1-4 -->

### AI-hint

AI-hint: Defines the persistent storage directory for the MiOS skill catalog at /var/lib/mios/skills, ensuring the miner (uid 822) can write and all AI agents (gid 850) can read the shared catalog.json file.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md
Owned by the agent-pipe sysuser (uid 822) so the miner timer (which
runs as that user) can write the catalog.json + any operator-
authored template files dropped here. Group=mios-ai (gid 850) so
every other AI agent (hermes, opencode, ...) can READ the
catalog without an explicit per-agent ACL. USER/SYSTEM/AI
separation -- writes still require uid 822 / sudo.

<!-- mios-src:db9b5d58eb7e from usr/lib/tmpfiles.d/mios-skills.conf:1-8 -->

### AI-hint

AI-hint: Declares /etc/mios/theme (Law 2: NO-MKDIR-IN-VAR / no ad-hoc mkdir at build or run time -- every /var and /etc runtime-writable path this repo creates is declared here so systemd-tmpfiles owns creation + permissions).
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md

<!-- mios-src:ab714b960648 from usr/lib/tmpfiles.d/mios-theme.conf:1-2 -->

### AI-hint

AI-hint: Defines the declarative materialization of the 'mios' user's home directory, skeleton files, and local assets (icons/fonts) to ensure persistent ownership and Flatpak-accessible paths on first boot.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md
Home directory + skel copy (one-shot at first boot).

<!-- mios-src:473a98a584ae from usr/lib/tmpfiles.d/mios-user.conf:1-3 -->

### AI-hint

AI-hint: Defines /tmp/.X11-unix as a physical directory (1777) instead of a symlink to ensure Flatpak/bwrap compatibility while allowing the mios-wslg-permissions-fix.service to bind-mount the WSLg X11 socket.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md
/tmp/.X11-unix as a real sticky directory (1777, root:root).

<!-- mios-src:8d3c70b6e9d7 from usr/lib/tmpfiles.d/mios-wslg.conf:1-3 -->

### AI-hint

AI-hint: Defines systemd-tmpfiles directory permissions and ownership for MiOS core components, ensuring the mios-ai user has proper access to the /var/lib/mios/ tree for model state, MCP context, and coderun scratch space.
AI-doc: usr/share/doc/mios/manual/tmpfiles.d.md

<!-- mios-src:b9db78c413d1 from usr/lib/tmpfiles.d/mios.conf:1-2 -->
