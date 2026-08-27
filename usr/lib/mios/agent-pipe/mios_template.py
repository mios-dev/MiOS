# AI-hint: Renders an SSOT verb command template into the broker bash line.
# AI-related: usr/lib/mios/agent-pipe/mios_template.py, usr/lib/mios/agent-pipe/test_mios_template.py
# AI-functions: _template_to_cmd
"""Command template rendering logic for MiOS verbs.

Renders template placeholders like {arg}, {arg!}, {arg=default}, {arg?FLAG},
and {arg*} by resolving them via _arg_with_synonyms and shlex-quoting the values.
"""

from __future__ import annotations

import functools
import logging
import os
import re
import shlex
from typing import Optional, NamedTuple, Union

from mios_argval import _arg_with_synonyms

log = logging.getLogger("mios-agent-pipe")

_TEMPLATE_PH_RE = re.compile(r"\{([a-zA-Z_]\w*)(?:(=|\?|!|\*)([^}]*))?\}")

class _TemplateAbort(Exception):
    """Intentional render abort: a REQUIRED {arg!} placeholder was empty."""
    pass

class _Placeholder(NamedTuple):
    name: str
    op: Optional[str]
    rest: Optional[str]

class CompiledTemplate:
    """A pre-parsed command template with placeholder-name reflection and fast rendering."""

    def __init__(self, template: str, segments: list[Union[str, _Placeholder]], placeholder_names: set[str]):
        self.template = template
        self.segments = segments
        self.placeholder_names = placeholder_names

    def render(self, tool: str, args: dict) -> Optional[str]:
        """Render this compiled template into a bash command line."""
        try:
            out_parts = []
            for seg in self.segments:
                if isinstance(seg, str):
                    out_parts.append(seg)
                    continue

                name, op, rest = seg.name, seg.op, seg.rest
                val = _arg_with_synonyms(tool, name, args)

                if op == "!":
                    if _is_empty(val):
                        raise _TemplateAbort(name)
                    out_parts.append(_quote_val(val))
                elif op == "*":
                    if _is_empty(val):
                        continue
                    out_parts.append(" " + _quote_val(val))
                elif op == "?":
                    if _is_empty(val):
                        continue
                    flag = (rest or "").strip()
                    q = _quote_val(val)
                    out_parts.append(f" {flag} {q}" if flag else f" {q}")
                elif op == "=" and _is_empty(val):
                    dflt = rest if rest is not None else ""
                    if dflt.startswith("$"):
                        envname, _sep, fallback = dflt[1:].partition(":")
                        dflt = os.environ.get(envname, fallback)
                    out_parts.append(shlex.quote(str(dflt)))
                else:
                    out_parts.append(_quote_val(val))

            rendered = "".join(out_parts).strip()
            return rendered or None
        except _TemplateAbort:
            return None
        except Exception as e:
            log.warning("verb template render failed for %s: %s", tool, e)
            return None

def _quote_val(val):
    """Quote a scalar or list/tuple value for shell use."""
    if isinstance(val, (list, tuple)):
        return " ".join(shlex.quote(str(el)) for el in val)
    return shlex.quote("" if val is None else str(val))

def _is_empty(val):
    """Check if a value is absent/empty (scalar or list)."""
    if val is None:
        return True
    if isinstance(val, (list, tuple)):
        return len(val) == 0
    return not str(val).strip()

@functools.lru_cache(maxsize=256)
def compile_template(template: str) -> CompiledTemplate:
    """Compile an SSOT verb template string into a cached CompiledTemplate."""
    segments: list[Union[str, _Placeholder]] = []
    placeholder_names: set[str] = set()
    last_idx = 0

    for m in _TEMPLATE_PH_RE.finditer(template):
        start, end = m.span()
        if start > last_idx:
            segments.append(template[last_idx:start])

        name, op, rest = m.group(1), m.group(2), m.group(3)
        placeholder_names.add(name)
        segments.append(_Placeholder(name, op, rest))
        last_idx = end

    if last_idx < len(template):
        segments.append(template[last_idx:])

    return CompiledTemplate(template, segments, placeholder_names)

def _template_to_cmd(tool: str, template: str, args: dict) -> Optional[str]:
    """Render an SSOT verb command template into the bash line."""
    if not template:
        return None
    return compile_template(template).render(tool, args)

