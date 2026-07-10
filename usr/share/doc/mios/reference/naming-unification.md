<!-- AI-hint: The WS-NAME workflow -- a TRUE GLOBAL minification of MiOS naming: collapse the entire TOML-key/env-var/verb/const surface onto ONE deterministic, capability-matched unified names+keys registry (mios.toml section.key <-> MIOS_SECTION_KEY, 1:1), deleting the hand-maintained translation tables. Convention + registry + phased global migration + drift-gate. -->
<!-- AI-related: tools/lib/userenv.sh, usr/lib/mios/userenv.sh, automation/lib/globals.sh, automation/lib/globals.ps1, usr/share/mios/mios.toml, usr/lib/mios/mios_toml.py, automation/38-drift-checks.sh -->

# WS-NAME — Global Naming Minification → one unified names/keys registry

**Status:** planned (workstream) · **Source:** operator directive 2026-07-10 · **Effort:** XL (global, phased)

## Goal

A **true global minification and refactoring** of every name in MiOS — TOML keys,
env vars, verbs, shell/PS constants, configurator data-keys, emitted vars — into
**ONE unified names+keys registry** where every name:

1. **matches its capability** (the name says what it is/does — semantic, not arbitrary),
2. follows **one naming convention** (deterministic, no exceptions), and
3. is **minified**: exactly one canonical name per capability — no synonyms, no
   duplicates, no hand-maintained translation layer, and
4. is **folded**: *similar* capabilities are combined into one unified entry
   (often parametric) rather than N near-duplicate names — e.g. the many
   per-model/per-endpoint/per-tokenizer vars fold into one indexed/typed family;
   the per-color vars are one `colors.<name>` family; per-service ports are one
   `ports.<service>` family. Fold by capability, not by lexical accident.

**Hard invariant: NO loss of functionality.** Folding combines *names*, never
behaviors — every capability reachable today stays reachable (same values, same
effect); a fold that would drop or merge a real behavior is not done. This is a
rename/collapse only.

## The model: ONE registry, no translations

There is **one unified names/keys registry** — the single SSOT for naming. It holds
**one entry per capability** (minimal, combined: duplicates/synonyms merged). Every
surface **sources the same canonical identifier directly from that one entry** —
nothing is mapped, aliased, or translated:

- **No translation layer.** The 418-entry `userenv.sh` key→env table, the
  121-const `globals.sh`/`.ps1` mirror, and every emitter rename are **deleted**.
  There is no per-name authored mapping anywhere — a name exists in exactly one
  place (the registry) and is emitted verbatim to each surface's lexical form.
- **One identifier per capability.** Each registry entry carries the capability's
  canonical token (matching what it *does*). Its TOML key and its `MIOS_*` env name
  are the **same identifier** in the two required lexical forms (dotted-lower for
  TOML, `MIOS_`-UPPER_SNAKE for env) — generated together from the one entry, so
  they can never diverge. No reader-flavored prefixes (`MIOS_VERB_*`,
  `MIOS_AGENT_PIPE_*`), no arbitrary shortenings (`MIOS_USER`, `MIOS_KEYBOARD`), no
  suffix forms (`*_PORT`).
- **Verbs + consts** are entries in the same registry: a verb's name and its backend
  (`mios-<capability>`) come from its entry; a const is just an entry's env form —
  no independently-authored constant for a value the registry already owns.

### Why this is THE minification

Today ~1,290 names are **individually authored** across `userenv.sh` (418),
`globals.sh`/`.ps1` (121×2), emitters, verbs, and configurator — many are synonyms
for the same capability. Collapsing to **one registry, sourced everywhere** removes
every authored mapping and every synonym: the name count drops to the number of
distinct capabilities, and each is defined once.

## Registry artifact

The registry is an authored SSOT — `usr/share/mios/names.toml` (or a `[names]` tree
in `mios.toml`): one entry per capability = `{ token, kind, description }`. From it,
generators emit every surface: the env exports (replacing `userenv.sh`), the
`globals.*` consts, the verb→backend bindings, the configurator `data-key`s. A
committed `names.generated.txt` mirror is the auditable flat list; the drift-gate
regenerates and diffs it. This file/tree **is** the unified names/keys list.

## Global fix categories (what the migration collapses)

From the 2026-07-10 ultracode inventory (418 userenv + 121 globals + 635 misc +
117 verbs):

- **Reader-flavored prefixes** → capability prefix: `MIOS_VERB_EMBED_MODEL`,
  `MIOS_AGENT_PIPE_VISION_MODEL`, `MIOS_STACK_MODEL`, `MIOS_MICRO_*`,
  `MIOS_TOKENIZER_*` → `MIOS_AI_*` (their key lives under `[ai]`).
- **Short/native aliases** → deterministic key form: `MIOS_USER` →
  `MIOS_IDENTITY_USERNAME`, `MIOS_HOSTNAME` → `MIOS_IDENTITY_HOSTNAME`,
  `MIOS_KEYBOARD` → `MIOS_LOCALE_KEYBOARD_LAYOUT`, `MIOS_TIMEZONE` →
  `MIOS_LOCALE_TIMEZONE`, `MIOS_AI_KEY` → `MIOS_AI_API_KEY`, `MIOS_COLOR_*` →
  `MIOS_COLORS_*`, etc. (These were the "translations"; now 1:1 with the key.)
- **Suffix-form ports** → prefix form: `MIOS_K3S_API_PORT` → `MIOS_PORTS_K3S_API`
  (section is `[ports]` → `MIOS_PORTS_*`, uniformly).
- **Emitter/synonym collapse**: any var emitted under a second name
  (`MIOS_AI_BACKEND`, `MIOS_AI_HEAVY_ENDPOINT`, …) → drop the synonym; keep the one
  key-derived name.
- **De-dup**: two keys/consts for one capability → one canonical key; delete the rest.

> Decision to confirm during Phase 0: `[ports]` → `MIOS_PORTS_*` (pure determinism)
> vs the entrenched `MIOS_PORT_*` (12/16 already). Pick ONE and apply globally; the
> drift-gate then enforces it. (Deterministic-from-section favors `MIOS_PORTS_`.)

## Phased global migration (surface-shrinking)

- **Phase 0 — freeze the convention + generator.** Land the `section.key ->
  MIOS_SECTION_KEY` transform in `mios_toml.py` + a generator that emits
  `naming.generated.txt`. Resolve the `[ports]` prefix decision. No renames yet.
- **Phase 1 — resolver becomes deterministic.** Replace the 418-entry `userenv.sh`
  table with the generic transform (both parity copies; drift-check 27). Emit BOTH
  the new canonical name AND the legacy name (compat shim) for one release.
- **Phase 2 — repoint every reader**, domain by domain, lowest-blast-radius first
  (AI-plane ~3-4 readers each; ports 5-16; identity/colors moderate). Update
  `globals.*`, emitters, configurator data-keys, code, units, docs to the canonical.
- **Phase 3 — delete the shims + legacy names.** Remove every legacy alias so only
  the unified registry ships. `grep` of any legacy name = 0.

Each phase: `just drift-gate` green + `test_mios_*` pass + byte-parity held.

## Drift-gate (make it self-enforcing)

New `automation/38-drift-checks.sh` check: regenerate `naming.generated.txt` and
FAIL if (a) it differs from the committed copy, (b) any exported `MIOS_*` var is not
a deterministic image of a `mios.toml` key, or (c) a second name maps to a key that
already has a canonical env name. This makes the minimal unified surface permanent.

## Blast radius & risks

- **Scope:** global — ~1,290 authored names collapse to the SSOT key tree (one name
  per capability). Highest-reader migrations: `MIOS_PORT_PGVECTOR` (16),
  `MIOS_PORT_HERMES` (14), `MIOS_PORT_AGENT_PIPE`/`LLM_LIGHT` (12),
  `MIOS_IDENTITY_USERNAME` (27), `MIOS_DESKTOP_FLATPAKS` (10), `MIOS_IMAGE_BASE` (10).
- **Risks:** `userenv.sh` byte-parity; `install.env` emitters read on both Windows
  and Linux; configurator data-keys (598, already key-shaped — low risk); the
  compat-shim phase guarantees no functional gap. Do it domain-by-domain, verify each.
