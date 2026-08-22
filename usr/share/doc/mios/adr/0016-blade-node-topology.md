<!-- AI-hint: The Blade-Node topology decision: what a blade is, what a node is, how a MiOS addresses a service that lives on another machine, and why "MiOS-Mini" currently names three different things. Establishes that base LINEAGE (which bootc base) and ROLE (what the machine does) are orthogonal axes, that service offload is a [urls] overlay rather than a code change because every pod is Network=host, and that the blade registry must key on something other than the port -- since port is currently the whole of a service's identity. Corrects the assumption that role selection is undecided: [blade] SINGULAR already implements one-image-role-by-flag and is a different axis from [blades] PLURAL. -->
<!-- AI-related: usr/share/doc/mios/concepts/mios-metal-architecture.md, usr/share/mios/mios.toml [blade], [urls], [ports], [blades], [nodes], [profile], usr/libexec/mios/role-apply, tools/generate-blade-dropins.py, usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py, usr/lib/mios/agent-pipe/mios_pipe/scheduler/vram.py -->
---
adr: 0016
title: "Blade-Node topology — orthogonal lineage/role axes, and service offload as a URL overlay"
status: accepted
date: 2026-08-22
deciders: [operator, ai-pair]
tags: [topology, blades, nodes, mini, offload, addressing, image-variants]
laws: [1, 3, 5, 7, 8, 9, 12]
ssot_keys: [urls, ports, blade, blade.archetypes, blade.requires, blades, nodes, profile, mini, quadlets.enable, greenboot.critical_services]
related_ws: [WS-BLADE, WS-MIOSSYS, WS-GUARD]
supersedes: []
superseded_by: []
---

# ADR-0016: Blade-Node topology — orthogonal lineage/role axes, and service offload as a URL overlay

## Status

**Accepted — all four decisions settled.** A seat is an **archetype**, not an image; the two
Hermes port keys **collapse into one**; blade-reachability as a boot-critical condition is
**configurable, defaulting to off**; and `Containerfile.minimal` is **deleted**. Decisions 1 and 2
were already mechanical consequences of what the tree is.

**Decision 3 is settled too, and it was settled by the requirement itself**: *"MiOS-Mini is the
full image just meant to offload all services to hosted (local, localhost or remote) MiOS OCI
image(s)."* That sentence assigns the name. **MiOS-Mini is the seat.** The hypervisor-router is
renamed **MiOS-Metal** and its SSOT surface moves `[mini]` → `[metal]`.

## Context

Three separate things in this repository currently answer to a variant of the name *mini*:

| Claimant | What it actually is | Evidence |
|---|---|---|
| `[metal]` (was `[mini]`) + `mios-metal-architecture.md` | A **tiny headless hypervisor-router**: binds every dGPU to `vfio-pci`, owns the NICs/radios/TPM, and boots the *full* MiOS as a super-privileged guest VM | `bind_dgpu_vfio = true`, `dgpumode = "vfio-pci"`, `[metal.gpu].assignments`, `[metal.mesh]` headscale; 224-line architecture doc with decisions D1–D5 and risks R1–R10 |
| `Containerfile.minimal` (**deleted**) | A **base-lineage variant** on bare `fedora-bootc`. It could not build: 8 of the 9 phase scripts it named no longer existed | header called it *"MiOS-Lite"*, `STUB / EXPERIMENTAL`; removed with its three dead `[image].minimal_*` keys |
| The operator's stated intent | A **full-featured seat** that runs the whole UX but offloads every service to a hosted MiOS OCI image, local / localhost / remote | stated requirement |

The first two are not variants of each other, and neither is the third. They differ on **two
orthogonal axes** that the naming has collapsed into one:

* **Lineage** — which bootc base the image is built from (`ucore-hci` vs `fedora-bootc`). Affects
  size, inherited kmods, and upstream lag. Decided at bake time.
* **Role** — what the machine *does* (owns metal and hypervises; serves services to others; runs
  the UX and consumes services). Affects which units start and where addresses point.

Conflating them is why "mini" had three meanings. Deleting `Containerfile.minimal` removes the
lineage claimant outright: it named 8 phase scripts that no longer exist, so it had not been
buildable for some time, and its `[image].minimal_base/_tag/_name` keys had zero consumers and
were not even emitted. **Two claimants remain, both on the role axis**, which is what makes the
naming question tractable.

### What the tree can express today

Measured, not assumed:

| Fact | Value |
|---|---|
| Pods | **All three are `Network=host`.** No container publishes a port |
| `[urls]` coverage | **9 of 40** addressable ports have a canonical URL; the other **31 are hand-composed** in 1–18 files each |
| Consumers hand-composing an address | ~125 non-generated, non-doc files |
| `[blade]` **singular** | **Implemented.** `type = "hybrid"`, `[blade.archetypes]`, `[blade.requires]` — the OS-role activation axis |
| `[blades]` **plural** | **Zero keys.** An empty section under a 30-line comment about nodes — a different axis (see below) |
| `[admission].multiblade_enable` | `false` |
| `[nodes.*]` | 6 declared; **5 point at the same endpoint and the same model**; 1 ships empty |
| `[nodes.local-cpu]` | `lane = "gpu"`, endpoint = the GPU heavy lane. There is no CPU lane |
| `[greenboot].critical_services` | `agent-pipe`, `llm-light`, `pgvector` |
| `[quadlets.enable]` gated off | exactly **one** container |

### The role axis is already built — on a different SSOT key

`[blade]` singular and `[blades]` plural are one letter apart and are **not the same axis**:

| Key | Axis | Answers | State |
|---|---|---|---|
| `[blade]` (singular) | **OS role** — what *this* machine activates | "am I a gpu-serving box or a controller?" | shipping |
| `[blades]` (plural) | **Fleet** — which *other* machines serve me | "who else is out there and how big are they?" | empty |

The `[blade]` chain is complete end to end: `[blade.requires]` → `tools/generate-blade-dropins.py`
→ `usr/share/mios/dropins/blade-<cap>.conf` (each a bare `ConditionPathExists=/etc/mios/blade.d/<cap>`)
→ `automation/48-mios-dropin-fanout.sh` → `<unit>.service.d/50-blade-<cap>.conf`, with
`usr/libexec/mios/role-apply` materializing the `/etc/mios/blade.d/*` markers and `/run/mios/blade.env`,
`mios-{hybrid,compute,endpoint,controller,headless,desktop}.target` present, `usr/libexec/mios/mios-blade`
present, and `usr/lib/greenboot/check/required.d/10-mios-role.sh` present.

Three things WS-BLADE claims as `done` are **not** in the tree, and each matters to this ADR:

1. **`usr/lib/bootc/kargs.d/05-mios-blade.toml` does not exist.** `role-apply` parses `mios.blade=`
   and `mios.role=` out of `/proc/cmdline`, so the *reader* ships; the generated karg default does
   not. Deploy-time role selection therefore works only where the installer sets the karg by hand.
2. **`role-apply` was never demoted.** BLADE-01 specifies a marker-writing resolver; it still calls
   `systemctl set-default --no-block` and `systemctl start --no-block` on the resolved target. The
   declarative half (markers + `Condition*`) and the imperative half both run.
3. **`[profile]` was never folded into `[blade]`.** `[profile].role = "developer"` is not one of the
   archetypes `role-apply` accepts (`hybrid|compute|endpoint|controller|headless|desktop|k3s*|ha*`),
   and `role-apply` never reads `[profile]` at all. Two role systems, no edge between them —
   `"developer"` would fall through to `*) WARN: unknown role … defaulting to headless`.

`Network=host` is the load-bearing one. It means every service genuinely *is* on the host's
loopback, so a service's identity is **its port number** and nothing more — `_discover_portal_services()`
dedupes the entire service surface by port. It also means the ~600 `localhost` references across
the tree are not sloppiness; they are the architecture stating itself.

The consequence cuts both ways. Because there is no network namespace to re-plumb, **moving a
service to another machine is purely an addressing change** — but because service identity *is*
the port, there is currently nowhere to put the "which machine" half of the answer.

### Addressing is already wrong locally — Hermes as the worked example

Decision 1 is not tidying. Traced end to end, one service disagrees with itself five ways:

| Source | Port | Kind |
|---|---|---|
| `[ports].hermes` | 8720 | SSOT |
| `[ports].hermes_worker` | 8730 | SSOT |
| `hermes-worker.service` `Environment=API_SERVER_PORT=` | **8643** | literal in the only gateway unit that ships |
| `mios_pipe/kernel/config.py`, `context/grounding.py` fallbacks | **8642** | literal, and a **retired** port |
| `mios_pipe/health.py` fallback | 8720 | agrees with the SSOT |

`hermes-worker.service` is the *only* unit in the tree that runs `hermes gateway run`, and it binds
a port the SSOT assigns to nothing. `hermes.service` and `hermes-agent.service` — named by the
greenboot probe, by unit comments and by the drift-check's external-unit allowlist — have no unit
file, so `[ports].hermes = 8720` is addressed by `[urls].hermes` and by agent-pipe's backend while
**nothing binds it**. The greenboot line `check_service hermes.service "${MIOS_PORT_HERMES:-}" tcp`
is therefore dead twice over: wrong unit name, and a port with no listener.

The retired-port fallbacks are the general form: **17 executable `os.environ.get("MIOS_PORT_X",
"<retired>")` defaults across 12 files**, each naming the correct variable and defaulting to a port
`[docs].retired_ports` says is gone. `check_doc_port_scheme` enforces Law 5 only over
`[docs].port_clean` — a list of *documents* — so no gate has ever looked at the code. A missing env
var makes these talk to a dead port quietly instead of failing loudly.

This is the same shape as the empty-set failures elsewhere in the tree: **a gate that reports
success over a set that excludes the thing it checks.** It is also the strongest argument for
Decision 1 — "offload is only an addressing change" is a promise the tree cannot keep until one
service has one address.

**Resolved.** There is one Hermes, so there is now one key: `[ports].hermes = 8720`, which
`hermes-worker.service` binds. `hermes_worker` is gone, the greenboot probe names the unit that
exists, and all 17 executable retired-port defaults now carry their SSOT value.

Deleting the key exposed a second defect worth recording, because it nearly shipped: **`[ports]`
allocates positionally** (`base + index * stride`), so removing one member silently renumbered the
five services after it — `daemon_agent`, `model_router`, `arbiter`, `mcp` and `opencode_gateway`
each slid down a slot. A collapse of two Hermes keys had a blast radius of five unrelated services,
and no gate would have objected because the result was internally consistent. `[ports.categories]`
now accepts an **empty member as a reserved slot** that holds its index without naming a port, so a
retired service cannot renumber its neighbours. Every other port is byte-identical to before.

## Decision

### 1. A service's canonical address is the key its consumers already read, and offload is an overlay

**The overlay half is proven.** `tests/test-offload-overlay.py` writes an `/etc/mios` overlay,
resolves the SSOT in a child process exactly as a booted host does, and asserts that the named
services move to the remote blade, that the unnamed ones stay local, that an empty override never
wins (Law 1), and that **no file under `usr/` changes**. Sabotaging the host tier turns it red.
So `Network=host` plus the three-layer resolver really does make offload an addressing change.

**The prescription in this decision's first draft was wrong, and the measurement is why.** It said
every service gets a key in `[urls]` and consumers resolve `MIOS_URL_*`. Measured:

| Variable | Tracked files that read it |
|---|---|
| `MIOS_AI_ENDPOINT` (from `[ai].endpoint`) | **72** |
| `MIOS_AGENT_PIPE_BACKEND` | 7 |
| `MIOS_DB_URL` | 4 |
| `MIOS_LLM_CPU_ENDPOINT` | 3 |
| `MIOS_CRAWL_SERVICE_URL` | 3 |
| `MIOS_HERMES_ENDPOINT` | 1 |
| **every `MIOS_URLS_*`** (all 12 `[urls]` keys) | **0** |

Every `MIOS_URLS_*` variable is emitted and read by no shipped code, while a parallel set of
endpoint keys carries the real traffic. (`MIOS_URLS_FORGE` has exactly one hit, and it is sample
data in `tools/test_render_globals.py` — a fixture, not a consumer.) Migrating ~125 consumer files onto `MIOS_URL_*` would have stood up a
**second** canonical naming scheme beside the one that already works — the exact Law-9 violation
this ADR argues against everywhere else, committed in Law 9's name.

So the decision is inverted: **a service's canonical address is whichever single key its consumers
already resolve.** Offloading the AI plane today means overriding `[ai].endpoint`, and that works.
What `[urls]` is for is the *browser-openable* surface — portal tiles, `openInBrowser` labels, docs
— which is a different job from an inter-service endpoint, and it should either be scoped to that
job explicitly or retired.

What still holds, unchanged, is the enforcement: exactly one canonical name per service, and no
consumer hand-composing `localhost:${MIOS_PORT_*}` for itself. `check_service_urls` classifies
every port as addressed-or-registered so a new service cannot land without an answer, and
`check_ports_bound` catches the adjacent failure — a port allocated but bound by nothing.

This is Law 9 (one canonical name) applied to **addresses**, and it is required under *every*
answer to the naming question, which is why it is decided first and separately.

**`[urls]` is now scoped rather than proposed.** This decision said `[urls]` is "the browser-openable
surface … to be scoped to that job or retired". It is scoped: every entry must use an `http`/`https`
scheme, which is what *a person can open it* means, and `check_service_urls` fails anything else.
Four entries were inter-service addresses wearing a tile's clothes — `pgvector` was a
`postgresql://` DSN, and `llm_light`, `hermes` and `crawl_service` were `/v1` API bases. Each already
has exactly one canonical name its consumers resolve (`MIOS_DB_URL`, `MIOS_LLM_CPU_ENDPOINT`,
`MIOS_HERMES_ENDPOINT`, `MIOS_CRAWL_SERVICE_URL`), so a `[urls]` key for them was the second name
this decision exists to prevent. They move to the register, whose comment now names the only two
reasons an entry may appear there: the port serves no page, or its address is already stated
elsewhere. The register stops being debt and becomes a classification — which is what it always was.

### 2. A blade is a machine; a node is a lane on a blade

* A **blade** is a machine that serves addresses. `[blades.<name>]` becomes the machine registry:
  reachability (host or tailnet name), what it serves, and its capacity envelope.
* A **node** stays what `_load_node_pool()` already makes it — one canonical inference worker on
  one lane — and gains a `blade` field naming its host. `[nodes.*]` keys stop pretending to be
  machines (`local-dgpu` and `local-sglang` are the same box, the same port and the same model).
* A **seat** is a machine that runs the UX and consumes addresses. A seat may also be a blade.

The existing `health_gate = true` semantics — *auto-join when reachable, drop when gone* — become
the blade-level availability primitive rather than a per-node flag.

`[blades]` being empty today is not a gap to fill with the current node list; the current node list
is five aliases for one backend and must collapse before anything is built on it.

`[blades]` plural is the fleet axis and must stay orthogonal to `[blade]` singular, exactly as
BLADE-01's own acceptance criterion already requires (*"`[blades.*]`/`[nodes.*]` fleet-dispatch
(Axis B) stays orthogonal to `[blade]` OS-activation (Axis A)"*). The two keys differing by one
letter is a Law 9 hazard in waiting; if either is renamed, rename it for the axis it names.

### 3. Naming — MiOS-Mini is the seat; the hypervisor-router becomes MiOS-Metal

The requirement assigns the name: *MiOS-Mini is the image that offloads its services*. So **mini
names the seat**, and the hypervisor-router — which does the opposite, owning the metal and
hosting a full MiOS as a guest — is renamed **MiOS-Metal**.

The word was carrying five meanings, which is why this had to be resolved rather than left open:

| Claimant | Now |
|---|---|
| `[mini]` VFIO hypervisor-router | renamed `[metal]` / MiOS-Metal |
| `Containerfile.minimal` "MiOS-Lite" | deleted (Decision 4's lineage note) |
| The operator's offloading seat | **MiOS-Mini** |
| `MiOS-Mon.py --mini` compact dashboard | unrelated, untouched |
| `zz-mios-motd.sh` terminal "mini" view | unrelated, untouched |

**MiOS-Mini is a product name for a role, not an image.** A MiOS-Mini is a machine running
`[blade].type = "endpoint"` — the seat archetype from Decision 4 — with an `/etc/mios` `[urls]`
overlay pointing at its blades. It is the *same OCI image* as every other MiOS; nothing about it
is smaller at bake time (Law 3 BOUND-IMAGES still ships every Quadlet image with the host). What
makes it mini is what it *activates*, not what it *contains*.

That is why the archetype key stays `endpoint` rather than becoming `mini`: `endpoint` is the
technical role name the role system already uses, and a second SSOT spelling for one concept is
the Law-9 violation this ADR keeps arguing against. Product name and SSOT key are different
registers, and only the SSOT key has to be unique.

The rename moved `[mini]`/`[mini.gpu]`/`[mini.mesh]` → `[metal]`, the three `[editions.*].mini.gpu`
overlays, the eleven `MIOS_MINI_*` resolver keys, `mios-mini-{vfio,mesh}-gen`, drift-check #68
(`check_mini_vfio` → `check_metal_vfio`) with its negative test, the names registry on both twins,
and `mios-mini-architecture.md` → `mios-metal-architecture.md`.

The lineage axis now has **one** member — the single root `Containerfile` — so nothing on that
axis competes for the name. `check_lint_is_final` globs `Containerfile*` rather than naming files,
and fails when the glob is empty, so a future lineage variant is covered the day it lands and a
tree with none cannot pass Law 4 vacuously.

### 4. One image, role by flag — already the mechanism; finish it on `[blade]`

Role is a **runtime** activation, not a bake-time fork, and this is not a proposal: `[blade].type`
→ capability markers → `ConditionPathExists` drop-ins is the WS-BLADE *"one image, role by flag"*
position and it ships. A seat is therefore **not a new image** — it is an archetype.

What this ADR decides is the three unfinished pieces, and that they land on `[blade]`, not beside
it. All three have now landed; what each turned out to be is recorded below, because two of them
were not what they looked like.

* **`[profile]` is gone, not aliased.** The plan was "alias onto `[blade]` for one release, then
  retire". Measurement made the alias pointless: `[profile].role = "developer"` was not a legal
  archetype, `role-apply` read `[blade].type` and never `[profile]`, `MIOS_PROFILE_ROLE` and
  `MIOS_PROFILE_FEATURES` were emitted by both `globals` twins and consumed by no shipped code —
  the resolver already classed the whole section `WALK_MOSTLY_DEAD` and resurrected exactly those
  two names through an explicit `WALK_EMIT_KEEP` exception — and the section's **only writer**,
  `user-setup.sh`, emitted `Role` with a capital `R`, which no reader spells that way. A key that
  is dead on both ends has nothing to alias. `[profile].features` had the same problem in a
  sharper form: its shipped values were `ai`, `virtualization`, `k3s`, and **none of them is a
  capability any archetype grants**. Retired outright; `check_role_ssot` fails a re-added
  `[profile].role` that is not a legal `[blade].type`, and fails either keep-list that names the
  retired vars again.

* **`05-mios-blade.toml` gets generated — and generating it broke three things.** The producer
  landed as specified (`tools/generate-blade-karg.py`, gate `check_blade_karg`). But the karg it
  emits is on **every** cmdline, and `role-apply` guarded its remaining tiers with
  `if [[ -z "$ROLE" ]]`. With the vendor karg always present, `ROLE` was never empty, so in one
  commit and with no error anywhere:
  `/etc/mios/role.conf` stopped being read (**`mios blade set` silently did nothing**), its
  `FEATURES=` stopped being read (**`mios blade add-capability` was erased on the next boot**,
  because `role-apply` clears `/etc/mios/blade.d` on every run), and the WSL / Blackwell / no-DRM
  hardware fallbacks became unreachable. This is the cost of a projection landing without the
  reader being re-read: the generator was correct in isolation and wrong in composition.

  The fix is a precedence **ladder** rather than a presence test, and it restores the same tier
  order the config overlay already uses — vendor(`/usr`) < host(`/etc`) < explicit:

  1. `mios.blade=` / `mios.role=` on the cmdline **that differs from `[blade].type`** — an
     operator changed it, so it wins;
  2. `ROLE=` in `/etc/mios/role.conf` — the host tier (Law 1);
  3. `[blade].type`, equivalently the generated karg — the vendor tier;
  4. the hardware sniff, which demotes **tier 3 only** to `[blade].fallback`: it corrects a role
     the vendor guessed and never overrules one a person chose.

  There is no fifth tier and **no archetype name anywhere in the blade code**. When the SSOT will
  not parse, `[blade].type` is empty, so any `mios.blade=` token differs from it and tier 1 claims
  it: the generated karg *is* the Law-12 floor. With neither, the resolver returns nothing rather
  than inventing an archetype. `tests/test-role-apply-precedence.sh` drives the real functions
  against fixtures; restoring the old presence test turns it red.

  Two smaller repairs fell out of the same reading. `role.conf` is now **parsed, not sourced** —
  `.` on a file under `/etc` runs it as root and clobbers whatever names it sets, which is how
  `FEATURES` used to vanish. And `mios.features=` used to `touch` any string into the capability
  namespace, so a typo created a marker nothing asks for and `mios.features=gpu-serving` was an
  undeclared escalation path; capability names are now the closed union of `[blade.archetypes]`,
  and `mios blade` refuses an unknown one with the legal set.

* **`role-apply` is demoted, but NOT to "starts nothing" — and that is a correction to this ADR.**
  The subtraction looked free and is not. Four of the six role targets are thin, and that sample
  produced the wrong generalisation: `mios-hybrid.target`, the **default**, carries
  `Requires=graphical.target` and `Wants=k3s-agent.service`, and `mios-desktop.target` requires
  `gdm.service` plus the libvirt stack. `automation/88-finalize.sh` bakes
  `set-default multi-user.target`, so on the **first** boot after install the role target is not
  reached by anything except `role-apply`'s `systemctl start`. Delete it and a fresh desktop
  install boots to a text console.

  Baking a role target instead was considered and rejected: it would put `Requires=graphical.target`
  on the boot-critical path of headless hardware, which fails worse and less visibly than a
  first-boot console. So `role-apply` keeps exactly one imperative act, and it is now
  **conditional**: `set-default` (declarative, decides the next boot, starts nothing) always; a
  `systemctl start` only when the resolved target differs from the one recorded in
  `/var/lib/mios/role.active`. Steady-state boots take neither branch — the markers alone decide
  what runs — so the "two racing schedulers" this bullet was written about are gone, without
  trading them for a broken first boot.

* **The role targets did not form a switchable set.** Day-2 switching depends on `Conflicts=`,
  since the new target is started rather than isolated. The graph shipped incomplete and the
  **default archetype conflicted with nothing at all**, so `mios blade set headless` on a hybrid
  blade started headless and left hybrid running. `[blade.archetypes]` and the shipped targets are
  now a complete pairwise graph, gated. Separately, `mios-hybrid.target` and `mios-k3s-worker.target`
  each declared `Alias=default.target.mios-<role>` — an alias must carry its unit's own suffix, so
  systemd can never install it, and because that alias *was* their entire `[Install]` section the
  default role target had no `WantedBy=` while all seven peers did.

* **Two roles selected a target while granting no capabilities.** `role-apply` matched `k3s*` and
  `ha*` as case globs, so `mios.blade=k3s` set `mios-k3s-master.target` and then resolved to `[]`
  capabilities — the target came up and the entire service plane stayed condition-skipped. Both
  are now declared archetypes, and the two legacy spellings are **data** in `[blade.role_aliases]`
  rather than globs, so `k3sx` no longer selects anything.

**A seat is `[blade.archetypes].endpoint`** — no new name for a thing the tree already had. An
archetype with **no capabilities is a seat**, because a blade activates a unit only when its
`ConditionPathExists=/etc/mios/blade.d/<cap>` marker is present.

**The taxonomy is the requirement's own words: a seat offloads *all* services.** So every declared
container requires the `service-plane` capability, which every archetype grants **except**
`endpoint`. The GPU lanes additionally require `gpu-serving` — repeated `ConditionPathExists` is an
AND, so a lane needs both markers.

| Archetype | Capabilities | Containers it activates (of 23) |
|---|---|---|
| `hybrid` (default) | `gpu-serving`, `controller`, `service-plane` | 23 |
| `compute` | `gpu-serving`, `service-plane` | 23 |
| `controller` | `controller`, `service-plane` | 20 |
| `headless` | `service-plane` | 20 |
| `desktop` | `service-plane` | 20 |
| `k3s-master` | `controller`, `service-plane` | 20 |
| `ha-node` | `controller`, `service-plane` | 20 |
| **`endpoint`** — the seat | *(none)* | **0** |

Only the seat's behaviour changes: every other archetype activates exactly what it did before,
because the three GPU lanes were already skipped wherever `gpu-serving` was absent.

**"Offload all services" cannot mean "start nothing."** The containers were half the plane: 18
long-running native `.service` units shipped ungated, so a seat started every one of them, and the
coverage gate's own "23 of 23" was reported over a set that excluded them. Those 18 split on the
seat/serving line this ADR already draws — *a seat runs the UX and consumes addresses*:

* **Gated off on a seat** (serving): `hermes-worker`, `k3s`, `mios-account-sync`, `mios-agents`,
  `mios-cron-director`, `mios-daemon`, `mios-finetune-serve`, `mios-mcp`, `mios-opencode-gateway`,
  `mios-policy-arbiter`.
* **`[blade].seat_side`** — a *positive* declaration, not debt: `mios-agent-pipe` (the local front
  door whose `MIOS_AI_ENDPOINT` points at the blade), `hermes-dashboard`, the two CDP browsers,
  `mios-hermes-tail`, and the two `ttyd` bridges. A seat with no agent-pipe has no way to reach its
  blade at all.

The gate now classifies **40 units** — containers and native units share one namespace, since a
Quadlet named `x` generates `x.service` — into exactly one of gated / seat-side / ungated-debt.
`tests/test-seat-activates-nothing.py` is the executable definition and runs in CI; returning one
container *or one native unit* to ungated turns it red.

**Hand-classification is not enough, and one derived rule proves it.** A unit that *activates* a
gated unit must carry that unit's capabilities, or it starts on a blade where its dependency is
condition-skipped and fails forever. Applied to the tree, that found **11 units nobody had
classified** — `mios-pgvector-backup`, `mios-embed-backfill`, `mios-skills-miner`,
`mios-userdb-render`, `mios-sys-env-refresh`, `mios-passport-provision`, the three forge
provisioners, `mios-k3s-master.target`, and `hermes-worker`. On a seat those timers would fire
forever against a database the machine does not run.

Two distinctions make the rule correct rather than merely strict. `After=` is ordering and
activates nothing, so it never propagates a gate. And a *soft* pull on a gated unit is acceptable
when the puller genuinely degrades — `hermes-worker` `Wants=` both lanes and falls back to the
light one — so `[blade].soft_ok` records that as a deliberate exemption instead of over-gating it
off three archetypes where it works today.

This is also why "must be classified" and "may be gated" are different sets: a oneshot needs no
classification of its own, but may legitimately be gated because of what it activates. Ten units
are gated for exactly that reason.

#### The line itself: a seat runs I/O, a blade runs compute and state

The `seat_side` list was assembled unit by unit, which left the *rule* implicit — and an implicit
rule cannot be checked. Stated: **a seat runs what the person touches; a blade runs what the work
needs.** Everything that survives on a seat is local I/O — the front door every client dials
(`mios-agent-pipe`), the browser the person watches (`mios-hermes-browser`), the UI
(`hermes-dashboard`), the journal view (`mios-hermes-tail`), and two ptys. Everything gated is
compute or state — inference, database, search, crawl, workers, cluster.

That rule settles the case that exposed it. **`mios-hermes-browser-worker` was seat-side and should
never have been:** it is not the person's browser, it is a second headless Chrome on `profile-w2`
whose only client is `hermes-worker`, which a seat does not run. A seat was starting a browser for a
worker it did not have. It is now gated with its consumer, which changes **only** the seat — every
other archetype keeps it.

The rule is mechanical, and the mechanism is why it was missed. **The AI plane couples over
ADDRESSES, not unit dependencies**, so the `Requires=`/`Wants=` walk that found the eleven
dependency violations structurally could not see this one: `hermes-worker` reaches the browser
through `BROWSER_CDP_URL`, and systemd has no idea. `check_blade_coverage` now also reads the port
graph: a seat-side unit that binds a port whose every *other* namer is capability-gated serves
nothing on a seat and fails the gate. The exemption is derived, not declared — a port is
person-facing when it has a browser-openable `[urls]` entry or is the one `[ai].endpoint` resolves,
which is exactly why `mios-agent-pipe` is legitimate seat-side while the worker browser is not.

#### Two roles the archetype table had not been asked about

**CDP stays local, permanently, and that is not a limitation.** The primary browser's binder is
`usr/share/mios/flatpak-flags/com.google.ChromeDev.flags`, a static flatpak argument file that
cannot template a placeholder — so `chrome_cdp` is pinned at 9222 rather than derived into the 8xxx
band. Under the I/O-versus-compute line that is correct rather than merely unavoidable: the browser
is a *device*, like the display and the keyboard. A seat offloads compute and state; it does not
offload the screen it is looking at.

**`mios-k3s` runs `k3s server` — a cluster control plane — and now requires `controller`.** The
default is unchanged: `[blade].type = "hybrid"` grants `controller`, as do `controller`,
`k3s-master` and `ha-node`. What changes is that an explicitly-chosen `compute`, `desktop` or
`headless` blade stops running a Kubernetes control plane, which is the plain meaning of those
names — `hybrid`'s own target wants `k3s-agent.service`, the *agent*, not the server. This is the
last consumer the `controller` capability needed: it was granted by four archetypes and required by
nothing, so a `controller` blade behaved exactly like a `headless` one.

A seat therefore costs one archetype plus the overlay from Decision 1. No new Containerfile, no new
axis, and — measured — **no service.**

Lineage stays a **bake-time** fork, because it is one — a different `FROM`.

The two must not be conflated again: a role must never require its own Containerfile, and a lineage
must never imply a role.

### 5. A seat's front door is off-box by design, so the seat is where auth stops being optional

Decision 1 makes offload an overlay: the seat repoints `[ai].endpoint` and the canonical key its
consumers already read. The `[ai]` header said the opposite — *"endpoint MUST stay on localhost;
vendor cloud URLs are forbidden by audit (postcheck #12 enforces this in the active config)"* — and
**there is no postcheck #12**; nothing in the tree enforced it. A rule guarded by a citation to a
check that does not exist is the `[profile].role` failure again, and here it directly contradicted
the topology.

The rule, restated so it is both true and enforceable:

* The **vendor** default stays local. `usr/share/mios/mios.toml` never ships an off-box endpoint,
  and never a vendor cloud URL — that half of Law 5 is real and is now checkable.
* An **operator overlay** may point the endpoint anywhere. That is the whole mechanism; local,
  localhost and remote are three values of it.
* An off-box endpoint means the request leaves the machine, so **`[security].api_require_auth` is
  the seat's precondition, not a preference.**

That last clause was unstatable until T-325: `api_require_auth` and `principal_bind_mode` had been
orphaned under an unclosed `[security.nohc_allowlist]` header, and both consumers read
`[security].<key>`, so both always took their compiled default. **The controls that bound a seat
could not be switched on.** They are reachable now; the defaults are unchanged (`false` and `off`),
because turning them on is an operator decision about front-door posture.

The tenancy question is what makes this a seat-specific decision rather than general hygiene. A
fully hosted MiOS is one machine, loopback, one human — an ungated front door costs little. A seat
inverts every term: the endpoint is off-box, N seats share one blade, and `owner_user`, the
row-scope on the shared pgvector memory, is derived from the request body's `user` field plus
forwarded headers, both settable by any direct caller. `principal_bind_mode = enforce` is what binds
that owner to an authenticated key. **It is the seat topology's only tenancy boundary.**

### 6. A seat has no local inference floor, and that is the definition rather than a gap

Every lane — heavy, alt, light, and the CPU node — is capability-gated off on `endpoint`, including
the one the resolver calls the always-on floor. When the blade is unreachable, a seat has a front
door that reaches nothing.

That is kept, because "offload *all* services" is the requirement and a floor would contradict it.
What is added is an **opt-in**, so the choice is the operator's rather than the archetype's: a
`seat-floor` capability, granted by no archetype, that ungates exactly one micro lane. `lfm2-700m`
is already baked and CPU-only, so the cost when it is off is zero and the cost when it is on is one
small model. A seat that wants degraded-but-alive grants it in `/etc/mios/role.conf`; a seat that
wants the pure definition does nothing.

The failure must also be *legible*, which is the half that was missing: a seat whose blade is gone
should say "blade unreachable", not surface a model error. The detection exists; wiring it to the
dashboard is what remains.

### 7. One image, always. The seat pays blade-sized disk and that is the correct trade

A seat carries every baked payload it will never load, including the vLLM AWQ snapshot (~16 GB by
the SSOT's own figure) and the GGUF set. Splitting the image would end that, and is refused: one
rebuildable image is the whole `bootc` premise, a second tag doubles the CVE surface for what is a
*runtime* difference, and Law 12 exists precisely so first boot never depends on egress.

Two corrections follow rather than a split. The cost must be **visible** — the baked-weight byte
count belongs in the generated comparison, so "a seat carries N GB it never loads" is a number an
operator can weigh. And `[ai.vllm].bake_model` is baked by default while `[ai.vllm].enable = false`,
which is not Law 12 discipline but an unreviewed default; the payload, not the image, is what should
become opt-in there.

### 8. A seat is stateless by definition, and skew between seat and blade must be visible

Memory, sessions, skills and events live on the blade. A seat keeps nothing, which is the honest
reading of "offload all services" and is hereby the contract rather than an accident.

Two consequences the tree did not express. `[greenboot].blade_reachability_critical = false` is
right — a seat must not roll itself back over someone else's outage — but it meant a seat's greenboot
could only ever fail on `mios-agent-pipe`, and the key itself was read by nothing: its only consumer
was the generator that *described* it. Blade reachability is now **recorded on every boot** and
becomes critical only when that flag says so (T-329). And nothing anywhere expresses a compatibility floor: seat and
blade `bootc upgrade` independently, and a seat two releases ahead of its blade fails
mysteriously. `[blade].min_peer_version`, reported by the reachability probe and **non-fatal**, is
the smallest thing that makes that legible.

### 9. "MiOS-Mini" is a role name and must never become a tag

The seat is byte-identical to the full image. "Mini" reads like a smaller build, and it is not one;
the generated comparison says so in its first line, and that is deliberate. If Mini ever became a
tag it would reverse Decision 7, so the two are recorded together: **the name describes a
`[blade].type`, never an artifact.**

## Consequences

**Enabling**

* Offload becomes a config overlay. A seat pointed at a blade is `[urls]` rewritten, nothing more.
* "local, localhost or remote" collapses into one mechanism: they are three values of the same URL.
* The blade registry gives the VRAM/admission machinery (`_BLADE_POOL`, `_ENDPOINT_BLADE`,
  `MULTIBLADE_ENABLE`) an SSOT to read, which it currently lacks.

**Costs and hazards**

* **A seat would have rolled itself back on every boot, and I said twice that it would not.** The
  first draft of this ADR predicted the rollback loop; the second "corrected" it on the grounds that
  `40-mios-ai-plane.sh` opens each probe with `systemctl is-enabled --quiet "$unit" || return 0`.
  That correction was wrong. **`is-enabled` reports installation, not whether a unit will start.**
  `Condition*` is evaluated at *start* time, so a capability-skipped unit is still enabled — and a
  Quadlet-generated unit reports `generated`, which also exits 0. On a seat the guard therefore does
  not fire: greenboot probes `mios-pgvector` and `mios-llm-light` on ports nothing is listening on,
  fails the required check, and hands `bootc` a bad boot.

  *Evidence level, stated honestly:* the units carry `[Install] WantedBy=` so Quadlet installs them,
  and `Condition*`-vs-enablement is documented systemd behaviour — but this container has no system
  bus and no man pages, so that half is reasoning rather than measurement. The fix does not depend on
  resolving it: the probe now asks **the same question the unit's own `ConditionPathExists` asks** —
  is the capability marker present in `/etc/mios/blade.d/`. Under the pessimistic reading that
  removes the rollback loop; under the optimistic one it replaces an accident with a design.
  `tests/test-greenboot-blade-guard.sh` exercises the real predicate against a fixture tree (no
  systemd required) and runs in CI; neutering the marker check turns it red. It degrades open when
  the blade resolver has not run at all, per Law 12.

* **`[greenboot].critical_services` is still read by nothing.** The check
  hardcodes its own four unit/port pairs. `MIOS_GREENBOOT_CRITICAL_SERVICES` is emitted by both
  `globals` twins and consumed by no shipped code — the same decorative-key failure as
  `[profile].role`, and it had already drifted: the SSOT lists three services, the check probes four
  (it adds `hermes`), and `check_greenboot` hardcoded the *check's* four rather than the *SSOT's*
  three, so the script and its gate agreed with each other while both ignored the source of truth.
  The gate now reads the SSOT; wiring the *probe* to it is what remains of T-314.
* **Whether a seat's "critical" may include reaching its blade is now a recorded choice**, not an
  implication: `[greenboot].blade_reachability_critical` defaults to `false`, so Law 12 holds by
  default (degrade open, never block boot) and an operator who wants a seat to fail its boot when
  its blade is unreachable opts in explicitly, in the SSOT, where the trade is visible.
* **Law 3 BOUND-IMAGES** symlinks every Quadlet image so it ships *with* the host. A seat that runs
  none of them still carries all of them. Either Law 3 gains a role-aware exception, or a seat is
  not actually smaller — only quieter.
* **Service identity is the port.** Two blades serving the same service collide in
  `_discover_portal_services()`, which dedupes by port. Either the portal service list moves to
  `[urls]`, or blades get a port offset — `[ports].stack_id` already computes `stack_id * 10000`
  and is the obvious candidate for a blade ordinal.
* **`Network=host` on a blade exposes every service** to anything that can route to it. A blade is
  only as safe as its mesh plus inbound auth; there is no per-service network boundary to attach a
  policy to.
* **Shared state is not shared identity.** Two seats on one pgvector collide on the `uid_alloc` /
  `gid_alloc` sequences and the RLS owner column. Either the blade is the identity authority, or
  seats keep local identity and rent only the vector store.

**Deliberately not decided here**

* Whether URLs gain a per-service host variable (`${MIOS_HOST_X}`) or are overridden whole. Whole-URL
  override needs no new machinery and is the default until a blade ordinal exists.
* Whether a seat may write to a blade's pgvector, and whose `[security.redact]` policy applies on
  the persist path when it does.
* Blade discovery. Static endpoints work today; `mios_gossip.py` has no transport under it (T-229).

## Rationale

The alternative — building a second image and a service-placement engine — was rejected because the
tree does not need one. `Network=host` already made every service address a real, routable address;
the only thing missing is a canonical name for each address and the discipline to use it. That is a
gate and a register, not an architecture.

Starting from naming would have been the mistake. The naming collision is real but it is
downstream: every mechanism above is identical whichever image ends up called *mini*.

This ADR's first draft read `[blades]` as empty and concluded the role axis was undecided. That was
an artifact of reading the plural key and not the singular one. Re-measured against the tree, the
role axis is the most finished mechanism in scope and the open work on it is subtraction — retire
`[profile]`, stop `role-apply` acting, generate the karg — not design. The unfinished axis is
addressing, which is Decision 1.
