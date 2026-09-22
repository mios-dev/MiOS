<!-- AI-hint: Manual pages distilled from the source comments of gateway-agent, sanitized, each passage anchored to the comment it came from. -->

# gateway-agent

### The OpenAI error envelope

The OpenAI error envelope: `error` is an OBJECT, never a bare string.

    Every client on this endpoint (openai-python, OWUI, the Hermes gateway)
    reads body["error"]["message"], so a `{"error": "..."}` string raised a
    TypeError in the caller instead of surfacing the failure.

<!-- mios-src:808f14b677ac from usr/lib/mios/gateway-agent/server.py:114-118 -->

### A stream MUST close with a chunk carrying a finish_reason....

A stream MUST close with a chunk carrying a finish_reason. Every
path below that emits one flips this; the guard before [DONE]
covers the run that produced only ActionSteps and no
FinalAnswerStep, which used to end on nothing but null.

<!-- mios-src:a353b6b8322f from usr/lib/mios/gateway-agent/server.py:266-269 -->
