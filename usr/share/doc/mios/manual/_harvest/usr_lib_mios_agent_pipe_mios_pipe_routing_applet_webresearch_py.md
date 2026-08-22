<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Web-research SSE applet -- app-ifies the "Discovery / resolution" verb cluster (web_search/web_extract/crawl) as an HTML-over-SSE applet that streams progressively into the Gecko portal's iframe-applet shell (the slot the Configurator already occupies). Reuses the SAME transport as the chat pane (StreamingResponse text/event-stream) and the SAME dispatch chokepoint (dispatch_mios_verb via the configure() DI seam) -- no new language, image, or toolchain. `stream_webresearch(query, dispatch)` is a pure async generator (FastAPI-free) so it is unit-testable in isolation; build_router() wraps it for the portal; server.py mounts it with app.include_router(build_router()) after calling configure(dispatch=dispatch_mios_verb). Named SSE events (status/result/error/done) carry HTML fragments that htmx's SSE extension (hx-ext=sse, sse-swap) patches into the DOM one result at a time.
AI-related: ./portal.py, ./sse.py, ./chat.py, ../../mios_dispatch.py, ./verbcatalog.py, test_mios_applet_webresearch.py
AI-functions: configure, _sse, _li, _extract_results, stream_webresearch, build_router

<!-- mios-src:cc774efb8da2 from usr/lib/mios/agent-pipe/mios_pipe/routing/applet_webresearch.py:1-3 -->

