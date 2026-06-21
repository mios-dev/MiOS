#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_manifest (WS-A1 verb-catalog -> ai/v1 manifest projection; drift-check 8 depends on it). Pure stdlib, no server.py/DB/pytest. Verifies load_verbs_from_toml section-gating (skips sectionless configurator buttons) from a temp .toml, project_verb_catalog deterministic shape/ordering (sorted-by-name, fixed field subset, registry_kind="verb-catalog", conflict_group/parallel_limit conditional projection, hidden flag), and diff_manifest ([] on identical, +add/-remove/~changed incl. conflict_group/parallel_limit drift + registry_kind guard).
# AI-related: ./mios_manifest.py
# AI-functions: check, main
"""Unit tests for mios_manifest (WS-A1 verb-catalog manifest projection)."""

import copy
import os
import sys
import tempfile

import mios_manifest as mm

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _write_toml(text):
    fd, path = tempfile.mkstemp(suffix=".toml", prefix="mios_manifest_test_")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


# A small in-test catalog covering: real verbs (with section), a configurator
# button (no section -> must be skipped), hidden verbs, conflict_group +
# parallel_limit metadata, and out-of-order names (to prove sorting).
SAMPLE_TOML = """\
[verbs.zeta_verb]
section = "Misc"
model_name = "Zeta"
sig = "zeta(x)"
desc = "the last verb alphabetically"
tier = "rare"
permission = "write"

[verbs.alpha_verb]
section = "Apps"
model_name = "Alpha"
sig = "alpha()"
desc = "first verb alphabetically"

[verbs.hidden_verb]
section = "System"
model_name = "Hidden"
hidden = true

[verbs.serialized_verb]
section = "OS"
model_name = "Serial"
conflict_group = "os-control"
parallel_limit = 3

[verbs.configurator_button]
model_name = "NotAVerb"
desc = "a UI button with no section -- must be skipped"
"""


def t_load_section_gating():
    path = _write_toml(SAMPLE_TOML)
    try:
        verbs = mm.load_verbs_from_toml(path)
    finally:
        os.unlink(path)
    check("load: returns a dict", isinstance(verbs, dict))
    check("load: includes sectioned verbs",
          set(verbs) == {"zeta_verb", "alpha_verb", "hidden_verb", "serialized_verb"},
          sorted(verbs))
    check("load: SKIPS sectionless configurator button",
          "configurator_button" not in verbs)
    check("load: preserves spec fields", verbs.get("serialized_verb", {}).get("parallel_limit") == 3)


def t_load_empty_and_no_verbs():
    # No [verbs] table at all -> empty dict, not error.
    p1 = _write_toml("[other]\nfoo = 1\n")
    # [verbs] present but every entry lacks a section.
    p2 = _write_toml("[verbs.btn1]\nlabel = \"x\"\n\n[verbs.btn2]\nlabel = \"y\"\n")
    try:
        check("load: missing [verbs] -> {}", mm.load_verbs_from_toml(p1) == {})
        check("load: all-sectionless -> {}", mm.load_verbs_from_toml(p2) == {})
    finally:
        os.unlink(p1)
        os.unlink(p2)


def t_project_shape():
    path = _write_toml(SAMPLE_TOML)
    try:
        verbs = mm.load_verbs_from_toml(path)
    finally:
        os.unlink(path)
    man = mm.project_verb_catalog(verbs)
    check("project: object header", man.get("object") == "mios.verb.catalog")
    check("project: default version v1", man.get("version") == "v1")
    check("project: registry_kind verb-catalog (NOT hermes-build-tools)",
          man.get("registry_kind") == "verb-catalog")
    check("project: generated flag true", man.get("generated") is True)
    check("project: source points at mios.toml [verbs.*]",
          man.get("source") == "/usr/share/mios/mios.toml#[verbs.*]")
    check("project: count == len(data)", man.get("count") == len(man.get("data", [])))
    check("project: count == 4 sectioned verbs", man.get("count") == 4)
    # version override is honored.
    man_v2 = mm.project_verb_catalog(verbs, version="v2")
    check("project: version override", man_v2.get("version") == "v2")


def t_project_ordering_determinism():
    path = _write_toml(SAMPLE_TOML)
    try:
        verbs = mm.load_verbs_from_toml(path)
    finally:
        os.unlink(path)
    man = mm.project_verb_catalog(verbs)
    names = [e["name"] for e in man["data"]]
    check("project: data sorted by name",
          names == ["alpha_verb", "hidden_verb", "serialized_verb", "zeta_verb"], names)
    # Determinism: projecting twice yields byte-identical JSON.
    import json
    a = json.dumps(mm.project_verb_catalog(verbs), sort_keys=False)
    b = json.dumps(mm.project_verb_catalog(verbs), sort_keys=False)
    check("project: re-run byte-identical", a == b)
    # Determinism is independent of input dict insertion order (dicts preserve
    # insertion order in py3.7+, so reversing input must not reorder output).
    rev = {k: verbs[k] for k in reversed(list(verbs))}
    check("project: order-independent of input dict order",
          [e["name"] for e in mm.project_verb_catalog(rev)["data"]] == names)


def t_project_field_defaults_and_flags():
    path = _write_toml(SAMPLE_TOML)
    try:
        verbs = mm.load_verbs_from_toml(path)
    finally:
        os.unlink(path)
    man = mm.project_verb_catalog(verbs)
    by = {e["name"]: e for e in man["data"]}

    # alpha_verb has only minimal fields -> defaults applied.
    a = by["alpha_verb"]
    check("project: default tier=common", a["tier"] == "common")
    check("project: default permission=read", a["permission"] == "read")
    check("project: hidden defaults False", a["hidden"] is False)
    check("project: description from desc key", a["description"] == "first verb alphabetically")
    check("project: minimal verb omits conflict_group", "conflict_group" not in a)
    check("project: minimal verb omits parallel_limit", "parallel_limit" not in a)

    # zeta_verb overrides tier/permission.
    z = by["zeta_verb"]
    check("project: tier override", z["tier"] == "rare")
    check("project: permission override", z["permission"] == "write")

    # hidden_verb -> hidden True, and still projected (dispatchable).
    h = by["hidden_verb"]
    check("project: hidden verb still projected", h is not None)
    check("project: hidden flag True", h["hidden"] is True)

    # serialized_verb -> conflict_group + parallel_limit projected.
    s = by["serialized_verb"]
    check("project: conflict_group projected", s.get("conflict_group") == "os-control")
    check("project: parallel_limit projected as int", s.get("parallel_limit") == 3)

    # Every entry carries the fixed field subset (the stable surface).
    fixed = {"name", "model_name", "section", "sig", "description", "tier", "permission", "hidden"}
    check("project: every entry has fixed field subset",
          all(fixed.issubset(set(e)) for e in man["data"]))


def t_project_edge_cases():
    # Empty / None catalog -> count 0, empty data, headers intact.
    empty = mm.project_verb_catalog({})
    check("project: empty catalog count 0", empty["count"] == 0 and empty["data"] == [])
    none = mm.project_verb_catalog(None)
    check("project: None catalog -> count 0", none["count"] == 0 and none["data"] == [])

    # Non-dict spec values are skipped (defensive against malformed catalog).
    bad = mm.project_verb_catalog({"good": {"section": "Misc"}, "bad": "not-a-dict"})
    check("project: non-dict spec skipped", bad["count"] == 1 and bad["data"][0]["name"] == "good")

    # parallel_limit < 1 is NOT projected (only >= 1).
    pl0 = mm.project_verb_catalog({"v": {"section": "Misc", "parallel_limit": 0}})
    check("project: parallel_limit 0 omitted", "parallel_limit" not in pl0["data"][0])
    pl1 = mm.project_verb_catalog({"v": {"section": "Misc", "parallel_limit": 1}})
    check("project: parallel_limit 1 projected", pl1["data"][0].get("parallel_limit") == 1)

    # Garbage parallel_limit -> coerced to 0 -> omitted, no crash.
    plbad = mm.project_verb_catalog({"v": {"section": "Misc", "parallel_limit": "lots"}})
    check("project: non-int parallel_limit omitted (no crash)", "parallel_limit" not in plbad["data"][0])

    # Whitespace-only conflict_group -> stripped to empty -> omitted.
    cgws = mm.project_verb_catalog({"v": {"section": "Misc", "conflict_group": "   "}})
    check("project: whitespace conflict_group omitted", "conflict_group" not in cgws["data"][0])

    # model_name is stripped.
    ms = mm.project_verb_catalog({"v": {"section": "Misc", "model_name": "  Padded  "}})
    check("project: model_name stripped", ms["data"][0]["model_name"] == "Padded")


def t_diff_identical():
    path = _write_toml(SAMPLE_TOML)
    try:
        verbs = mm.load_verbs_from_toml(path)
    finally:
        os.unlink(path)
    man = mm.project_verb_catalog(verbs)
    check("diff: identical -> []", mm.diff_manifest(man, man) == [])
    # A fresh independent projection must also diff-clean (determinism end-to-end).
    check("diff: re-projected -> []",
          mm.diff_manifest(mm.project_verb_catalog(verbs), copy.deepcopy(man)) == [])


def t_diff_add_remove():
    base = mm.project_verb_catalog({
        "alpha": {"section": "Misc"},
        "beta": {"section": "Misc"},
    })
    # Committed is missing 'beta' -> generated has it -> "+ in SSOT not committed".
    committed_missing = mm.project_verb_catalog({"alpha": {"section": "Misc"}})
    diffs = mm.diff_manifest(base, committed_missing)
    check("diff: reports added verb",
          any("+ verb 'beta'" in d and "in SSOT but not in committed" in d for d in diffs), diffs)

    # Committed has an extra verb the SSOT dropped -> "- in committed not SSOT".
    committed_extra = mm.project_verb_catalog({
        "alpha": {"section": "Misc"},
        "beta": {"section": "Misc"},
        "gamma": {"section": "Misc"},
    })
    diffs2 = mm.diff_manifest(base, committed_extra)
    check("diff: reports removed verb",
          any("- verb 'gamma'" in d and "in committed manifest but not in SSOT" in d for d in diffs2), diffs2)


def t_diff_changed_fields():
    base = mm.project_verb_catalog({"v": {"section": "Misc", "permission": "read"}})

    # permission change -> ~ changed.
    perm = mm.project_verb_catalog({"v": {"section": "Misc", "permission": "admin"}})
    check("diff: permission change detected",
          any("~ verb 'v' changed" in d for d in mm.diff_manifest(base, perm)), )

    # conflict_group drift (WS-A7 serialization metadata) -> ~ changed.
    cg_base = mm.project_verb_catalog({"v": {"section": "Misc", "conflict_group": "g1"}})
    cg_drift = mm.project_verb_catalog({"v": {"section": "Misc", "conflict_group": "g2"}})
    check("diff: conflict_group drift detected",
          mm.diff_manifest(cg_base, cg_drift) == ["~ verb 'v' changed (regenerate the manifest)"],
          mm.diff_manifest(cg_base, cg_drift))

    # parallel_limit drift -> ~ changed.
    pl_base = mm.project_verb_catalog({"v": {"section": "Misc", "parallel_limit": 2}})
    pl_drift = mm.project_verb_catalog({"v": {"section": "Misc", "parallel_limit": 5}})
    check("diff: parallel_limit drift detected",
          any("~ verb 'v' changed" in d for d in mm.diff_manifest(pl_base, pl_drift)))

    # Adding a conflict_group where there was none -> changed.
    none_cg = mm.project_verb_catalog({"v": {"section": "Misc"}})
    add_cg = mm.project_verb_catalog({"v": {"section": "Misc", "conflict_group": "new"}})
    check("diff: newly-added conflict_group detected",
          any("~ verb 'v' changed" in d for d in mm.diff_manifest(none_cg, add_cg)))


def t_diff_registry_kind_guard():
    good = mm.project_verb_catalog({"v": {"section": "Misc"}})

    # committed missing/None/unparseable.
    check("diff: None committed -> error",
          mm.diff_manifest(good, None) == ["committed manifest missing or unparseable"])
    check("diff: non-dict committed -> error",
          mm.diff_manifest(good, "garbage") == ["committed manifest missing or unparseable"])

    # committed with wrong registry_kind (e.g. the hermes-build-tools registry).
    wrong_kind = copy.deepcopy(good)
    wrong_kind["registry_kind"] = "hermes-build-tools"
    diffs = mm.diff_manifest(good, wrong_kind)
    check("diff: wrong registry_kind flagged",
          "committed manifest registry_kind != 'verb-catalog'" in diffs, diffs)

    # committed entirely missing the registry_kind key (empty dict) -> flagged,
    # plus all generated verbs reported as added (committed has no data).
    diffs_empty = mm.diff_manifest(good, {})
    check("diff: empty committed flags registry_kind",
          "committed manifest registry_kind != 'verb-catalog'" in diffs_empty)
    check("diff: empty committed reports verbs as added",
          any("+ verb 'v'" in d for d in diffs_empty), diffs_empty)


def t_diff_ignores_volatile_toplevel():
    # diff compares data entries + registry_kind; volatile top-level fields like
    # count/source/version differences alone must NOT produce diffs.
    a = mm.project_verb_catalog({"v": {"section": "Misc"}})
    b = copy.deepcopy(a)
    b["count"] = 999
    b["source"] = "somewhere/else"
    b["version"] = "v9"
    check("diff: ignores volatile top-level fields (count/source/version)",
          mm.diff_manifest(a, b) == [], mm.diff_manifest(a, b))


def main():
    t_load_section_gating()
    t_load_empty_and_no_verbs()
    t_project_shape()
    t_project_ordering_determinism()
    t_project_field_defaults_and_flags()
    t_project_edge_cases()
    t_diff_identical()
    t_diff_add_remove()
    t_diff_changed_fields()
    t_diff_registry_kind_guard()
    t_diff_ignores_volatile_toplevel()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
