#!/usr/bin/env python3
"""Verify the ReWOO #E<id> substitution now smart-extracts a single
field instead of pasting the whole upstream JSON blob.

Test cases derived from operator's failure trace where the planner
emitted open_app(name=#En1) and substitution pasted mios_apps's
entire NDJSON output as the arg.
"""
from __future__ import annotations
import sys

sys.path.insert(0, "/usr/lib/mios/agent-pipe")
import server


def _make(out: str) -> dict:
    return {"output": out, "success": True}


def main() -> int:
    NDJSON = (
        '{"category":"linux-flatpak","name":"devel","description":'
        '"Files (org.gnome.Nautilus.Devel)","launch":"mios-gui devel"}\n'
        '{"category":"linux-rpm-gui","name":"org.gnome.Nautilus.Devel_flatpak"'
        ',"description":"Files","launch":"mios-gui org.gnome.Nautilus.Devel_flatpak"}\n'
    )
    JSON_OBJ = '{"name":"chrome","launch":"mios-gui chrome","desc":"Chromium"}'
    PLAIN = "Kingdom Come: Deliverance II"
    LONG = "a" * 2000

    cases = [
        ("ndjson_bare_ref",
         {"name": "#En1"},
         {"n1": _make(NDJSON)},
         {"name": "devel"}),  # first object's `name` field
        ("ndjson_field_ref_launch",
         {"name": "#En1.launch"},
         {"n1": _make(NDJSON)},
         {"name": "mios-gui devel"}),
        ("ndjson_field_ref_description",
         {"label": "#En1.description"},
         {"n1": _make(NDJSON)},
         {"label": "Files (org.gnome.Nautilus.Devel)"}),
        ("single_json_object_bare",
         {"name": "#En2"},
         {"n2": _make(JSON_OBJ)},
         {"name": "chrome"}),
        ("plain_text_bare",
         {"name": "#En3"},
         {"n3": _make(PLAIN)},
         {"name": PLAIN}),
        ("long_payload_capped",
         {"name": "#En4"},
         {"n4": _make(LONG)},
         {"name": "a" * 1024}),  # capped
        ("missing_ref_preserved",
         {"name": "#Enmissing"},
         {"n1": _make(NDJSON)},
         {"name": "#Enmissing"}),
    ]
    fails = 0
    for label, args, results, expected in cases:
        got = server._substitute_ek_refs(args, results)
        if got == expected:
            print(f"  PASS  {label}")
        else:
            print(f"  FAIL  {label}")
            print(f"        input:    {args}")
            print(f"        expected: {expected}")
            print(f"        got:      {got}")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
