# AI-hint: Renders an SSOT verb command template into the broker bash line.
# AI-related: usr/lib/mios/agent-pipe/mios_template.py, usr/lib/mios/agent-pipe/test_mios_template.py
# AI-functions: _template_to_cmd
"""Command template rendering logic for MiOS verbs.

Renders template placeholders like {arg}, {arg!}, {arg=default}, {arg?FLAG},
and {arg*} by resolving them via _arg_with_synonyms and shlex-quoting the values.
"""

from __future__ import annotations

import os
import re
import shlex
import logging
from typing import Optional

from mios_argval import _arg_with_synonyms

log = logging.getLogger("mios-agent-pipe")

_TEMPLATE_PH_RE = re.compile(r"\{([a-zA-Z_]\w*)(?:(=|\?|!|\*)([^}]*))?\}")


class _TemplateAbort(Exception):
    """Intentional render abort: a REQUIRED {arg!} placeholder was empty."""
    pass


def _template_to_cmd(tool: str, template: str, args: dict) -> Optional[str]:
    """Render an SSOT verb command template (mios.toml [verbs.*].cmd) into the
    bash line the broker runs (P3: retire hardcoded dispatch branches into the
    catalog). Placeholder forms (all values resolved via _arg_with_synonyms,
    then shlex-quoted):
      {arg}          required -- substituted in place (empty -> '').
      {arg!}         REQUIRED-or-abort -- if empty the WHOLE template renders to
                     None (replaces a hardcoded `if not arg: return None` guard).
      {arg=default}  default used when the arg is absent/empty. If `default`
                     starts with `$`, it is an ENV default `$ENVVAR:fallback`:
                     the value comes from os.environ[ENVVAR] (or `fallback` when
                     unset) -- e.g. {fanout=$MIOS_WEB_FANOUT:2}.
      {arg?FLAG}     OPTIONAL -- emits nothing when absent; else a
                     LEADING-space-prefixed " FLAG <value>" (or just " <value>"
                     when FLAG is empty). Author places NO literal space before
                     an optional placeholder, so an absent optional leaves no
                     double-space (no fragile whitespace-collapsing needed).
      {arg*}         SPLAT (varargs) -- for list/array parameters. Emits nothing
                     when absent/empty; else space-prefixed individually-quoted
                     elements (e.g. args=["a","b"] -> ' a b'). Designed for
                     positional trailing arguments like open_app.args.
    List/tuple values: when ANY placeholder resolves to a list/tuple, each
    element is individually shlex.quote'd and joined with spaces (automatic
    flattening). This applies to all placeholder forms, not just {arg*}.
    A template with no placeholders renders to its literal. Deliberately
    MINIMAL -- verbs needing conditional/recursive/base64 logic keep their code
    branch (the builder falls through when no `cmd` is set). Returns the rendered
    command, or None on render error (caller falls back to the hardcoded branch)."""
    try:
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

        def _sub(m: "re.Match") -> str:
            name, op, rest = m.group(1), m.group(2), m.group(3)
            val = _arg_with_synonyms(tool, name, args)
            if op == "!":
                # REQUIRED: empty -> abort the whole render (-> None).
                if _is_empty(val):
                    raise _TemplateAbort(name)
                return _quote_val(val)
            if op == "*":
                # SPLAT (varargs): list -> individually quoted, space-prefixed.
                if _is_empty(val):
                    return ""
                return " " + _quote_val(val)
            if op == "?":
                if _is_empty(val):
                    return ""
                flag = (rest or "").strip()
                q = _quote_val(val)
                return f" {flag} {q}" if flag else f" {q}"
            if op == "=" and _is_empty(val):
                dflt = rest if rest is not None else ""
                # ENV default: `$ENVVAR:fallback` -- the one place a verb default
                # legitimately comes from the host env.
                if dflt.startswith("$"):
                    envname, _sep, fallback = dflt[1:].partition(":")
                    dflt = os.environ.get(envname, fallback)
                return shlex.quote(str(dflt))
            return _quote_val(val)
        rendered = _TEMPLATE_PH_RE.sub(_sub, template).strip()
        return rendered or None
    except _TemplateAbort:
        return None
    except Exception as e:
        log.warning("verb template render failed for %s: %s", tool, e)
        return None
