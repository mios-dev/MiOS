<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Static public-surface projection + diff for the agent-pipe...

Static public-surface projection + diff for the agent-pipe server monolith.

The refactor (R0..R12) MOVES blocks of ``server.py`` into sibling modules
behavior-identically, re-importing the moved names so the module's importable
surface is unchanged, and finally collapses ``server.py`` to a re-export shim.
The silent regressions that move can cause are:

  1. an ``@app`` route is dropped / its path or handler renamed, and
  2. a name that external code relies on (a sibling ``mios_*.py``, a ``test_*.py``,
     or a libexec tool that does ``from server import X`` / accesses ``server.X``)
     vanishes from the module entirely.

Both are invisible to a syntax check and to the per-module unit tests. This
projector captures the surface as a committed golden
(``usr/share/mios/ai/v1/surface.generated.json``); the ``check_surface_parity``
gate in ``98-drift-checks.sh`` regenerates it from the live ``server.py`` and
fails on any diff.

KEY INVARIANT -- ``provided`` counts a re-imported name the SAME as a defined one
(it is the set of all module-level *bound* names), so a legitimate
"move definition into a sibling + ``from sibling import name``" extraction is
**zero-diff**, while deleting the name with no re-export is a REMOVED violation.
Pure stdlib + ``ast`` only (no execution of server code) -- the offline half of
"make the refactor regression-proof".

``project_surface`` projects ONE file. ``project_package`` projects a whole
package (the entry module plus the sibling router modules it mounts), resolving
``app.include_router`` mounts that cross file boundaries so the gate stays honest
once routes migrate off ``@app`` onto APIRouter instances in sibling modules. It
is a strict superset of ``project_surface``: on a single-file layout (the current
``server.py``) the two produce the IDENTICAL projection.

<!-- mios-src:24613613b335 from usr/lib/mios/agent-pipe/mios_surface.py:3-34 -->

### Map ``<targets> = APIRouter(...)`` to ``(prefix, [bound...

Map ``<targets> = APIRouter(...)`` to ``(prefix, [bound names])``.

    The router constructor is recognised by its terminal callee name, so both a
    bare ``APIRouter(...)`` and an attribute ``<pkg>.APIRouter(...)`` form match --
    the same structural-API basis on which the ``app`` route object is recognised.
    ``prefix`` is the literal ``prefix=`` kwarg, the empty string when the kwarg is
    omitted (the constructor's own default), or ``_DYNAMIC`` when the kwarg is
    present but not a string literal. ``None`` for any other assignment.

<!-- mios-src:90ecd78ea9ee from usr/lib/mios/agent-pipe/mios_surface.py:92-100 -->

### Map an ``app.include_router(<router>, prefix=...)``...

Map an ``app.include_router(<router>, prefix=...)`` statement to
    ``(router name, mount prefix)``; ``None`` otherwise.

    Mounting a router prepends this prefix to every one of the router's paths.
    ``prefix`` is the literal kwarg, the empty string when omitted, or ``_DYNAMIC``
    when non-literal. Only ``app``-mounted routers are composed here (the in-file
    scope documented on ``project_surface``); a router mounted onto another router
    is not transitively chained.

<!-- mios-src:c3cb972858c7 from usr/lib/mios/agent-pipe/mios_surface.py:120-128 -->

### Map a ``@<obj>.<method>("/path", ...)`` decorator on a...

Map a ``@<obj>.<method>("/path", ...)`` decorator on a NON-``app`` object to
    ``(obj name, METHOD, path)``; ``None`` otherwise.

    Structurally identical to ``_route_from_decorator`` but for an object other
    than ``app`` -- a candidate router variable. The caller keeps only candidates
    whose object was bound to an ``APIRouter`` instance; ``app`` is excluded here
    because ``_route_from_decorator`` already projects it, so it is never counted
    twice.

<!-- mios-src:604f93c8d3d3 from usr/lib/mios/agent-pipe/mios_surface.py:146-154 -->

### Concatenate route path segments (mount prefix + router...

Concatenate route path segments (mount prefix + router prefix + decorator
    path) exactly as FastAPI mounts a router -- plain left-to-right concatenation.

    If ANY segment is the ``_DYNAMIC`` sentinel the whole path is ``_DYNAMIC``,
    mirroring how a single non-literal path is recorded: a path that is not fully
    statically known is reported as dynamic rather than half-resolved.

<!-- mios-src:3b14c68eb246 from usr/lib/mios/agent-pipe/mios_surface.py:171-177 -->

### Module-level bound names introduced by an import statement....

Module-level bound names introduced by an import statement.

    ``import a.b as c`` -> ``c``; ``import a.b`` -> ``a`` (the top package binds);
    ``from m import x, y as z`` -> ``x``, ``z``. ``from m import *`` binds an
    unknowable set -> recorded as the sentinel ``"*"`` so its presence is tracked.

<!-- mios-src:56eb903cd2d2 from usr/lib/mios/agent-pipe/mios_surface.py:184-189 -->

### Project the public surface of the Python module at...

Project the public surface of the Python module at ``path``.

    Deterministic (all lists sorted) so a byte-stable golden can be committed and
    diffed. Returns:

      * ``routes``   -- sorted ``"METHOD path -> handler"`` for every ``@app`` route
                        AND every route declared on an ``APIRouter`` instance. A
                        router route's path is composed as ``<mount prefix><router
                        prefix><decorator path>`` -- FastAPI's mount order -- so a
                        route MOVED from ``@app.get("/a/b")`` onto a prefixed router
                        yields the IDENTICAL record and the migration is zero-diff.
      * ``provided`` -- sorted union of EVERY module-level bound name: top-level
                        ``def``/``async def``, ``class``, assigned global (incl.
                        tuple/annotated targets), and imported name. This is the
                        runtime importable surface; a move+reimport keeps a name in
                        it, a true deletion removes it.
      * ``counts``   -- size summary for quick human scanning

    CROSS-FILE NOTE: router-route composition HERE is resolved from the AST of the
    SINGLE file scanned. When a router and its ``app.include_router(...)`` mount live
    in the same file the full path is recovered. When the package layout splits them
    across files (the ``mios_pipe/`` shape) this single-file scan sees the router's
    own prefix but NOT a mount prefix applied in another file -- it does the best
    in-file resolution (router prefix + decorator path) rather than fabricate the
    missing segment. ``project_package`` lifts this limitation: it parses the
    mounting (entry) file together with the imported router modules and composes the
    cross-file mount prefix. This single-file projector is deliberately unchanged so
    the in-file gate stays byte-stable.

<!-- mios-src:6ce650d4a6a3 from usr/lib/mios/agent-pipe/mios_surface.py:201-229 -->

### Per-file structural facts ``project_package`` composes...

Per-file structural facts ``project_package`` composes across files.

    Collected from a single module's top level (the same scope ``project_surface``
    scans): the APIRouter assignments and their prefixes, the routes decorated on
    those routers, every ``include_router`` mount (split into ``app``-targeted and
    router-nested), and the import bindings that resolve an included router name to
    its defining sibling module.

<!-- mios-src:a03486d151d9 from usr/lib/mios/agent-pipe/mios_surface.py:297-304 -->

### Classify an ``include_router`` first argument into a...

Classify an ``include_router`` first argument into a resolvable reference.

    ``("name", id)`` for a bare ``r``; ``("attr", obj, attr)`` for ``mod.r``;
    ``("other",)`` for any other (dynamic) shape -- which resolves to nothing rather
    than to a fabricated target.

<!-- mios-src:fc5cebd4bdcd from usr/lib/mios/agent-pipe/mios_surface.py:314-319 -->

### Map a ``<obj>.include_router(<arg>, prefix=...)`` statement...

Map a ``<obj>.include_router(<arg>, prefix=...)`` statement to
    ``(obj name, include ref, mount prefix)``; ``None`` otherwise.

    Generalises ``_include_router_call`` (which recognises only the ``app`` object,
    keeping ``project_surface``'s in-file scope) to ANY mounting object, so a router
    nested onto another router (``parent.include_router(child, ...)``) is captured
    for whole-package composition. ``prefix`` defaults to the empty string when
    omitted and is ``_DYNAMIC`` when present but non-literal.

<!-- mios-src:9b5bcf213530 from usr/lib/mios/agent-pipe/mios_surface.py:328-336 -->

### The module-binding maps an import introduces...

The module-binding maps an import introduces: ``(from_imports, plain_imports)``.

    ``from <mod> import <name> [as <b>]`` -> ``from_imports[b] = (<mod>, <name>)``;
    ``import <mod> [as <b>]`` -> ``plain_imports[b] = <mod>`` (a bare ``import a.b``
    binds the top package ``a``). A ``*`` import binds an unknowable set and is
    skipped (no router can be resolved through it).

<!-- mios-src:3f541a65d758 from usr/lib/mios/agent-pipe/mios_surface.py:352-358 -->

### Resolve a dotted module to a sibling ``<final...

Resolve a dotted module to a sibling ``<final component>.py`` in ``search_dir``.

    The static, no-import resolution the refactor's flat ``mios_*.py`` layout uses:
    the module's terminal name IS the filename. ``None`` when no such file exists (an
    external / unresolved module -- never guessed).

<!-- mios-src:5b2b9b3b29e9 from usr/lib/mios/agent-pipe/mios_surface.py:420-425 -->

### Resolve an include reference to ``(defining file, router...

Resolve an include reference to ``(defining file, router var)`` or ``(None, None)``.

    A bare name is a router defined in THIS file or one imported from a sibling
    (``from <mod> import <r>``); an attribute ``<mod>.<r>`` resolves ``<mod>`` through
    the import bindings to a sibling file. Anything that does not resolve to a local
    sibling file yields ``(None, None)`` -- unresolved, never fabricated.

<!-- mios-src:abbc1a97563e from usr/lib/mios/agent-pipe/mios_surface.py:473-479 -->

### Project the public surface of a multi-file package rooted...

Project the public surface of a multi-file package rooted at ``entry_path``.

    Identical to ``project_surface`` for the entry module's in-file surface (``@app``
    routes, any in-file routers, and the entry's ``provided`` names), then ADDS the
    routes contributed by sibling router modules the entry mounts via
    ``app.include_router(<imported router>, prefix=...)`` -- composing the mount
    prefix (entry file) with the router prefix + ``@router`` decorator paths (sibling
    file) into the SAME record. ``provided`` stays the ENTRY module's bound-name
    surface (see the section comment for why it is not aggregated).

    On a layout with no cross-file includes (e.g. the current single-file
    ``server.py``) this returns EXACTLY what ``project_surface`` does. ``search_dir``
    overrides where sibling ``<module>.py`` files are looked up (default: the entry
    file's own directory).

<!-- mios-src:30d811ac91af from usr/lib/mios/agent-pipe/mios_surface.py:534-548 -->

### Human-readable diffs between a fresh projection and the...

Human-readable diffs between a fresh projection and the committed golden.

    REMOVED (in golden, gone now) is the dangerous case -- a route/symbol the
    surface promised disappeared. ADDED (new now, not in golden) is reported too:
    a deliberate surface growth should regenerate the golden, an accidental one is
    worth seeing. Compares ``routes`` and ``provided``.

<!-- mios-src:e6243060d128 from usr/lib/mios/agent-pipe/mios_surface.py:575-581 -->

### CLI

CLI: ``mios_surface <server.py>`` prints the projection JSON;
    ``mios_surface <server.py> --check <golden.json>`` diffs and exits non-zero on drift.

    ``--package`` switches to whole-package projection (``project_package``),
    optionally with ``--search-dir <dir>`` for the sibling module lookup. Without
    it, the single-file ``project_surface`` path is used -- so the drift-gate's
    ``<server.py> --check <golden.json>`` invocation behaves exactly as before.

<!-- mios-src:60fe525377c2 from usr/lib/mios/agent-pipe/mios_surface.py:594-601 -->
