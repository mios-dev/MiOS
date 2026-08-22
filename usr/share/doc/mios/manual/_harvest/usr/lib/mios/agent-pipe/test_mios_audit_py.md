<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### NG-3

NG-3: a payload handed in as a pre-serialised JSON STRING and the SAME payload
        as a parsed dict must canonicalize identically. payload is a jsonb column;
        psycopg reads it back as the parsed object at verify time, so write-time (which
        may see either form) must not diverge from verify-time (which always sees the
        parsed object) -- else the chain reports a spurious "broken" link.

<!-- mios-src:7d84c8799dae from usr/lib/mios/agent-pipe/test_mios_audit.py:104-108 -->
