<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### render-ports.py -- project [ports.categories] onto the flat...

render-ports.py -- project [ports.categories] onto the flat [ports] table.

The categories table is the numbering SSOT: each category owns a `base`, a
`stride` and an ORDERED `members` list, and a member's port is

    base + index_in_members * stride

`pinned` entries (DNS/53) are protocol contracts and are emitted verbatim.

Usage:
    tools/render-ports.py            # rewrite the flat [ports] table in place
    tools/render-ports.py --check    # exit 1 if the flat table has drifted
    tools/render-ports.py --print    # print the derived name=port map

<!-- mios-src:11affdf550ad from tools/render-ports.py:3-16 -->

### Return {port_name: value} derived from [ports.categories]....

Return {port_name: value} derived from [ports.categories].

    Pinned ports are emitted at their literal value; derived ports are
    base + index*stride. stack_id is applied later by the resolver's
    process_val(), not here, so this stays the pre-offset SSOT.

<!-- mios-src:8f8b661954a5 from tools/render-ports.py:38-43 -->

### `${MIOS_PORT_X:-1234}` literals are degrade-open defaults...

`${MIOS_PORT_X:-1234}` literals are degrade-open defaults, but a
    hand-typed one silently goes stale the moment a category base moves. Treat
    them as GENERATED: rewrite every one to its SSOT value.

<!-- mios-src:8d84ef72541b from tools/render-ports.py:199-201 -->
