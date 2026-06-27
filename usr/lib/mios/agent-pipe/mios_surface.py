# AI-hint: Pure stdlib (ast) extractor of the server.py PUBLIC SURFACE for the refactor parity gate (refactor WS R0). Projects the module's HTTP route table (every @app.<method>("path") -> handler, AND every route declared on an APIRouter instance -- composing the router's prefix and any app.include_router(...) mount prefix exactly as FastAPI concatenates them, so a route MOVED from @app onto a prefixed router yields the IDENTICAL record) plus PROVIDED -- the full set of module-level bound names (top-level def/async-def, class, assigned global, AND imported name), i.e. the runtime importable surface a `from server import X` / `server.X` consumer sees. project_surface resolves router composition WITHIN one file; project_package (refactor R13 Step 2a) widens that to a WHOLE PACKAGE -- it follows each app.include_router(<router imported from a sibling>, prefix=...) into the sibling <module>.py (resolved purely by AST import + filename convention, no import/exec) and composes the cross-file mount + router + decorator prefixes into the SAME record, so migrating a route off @app onto a sibling-module router stays zero-diff; provided stays the ENTRY module's surface (the `import server` consumer set). The strangler-fig refactor MOVES a definition out into a mios_*.py sibling and RE-IMPORTS it; because PROVIDED counts an imported name identically to a defined one, a behavior-preserving move+reimport is zero-diff while a TRULY dropped route/symbol reds the build. No import of server.py, no FastAPI, no DB -- parses the file as text via ast, so it runs offline in CI with no built image. Sibling of mios_manifest (same project_*/diff_* shape consumed by 38-drift-checks.sh).
# AI-related: ./server.py, ./mios_manifest.py, ./test_mios_surface.py, ../../../../automation/38-drift-checks.sh, ../../../share/mios/ai/v1/surface.generated.json
# AI-functions: project_surface, project_package, diff_surface, _route_from_decorator, _router_decorator_candidate, _router_prefix_assign, _include_router_call, _any_include_call, _include_ref, _import_bindings, _scan_module, _module_file, _scan_file, _resolve_router_ref, _collect_router_routes, _compose_path, _kw_str, _const_str, _imported_names, main
"""Static public-surface projection + diff for the agent-pipe server monolith.

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
gate in ``38-drift-checks.sh`` regenerates it from the live ``server.py`` and
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
"""

from __future__ import annotations

import ast
import json
import os
import sys
from typing import Any, NamedTuple

# FastAPI route-decorator verbs we recognise on the ``app`` object. ``api_route``
# and ``websocket`` are included so a future route form is captured too.
_ROUTE_METHODS = (
    "get", "post", "put", "delete", "patch", "head", "options",
    "websocket", "api_route", "trace",
)

# Sentinel recorded for a path (or path segment) that is not a string literal and
# so cannot be resolved statically. A composed path collapses to this whenever any
# of its segments is dynamic, matching how a single non-literal path is reported.
_DYNAMIC = "<dynamic>"


def _const_str(node: ast.AST) -> str:
    """Return a string constant's value, or ``"<dynamic>"`` for a non-literal path."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return _DYNAMIC


def _route_from_decorator(dec: ast.AST) -> tuple[str, str] | None:
    """Map an ``@app.<method>("/path", ...)`` decorator to ``(METHOD, path)``.

    Returns ``None`` for any decorator that is not an ``app``-object route call.
    """
    if not isinstance(dec, ast.Call):
        return None
    func = dec.func
    if not isinstance(func, ast.Attribute):
        return None
    obj = func.value
    if not isinstance(obj, ast.Name) or obj.id != "app":
        return None
    method = func.attr.lower()
    if method not in _ROUTE_METHODS:
        return None
    path = _const_str(dec.args[0]) if dec.args else _DYNAMIC
    return method.upper(), path


def _kw_str(call: ast.Call, name: str) -> str | None:
    """Constant-string value of keyword ``name`` on a call.

    ``None`` when the keyword is absent, ``_DYNAMIC`` when it is present but not a
    string literal, else the literal value (an empty string is a real value).
    """
    for kw in call.keywords:
        if kw.arg == name:
            return _const_str(kw.value)
    return None


def _router_prefix_assign(node: ast.AST) -> tuple[str, list[str]] | None:
    """Map ``<targets> = APIRouter(...)`` to ``(prefix, [bound names])``.

    The router constructor is recognised by its terminal callee name, so both a
    bare ``APIRouter(...)`` and an attribute ``<pkg>.APIRouter(...)`` form match --
    the same structural-API basis on which the ``app`` route object is recognised.
    ``prefix`` is the literal ``prefix=`` kwarg, the empty string when the kwarg is
    omitted (the constructor's own default), or ``_DYNAMIC`` when the kwarg is
    present but not a string literal. ``None`` for any other assignment.
    """
    if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
        return None
    callee = node.value.func
    if isinstance(callee, ast.Attribute):
        cname = callee.attr
    elif isinstance(callee, ast.Name):
        cname = callee.id
    else:
        return None
    if cname != "APIRouter":
        return None
    prefix = _kw_str(node.value, "prefix")
    if prefix is None:
        prefix = ""
    names = [t.id for t in node.targets if isinstance(t, ast.Name)]
    return (prefix, names) if names else None


def _include_router_call(node: ast.AST) -> tuple[str, str] | None:
    """Map an ``app.include_router(<router>, prefix=...)`` statement to
    ``(router name, mount prefix)``; ``None`` otherwise.

    Mounting a router prepends this prefix to every one of the router's paths.
    ``prefix`` is the literal kwarg, the empty string when omitted, or ``_DYNAMIC``
    when non-literal. Only ``app``-mounted routers are composed here (the in-file
    scope documented on ``project_surface``); a router mounted onto another router
    is not transitively chained.
    """
    call = node.value if isinstance(node, (ast.Expr, ast.Assign)) else None
    if not isinstance(call, ast.Call):
        return None
    func = call.func
    if not (isinstance(func, ast.Attribute) and func.attr == "include_router"):
        return None
    if not (isinstance(func.value, ast.Name) and func.value.id == "app"):
        return None
    if not call.args or not isinstance(call.args[0], ast.Name):
        return None
    prefix = _kw_str(call, "prefix")
    if prefix is None:
        prefix = ""
    return call.args[0].id, prefix


def _router_decorator_candidate(dec: ast.AST) -> tuple[str, str, str] | None:
    """Map a ``@<obj>.<method>("/path", ...)`` decorator on a NON-``app`` object to
    ``(obj name, METHOD, path)``; ``None`` otherwise.

    Structurally identical to ``_route_from_decorator`` but for an object other
    than ``app`` -- a candidate router variable. The caller keeps only candidates
    whose object was bound to an ``APIRouter`` instance; ``app`` is excluded here
    because ``_route_from_decorator`` already projects it, so it is never counted
    twice.
    """
    if not isinstance(dec, ast.Call):
        return None
    func = dec.func
    if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Name):
        return None
    obj = func.value.id
    if obj == "app":
        return None
    method = func.attr.lower()
    if method not in _ROUTE_METHODS:
        return None
    path = _const_str(dec.args[0]) if dec.args else _DYNAMIC
    return obj, method.upper(), path


def _compose_path(*segments: str) -> str:
    """Concatenate route path segments (mount prefix + router prefix + decorator
    path) exactly as FastAPI mounts a router -- plain left-to-right concatenation.

    If ANY segment is the ``_DYNAMIC`` sentinel the whole path is ``_DYNAMIC``,
    mirroring how a single non-literal path is recorded: a path that is not fully
    statically known is reported as dynamic rather than half-resolved.
    """
    if any(seg == _DYNAMIC for seg in segments):
        return _DYNAMIC
    return "".join(segments)


def _imported_names(node: ast.AST) -> list[str]:
    """Module-level bound names introduced by an import statement.

    ``import a.b as c`` -> ``c``; ``import a.b`` -> ``a`` (the top package binds);
    ``from m import x, y as z`` -> ``x``, ``z``. ``from m import *`` binds an
    unknowable set -> recorded as the sentinel ``"*"`` so its presence is tracked.
    """
    out: list[str] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            out.append(alias.asname or alias.name.split(".")[0])
    elif isinstance(node, ast.ImportFrom):
        for alias in node.names:
            out.append(alias.asname or (alias.name if alias.name != "*" else "*"))
    return out


def project_surface(path: str) -> dict[str, Any]:
    """Project the public surface of the Python module at ``path``.

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
    """
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    tree = ast.parse(src, filename=os.path.basename(path))

    routes: set[str] = set()
    provided: set[str] = set()
    routers: dict[str, str] = {}                     # router var -> its own prefix
    includes: dict[str, list[str]] = {}              # router var -> [mount prefixes]
    pending: list[tuple[str, str, str, str]] = []    # (obj, METHOD, dec path, handler)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            provided.add(node.name)
            for dec in node.decorator_list:
                r = _route_from_decorator(dec)
                if r:
                    routes.add(f"{r[0]} {r[1]} -> {node.name}")
                cand = _router_decorator_candidate(dec)
                if cand:
                    pending.append((cand[0], cand[1], cand[2], node.name))
        elif isinstance(node, ast.ClassDef):
            provided.add(node.name)
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    provided.add(tgt.id)
                elif isinstance(tgt, (ast.Tuple, ast.List)):
                    for elt in tgt.elts:
                        if isinstance(elt, ast.Name):
                            provided.add(elt.id)
            ra = _router_prefix_assign(node)
            if ra:
                for nm in ra[1]:
                    routers[nm] = ra[0]
            inc = _include_router_call(node)
            if inc:
                includes.setdefault(inc[0], []).append(inc[1])
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.value is not None:
                provided.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            provided.update(_imported_names(node))
        elif isinstance(node, ast.Expr):
            inc = _include_router_call(node)
            if inc:
                includes.setdefault(inc[0], []).append(inc[1])

    # Second pass: a router's mount prefix is usually applied AFTER its routes are
    # declared (and a decorator could even precede its router assignment in
    # pathological order), so router-route paths are composed only once every
    # APIRouter assignment and include_router mount in the file has been collected.
    # A candidate whose object was never bound to an APIRouter is not a route and is
    # dropped here -- which is also why an all-``@app`` module is projected unchanged.
    for obj, method, dec_path, handler in pending:
        if obj not in routers:
            continue
        mount_prefixes = includes.get(obj) or [""]
        for mount in mount_prefixes:
            composed = _compose_path(mount, routers[obj], dec_path)
            routes.add(f"{method} {composed} -> {handler}")

    return {
        "routes": sorted(routes),
        "provided": sorted(provided),
        "counts": {"routes": len(routes), "provided": len(provided)},
    }


# ---------------------------------------------------------------------------
# Whole-package projection (refactor R13 Step 2a)
#
# ``project_surface`` recovers a router + its mount only when both live in ONE
# file. Once routes migrate onto APIRouter instances in sibling ``mios_*.py``
# modules, the mount prefix (``app.include_router`` in the entry module) and the
# router's own prefix + ``@router`` routes live in DIFFERENT files.
# ``project_package`` follows each ``app.include_router(<name>, prefix=...)`` whose
# ``<name>`` is a router IMPORTED from a sibling, parses that sibling by the
# flat-layout filename convention (``<module final component>.py`` in the same
# directory, or an explicit ``search_dir``), and composes mount + router prefix +
# decorator path into the SAME ``"METHOD path -> handler"`` record -- so a route
# MOVED from ``@app`` onto a sibling-module router is zero-diff.
#
# ``provided`` STAYS the entry module's surface (it is NOT aggregated across the
# package): the gate's ``provided`` half protects ``from server import X`` /
# ``server.X`` consumers, which import from the ENTRY module only. A name that moved
# to a sibling WITHOUT being re-imported into the entry SHOULD red the gate (its
# importable surface really shrank); aggregating would mask that. ``routes`` ARE
# aggregated -- a mounted route is reachable regardless of which file defines its
# handler.
#
# Resolution is pure ``ast`` + the filename convention (no import/exec -> offline).
# An include that cannot be resolved to a local sibling file contributes NO route
# records: its handlers are unknown and are never fabricated -- the same silent
# drop ``project_surface`` applies to a decorator whose object was never an
# APIRouter. A resolvable router reached past the supported nesting depth, or
# mounted under a non-literal prefix, degrades to the ``_DYNAMIC`` path sentinel
# with the handler PRESERVED -- mirroring how a single non-literal path is recorded.

# One ``router -> subrouter`` nesting hop is composed exactly; a deeper chain
# degrades to the ``_DYNAMIC`` path sentinel (handler preserved). This is the
# structural support depth (like the recognised method set), not a tunable weight.
_MAX_NEST = 1


class _Scan(NamedTuple):
    """Per-file structural facts ``project_package`` composes across files.

    Collected from a single module's top level (the same scope ``project_surface``
    scans): the APIRouter assignments and their prefixes, the routes decorated on
    those routers, every ``include_router`` mount (split into ``app``-targeted and
    router-nested), and the import bindings that resolve an included router name to
    its defining sibling module.
    """
    routers: dict[str, str]                                          # router var -> own prefix
    router_routes: tuple[tuple[str, str, str, str], ...]            # (router var, METHOD, dec path, handler)
    app_includes: tuple[tuple[tuple[str, ...], str], ...]          # (include ref, mount prefix) via app.include_router
    nested_includes: tuple[tuple[str, tuple[str, ...], str], ...]  # (parent var, child ref, mount prefix)
    from_imports: dict[str, tuple[str, str]]                        # bound name -> (module dotted, original name)
    plain_imports: dict[str, str]                                   # bound name -> module dotted


def _include_ref(arg: ast.AST) -> tuple[str, ...]:
    """Classify an ``include_router`` first argument into a resolvable reference.

    ``("name", id)`` for a bare ``r``; ``("attr", obj, attr)`` for ``mod.r``;
    ``("other",)`` for any other (dynamic) shape -- which resolves to nothing rather
    than to a fabricated target.
    """
    if isinstance(arg, ast.Name):
        return ("name", arg.id)
    if isinstance(arg, ast.Attribute) and isinstance(arg.value, ast.Name):
        return ("attr", arg.value.id, arg.attr)
    return ("other",)


def _any_include_call(node: ast.AST) -> tuple[str, tuple[str, ...], str] | None:
    """Map a ``<obj>.include_router(<arg>, prefix=...)`` statement to
    ``(obj name, include ref, mount prefix)``; ``None`` otherwise.

    Generalises ``_include_router_call`` (which recognises only the ``app`` object,
    keeping ``project_surface``'s in-file scope) to ANY mounting object, so a router
    nested onto another router (``parent.include_router(child, ...)``) is captured
    for whole-package composition. ``prefix`` defaults to the empty string when
    omitted and is ``_DYNAMIC`` when present but non-literal.
    """
    call = node.value if isinstance(node, (ast.Expr, ast.Assign)) else None
    if not isinstance(call, ast.Call):
        return None
    func = call.func
    if not (isinstance(func, ast.Attribute) and func.attr == "include_router"):
        return None
    if not isinstance(func.value, ast.Name) or not call.args:
        return None
    prefix = _kw_str(call, "prefix")
    if prefix is None:
        prefix = ""
    return func.value.id, _include_ref(call.args[0]), prefix


def _import_bindings(node: ast.AST) -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    """The module-binding maps an import introduces: ``(from_imports, plain_imports)``.

    ``from <mod> import <name> [as <b>]`` -> ``from_imports[b] = (<mod>, <name>)``;
    ``import <mod> [as <b>]`` -> ``plain_imports[b] = <mod>`` (a bare ``import a.b``
    binds the top package ``a``). A ``*`` import binds an unknowable set and is
    skipped (no router can be resolved through it).
    """
    fr: dict[str, tuple[str, str]] = {}
    pl: dict[str, str] = {}
    if isinstance(node, ast.ImportFrom):
        mod = node.module or ""
        for a in node.names:
            if a.name == "*":
                continue
            fr[a.asname or a.name] = (mod, a.name)
    elif isinstance(node, ast.Import):
        for a in node.names:
            pl[a.asname or a.name.split(".")[0]] = a.name
    return fr, pl


def _scan_module(tree: ast.Module) -> _Scan:
    """Collect the per-file structural facts ``project_package`` composes across
    files. Top-level only -- mirrors ``project_surface``'s scope (nested defs are
    not part of the route/router surface)."""
    routers: dict[str, str] = {}
    router_routes: list[tuple[str, str, str, str]] = []
    app_includes: list[tuple[tuple[str, ...], str]] = []
    nested_includes: list[tuple[str, tuple[str, ...], str]] = []
    from_imports: dict[str, tuple[str, str]] = {}
    plain_imports: dict[str, str] = {}

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                cand = _router_decorator_candidate(dec)
                if cand:
                    router_routes.append((cand[0], cand[1], cand[2], node.name))
            continue
        if isinstance(node, ast.Assign):
            ra = _router_prefix_assign(node)
            if ra:
                for nm in ra[1]:
                    routers[nm] = ra[0]
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            fr, pl = _import_bindings(node)
            from_imports.update(fr)
            plain_imports.update(pl)
            continue
        inc = _any_include_call(node)
        if inc:
            obj, ref, mount = inc
            if obj == "app":
                app_includes.append((ref, mount))
            else:
                nested_includes.append((obj, ref, mount))

    return _Scan(
        routers=routers,
        router_routes=tuple(router_routes),
        app_includes=tuple(app_includes),
        nested_includes=tuple(nested_includes),
        from_imports=from_imports,
        plain_imports=plain_imports,
    )


def _module_file(module: str, search_dir: str) -> str | None:
    """Resolve a dotted module to a sibling ``<final component>.py`` in ``search_dir``.

    The static, no-import resolution the refactor's flat ``mios_*.py`` layout uses:
    the module's terminal name IS the filename. ``None`` when no such file exists (an
    external / unresolved module -- never guessed).
    """
    if not module:
        return None
    cand = os.path.join(search_dir, module.split(".")[-1] + ".py")
    return cand if os.path.isfile(cand) else None


def _scan_file(path: str, cache: dict[str, "_Scan | None"]) -> "_Scan | None":
    """Parse + scan a file once, memoised by path. ``None`` when it is unreadable or
    unparsable -- a missing or broken sibling degrades to no routes, never raises."""
    if path in cache:
        return cache[path]
    scan: _Scan | None
    try:
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=os.path.basename(path))
        scan = _scan_module(tree)
    except (OSError, SyntaxError, ValueError):
        scan = None
    cache[path] = scan
    return scan


def _resolve_router_ref(ref: tuple[str, ...], scan: _Scan, this_file: str,
                        search_dir: str) -> tuple[str | None, str | None]:
    """Resolve an include reference to ``(defining file, router var)`` or ``(None, None)``.

    A bare name is a router defined in THIS file or one imported from a sibling
    (``from <mod> import <r>``); an attribute ``<mod>.<r>`` resolves ``<mod>`` through
    the import bindings to a sibling file. Anything that does not resolve to a local
    sibling file yields ``(None, None)`` -- unresolved, never fabricated.
    """
    if ref[0] == "name":
        nm = ref[1]
        if nm in scan.routers:
            return this_file, nm
        if nm in scan.from_imports:
            mod, orig = scan.from_imports[nm]
            f = _module_file(mod, search_dir) or _module_file(orig, search_dir)
            if f:
                return f, orig
        return None, None
    if ref[0] == "attr":
        obj, attr = ref[1], ref[2]
        mod = scan.plain_imports.get(obj)
        if mod is None and obj in scan.from_imports:
            mod = scan.from_imports[obj][1]
        f = _module_file(mod or obj, search_dir)
        if f:
            return f, attr
        return None, None
    return None, None


def _collect_router_routes(file: str, var: str, prefix: str, budget: int,
                           visited: frozenset[tuple[str, str]], search_dir: str,
                           cache: dict[str, "_Scan | None"]) -> list[tuple[str, str, str]]:
    """Compose every route reachable through router ``var`` in ``file`` under the
    accumulated ``prefix``, following one in-budget nesting hop. Cycle- and
    depth-guarded (a revisit or an over-budget hop stops / collapses to ``_DYNAMIC``
    rather than recursing forever). Returns ``(METHOD, composed path, handler)``.
    """
    key = (file, var)
    if key in visited:
        return []                                   # cycle -> terminate, no fabrication
    scan = _scan_file(file, cache)
    if scan is None or var not in scan.routers:
        return []                                   # unresolved router -> no routes
    visited = visited | {key}
    here = _compose_path(prefix, scan.routers[var])
    out = [(m, _compose_path(here, dec), h)
           for (rv, m, dec, h) in scan.router_routes if rv == var]
    for parent, child_ref, mount in scan.nested_includes:
        if parent != var:
            continue
        cf, cv = _resolve_router_ref(child_ref, scan, file, search_dir)
        if cf is None or cv is None:
            continue                                # unresolved child -> no routes
        nb = budget - 1
        child_prefix = _compose_path(here, mount) if nb >= 0 else _DYNAMIC
        out.extend(_collect_router_routes(cf, cv, child_prefix, max(nb, 0),
                                          visited, search_dir, cache))
    return out


def project_package(entry_path: str, *, search_dir: str | None = None) -> dict[str, Any]:
    """Project the public surface of a multi-file package rooted at ``entry_path``.

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
    """
    base = project_surface(entry_path)
    routes: set[str] = set(base["routes"])
    search_dir = search_dir or os.path.dirname(os.path.abspath(entry_path)) or "."
    cache: dict[str, _Scan | None] = {}
    entry_abs = os.path.abspath(entry_path)
    entry_scan = _scan_file(entry_abs, cache)
    if entry_scan is not None:
        for ref, mount in entry_scan.app_includes:
            if ref[0] == "name" and ref[1] in entry_scan.routers:
                continue                            # local router -> already composed in-file
            f, var = _resolve_router_ref(ref, entry_scan, entry_abs, search_dir)
            if f is None or var is None:
                continue                            # external / unresolved -> no fabrication
            for method, path, handler in _collect_router_routes(
                    f, var, mount, _MAX_NEST, frozenset(), search_dir, cache):
                routes.add(f"{method} {path} -> {handler}")

    out_routes = sorted(routes)
    return {
        "routes": out_routes,
        "provided": base["provided"],
        "counts": {"routes": len(out_routes), "provided": len(base["provided"])},
    }


def diff_surface(generated: dict[str, Any], committed: dict[str, Any]) -> list[str]:
    """Human-readable diffs between a fresh projection and the committed golden.

    REMOVED (in golden, gone now) is the dangerous case -- a route/symbol the
    surface promised disappeared. ADDED (new now, not in golden) is reported too:
    a deliberate surface growth should regenerate the golden, an accidental one is
    worth seeing. Compares ``routes`` and ``provided``.
    """
    diffs: list[str] = []
    for key in ("routes", "provided"):
        gen = set(generated.get(key, []))
        com = set(committed.get(key, []))
        for removed in sorted(com - gen):
            diffs.append(f"{key}: REMOVED {removed!r} (in golden, gone from server.py)")
        for added in sorted(gen - com):
            diffs.append(f"{key}: ADDED {added!r} (in server.py, not in golden -- regenerate golden if intended)")
    return diffs


def main(argv: list[str]) -> int:
    """CLI: ``mios_surface <server.py>`` prints the projection JSON;
    ``mios_surface <server.py> --check <golden.json>`` diffs and exits non-zero on drift.

    ``--package`` switches to whole-package projection (``project_package``),
    optionally with ``--search-dir <dir>`` for the sibling module lookup. Without
    it, the single-file ``project_surface`` path is used -- so the drift-gate's
    ``<server.py> --check <golden.json>`` invocation behaves exactly as before.
    """
    target: str | None = None
    check: str | None = None
    package = False
    search_dir: str | None = None
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--check":
            i += 1
            check = argv[i] if i < len(argv) else None
        elif a == "--search-dir":
            i += 1
            search_dir = argv[i] if i < len(argv) else None
        elif a == "--package":
            package = True
        elif not a.startswith("--") and target is None:
            target = a
        i += 1
    if target is None:
        sys.stderr.write(
            "usage: mios_surface <server.py> [--check <golden.json>] "
            "[--package [--search-dir <dir>]]\n")
        return 2
    proj = project_package(target, search_dir=search_dir) if package else project_surface(target)
    if check is not None:
        with open(check, encoding="utf-8") as fh:
            committed = json.load(fh)
        diffs = diff_surface(proj, committed)
        for d in diffs:
            sys.stderr.write("    " + d + "\n")
        return 1 if diffs else 0
    json.dump(proj, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
