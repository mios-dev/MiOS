<!-- AI-hint: Manual pages distilled from the source comments of log, sanitized, each passage anchored to the comment it came from. -->

# log

### Law 5

Law 5: the endpoint is MIOS_AI_ENDPOINT, or the SSOT agent-pipe port. The
resolver emits the name with a ${MIOS_PORT_*} placeholder, so an unexpanded
value is not usable and falls through to the port.

<!-- mios-src:ad0b3c8bec31 from usr/libexec/mios/log/mios-log-streamer:53-55 -->
