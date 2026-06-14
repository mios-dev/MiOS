<!-- AI-hint: Documentation for the MiOS Portal Android app, a minimal native WebView wrapper that gives MiOS a standalone, chrome-less mobile front-end to the MiOS Portal (the dashboard + chat UI served by mios-agent-pipe at GET / over the tailnet). Covers why this wrapper exists in the whole-system context, and three build paths for the APK: Android Studio (signed APK), command-line Gradle, and Bubblewrap TWA from the portal PWA manifest — plus the no-build PWA install option.
     AI-related: mios-portal-app, mios-agent-pipe -->
# MiOS Portal — Android app

## Purpose

MiOS is an immutable, bootc/OCI-shaped Fedora workstation that is *also* a
local, self-hosted agentic AI operating system: the same image that ships the
GNOME desktop ships the inference lanes, the multi-agent **agent-pipe**
orchestrator, MiOS-Hermes, and the PostgreSQL+pgvector memory behind one
OpenAI-compatible endpoint. The **MiOS Portal** is that system's web front door —
a dashboard + chat UI **served by `mios-agent-pipe` itself** (`GET /`, with its
`/portal/*` data endpoints for stats, services, and the swarm view), reachable
over the box's Tailscale tailnet at `https://mios.taildd86d0.ts.net/`. Login
gates the portal UI; the `/v1`, `/a2a`, and `/health` surfaces stay open as
programmatic endpoints.

This subproject is the Portal's **mobile face**: a minimal native Android
**WebView wrapper** so the operator can drive the running MiOS box from a phone
as if the Portal were a standalone app — one full-screen Activity, no browser
chrome, links stay in-app, hardware Back navigates WebView history. It is the
"minimal Android webapp wrapper" — the offline-buildable APK option, for when a
native installable is preferable to a browser tab. It adds no MiOS-side state of
its own; it simply renders the Portal that the agent-pipe already serves.

> **Where this builds.** The build host needs the Android toolchain (JDK 17 +
> Android SDK). That toolchain is **NOT present in the MiOS VM** (it isn't part
> of the OS image), so the APK is built *here*, on a machine with Android Studio
> (which bundles the SDK + Gradle). The MiOS box only needs to be reachable over
> the tailnet so the WebView has something to load.

## Build a signed APK (Android Studio — easiest)
1. **Android Studio → Open** → select this folder (`tools/mios-portal-app`).
   Let it sync (it provides Gradle + SDK; it will regenerate the gradle
   wrapper jar if missing).
2. Edit the target URL if your tailnet name differs:
   `app/src/main/res/values/strings.xml` → `portal_url`
   (default `https://mios.taildd86d0.ts.net/`).
3. **Build → Generate Signed Bundle / APK → APK** → create/select a keystore
   → **release** → finish. The signed `app-release.apk` is under
   `app/build/outputs/apk/release/`.
4. Sideload it on the phone (allow "install unknown apps"). Open it with
   **Tailscale connected + "Use Tailscale DNS" ON** (the WebView uses the
   system resolver, so the `.ts.net` name resolves — no Chrome DoH issue).

## Command line (if you have JDK 17 + Android SDK on PATH)
```bash
# one-time, if the wrapper jar is absent:
gradle wrapper --gradle-version 8.7
./gradlew assembleRelease            # unsigned -> app/build/outputs/apk/release/
# then sign with apksigner using your keystore.
```

## Alternative — Bubblewrap (TWA from the PWA, uses the manifest)
`node`/`npm` are present in the MiOS VM. With a build host that has internet
once (Bubblewrap fetches JDK + Android SDK on first run):
```bash
npx @bubblewrap/cli init --manifest https://mios.taildd86d0.ts.net/portal/manifest.webmanifest
npx @bubblewrap/cli build
```
This produces a Trusted Web Activity APK from the Portal's web manifest (served
by the agent-pipe at `/portal/manifest.webmanifest`). A TWA additionally needs
`/.well-known/assetlinks.json` with the signing fingerprint for full
URL-bar-less mode; the WebView wrapper above needs none.

## Easiest of all — no APK
The Portal is an installable PWA: open it in Chrome → **Install** button (top
bar) or **⋮ → Add to Home Screen** → standalone chrome-less app. No build. Same
URL, same Tailscale-DNS requirement as above — this is the zero-toolchain way to
get a home-screen icon for the running MiOS box.
