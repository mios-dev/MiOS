<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Deliberative Collective Intelligence (DCI) vocab + critic +...

Deliberative Collective Intelligence (DCI) vocab + critic + convergent flow.

Extracted verbatim from ``server.py``. Holds the DCI epistemic-act vocabulary +
JSON schema, the four persona system prompts, the single-persona B.1 critic
(``dci_critic_pass``), the 4-persona B.2 convergent flow (``run_dci_flow`` /
``_dci_call_persona``) and the B.3 conditional-escalation chain
(``critic_then_maybe_flow``). ``server.py`` re-imports every name under its
original alias so the module's public surface is byte-identical.

Config constants come from ``mios_config``; the server-side DB-event helpers and
the outbound-auth header stamper are injected via :func:`configure` (one-way
module boundary -- this module never imports ``server``).

<!-- mios-src:9204f1c1d38b from usr/lib/mios/agent-pipe/mios_pipe/routing/dci.py:3-15 -->

### Run the DCI-CF convergent flow on (user_text, envelope)....

Run the DCI-CF convergent flow on (user_text, envelope).
    Returns a structured deliberation result:
      {decision: <Integrator's final recommend act>,
       rounds: [[act_per_persona, ...], ...],
       dissents: [<tension acts>],
       converged: bool}
    Always returns -- the bounded loop guarantees termination.

<!-- mios-src:52c3686dedfd from usr/lib/mios/agent-pipe/mios_pipe/routing/dci.py:296-302 -->

### Chain B.1 critic -> conditional B.2 flow. Fire-and-forget...

Chain B.1 critic -> conditional B.2 flow. Fire-and-forget
    via _db_fire so the dispatch reply isn't delayed.

    Phase B.3 flow:
      1. Run dci_critic_pass (single-persona Challenger).
      2. If the act is in (challenge, ask) AND confidence is high,
         escalate to run_dci_flow (4 personas, bounded loop).
      3. If the flow surfaces unresolved dissent, write a tainted
         tool_call row keyed to the session so any subsequent
         high-privilege verb in this session gets firewalled.

<!-- mios-src:26ddc9d86479 from usr/lib/mios/agent-pipe/mios_pipe/routing/dci.py:420-430 -->

### Post-dispatch critic

Post-dispatch critic: invokes the DCI Challenger persona on
    the (user_text, envelope) pair and emits ONE typed epistemic
    act. Returns the parsed act dict, or None on any error.

    Fire-and-forget at the caller's discretion -- the chat reply is
    already rendered by the time this runs. Event row
    written automatically (kind=dci_act, source=mios-agent-pipe).

<!-- mios-src:ef943498b2b0 from usr/lib/mios/agent-pipe/mios_pipe/routing/dci.py:476-483 -->
