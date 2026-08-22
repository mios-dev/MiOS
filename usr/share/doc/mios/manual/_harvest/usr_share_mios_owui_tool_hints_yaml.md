<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Source of truth for the MiOS-Agent refine pipe; maps canonical_verbs to intent descriptions and examples to make the model tool-aware and steer it toward specific shims like mios-find or mios-web-search.
AI-related: /usr/share/mios/owui/tool-hints.yaml, /usr/share/mios/configurator/mios.html, mios-find, mios-web-search, mios-everything, mios-apps, mios-gui-launch, mios-open-url, mios-show-image, mios-map
/usr/share/mios/owui/tool-hints.yaml

Canonical-verb manifest -- the source of truth the MiOS-Agent pipe
loads at init to make its refine step TOOL-AWARE. Operator
directive "prompt refining should be tool aware to be
able to hint". The refine system prompt was previously hardcoding
an intent table that had to be edited every time a shim was added
or removed; now the table is rendered from this YAML so:
  * Adding a new shim = one entry here + one shim binary
  * Refine starts hinting it on the next pipe reload (OWUI restart)
  * SOUL.md + Hermes still discover the shim via PATH, but the
    refine layer already steered the model toward it

Schema:
  canonical_verbs:
    - name:      <shim name, no path>
      intent:    <one-line description of the intent it fulfils>
      example:   <single example command the model should emit>
      tags:      [tag, tag, ...]   # optional, for grouping

Conventions:
  * Keep `intent` <90 chars: it becomes a single row in the refine
    prompt's markdown table.
  * Use placeholder angle-bracket tokens (<NAME>, <URL>, etc.) --
    the refine model substitutes the operator's actual nouns.
  * Order matters: refine sees the table top-down, so put the
    highest-value shims first (the ones the model otherwise
    hallucinates around: launchers, image, map, GUI, browser).

<!-- mios-src:53013e0423ce from usr/share/mios/owui/tool-hints.yaml:1-30 -->

