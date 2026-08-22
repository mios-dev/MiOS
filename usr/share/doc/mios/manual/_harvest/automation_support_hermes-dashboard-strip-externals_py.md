<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Strip externally-hosted asset URLs from the built Hermes...

Strip externally-hosted asset URLs from the built Hermes dashboard.

Runs after `npm run build` against `<repo>/hermes_cli/web_dist`. The
upstream React bundle ships five OPTIONAL theme stylesheets that
reference `fonts.googleapis.com` for typography (Inter, JetBrains Mono,
Spectral, IBM Plex, Share Tech Mono, Fraunces, DM Mono). The DEFAULT
theme uses the @nous-research/ui bundled woff2 fonts (in `web/public/
fonts/`) and works offline. Patching the optional-theme URLs to an
inert `data:text/css,` URI keeps the theme switcher's UI alive but
turns the non-default themes into a no-op rather than a Google Fonts
fetch.

Architectural Law 7 (OFFLINE-FIRST): the runtime must never reach out
to an external service. Build-time deps (npm install from registry)
happen once during image build; runtime is offline.

Usage:
    hermes-dashboard-strip-externals.py /path/to/hermes_cli/web_dist

<!-- mios-src:f28ea281a9e5 from automation/support/hermes-dashboard-strip-externals.py:3-21 -->
