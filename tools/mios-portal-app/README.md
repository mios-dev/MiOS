# MiOS Portal — Android app

A minimal native **WebView wrapper** around the MiOS Portal
(`https://mios.taildd86d0.ts.net/`): one full-screen Activity, no browser
chrome, links stay in-app, hardware Back navigates WebView history. This is
the "minimal Android webapp wrapper" — the offline-buildable APK option.

> The build host needs the Android toolchain (JDK 17 + Android SDK). It is
> NOT present in the MiOS VM, so the APK is built here, on a machine with
> Android Studio (which bundles the SDK + Gradle).

## Build a signed APK (Android Studio — easiest)
1. **Android Studio → Open** → select this folder (`tools/mios-portal-app`).
   Let it sync (it provides Gradle + SDK; it will regenerate the gradle
   wrapper jar if missing).
2. Edit the target URL if your tailnet name differs:
   `app/src/main/res/values/strings.xml` → `portal_url`.
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
This produces a Trusted Web Activity APK from the portal's web manifest.
(TWA additionally needs `/.well-known/assetlinks.json` with the signing
fingerprint for full URL-bar-less mode; the WebView wrapper above needs none.)

## Easiest of all — no APK
The portal is an installable PWA: open it in Chrome → **Install** button (top
bar) or **⋮ → Add to Home Screen** → standalone chrome-less app. No build.
