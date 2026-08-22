<!-- AI-hint: Chapter 55: Dead Schema and Half-Wired Units. Two fitness functions for things that exist but do nothing. check_schema_consumers requires every table in schema-init.sql to have a real code consumer, and explains why a doc, a config file or a generated projection is not one. check_firstboot_provisioners requires each first-boot triple - fetcher, unit, preset, tmpfiles - to be whole, because a half-wired one looks installed and silently never runs. Records the nine dead tables found, including the one-letter duplicate that would have looked correct while losing every row. -->

# <a name="55_dead_schema_and_half_wired_units"></a>Chapter 55: Dead Schema and Half-Wired Units

> Part VII: Build, Test & Upstream Maintenance of the [MiOS manual](../manual.md).

> Path Reference: `/usr/share/doc/mios/manual.md#55_dead_schema_and_half_wired_units`

#### Overview

A missing thing announces itself. A thing that *exists but does nothing* does
not: the table is in the schema, the unit is in the preset, everything reads as
built. Two gates cover that shape.

#### <a name="55_the_dead_table_gate"></a>55.The Dead-Table Gate: The Dead-Table Gate

`check_schema_consumers` requires every table in
`usr/share/mios/postgres/schema-init.sql` to have at least one **code**
consumer. A table nobody reads or writes is one of two things, and both are
worth surfacing:

* **Planned but unbuilt.** Legitimate, but it should be recorded rather than
  inferred from silence.
* **A trap.** `mios_identity.account_preferences` sits one letter from the live
  `account_preference` that `materialize-user-config.py` actually reads. A
  writer aimed at the wrong name would run without error, return success, and
  lose every row.

Nine tables were dead when the gate went in: the six `mios_security.*` WS-SEC
tables (`fido2_keys`, `usb_rules`, the three `headscale_*`, `keepass_vaults` —
mentioned *nowhere* in the tree), the `account_preferences` duplicate, and
`person_device` + `person_app_install`. All nine are listed in
`[schema].unconsumed` with a reason. The register is **shrink-only**: a
registered table that later gains a consumer *fails* the gate until its entry is
removed, so the list drains instead of accumulating.

#### <a name="55_what_counts_as_a_consumer"></a>55.What Counts as a Consumer: What Counts as a Consumer

Getting this wrong is how the gate would have become vacuous, and two of the
three exclusions were found by the gate failing on itself.

| Surface | Counts? | Why |
|---|---|---|
| `.py`, `.sh`, `.rs`, … | **yes** | it can actually read or write rows |
| `.md`, `.txt`, `.tsv` | no | a doc mentions a table; it does not use it |
| `.toml` | no | config *declares policy about* a table — and this gate's own register names every table in it, so counting TOML would let the register satisfy the gate |
| generated projections | no | a file stamped `GENERATED IN FULL from usr/share/mios/mios.toml` re-emits whatever the SSOT says, register included |

The last one is not hypothetical. The first version excluded `.toml` but not
generated files; the next `sync-generated.sh` run rebuilt
`automation/lib/globals.sh` from the SSOT, which now contained the register, and
all nine registered tables suddenly looked consumed. Generated files are
detected by the marker the renderers stamp, so a new projection is excluded
automatically rather than needing a list. Both cases are pinned by tests.

Two of the nine — `person_device` and `person_app_install` — only appeared once
`.toml` stopped counting. Their sole mentions were in the SSOT.

#### <a name="55_the_provisioner_triple_gate"></a>55.The Provisioner-Triple Gate: The Provisioner-Triple Gate

A first-boot provisioner is not one file, it is a triple: a libexec fetcher, a
systemd unit, and a preset line — plus the tmpfiles declarations for whatever
`/var` paths it writes. Any one of those missing produces a unit that looks
installed and silently never does its job.

`check_firstboot_provisioners` asserts all of it:

1. The fetcher exists **and is the unit's `ExecStart`**.
2. The unit carries `ConditionPathExists=!<sentinel>`. Without it the oneshot
   re-runs on every boot.
3. That sentinel path is one the fetcher **actually names**. Gating on a path
   nothing writes is the mirror failure: the unit runs forever.
4. A preset line enables it — otherwise it ships installed but unstarted.
5. Every `/var` directory it writes is declared in `tmpfiles.d` (Law 2), not
   `mkdir`'d at runtime.

Clause 3 is the one worth dwelling on, because it is the shape the sentinel bug
took in `mios-models-firstboot`: the gate and the writer have to agree on a
string, and nothing but a gate makes them.
