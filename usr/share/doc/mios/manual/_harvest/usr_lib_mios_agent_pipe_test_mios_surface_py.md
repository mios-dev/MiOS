<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_surface (refactor WS R0 parity gate + R13 Step 2a whole-package projection). Pure stdlib, no server.py/DB/pytest/FastAPI. Builds a tiny temp module (two @app routes + middleware + funcs + class + globals + imports), asserts project_surface extracts the route table (METHOD path -> handler), folds EVERY module-level bound name (def/class/global/imported) into `provided`, and excludes nested defs + non-route decorators; then asserts the central refactor invariant: MOVING a def out and RE-IMPORTING it under the same name is ZERO-diff, while truly deleting a route/name reds via diff_surface. Also asserts routes declared on an APIRouter instance are projected with the router prefix + any app.include_router mount prefix composed (so an @app route moved onto a prefixed router is zero-diff), that the router method set equals the @app method set, and that a non-literal prefix collapses the path to the <dynamic> sentinel. The package-projection cases build a SYNTHETIC multi-file fixture in an ephemeral temp dir (cleaned up) and assert project_package resolves a cross-file app.include_router into a sibling module, composes one router->subrouter nesting level, degrades an unresolved include (no fabrication) and a dynamic mount prefix (to <dynamic>) deterministically, that a route moved @app->sibling-router is zero-diff, and that on the current single-file server.py project_package == project_surface byte-for-byte. Locks the surface projector that protects every later server.py extraction.
AI-related: ./mios_surface.py, ./server.py
AI-functions: check, _project, _project_package, t_routes, t_provided, t_move_reimport_zero_diff, t_real_drop, t_router_routes, t_router_method_set_matches_app, t_app_to_router_zero_diff, t_router_dynamic_prefix, t_package_cross_file_include, t_package_app_to_sibling_zero_diff, t_package_one_level_nesting, t_package_unresolved_degrades, t_package_dynamic_mount_degrades, t_package_superset_of_surface_on_current_tree, main

<!-- mios-src:35d4bfb180e4 from usr/lib/mios/agent-pipe/test_mios_surface.py:1-4 -->

