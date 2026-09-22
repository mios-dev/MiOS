<!-- AI-hint: Manual pages distilled from the source comments of harness, sanitized, each passage anchored to the comment it came from. -->

# harness

### MiOS embedded harness verification gate evaluator....

MiOS embedded harness verification gate evaluator.

Discovers `invariants/test_*.sh` scripts and executes each one, instead of
merely counting how many exist. Exit-code contract for invariant scripts:

    0   PASS  - invariant verified on this host/container.
    2   SKIP  - invariant is not applicable here (declared optional hardware
                or capability is absent); NOT counted as a pass.
    any other non-zero - FAIL.

The gate fails closed: zero discovered scripts, zero executed scripts, or an
all-SKIP run (nothing actually verified) all exit non-zero. This avoids the
"no tests found -> declared success" and "skip-as-pass" failure modes.

<!-- mios-src:39b79bed2e84 from harness/verification_gates.py:2-15 -->
