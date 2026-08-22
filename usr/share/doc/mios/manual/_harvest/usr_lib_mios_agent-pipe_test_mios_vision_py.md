<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Stdlib assert-script for mios_vision (refactor R9). Covers...

Stdlib assert-script for mios_vision (refactor R9).

Covers the two load-bearing branches of the extracted module with stubs (no
network / no DB):

  1. the VISION honest-error gate -- with NO vision model provisioned,
     ``_vision_complete`` returns an HONEST "vision unavailable" assistant turn
     (never a raw 5xx, never a fabricated description); ``_vision_backend_failed``
     classifies a degraded backend correctly.
  2. the CLIENT-TOOLS tool_call handback -- when the model emits a CLIENT
     (non-MiOS) tool_call, ``_client_tools_loop`` hands the whole assistant
     message back UNCHANGED for the caller to execute, and ``_client_tools_wrap``
     shapes it with finish_reason=tool_calls.

<!-- mios-src:a17a05418629 from usr/lib/mios/agent-pipe/test_mios_vision.py:3-16 -->
