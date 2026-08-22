<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Pre-flight

Pre-flight: the three inputs must exist. Missing inputs is a hard error
(the lint cannot make any assertion) -- but stay degrade-friendly: if the
Quadlet dir is simply absent (e.g. a minimal checkout), PASS vacuously.

<!-- mios-src:3f7fe6a1077a from automation/97-ssot-lint.sh:19-21 -->

### (1) Collect every ${MIOS_*} referenced in an...

--- (1) Collect every ${MIOS_*} referenced in an Exec=/Environment= line. ----
We scan recursively (the dir has a users/ subtree). Match the directive at
line start (Exec=, ExecStart=, ExecStartPre=, ExecStartPost=, Environment=).
From those lines, extract bare placeholder NAMES of the form ${MIOS_...}
(with or without a ':-default' tail). Critically we extract only the
PLACEHOLDER inside ${...}; the left-hand `Environment=MIOS_FOO=` literal
(a container-internal env var name being SET) is NOT a placeholder and is
correctly ignored because it is not wrapped in ${...}.

<!-- mios-src:7daebbc3a66d from automation/97-ssot-lint.sh:40-47 -->

### (2) Build the userenv.sh wiring set....

--- (2) Build the userenv.sh wiring set. -------------------------------------
A var is "wired in userenv" if it appears, on a NON-comment line, either as
a typed slot target  ("section.field", "MIOS_X")  -> the quoted token
"MIOS_X"  -- or as an explicit  export MIOS_X=  /  MIOS_X=  assignment, or
named in a legacy for-loop. We strip full-line comments first so a var that
is only *mentioned* in prose (e.g. MIOS_CRAWL_CDP_URL in a doc paragraph)
does NOT count as wired.

<!-- mios-src:bd0d334822c4 from automation/97-ssot-lint.sh:65-71 -->

### (3) Build the render-quadlets.sh allowlist set....

--- (3) Build the render-quadlets.sh allowlist set. --------------------------
A var is "wired in render" if it appears in the envsubst allowlist string
( ${MIOS_X} ) and/or the bash-fallback `for var in ...` list ( MIOS_X ),
on a NON-comment line. Both forms reduce to: the bareword MIOS_X occurs in
render-quadlets.sh code. (render-quadlets.sh also EXPORTS a couple vars
dynamically -- e.g. MIOS_CODE_SERVER_UID via `id -u` -- which the bareword
match likewise accepts.)

<!-- mios-src:8abe5835330f from automation/97-ssot-lint.sh:98-104 -->
