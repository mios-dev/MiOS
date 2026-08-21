<!-- AI-hint: Manual pages distilled from the source comments of searxng, sanitized, each passage anchored to the comment it came from. -->

# searxng

### Outgoing-request resilience. The default Google /...

Outgoing-request resilience. The default Google /
DuckDuckGo scrape paths CAPTCHA / 403 / 429 a self-hosted instance
(SearxEngineTooManyRequests / AccessDenied / CAPTCHA in the logs), which
zeroed result sets and made the agent fall back to geo-IP'd data. More
time + one retry keeps a slow engine from emptying the results; the cap
stops one dead engine stalling the whole query.

<!-- mios-src:122772c0039a from usr/share/mios/searxng/settings.yml:58-63 -->

### Engine curation. use_default_settings:true means this list...

Engine curation. use_default_settings:true means this list PATCHES the
upstream defaults by name (it does not replace them). Disable the chronic
blockers (Google scrape endpoints -- 403 / IndexError / CAPTCHA from a
self-hosted IP) and lean on engines that serve a self-hosted instance
reliably WITHOUT an API key. SearXNG auto-suspends any engine that errors,
so the remaining set fills in; DuckDuckGo is kept (it recovers from its
transient CAPTCHA) but is no longer load-bearing.

<!-- mios-src:e51c91dcad30 from usr/share/mios/searxng/settings.yml:71-77 -->
