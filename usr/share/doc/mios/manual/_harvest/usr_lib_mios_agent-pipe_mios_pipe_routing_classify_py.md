<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Stage-1 of the domain router

Stage-1 of the domain router: classify the query into ONE [routing.domains]
    label via a constrained enum (response_format json_schema), THINKING-OFF
    (llama.cpp #20345 silently drops the grammar when thinking is on). Returns the
    validated domain, or None to fall through to the FULL surface (router off / no
    domains / classify error / out-of-enum result). We VALIDATE the label in code
    and never trust HTTP 200 alone (fail-open #19051).

<!-- mios-src:073a9eccad06 from usr/lib/mios/agent-pipe/mios_pipe/routing/classify.py:129-134 -->
