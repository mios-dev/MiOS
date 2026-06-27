#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_surface (refactor WS R0 parity gate + R13 Step 2a whole-package projection). Pure stdlib, no server.py/DB/pytest/FastAPI. Builds a tiny temp module (two @app routes + middleware + funcs + class + globals + imports), asserts project_surface extracts the route table (METHOD path -> handler), folds EVERY module-level bound name (def/class/global/imported) into `provided`, and excludes nested defs + non-route decorators; then asserts the central refactor invariant: MOVING a def out and RE-IMPORTING it under the same name is ZERO-diff, while truly deleting a route/name reds via diff_surface. Also asserts routes declared on an APIRouter instance are projected with the router prefix + any app.include_router mount prefix composed (so an @app route moved onto a prefixed router is zero-diff), that the router method set equals the @app method set, and that a non-literal prefix collapses the path to the <dynamic> sentinel. The package-projection cases build a SYNTHETIC multi-file fixture in an ephemeral temp dir (cleaned up) and assert project_package resolves a cross-file app.include_router into a sibling module, composes one router->subrouter nesting level, degrades an unresolved include (no fabrication) and a dynamic mount prefix (to <dynamic>) deterministically, that a route moved @app->sibling-router is zero-diff, and that on the current single-file server.py project_package == project_surface byte-for-byte. Locks the surface projector that protects every later server.py extraction.
# AI-related: ./mios_surface.py, ./server.py
# AI-functions: check, _project, _project_package, t_routes, t_provided, t_move_reimport_zero_diff, t_real_drop, t_router_routes, t_router_method_set_matches_app, t_app_to_router_zero_diff, t_router_dynamic_prefix, t_package_cross_file_include, t_package_app_to_sibling_zero_diff, t_package_one_level_nesting, t_package_unresolved_degrades, t_package_dynamic_mount_degrades, t_package_superset_of_surface_on_current_tree, main
"""Unit tests for mios_surface (refactor R0 surface-parity gate)."""

import os
import shutil
import sys
import tempfile

import mios_surface as s

_fails = 0

_BEFORE = '''\
import os
import a.b.c as abc
from helpers import scrub, translate as _xlate
A_CONST = 1
B_CONST, C_CONST = 2, 3
TYPED: int = 4


@app.get("/health")
def health():
    return "ok"


@app.post("/v1/chat/completions")
async def chat_completions(req):
    return req


@app.middleware("http")
async def _mw(request, call_next):
    return await call_next(request)


def scrub(x):  # defined locally here, BEFORE the move
    return x


class Widget:
    def method(self):  # nested def must NOT appear as a top-level name
        return 1
'''

# Same module after a behavior-preserving extraction: ``scrub`` is MOVED into a
# sibling and RE-IMPORTED under the same name. The importable surface is identical.
_AFTER_MOVE = _BEFORE.replace(
    "from helpers import scrub, translate as _xlate",
    "from helpers import translate as _xlate\nfrom mios_scrub import scrub",
).replace(
    "def scrub(x):  # defined locally here, BEFORE the move\n    return x\n\n\n", "",
)


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _project(src):
    fd, path = tempfile.mkstemp(suffix=".py")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(src)
        return s.project_surface(path)
    finally:
        os.unlink(path)


def _project_package(files, entry):
    """Write a synthetic multi-file package to a fresh temp dir, project the whole
    package from ``entry``, then remove the dir. ``files`` maps filename -> source.
    Uses an ephemeral ``tempfile`` dir (no fixed path baked in) and cleans up."""
    d = tempfile.mkdtemp()
    try:
        for name, src in files.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                fh.write(src)
        return s.project_package(os.path.join(d, entry))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t_routes():
    proj = _project(_BEFORE)
    routes = set(proj["routes"])
    check("route: GET /health -> health", "GET /health -> health" in routes)
    check("route: POST chat_completions", "POST /v1/chat/completions -> chat_completions" in routes)
    check("route: middleware is NOT a route", not any("_mw" in r for r in routes), routes)
    check("route: exactly 2 routes", proj["counts"]["routes"] == 2, str(proj["counts"]))
    check("route: sorted", proj["routes"] == sorted(proj["routes"]))


def t_provided():
    prov = set(_project(_BEFORE)["provided"])
    # defs (incl route handlers) + class + globals + imported names all present
    check("provided: top-level funcs", {"health", "chat_completions", "_mw", "scrub"} <= prov)
    check("provided: nested method excluded", "method" not in prov)
    check("provided: class", "Widget" in prov)
    check("provided: globals simple+tuple+annotated", {"A_CONST", "B_CONST", "C_CONST", "TYPED"} <= prov)
    check("provided: import asname (a.b.c as abc)", "abc" in prov)
    check("provided: plain import binds top pkg (os)", "os" in prov)
    check("provided: from-import names", {"scrub", "_xlate"} <= prov)


def t_move_reimport_zero_diff():
    before = _project(_BEFORE)
    after = _project(_AFTER_MOVE)
    # scrub left the local `def` but re-enters via `from mios_scrub import scrub`
    check("move: scrub still defined-locally before", "scrub" in set(before["provided"]))
    check("move: scrub still provided after (via import)", "scrub" in set(after["provided"]))
    diffs = s.diff_surface(after, before)
    check("move+reimport is ZERO-diff", diffs == [], " | ".join(diffs))


def t_real_drop():
    before = _project(_BEFORE)
    # golden has an extra route + name the current projection lacks -> both REMOVED
    golden = {
        "routes": before["routes"] + ["DELETE /v1/old -> old_handler"],
        "provided": before["provided"] + ["removed_symbol"],
    }
    diffs = s.diff_surface(before, golden)
    blob = " | ".join(diffs)
    check("drop: REMOVED route flagged", "REMOVED 'DELETE /v1/old -> old_handler'" in blob, blob)
    check("drop: REMOVED symbol flagged", "REMOVED 'removed_symbol'" in blob, blob)
    check("identical == clean", s.diff_surface(before, before) == [])


# A synthetic module exercising APIRouter projection. Three routers: ``r`` is
# mounted under ``prefix="/api"`` (full composition), ``empty`` has an empty router
# prefix and a no-prefix mount, ``orphan`` is never mounted in-file (best in-file
# resolution = router prefix only). A plain ``@app`` route in the SAME module must
# still project identically. Synthetic paths/handlers -- no real route copied.
_ROUTER_FIXTURE = '''\
from fastapi import APIRouter

r = APIRouter(prefix="/v1/x")
empty = APIRouter(prefix="")
orphan = APIRouter(prefix="/orphan")


@r.get("/y")
def handler_y():
    return 1


@r.post("/z")
async def handler_z(req):
    return req


@empty.get("/e")
def handler_e():
    return 2


@orphan.get("/o")
def handler_o():
    return 3


@app.get("/plain")
def plain_handler():
    return 4


app.include_router(r, prefix="/api")
app.include_router(empty)
'''


def t_router_routes():
    routes = set(_project(_ROUTER_FIXTURE)["routes"])
    # mount prefix + router prefix + decorator path, in FastAPI's concat order
    check("router: composed GET /api/v1/x/y", "GET /api/v1/x/y -> handler_y" in routes, routes)
    check("router: composed POST (async handler)", "POST /api/v1/x/z -> handler_z" in routes, routes)
    # empty router prefix + no-prefix mount -> just the decorator path
    check("router: empty prefixes -> /e", "GET /e -> handler_e" in routes, routes)
    # never mounted in-file: best in-file resolution = router prefix only, no mount
    check("router: un-mounted uses router prefix only", "GET /orphan/o -> handler_o" in routes, routes)
    # a plain @app route in the same module still projects exactly as before
    check("router: @app route unchanged alongside routers", "GET /plain -> plain_handler" in routes, routes)
    # composition order is mount<router<path, never reordered
    check("router: no mis-ordered path", not any("/v1/x/api" in rt for rt in routes), routes)


def t_router_method_set_matches_app():
    # Build, for EVERY route method the projector recognises, one @app route and one
    # @router route; assert the router yields the SAME method set as @app (read from
    # the module, not a restated literal list).
    methods = list(s._ROUTE_METHODS)
    lines = ["r = APIRouter()"]
    for i, m in enumerate(methods):
        lines += [f'@app.{m}("/a{i}")', f"def a{i}(): pass",
                  f'@r.{m}("/b{i}")', f"def b{i}(): pass"]
    lines.append("app.include_router(r)")
    routes = set(_project("\n".join(lines) + "\n")["routes"])
    app_methods = {rt.split(" ", 1)[0] for rt in routes if " -> a" in rt}
    router_methods = {rt.split(" ", 1)[0] for rt in routes if " -> b" in rt}
    check("router method set == app method set", app_methods == router_methods,
          f"app={sorted(app_methods)} router={sorted(router_methods)}")
    check("router covers the full recognised method set", len(router_methods) == len(methods),
          f"{len(router_methods)} of {len(methods)}")


def t_app_to_router_zero_diff():
    # The central migration property: a route MOVED from @app onto a prefixed router
    # mounted to reconstruct the same absolute path yields the IDENTICAL route record.
    as_app = _project('@app.get("/api/v1/x/y")\ndef h():\n    return 1\n')
    as_router = _project(
        'r = APIRouter(prefix="/v1/x")\n'
        '@r.get("/y")\n'
        'def h():\n    return 1\n'
        'app.include_router(r, prefix="/api")\n'
    )
    rec = "GET /api/v1/x/y -> h"
    check("zero-diff: @app form yields the record", rec in set(as_app["routes"]), as_app["routes"])
    check("zero-diff: router form yields the SAME record", rec in set(as_router["routes"]), as_router["routes"])
    check("zero-diff: route surface identical across the move",
          set(as_app["routes"]) == set(as_router["routes"]),
          f"{as_app['routes']} vs {as_router['routes']}")


def t_router_dynamic_prefix():
    # A non-literal prefix cannot be resolved statically -> the whole path collapses
    # to the <dynamic> sentinel, exactly as a non-literal single path already does.
    routes = set(_project(
        'PFX = make_prefix()\n'
        'r = APIRouter(prefix=PFX)\n'
        '@r.get("/y")\n'
        'def h():\n    return 1\n'
        'app.include_router(r)\n'
    )["routes"])
    check("dynamic prefix collapses path to <dynamic>", "GET <dynamic> -> h" in routes, routes)


# --- Whole-package projection (refactor R13 Step 2a) --------------------------
# A router declared in a SIBLING module (B) and mounted by the ENTRY module (A)
# via app.include_router. The single-file scan of A cannot see B's prefix/routes;
# project_package follows the import (resolved by filename convention) and composes
# mount + router + decorator prefixes across the two files. Synthetic only.
_PKG_MOD_X = '''\
from fastapi import APIRouter

router_x = APIRouter(prefix="/v1/x")


@router_x.get("/y")
def handler_y():
    return 1


@router_x.post("/z")
async def handler_z(req):
    return req
'''


def t_package_cross_file_include():
    files = {
        "mios_routes_x.py": _PKG_MOD_X,
        "entry.py": (
            "from fastapi import FastAPI\n"
            "from mios_routes_x import router_x\n"
            "app = FastAPI()\n"
            '@app.get("/plain")\n'
            "def plain_handler():\n    return 0\n"
            'app.include_router(router_x, prefix="/api")\n'
        ),
    }
    proj = _project_package(files, "entry.py")
    routes = set(proj["routes"])
    # mount(/api) + router(/v1/x) + decorator(/y), in FastAPI concat order
    check("package: cross-file GET composed /api/v1/x/y",
          "GET /api/v1/x/y -> handler_y" in routes, routes)
    check("package: cross-file POST (async) composed",
          "POST /api/v1/x/z -> handler_z" in routes, routes)
    # the entry's own @app route still projects exactly as single-file
    check("package: entry @app route preserved",
          "GET /plain -> plain_handler" in routes, routes)
    # provided is the ENTRY module's surface only -- sibling handlers are NOT in it
    prov = set(proj["provided"])
    check("package: provided is entry-only (sibling handler absent)",
          "handler_y" not in prov and "router_x" in prov, sorted(prov))


def t_package_app_to_sibling_zero_diff():
    # The cross-file migration property: an @app route moved onto a sibling router
    # mounted to reconstruct the same absolute path yields the IDENTICAL record AND
    # an identical route surface (entry has no other route here).
    as_app = _project('@app.get("/api/v1/x/y")\ndef h():\n    return 1\n')
    as_pkg = _project_package(
        {
            "modx.py": (
                "from fastapi import APIRouter\n"
                'h_router = APIRouter(prefix="/v1/x")\n'
                '@h_router.get("/y")\n'
                "def h():\n    return 1\n"
            ),
            "entry.py": (
                "from fastapi import FastAPI\n"
                "from modx import h_router\n"
                "app = FastAPI()\n"
                'app.include_router(h_router, prefix="/api")\n'
            ),
        },
        "entry.py",
    )
    rec = "GET /api/v1/x/y -> h"
    check("package zero-diff: @app form yields the record", rec in set(as_app["routes"]))
    check("package zero-diff: sibling-router form yields the SAME record",
          rec in set(as_pkg["routes"]), as_pkg["routes"])
    check("package zero-diff: route surface identical across the cross-file move",
          set(as_app["routes"]) == set(as_pkg["routes"]),
          f"{as_app['routes']} vs {as_pkg['routes']}")


def t_package_one_level_nesting():
    # parent.include_router(child) composes one level: app mount + parent prefix +
    # nested mount + child prefix + decorator path.
    files = {
        "mios_nest.py": (
            "from fastapi import APIRouter\n"
            'child = APIRouter(prefix="/c")\n'
            '@child.get("/leaf")\n'
            "def leaf_handler():\n    return 1\n"
            'parent = APIRouter(prefix="/p")\n'
            'parent.include_router(child, prefix="/sub")\n'
            '@parent.get("/direct")\n'
            "def direct_handler():\n    return 2\n"
        ),
        "entry.py": (
            "from fastapi import FastAPI\n"
            "from mios_nest import parent\n"
            "app = FastAPI()\n"
            'app.include_router(parent, prefix="/api")\n'
        ),
    }
    routes = set(_project_package(files, "entry.py")["routes"])
    check("package nesting: parent direct route composed /api/p/direct",
          "GET /api/p/direct -> direct_handler" in routes, routes)
    check("package nesting: child composed /api/p/sub/c/leaf",
          "GET /api/p/sub/c/leaf -> leaf_handler" in routes, routes)


def t_package_unresolved_degrades():
    # An include whose router resolves to NO local file contributes nothing (its
    # handlers are unknown and never fabricated); resolvable includes alongside it
    # still project; the result is deterministic.
    files = {
        "mios_routes_x.py": _PKG_MOD_X,
        "entry.py": (
            "from fastapi import FastAPI\n"
            "from mios_routes_x import router_x\n"
            "from mios_missing import ghost_router\n"
            "app = FastAPI()\n"
            'app.include_router(router_x, prefix="/api")\n'
            'app.include_router(ghost_router, prefix="/nope")\n'
        ),
    }
    proj = _project_package(files, "entry.py")
    routes = set(proj["routes"])
    check("package unresolved: resolvable router still composed",
          "GET /api/v1/x/y -> handler_y" in routes, routes)
    check("package unresolved: nothing fabricated for the missing module",
          not any("nope" in r or "ghost" in r for r in routes), routes)
    check("package unresolved: deterministic across repeated calls",
          _project_package(files, "entry.py") == proj)


def t_package_dynamic_mount_degrades():
    # A non-literal mount prefix cannot be resolved statically -> the composed path
    # collapses to <dynamic> (mirroring the single-file convention) while the handler
    # is preserved -- never dropped, never guessed.
    files = {
        "mios_routes_x.py": _PKG_MOD_X,
        "entry.py": (
            "from fastapi import FastAPI\n"
            "from mios_routes_x import router_x\n"
            "app = FastAPI()\n"
            "PFX = make_prefix()\n"
            "app.include_router(router_x, prefix=PFX)\n"
        ),
    }
    routes = set(_project_package(files, "entry.py")["routes"])
    check("package dynamic mount: path collapses, handler preserved",
          "GET <dynamic> -> handler_y" in routes, routes)


def t_package_superset_of_surface_on_current_tree():
    # The projector's contract on the REAL tree: project_package is a strict SUPERSET
    # of project_surface -- identical `provided` (entry-only; never aggregated across
    # the package) and a routes set that CONTAINS every single-file @app route PLUS any
    # route migrated cross-file onto a sibling-module APIRouter that server.py mounts
    # via app.include_router (R13 moved the /a2a routes that way). Before any route
    # moved cross-file the two were byte-identical; once one does, package recovers the
    # moved route where surface (single-file) cannot -- and `provided` never diverges.
    server = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
    if not os.path.isfile(server):
        check("package>=surface (server.py absent -> skipped)", True)
        return
    surf = s.project_surface(server)
    pkg = s.project_package(server)
    surf_routes, pkg_routes = set(surf["routes"]), set(pkg["routes"])
    check("package routes are a superset of surface routes", surf_routes <= pkg_routes,
          f"surface routes package lacks: {sorted(surf_routes - pkg_routes)}")
    check("package routes count >= surface routes count",
          pkg["counts"]["routes"] >= surf["counts"]["routes"],
          f"{pkg['counts']} vs {surf['counts']}")
    check("package preserves the provided surface (entry-only, not aggregated)",
          pkg["provided"] == surf["provided"],
          f"pkg-only={sorted(set(pkg['provided']) - set(surf['provided']))} "
          f"surf-only={sorted(set(surf['provided']) - set(pkg['provided']))}")
    check("package preserves the provided count",
          pkg["counts"]["provided"] == surf["counts"]["provided"], str(pkg["counts"]))


def main():
    t_routes()
    t_provided()
    t_move_reimport_zero_diff()
    t_real_drop()
    t_router_routes()
    t_router_method_set_matches_app()
    t_app_to_router_zero_diff()
    t_router_dynamic_prefix()
    t_package_cross_file_include()
    t_package_app_to_sibling_zero_diff()
    t_package_one_level_nesting()
    t_package_unresolved_degrades()
    t_package_dynamic_mount_degrades()
    t_package_superset_of_surface_on_current_tree()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
