# Law 7 — OFFLINE-FIRST capability matrix

> Operator directive 2026-05-17: "if a user had; 1. a MiOS Image to
> deploy, or 2. full repos offline on a usb drive, a windows or
> minimal fedora live environment — users can overlay, pull, build,
> deploy, run, host, re-build, use AI — ALL OFFLINE!!!"

This doc lists, per lifecycle phase, what works fully offline TODAY
and what still touches the network. The aspirational column lists the
fix needed to close the gap; track each in a PR.

## Scenarios

| Scenario | What the operator has | What they're doing |
|---|---|---|
| **1. Pre-built image** | A finished MiOS bootc OCI image (`localhost/mios:<tag>` or `.qcow2`/`.iso` artifact) | Boots the image, runs services + AI |
| **2. Full repos offline** | `mios.git` + `mios-bootstrap.git` checked out on USB, a Windows host or minimal Fedora live env with `podman` + `bootc` | Overlays repos, builds the image locally, deploys, runs |

Both scenarios MUST work with the host's network unplugged.

## Per-phase capability matrix

| Phase | Scenario 1 (image) | Scenario 2 (build) | Notes |
|---|---|---|---|
| **overlay** (apply repo files to `/`) | n/a | ✅ offline | Plain `install`/`cp` from the USB; no network needed |
| **pull** (acquire deps + sources) | n/a (image already has) | ⚠️ partial | dnf packages come from the OCI base layer (works if the base layer is cached); `automation/05-enable-external-repos.sh` + `09-fonts.sh` + `10-gnome.sh` + `13-ceph-k3s.sh` + `19-k3s-selinux.sh` + `38-hermes-agent.sh` hit github.com / pypi.org / flathub.org. **Gap.** |
| **build** (`bib`/`podman build` the OCI image) | n/a | ⚠️ partial | Bound-images law (3) bakes Quadlet container refs into `bound-images.d/` so the FINAL image carries them, but the BUILD step still pulls from the registry to populate. Pre-pulled local registry mirror closes this. |
| **deploy** (`bootc switch`/`bootc upgrade` to the new image) | ✅ offline | ✅ offline | bootc reads from the local image store; no network if the image is local |
| **run** (boot + start services) | ✅ offline | ✅ offline | All systemd units + Quadlets reference images from the local store via bound-images.d/ |
| **host** (serve OWUI, hermes, ollama, searxng, cockpit, k3s) | ✅ offline | ✅ offline | Every port (3030, 8642, 11434, 8888, 9090, 6443) binds localhost-or-LAN. No vendor cloud calls. |
| **re-build** (re-overlay + re-build after a code edit) | ✅ offline (if `automation/*-render-*.sh` only) | ⚠️ partial | Same gap as "pull" — if the edit touches a script that re-fetches an external dep, the re-build needs that dep cached |
| **use AI** (chat, refine, agent loop, tool calls) | ✅ offline | ✅ offline | Ollama models baked via `automation/37-ollama-prep.sh`; Hermes config seeded with `model.provider: custom:local-ollama` + `web.search_backend: searxng`; mios-sys-agent refiner on CPU via `/api/chat` with `options.num_gpu: 0`; all skills + SOUL.md on disk. Internet-using tools (Discord, Firecrawl) are OPTIONAL valves. |

## Remaining build-time gaps (Scenario 2)

These files reach the internet at build time. Each blocks a fully-
offline scenario-2 build. Tracking the work needed to vendor:

| File | What it fetches | Vendor as |
|---|---|---|
| `automation/05-enable-external-repos.sh` | `terra.repo` from github.com | Bundle `usr/share/mios/repos/terra.repo` |
| `automation/09-fonts.sh` | Geist + Nerd-Fonts archives from github.com | `usr/share/mios/vendored/fonts/{geist,nerd}.tar.xz` (LFS or bundled) |
| `automation/10-gnome.sh` | Bibata cursor + flathub remote URL | Bundle `usr/share/mios/vendored/bibata-*.tar.xz`; ship a local flathub mirror image |
| `automation/13-ceph-k3s.sh` | k3s binary + checksums from github.com | Bundle `usr/share/mios/vendored/k3s/k3s-<tag>` |
| `automation/19-k3s-selinux.sh` | k3s-selinux git clone | Bundle as a tarball in `usr/share/mios/vendored/k3s-selinux-<tag>.tar.xz` |
| `automation/38-hermes-agent.sh` | hermes-agent git + pip deps (aiohttp, websockets, discord.py) | Vendor wheels in `usr/share/mios/vendored/wheels/`; use `pip install --no-index --find-links=...` |
| (any) | dnf packages from Fedora mirrors | Already mostly cached by bootc base layer; for full offline, ship a local rpm mirror image |

## How to know if a build is fully offline

```
# from inside the build context, before `bib build`:
nmcli connection down "<your wifi>"  # cut the network
sudo podman build ...                 # if this succeeds, build is offline-safe
```

A passing offline build run is the canonical proof of compliance. The
`bib build` step itself is offline-safe (it reads from the local podman
store); the question is whether the IMAGE LAYERS the build references
were already pulled before the network cut.

## Audit (live, this host, 2026-05-17)

Runtime audit script: `/var/lib/mios/ai/scratch/audit-offline.sh`.
All 6 core services reachable on localhost; 4 of 4 tier models loaded
in Ollama; config.yaml provider/search/browser all local; SOUL + 5
skills + 9 mios-* verbs present; zero cloud API keys configured; 11
Quadlet images symlinked into `/usr/lib/bootc/bound-images.d/`.

**Runtime + use-AI phases: 100% offline-capable.**
**Build phase: needs the gaps above closed for true offline-from-USB.**
