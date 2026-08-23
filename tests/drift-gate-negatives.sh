#!/usr/bin/env bash
# AI-hint: bash Negative-test harness for the new drift gates. Inject violations, assert they fail, restore, and assert pass.
# AI-doc: usr/share/doc/mios/manual/_harvest/tests_drift_gate_negatives_sh.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PATH="${ROOT}/.gemini/antigravity-ide/brain/65e96314-c09e-454f-843e-7baf8bdd3df7/scratch:${PATH}"

log() {
    echo -e "\033[1;34m[drift-gate-negatives]\033[0m $1"
}

die() {
    echo -e "\033[1;31m[drift-gate-negatives] ERROR:\033[0m $1" >&2
    exit 1
}

test_version_ssot() {
    log "Testing check_version_ssot"
    local version_file="${ROOT}/VERSION"
    local orig_val
    orig_val="$(cat "$version_file")"
    echo "$orig_val" > "$version_file"

    rm -f "$version_file"
    echo "9.9.9" > "$version_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_version_ssot >/dev/null 2>&1; then
        rm -f "$version_file"
        echo "$orig_val" > "$version_file"
        die "Check_version_ssot passed despite version drift violation"
    fi

    rm -f "$version_file"
    echo "$orig_val" > "$version_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_version_ssot >/dev/null 2>&1 \
        || die "Check_version_ssot failed after restoration"
    log "Check_version_ssot negative test passed"
}

test_resolver_equivalence() {
    log "Testing check_resolver_twin_equivalence"
    local userenv_file="${ROOT}/usr/lib/mios/userenv.sh"
    local bak_file="${userenv_file}.bak"
    cp "$userenv_file" "$bak_file"

    echo 'export MIOS_AI_TEST_TEMP="invalid-drift-val"' >> "$userenv_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_resolver_twin_equivalence >/dev/null 2>&1; then
        cp "$bak_file" "$userenv_file" && rm -f "$bak_file"
        die "Check_resolver_twin_equivalence passed despite mismatch"
    fi

    cp "$bak_file" "$userenv_file" && rm -f "$bak_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_resolver_twin_equivalence >/dev/null 2>&1 \
        || die "Check_resolver_twin_equivalence failed after restoration"
    log "Check_resolver_twin_equivalence negative test passed"
}

test_eval_safety() {
    log "Testing check_cli_eval_safety"
    local temp_verb="${ROOT}/usr/libexec/mios/mios-test-temp-eval"

    rm -f "$temp_verb"

    cat << 'EOF' > "$temp_verb"
#!/bin/bash
eval "$1"
EOF
    chmod +x "$temp_verb"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cli_eval_safety >/dev/null 2>&1; then
        rm -f "$temp_verb"
        die "Check_cli_eval_safety passed despite eval injection"
    fi

    rm -f "$temp_verb"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cli_eval_safety >/dev/null 2>&1 \
        || die "Check_cli_eval_safety failed after restoration"
    log "Check_cli_eval_safety negative test passed"
}

test_shellcheck_failure() {
    log "Testing check_shellcheck"
    
    local tmp_bin_dir
    tmp_bin_dir="$(mktemp -d)"
    cat << 'EOF' > "${tmp_bin_dir}/shellcheck"
echo "Injected shellcheck failure"
exit 1
EOF
    chmod +x "${tmp_bin_dir}/shellcheck"

    local old_path="$PATH"
    export PATH="${tmp_bin_dir}:${PATH}"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_shellcheck >/dev/null 2>&1; then
        export PATH="$old_path"
        rm -rf "$tmp_bin_dir"
        die "Check_shellcheck passed despite shellcheck failure"
    fi

    export PATH="$old_path"
    rm -rf "$tmp_bin_dir"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_shellcheck >/dev/null 2>&1 \
        || die "Check_shellcheck failed after restoration"
    log "Check_shellcheck negative test passed"
}

test_names_registry() {
    log "Testing check_names_registry"
    local reg_file="${ROOT}/usr/share/mios/referenced_names.txt"
    [[ -f "$reg_file" ]] || python3 "$ROOT/tools/generate-names-registry.py" >/dev/null 2>&1 || true
    local bak_file="${reg_file}.bak"
    cp "$reg_file" "$bak_file" 2>/dev/null || true

    echo "Fake_drip.key MIOS_FAKE_TEST_VARIABLE_DRIP" >> "$reg_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_names_registry >/dev/null 2>&1; then
        [[ -f "$bak_file" ]] && cp "$bak_file" "$reg_file" && rm -f "$bak_file"
        python3 "$ROOT/tools/generate-names-registry.py" >/dev/null 2>&1 || true
        die "Check_names_registry passed despite stale names.generated.txt"
    fi

    [[ -f "$bak_file" ]] && cp "$bak_file" "$reg_file" && rm -f "$bak_file"
    python3 "$ROOT/tools/generate-names-registry.py" >/dev/null 2>&1 || true
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_names_registry >/dev/null 2>&1 \
        || die "Check_names_registry failed after restoration"
    log "Check_names_registry negative test passed"
}

test_root_toml_subset() {
    log "Testing check_root_toml_subset"
    local root_toml="${ROOT}/mios.toml"
    local orig_val="" created=0
    if [[ -f "$root_toml" ]]; then
        orig_val="$(cat "$root_toml")"
        echo "$orig_val" > "$root_toml"
    else
        created=1
        : > "$root_toml"
    fi

    cat << 'EOF' >> "$root_toml"
[meta.nonexistent_drift_test_section]
fake_key_drift_assertion = "drift"
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_root_toml_subset >/dev/null 2>&1; then
        if [[ $created -eq 1 ]]; then rm -f "$root_toml"; else rm -f "$root_toml" && echo "$orig_val" > "$root_toml"; fi
        die "Check_root_toml_subset passed despite invalid key injection"
    fi

    if [[ $created -eq 1 ]]; then rm -f "$root_toml"; else rm -f "$root_toml" && echo "$orig_val" > "$root_toml"; fi
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_root_toml_subset >/dev/null 2>&1 \
        || die "Check_root_toml_subset failed after restoration"
    log "Check_root_toml_subset negative test passed"
}

test_toml_projection() {
    log "Testing check_toml_projection"
    local root_toml="${ROOT}/mios.toml"
    if [[ ! -f "$root_toml" ]]; then
        log "Root mios.toml absent"
        return 0
    fi
    local orig_val
    orig_val="$(cat "$root_toml")"
    echo "$orig_val" > "$root_toml"

    python3 - "$root_toml" << 'EOF'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
new = t.replace('accent      = "#1A407F"', 'accent      = "#DEAD00"', 1)
if new == t:
    new = t.replace('#1A407F', '#DEAD00', 1)   # fallback if spacing differs
open(p, "w", encoding="utf-8").write(new)
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_toml_projection >/dev/null 2>&1; then
        rm -f "$root_toml"
        echo "$orig_val" > "$root_toml"
        die "Check_toml_projection passed despite injected [colors] drift"
    fi

    rm -f "$root_toml"
    echo "$orig_val" > "$root_toml"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_toml_projection >/dev/null 2>&1 \
        || die "Check_toml_projection failed after restoration"
    log "Check_toml_projection negative test passed"
}

test_curl_retry() {
    log "Testing check_curl_retry"
    local temp_script="${ROOT}/automation/temp_curl_test.sh"
    cat << 'EOF' > "$temp_script"
curl https://example.com/unretried_file.tar.gz -o /tmp/file.tar.gz
EOF
    chmod +x "$temp_script"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_curl_retry >/dev/null 2>&1; then
        rm -f "$temp_script"
        die "Check_curl_retry passed despite unretried curl fetch"
    fi

    rm -f "$temp_script"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_curl_retry >/dev/null 2>&1 \
        || die "Check_curl_retry failed after restoration"
    log "Check_curl_retry negative test passed"
}

test_resolver_ssot_refs() {
    log "Testing check_resolver_ssot_refs"
    local target="${ROOT}/usr/libexec/mios/mios-resolve-latest"
    local backup="${target}.negtest.bak"
    cp "$target" "$backup"
    printf '    local drifted_ref="docker.io/pgvector/pgvector:pg16"\n' >> "$target"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_resolver_ssot_refs >/dev/null 2>&1; then
        mv "$backup" "$target"
        die "check_resolver_ssot_refs passed despite a hardcoded registry image ref"
    fi

    mv "$backup" "$target"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_resolver_ssot_refs >/dev/null 2>&1 \
        || die "check_resolver_ssot_refs failed after restoration"
    log "check_resolver_ssot_refs negative test passed"
}

test_nested_podman_caps() {
    log "Testing check_nested_podman_caps"
    local doc_file="${ROOT}/usr/share/doc/mios/reference/nested-podman-caps.md"
    local orig_val
    orig_val="$(cat "$doc_file")"
    rm -f "$doc_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1; then
        rm -f "$doc_file"
        echo "$orig_val" > "$doc_file"
        die "Check_nested_podman_caps passed despite missing reference doc"
    fi

    rm -f "$doc_file"
    echo "$orig_val" > "$doc_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1 \
        || die "Check_nested_podman_caps failed after restoration"
    log "Check_nested_podman_caps negative test passed"
}

test_bake_budget() {
    log "Testing check_bake_budget"
    local sbom_tsv="${ROOT}/usr/share/mios/artifacts/sbom/bound-images.tsv"
    local orig_val=""
    if [[ -f "$sbom_tsv" ]]; then
        orig_val="$(cat "$sbom_tsv")"
        echo "$orig_val" > "$sbom_tsv"
    else
        mkdir -p "$(dirname "$sbom_tsv")"
    fi

    rm -f "$sbom_tsv"
    {
        echo "$orig_val"
        for i in $(seq 1 35); do
            echo "Image_${i}	quay.io/mios/fake_${i}:latest	1.0GB"
        done
    } > "$sbom_tsv"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_budget >/dev/null 2>&1; then
        rm -f "$sbom_tsv"
    echo "$orig_val" > "$sbom_tsv"
        die "Check_bake_budget passed despite exceeding sidecar threshold"
    fi

    rm -f "$sbom_tsv"
    echo "$orig_val" > "$sbom_tsv"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_budget >/dev/null 2>&1 \
        || die "Check_bake_budget failed after restoration"
    log "Check_bake_budget negative test passed"
}

test_module_test_coverage() {
    log "Testing check_module_test_coverage"
    local temp_submodule="${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/identity/temp_untested_mod.py"
    echo "# Temp untested submodule" > "$temp_submodule"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_module_test_coverage >/dev/null 2>&1; then
        rm -f "$temp_submodule"* "${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/identity/__pycache__/temp_untested_mod"* 2>/dev/null || true
        die "Check_module_test_coverage passed despite missing submodule sibling test"
    fi

    rm -f "$temp_submodule"* "${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/identity/__pycache__/temp_untested_mod"* 2>/dev/null || true

    local temp_tool="${ROOT}/tools/temp_untested_tool_mod.py"
    echo "# Temp untested tool" > "$temp_tool"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_module_test_coverage >/dev/null 2>&1; then
        rm -f "$temp_tool"
        die "Check_module_test_coverage passed despite un-grandfathered tools module"
    fi
    rm -f "$temp_tool"

    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_module_test_coverage >/dev/null 2>&1 \
        || die "Check_module_test_coverage failed after restoration"
    log "Check_module_test_coverage negative test passed"
}

test_router_parity() {
    log "Testing check_router_parity"
    local temp_mod="${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/routing/temp_unmapped_router_branch.py"
    echo 'def _bogus_intent_branch(intent):' > "$temp_mod"
    echo '    if intent == "unmapped_bogus_intent": return True' >> "$temp_mod"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_router_parity >/dev/null 2>&1; then
        rm -f "$temp_mod"* "${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/routing/__pycache__/temp_unmapped_router_branch"* 2>/dev/null || true
        die "Check_router_parity passed despite unmapped intent branch in routing code"
    fi

    rm -f "$temp_mod"* "${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/routing/__pycache__/temp_unmapped_router_branch"* 2>/dev/null || true
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_router_parity >/dev/null 2>&1 \
        || die "Check_router_parity failed after restoration"
    log "Check_router_parity negative test passed"
}

test_council_gate_ssot() {
    log "Testing check_council_gate_ssot"
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local bak_file="${toml_file}.council_bak"
    cp "$toml_file" "$bak_file"

    python3 - "$toml_file" << 'EOF'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
new = t.replace('diversity_threshold         = 0.92', '# diversity_threshold disabled', 1)
open(p, "w", encoding="utf-8").write(new)
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_council_gate_ssot >/dev/null 2>&1; then
        cp "$bak_file" "$toml_file"
        rm -f "$bak_file"
        die "Check_council_gate_ssot passed despite missing diversity_threshold key in [agent_pipe.council]"
    fi

    cp "$bak_file" "$toml_file"
    rm -f "$bak_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_council_gate_ssot >/dev/null 2>&1 \
        || die "Check_council_gate_ssot failed after restoration"
    log "Check_council_gate_ssot negative test passed"
}

test_agent_pipe_budgets() {
    log "Testing check_agent_pipe_budgets"
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local orig_val
    orig_val="$(cat "$toml_file")"
    echo "$orig_val" > "$toml_file"

    python3 - "$toml_file" << 'EOF'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
new = t.replace('swarm_max_width      = 3', '# swarm_max_width disabled', 1)
open(p, "w", encoding="utf-8").write(new)
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_agent_pipe_budgets >/dev/null 2>&1; then
        rm -f "$toml_file"
        echo "$orig_val" > "$toml_file"
        die "Check_agent_pipe_budgets passed despite missing swarm_max_width key"
    fi

    rm -f "$toml_file"
    echo "$orig_val" > "$toml_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_agent_pipe_budgets >/dev/null 2>&1 \
        || die "Check_agent_pipe_budgets failed after restoration"
    log "Check_agent_pipe_budgets negative test passed"
}

test_bake_tokens() {
    log "Testing check_bake_plan with bogus firstboot token"
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local bak_file="${toml_file}.bak"
    cp "$toml_file" "$bak_file"

    python3 - "$toml_file" << 'EOF'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
new = t.replace('firstboot_tokens = [', 'firstboot_tokens = ["bogus_unmatched_firstboot_token", ', 1)
open(p, "w", encoding="utf-8").write(new)
EOF

    if MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1; then
        cp "$bak_file" "$toml_file" && rm -f "$bak_file"
        MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
        die "Generate-bake-plan.py --check passed despite a bogus firstboot token"
    fi

    cp "$bak_file" "$toml_file" && rm -f "$bak_file"
    MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
    MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1 \
        || die "Generate-bake-plan.py --check failed after restoration"
    log "Test_bake_tokens negative test passed"
}
test_bake_unresolved_image() {
    log "Testing check_bake_plan detects an Image= that resolves nowhere"
    local q="${ROOT}/usr/share/containers/systemd/mios-ceph.container"
    local bak="${q}.bak"
    cp "$q" "$bak"

    sed -i 's|^Image=.*|Image=quay.io/ceph/ceph:${UNRESOLVABLE_PROBE_TAG}|' "$q"

    # Captured, not piped: the suite runs under `set -o pipefail`, so
    # `gate | grep -q` returns the gate's exit 1 even when grep matched, and
    # the detection is thrown away by the harness rather than missed.
    local out=""
    out="$(MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT"         MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh"         check_bake_plan 2>&1 || true)"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT"         MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh"         check_bake_plan >/dev/null 2>&1; then
        cp "$bak" "$q" && rm -f "$bak"
        die "check_bake_plan passed despite an Image= that resolves nowhere"
    fi

    if ! printf '%s' "$out" | grep -q "does not resolve against the SSOT"; then
        cp "$bak" "$q" && rm -f "$bak"
        die "check_bake_plan failed without naming the unresolvable Image="
    fi

    cp "$bak" "$q" && rm -f "$bak"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT"         MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh"         check_bake_plan >/dev/null 2>&1         || die "check_bake_plan failed after restoration"
    log "Test_bake_unresolved_image negative test passed"
}

test_containerfile_pinned_clones() {
    log "Testing check_containerfile_pinned_clones"
    local temp_containerfile="${ROOT}/usr/share/mios/sys/Containerfile.testtemp"

    cat << 'EOF' > "$temp_containerfile"
FROM alpine
RUN git clone https://github.com/example/unpinned-repo.git /tmp/unpinned
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_containerfile_pinned_clones >/dev/null 2>&1; then
        rm -f "$temp_containerfile"
        die "Check_containerfile_pinned_clones passed despite unpinned git clone"
    fi

    rm -f "$temp_containerfile"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_containerfile_pinned_clones >/dev/null 2>&1 \
        || die "Check_containerfile_pinned_clones failed after restoration"
    log "Check_containerfile_pinned_clones negative test passed"
}

test_firstboot_tier() {
    log "Testing check_firstboot_tier"
    local fb_list="${ROOT}/usr/lib/mios/bake/plan.d/firstboot.list"
    local bak_file="${fb_list}.bak"
    cp "$fb_list" "$bak_file"

    echo "docker.io/unmatched/bogus-image:latest" >> "$fb_list"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_tier >/dev/null 2>&1; then
        cp "$bak_file" "$fb_list" && rm -f "$bak_file"
        MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "$ROOT/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
        die "Check_firstboot_tier passed despite unmatched firstboot.list entry"
    fi

    cp "$bak_file" "$fb_list" && rm -f "$bak_file"
    MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "$ROOT/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_tier >/dev/null 2>&1 \
        || die "Check_firstboot_tier failed after restoration"
    log "Check_firstboot_tier negative test passed"
}

test_rechunk_budget() {
    log "Testing check_rechunk_budget"
    local script="${ROOT}/automation/build/rechunk.sh"
    local orig_val
    orig_val="$(cat "$script")"
    rm -f "$script"
    echo "$orig_val" > "$script"
    sed -i 's/rechunk_max_layers/unused_key/g' "$script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_rechunk_budget >/dev/null 2>&1; then
        rm -f "$script"
        echo "$orig_val" > "$script"
        die "Check_rechunk_budget passed despite missing rechunk_max_layers"
    fi

    rm -f "$script"
    echo "$orig_val" > "$script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_rechunk_budget >/dev/null 2>&1 \
        || die "Check_rechunk_budget failed after restoration"
    log "Check_rechunk_budget negative test passed"
}

test_bake_core_reconcile() {
    log "Testing test_bake_core_reconcile"
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local bak_file="${toml_file}.bcrbak"
    cp "$toml_file" "$bak_file"

    sed -i 's/core_image = ".*"/core_image = "unreferenced-image-xyz999"/' "$toml_file"
    if MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1; then
        cp "$bak_file" "$toml_file" && rm -f "$bak_file"
        MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
        die "test_bake_core_reconcile: generate-bake-plan.py --check passed despite missing core image reconcile"
    fi

    cp "$bak_file" "$toml_file" && rm -f "$bak_file"
    MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
    MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1 \
        || die "test_bake_core_reconcile: generate-bake-plan.py --check failed after core image reconcile restoration"
    log "Test_bake_core_reconcile negative test passed"
}

test_nested_podman_retry() {
    log "Testing check_nested_podman_caps"
    local script="${ROOT}/usr/libexec/mios/57-mios-sys-build.sh"
    local bak_file="${script}.bak"
    cp "$script" "$bak_file"

    sed -i 's/build_image_with_retry/build_image_direct/g' "$script"
    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1; then
        cp "$bak_file" "$script" && rm -f "$bak_file"
        die "test_nested_podman_retry: Check_nested_podman_caps passed despite missing build_image_with_retry"
    fi

    cp "$bak_file" "$script" && rm -f "$bak_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1 \
        || die "test_nested_podman_retry: check_nested_podman_caps failed after retry script restoration"
    log "Test_nested_podman_retry negative test passed"
}

test_gate_registry() {
    log "Testing check_gate_registry"
    local script="${ROOT}/automation/98-drift-checks.sh"
    local bak_file="${script}.bak"
    cp "$script" "$bak_file"

    # Test 1: Duplicate definition
    sed -i '/check_dead_lane() {/i check_dead_lane() { return 0; }\n' "$script"
    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "$script" check_gate_registry >/dev/null 2>&1; then
        cp "$bak_file" "$script" && rm -f "$bak_file"
        die "check_gate_registry passed despite duplicate check_dead_lane definition"
    fi
    cp "$bak_file" "$script"

    # Test 2: Unregistered definition
    echo 'check_unregistered_dummy() { return 0; }' >> "$script"
    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "$script" check_gate_registry >/dev/null 2>&1; then
        cp "$bak_file" "$script" && rm -f "$bak_file"
        die "check_gate_registry passed despite unregistered function definition"
    fi
    cp "$bak_file" "$script"

    # Test 3: Undefined call in main()
    sed -i '/check_dead_lane/a \    check_undefined_dummy' "$script"
    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "$script" check_gate_registry >/dev/null 2>&1; then
        cp "$bak_file" "$script" && rm -f "$bak_file"
        die "check_gate_registry passed despite undefined check function call in main()"
    fi

    cp "$bak_file" "$script" && rm -f "$bak_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "$script" check_gate_registry >/dev/null 2>&1 \
        || die "check_gate_registry failed after restoration"
    log "test_gate_registry negative test passed"
}

test_test_hermeticity() {
    log "Testing check_test_hermeticity"
    local temp_test="${ROOT}/tests/test_fake_live_resource.py"

    cat << 'EOF' > "$temp_test"
import psycopg
def test_live():
    conn = psycopg.connect("dbname=mios user=mios")
EOF

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_test_hermeticity >/dev/null 2>&1; then
        rm -f "$temp_test"
        die "Check_test_hermeticity passed despite unguarded psycopg.connect call"
    fi

    rm -f "$temp_test"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_test_hermeticity >/dev/null 2>&1 \
        || die "Check_test_hermeticity failed after restoration"
    log "Test_test_hermeticity negative test passed"
}

test_no_mkdir_in_var() {
    log "Testing check_no_mkdir_in_var"
    local temp_script="${ROOT}/automation/99-fake-var-mkdir.sh"
    echo 'mkdir -p /var/log/fake_test' > "$temp_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_no_mkdir_in_var >/dev/null 2>&1; then
        rm -f "$temp_script"
        die "Check_no_mkdir_in_var passed despite imperative /var mkdir"
    fi

    rm -f "$temp_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_no_mkdir_in_var >/dev/null 2>&1 \
        || die "Check_no_mkdir_in_var failed after restoration"
    log "Test_no_mkdir_in_var negative test passed"
}

test_quadlet_privilege() {
    log "Testing check_quadlet_privilege"
    local q_dir="${ROOT}/etc/containers/systemd"
    mkdir -p "$q_dir"
    local temp_q="${q_dir}/fake-unprivileged-violation.container"
    rm -f "$temp_q" 2>/dev/null || true
    cat << 'EOF' > "$temp_q"
[Container]
Image=docker.io/library/alpine:latest
User=root
EOF

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_quadlet_privilege >/dev/null 2>&1; then
        rm -f "$temp_q"
        die "Check_quadlet_privilege passed despite un-allowlisted User=root"
    fi

    rm -f "$temp_q"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_quadlet_privilege >/dev/null 2>&1 \
        || die "Check_quadlet_privilege failed after restoration"
    log "Test_quadlet_privilege negative test passed"
}

test_lint_is_final() {
    log "Testing check_lint_is_final"
    local cf="${ROOT}/Containerfile"
    local orig_val
    orig_val="$(cat "$cf")"
    echo "$orig_val" > "$cf"
    sed -i '/RUN bootc container lint/d' "$cf"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_lint_is_final >/dev/null 2>&1; then
        rm -f "$cf"
        echo "$orig_val" > "$cf"
        die "Check_lint_is_final passed despite missing bootc container lint"
    fi

    rm -f "$cf"
    echo "$orig_val" > "$cf"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_lint_is_final >/dev/null 2>&1 \
        || die "Check_lint_is_final failed after restoration"
    log "Test_lint_is_final negative test passed"
}

test_firstboot_degrade_open() {
    log "Testing check_firstboot_degrade_open"
    local temp_fb="${ROOT}/usr/libexec/mios/mios-fake-firstboot.sh"
    cat << 'EOF' > "$temp_fb"
set -e
echo "No degrade open escape here"
EOF

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_degrade_open >/dev/null 2>&1; then
        rm -f "$temp_fb"
        die "Check_firstboot_degrade_open passed despite set -e without degrade escape"
    fi

    rm -f "$temp_fb"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_degrade_open >/dev/null 2>&1 \
        || die "Check_firstboot_degrade_open failed after restoration"
    log "Test_firstboot_degrade_open negative test passed"
}

test_require_tools() {
    log "Testing MIOS_DRIFT_REQUIRE_TOOLS"
    local tmp_bin="${ROOT}/tmp_no_python"
    mkdir -p "$tmp_bin"

    if MIOS_DRIFT_REQUIRE_TOOLS=1 PATH="$tmp_bin" bash "${ROOT}/automation/98-drift-checks.sh" check_cli_eval_safety >/dev/null 2>&1; then
        rm -rf "$tmp_bin"
        die "Check_cli_eval_safety passed despite missing python3 when MIOS_DRIFT_REQUIRE_TOOLS=1"
    fi

    rm -rf "$tmp_bin"
    log "Test_require_tools negative test passed"
}

test_ssot_lint_deadkey() {
    log "Testing 97-ssot-lint.sh dead-key injection"
    local temp_q="${ROOT}/usr/share/containers/systemd/fake-deadkey-test.container"
    rm -f "$temp_q" 2>/dev/null || true
    local dummy_var="MI"
    dummy_var+="OS_FAKE_DEADKEY_UNWIRED_VAR"
    cat << EOF > "$temp_q"
[Container]
Image=docker.io/library/alpine:latest
Exec=/bin/sh -c "\${${dummy_var}:-false}"
User=mios
Group=mios
Delegate=yes
EOF

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/97-ssot-lint.sh" >/dev/null 2>&1; then
        rm -f "$temp_q"
        die "97-ssot-lint.sh passed despite dead key injection"
    fi

    rm -f "$temp_q"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/97-ssot-lint.sh" >/dev/null 2>&1 \
        || die "97-ssot-lint.sh failed after restoration"
    log "Test_ssot_lint_deadkey negative test passed"
}

test_soft_mode_not_committed() {
    log "Testing check_soft_mode_not_committed"
    local gha_file="${ROOT}/.github/workflows/mios-ci.yml"
    local orig_val
    orig_val="$(cat "$gha_file")"
    printf '%s\n%s\n' "$orig_val" "MIOS_DRIFT_CHECK_SOFT=1" > "$gha_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_soft_mode_not_committed >/dev/null 2>&1; then
        rm -f "$gha_file"
        echo "$orig_val" > "$gha_file"
        die "Check_soft_mode_not_committed passed despite committed MIOS_DRIFT_CHECK_SOFT=1"
    fi

    rm -f "$gha_file"
    echo "$orig_val" > "$gha_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_soft_mode_not_committed >/dev/null 2>&1 \
        || die "Check_soft_mode_not_committed failed after restoration"
    log "Test_soft_mode_not_committed negative test passed"
}

test_oci_archive_path() {
    log "Testing check_oci_archive_path"
    local stage_script="${ROOT}/usr/libexec/mios/mios-stage-oci-archive"
    local orig_val
    orig_val="$(cat "$stage_script")"
    rm -f "$stage_script"
    echo "$orig_val" > "$stage_script"
    sed -i 's/mios-latest\.tar/mios-mismatched-name\.tar/g' "$stage_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_oci_archive_path >/dev/null 2>&1; then
        rm -f "$stage_script"
        echo "$orig_val" > "$stage_script"
        die "Check_oci_archive_path passed despite producer/consumer path mismatch"
    fi

    rm -f "$stage_script"
    echo "$orig_val" > "$stage_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_oci_archive_path >/dev/null 2>&1 \
        || die "Check_oci_archive_path failed after restoration"
    log "Test_oci_archive_path negative test passed"
}

test_replaceme_mount_substitution() {
    log "Testing check_replaceme_mount_substitution"
    local justfile="${ROOT}/Justfile"
    local orig_val
    orig_val="$(cat "$justfile")"
    rm -f "$justfile"
    echo "$orig_val" > "$justfile"

    cat << 'EOF' >> "$justfile"

fake-raw-bib:
    sudo podman run -v ./config/artifacts/iso.toml:/config.toml:ro bib
EOF

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_replaceme_mount_substitution >/dev/null 2>&1; then
        rm -f "$justfile"
        echo "$orig_val" > "$justfile"
        die "Check_replaceme_mount_substitution passed despite raw-mounted REPLACEME template"
    fi

    rm -f "$justfile"
    echo "$orig_val" > "$justfile"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_replaceme_mount_substitution >/dev/null 2>&1 \
        || die "Check_replaceme_mount_substitution failed after restoration"
    log "Test_replaceme_mount_substitution negative test passed"
}

test_kickstart_shell_syntax() {
    log "Testing check_kickstart_shell_syntax"
    local cfg="${ROOT}/usr/share/mios/ventoy/mios-kickstart.cfg"
    local orig_val
    orig_val="$(cat "$cfg")"
    echo "$orig_val" > "$cfg"

    rm -f "$cfg"
    echo "$orig_val" > "$cfg"
    cat << 'EOF' >> "$cfg"
%post
if [ true ]; then
  echo "Missing fi"
%end
EOF

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_kickstart_shell_syntax >/dev/null 2>&1; then
        rm -f "$cfg"
        echo "$orig_val" > "$cfg"
        die "Check_kickstart_shell_syntax passed despite invalid bash syntax in %post"
    fi

    rm -f "$cfg"
    echo "$orig_val" > "$cfg"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_kickstart_shell_syntax >/dev/null 2>&1 \
        || die "Check_kickstart_shell_syntax failed after restoration"
    log "Test_kickstart_shell_syntax negative test passed"
}

test_offline_install_invariant() {
    log "Testing check_offline_install_invariant"
    local install_script="${ROOT}/tools/install.sh"
    local orig_val
    orig_val="$(cat "$install_script")"
    rm -f "$install_script"
    echo "$orig_val" > "$install_script"

    echo "podman pull ghcr.io/ublue-os/ucore-hci:latest" >> "$install_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_offline_install_invariant >/dev/null 2>&1; then
        rm -f "$install_script"
        echo "$orig_val" > "$install_script"
        die "Check_offline_install_invariant passed despite injected podman pull"
    fi

    rm -f "$install_script"
    echo "$orig_val" > "$install_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_offline_install_invariant >/dev/null 2>&1 \
        || die "Check_offline_install_invariant failed after restoration"
    log "Test_offline_install_invariant negative test passed"
}

test_installer_family_roles() {
    log "Testing check_installer_family_roles"
    local s_script="${ROOT}/install.sh"
    local orig_val
    orig_val="$(cat "$s_script")"
    rm -f "$s_script"
    echo "$orig_val" > "$s_script"

    sed -i 's/MIOS_INSTALLER_ROLE=root-overlay-redirector/MIOS_INSTALLER_ROLE=bootc-baremetal-disk-installer/g' "$s_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_installer_family_roles >/dev/null 2>&1; then
        rm -f "$s_script"
        echo "$orig_val" > "$s_script"
        die "Check_installer_family_roles passed despite duplicate role marker"
    fi

    rm -f "$s_script"
    echo "$orig_val" > "$s_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_installer_family_roles >/dev/null 2>&1 \
        || die "Check_installer_family_roles failed after restoration"
    log "Test_installer_family_roles negative test passed"
}

test_bib_configs_projection() {
    log "Testing check_bib_configs_projection"
    local bib_file="${ROOT}/config/artifacts/bib.toml"
    local orig_val
    orig_val="$(cat "$bib_file")"
    rm -f "$bib_file"
    echo "$orig_val" > "$bib_file"

    sed -i 's/minsize = "80 GiB"/minsize = "999 GiB"/g' "$bib_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bib_configs_projection >/dev/null 2>&1; then
        rm -f "$bib_file"
        echo "$orig_val" > "$bib_file"
        die "Check_bib_configs_projection passed despite unprojected minsize edit"
    fi

    rm -f "$bib_file"
    echo "$orig_val" > "$bib_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bib_configs_projection >/dev/null 2>&1 \
        || die "Check_bib_configs_projection failed after restoration"
    log "Test_bib_configs_projection negative test passed"
}

test_ssot_lint_equivalence() {
    log "Testing check_ssot_lint_equivalence"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ssot_lint_equivalence >/dev/null 2>&1 \
        || die "Check_ssot_lint_equivalence failed"
    log "Test_ssot_lint_equivalence negative test passed"
}

test_repo_partition_label_ssot() {
    log "Testing check_repo_partition_label_ssot"
    local install_script="${ROOT}/tools/install.sh"
    local orig_val
    orig_val="$(cat "$install_script")"
    rm -f "$install_script"
    echo "$orig_val" > "$install_script"

    sed -i 's/MiOS-Repo/MiOS-MismatchedLabel/g' "$install_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_repo_partition_label_ssot >/dev/null 2>&1; then
        rm -f "$install_script"
        echo "$orig_val" > "$install_script"
        die "Check_repo_partition_label_ssot passed despite label mismatch"
    fi

    rm -f "$install_script"
    echo "$orig_val" > "$install_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_repo_partition_label_ssot >/dev/null 2>&1 \
        || die "Check_repo_partition_label_ssot failed after restoration"
    log "Test_repo_partition_label_ssot negative test passed"
}

test_bib_single_config_invariant() {
    log "Testing check_bib_single_config_invariant"
    local justfile="${ROOT}/Justfile"
    local orig_val
    orig_val="$(cat "$justfile")"
    rm -f "$justfile"
    echo "$orig_val" > "$justfile"

    cat << 'EOF' >> "$justfile"

fake-double-config-bib:
    sudo podman run -v ./c1.toml:/config.toml:ro -v ./c2.toml:/config.toml:ro {{BIB}}
EOF

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bib_single_config_invariant >/dev/null 2>&1; then
        rm -f "$justfile"
        echo "$orig_val" > "$justfile"
        die "Check_bib_single_config_invariant passed despite double config mount"
    fi

    rm -f "$justfile"
    echo "$orig_val" > "$justfile"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bib_single_config_invariant >/dev/null 2>&1 \
        || die "Check_bib_single_config_invariant failed after restoration"
    log "Test_bib_single_config_invariant negative test passed"
}

test_chpasswd_plaintext() {
    log "Testing mios-hardcode-lint plaintext chpasswd"
    local autorun_script="${ROOT}/usr/share/mios/ventoy/autorun/01-sysrescue-firstboot.sh"
    local bak_file="${autorun_script}.bak"
    cp "$autorun_script" "$bak_file"

    echo 'echo "Root:hardcodedpass" | chpasswd' >> "$autorun_script"

    if python3 "${ROOT}/usr/libexec/mios/mios-hardcode-lint" "${ROOT}" >/dev/null 2>&1; then
        cp "$bak_file" "$autorun_script" && rm -f "$bak_file"
        die "Mios-hardcode-lint passed despite plaintext chpasswd injection"
    fi

    cp "$bak_file" "$autorun_script" && rm -f "$bak_file"
    python3 "${ROOT}/usr/libexec/mios/mios-hardcode-lint" "${ROOT}" >/dev/null 2>&1 \
        || die "Mios-hardcode-lint failed after restoration"
    log "Test_chpasswd_plaintext negative test passed"
}

test_build_artifacts_output_dir() {
    log "Testing check_build_artifacts_output_dir"
    local justfile="${ROOT}/Justfile"
    local orig_val
    orig_val="$(cat "$justfile")"
    rm -f "$justfile"
    echo "$orig_val" > "$justfile"

    cat << 'EOF' >> "$justfile"

fake-non-ssot-recipe:
    mkdir -p output/stray
EOF

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_build_artifacts_output_dir >/dev/null 2>&1; then
        rm -f "$justfile"
        echo "$orig_val" > "$justfile"
        die "Check_build_artifacts_output_dir passed despite stray output/ path"
    fi

    rm -f "$justfile"
    echo "$orig_val" > "$justfile"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_build_artifacts_output_dir >/dev/null 2>&1 \
        || die "Check_build_artifacts_output_dir failed after restoration"
    log "Test_build_artifacts_output_dir negative test passed"
}

test_win11_vm_template_xml() {
    log "Testing check_win11_vm_template_xml"
    local xml_file="${ROOT}/tools/win11-secureboot-template.xml"
    local orig_val
    orig_val="$(cat "$xml_file")"
    rm -f "$xml_file"
    echo "$orig_val" > "$xml_file"

    echo '<invalid_xml>unclosed tag' >> "$xml_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_win11_vm_template_xml >/dev/null 2>&1; then
        rm -f "$xml_file"
        echo "$orig_val" > "$xml_file"
        die "Check_win11_vm_template_xml passed despite invalid XML"
    fi

    rm -f "$xml_file"
    echo "$orig_val" > "$xml_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_win11_vm_template_xml >/dev/null 2>&1 \
        || die "Check_win11_vm_template_xml failed after restoration"
    log "Test_win11_vm_template_xml negative test passed"
}

test_ipa_enroll_projection() {
    log "Testing check_ipa_enroll_projection"
    local target_file="${ROOT}/etc/mios/ipa-enroll.env"
    [[ -f "$target_file" ]] || { mkdir -p "$(dirname "$target_file")"; MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-ipa-enroll-env.py" >/dev/null 2>&1 || true; }

    echo 'MIOS_IPA_REALM="MUTATED.REALM"' >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ipa_enroll_projection >/dev/null 2>&1; then
        MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-ipa-enroll-env.py" >/dev/null 2>&1 || true
        die "Check_ipa_enroll_projection passed despite mutated target file"
    fi

    MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-ipa-enroll-env.py" >/dev/null 2>&1 || true
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ipa_enroll_projection >/dev/null 2>&1 \
        || die "Check_ipa_enroll_projection failed after restoration"
    log "Test_ipa_enroll_projection negative test passed"
}

test_uki_cmdline_projection() {
    log "Testing check_uki_cmdline_projection"
    local target_file="${ROOT}/usr/lib/kernel/cmdline"
    [[ -f "$target_file" ]] || { mkdir -p "$(dirname "$target_file")"; MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-uki-cmdline.py" >/dev/null 2>&1 || true; }

    echo 'mutated_bogus_karg=1' >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_uki_cmdline_projection >/dev/null 2>&1; then
        MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-uki-cmdline.py" >/dev/null 2>&1 || true
        die "Check_uki_cmdline_projection passed despite mutated cmdline"
    fi

    MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-uki-cmdline.py" >/dev/null 2>&1 || true
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_uki_cmdline_projection >/dev/null 2>&1 \
        || die "Check_uki_cmdline_projection failed after restoration"
    log "Test_uki_cmdline_projection negative test passed"
}

test_composefs_projection() {
    log "Testing check_composefs_projection"
    local target_file="${ROOT}/usr/lib/ostree/prepare-root.conf"
    local orig_val
    orig_val="$(cat "$target_file")"
    echo "$orig_val" > "$target_file"

    echo '[composefs]' > "$target_file"
    echo 'enabled = off' >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_composefs_projection >/dev/null 2>&1; then
        echo "$orig_val" > "$target_file"
        die "Check_composefs_projection passed despite mutated prepare-root.conf"
    fi

    echo "$orig_val" > "$target_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_composefs_projection >/dev/null 2>&1 \
        || die "Check_composefs_projection failed after restoration"
    log "Test_composefs_projection negative test passed"
}

test_cockpit_projection() {
    log "Testing check_cockpit_projection"
    local target_file="${ROOT}/etc/cockpit/cockpit.conf"
    [[ -f "$target_file" ]] || { mkdir -p "$(dirname "$target_file")"; MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-cockpit-conf.py" >/dev/null 2>&1 || true; }

    echo 'AllowUnencrypted = false' >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cockpit_projection >/dev/null 2>&1; then
        MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-cockpit-conf.py" >/dev/null 2>&1 || true
        die "Check_cockpit_projection passed despite mutated cockpit.conf"
    fi

    MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-cockpit-conf.py" >/dev/null 2>&1 || true
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cockpit_projection >/dev/null 2>&1 \
        || die "Check_cockpit_projection failed after restoration"
    log "Test_cockpit_projection negative test passed"
}

test_chrony_ptp_dropin() {
    log "Testing check_chrony_ptp_dropin"
    local dropin_script="${ROOT}/usr/libexec/mios/mios-chrony-ptp-dropin"
    local orig_val
    orig_val="$(cat "$dropin_script")"
    rm -f "$dropin_script"
    echo "$orig_val" > "$dropin_script"

    echo 'syntax error ((((' >> "$dropin_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_chrony_ptp_dropin >/dev/null 2>&1; then
        rm -f "$dropin_script"
        echo "$orig_val" > "$dropin_script"
        die "Check_chrony_ptp_dropin passed despite syntax error"
    fi

    rm -f "$dropin_script"
    echo "$orig_val" > "$dropin_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_chrony_ptp_dropin >/dev/null 2>&1 \
        || die "Check_chrony_ptp_dropin failed after restoration"
    log "Test_chrony_ptp_dropin negative test passed"
}

test_chrony_projection() {
    log "Testing check_chrony_projection"
    local target_file="${ROOT}/etc/chrony.conf"
    local orig_val
    orig_val="$(cat "$target_file")"
    rm -f "$target_file"
    echo "$orig_val" > "$target_file"

    echo "Server 199.99.99.99 iburst" >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_chrony_projection >/dev/null 2>&1; then
        rm -f "$target_file"
        echo "$orig_val" > "$target_file"
        die "Check_chrony_projection passed despite mutated chrony.conf"
    fi

    rm -f "$target_file"
    echo "$orig_val" > "$target_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_chrony_projection >/dev/null 2>&1 \
        || die "Check_chrony_projection failed after restoration"
    log "Test_chrony_projection negative test passed"
}

test_nut_projection() {
    log "Testing check_nut_projection"
    local target_file="${ROOT}/etc/ups/ups.conf"
    local orig_val
    orig_val="$(cat "$target_file")"
    rm -f "$target_file"
    echo "$orig_val" > "$target_file"

    echo "Driver = bogus" >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nut_projection >/dev/null 2>&1; then
        rm -f "$target_file"
        echo "$orig_val" > "$target_file"
        die "Check_nut_projection passed despite mutated ups.conf"
    fi

    rm -f "$target_file"
    echo "$orig_val" > "$target_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nut_projection >/dev/null 2>&1 \
        || die "Check_nut_projection failed after restoration"
    log "Test_nut_projection negative test passed"
}

test_renderer_gate_coverage() {
    log "Testing check_renderer_gate_coverage"
    local bogus_script="${ROOT}/automation/99-bogus-render.sh"
    echo '#!/usr/bin/env bash' > "$bogus_script"
    echo 'echo "Bogus render"' >> "$bogus_script"
    chmod +x "$bogus_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_renderer_gate_coverage >/dev/null 2>&1; then
        rm -f "$bogus_script"
        die "Check_renderer_gate_coverage passed despite unmapped 99-bogus-render.sh"
    fi

    rm -f "$bogus_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_renderer_gate_coverage >/dev/null 2>&1 \
        || die "Check_renderer_gate_coverage failed after cleanup"
    log "Test_renderer_gate_coverage negative test passed"
}

test_clevis_luks() {
    log "Testing check_clevis_luks"
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    mkdir -p "${tmp_dir}/usr/libexec/mios"
    printf '#!/bin/sh\necho "CLEVIS_BROKEN=true"\n' > "${tmp_dir}/usr/libexec/mios/mios-clevis-luks-gen"
    chmod +x "${tmp_dir}/usr/libexec/mios/mios-clevis-luks-gen" 2>/dev/null || true

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$tmp_dir" MIOS_DRIFT_CHECK_ROOT="$tmp_dir" bash "${ROOT}/automation/98-drift-checks.sh" check_clevis_luks >/dev/null 2>&1; then
        rm -rf "$tmp_dir"
        die "Check_clevis_luks passed despite broken generator output"
    fi

    rm -rf "$tmp_dir"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_clevis_luks >/dev/null 2>&1 \
        || die "Check_clevis_luks failed after cleanup"
    log "Test_clevis_luks negative test passed"
}

test_metal_vfio() {
    log "Testing check_metal_vfio"
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    mkdir -p "${tmp_dir}/usr/libexec/mios"
    printf '#!/bin/sh\necho "METAL_BROKEN=true"\n' > "${tmp_dir}/usr/libexec/mios/mios-metal-vfio-gen"
    chmod +x "${tmp_dir}/usr/libexec/mios/mios-metal-vfio-gen" 2>/dev/null || true

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$tmp_dir" MIOS_DRIFT_CHECK_ROOT="$tmp_dir" bash "${ROOT}/automation/98-drift-checks.sh" check_metal_vfio >/dev/null 2>&1; then
        rm -rf "$tmp_dir"
        die "Check_metal_vfio passed despite broken generator output"
    fi

    rm -rf "$tmp_dir"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_metal_vfio >/dev/null 2>&1 \
        || die "Check_metal_vfio failed after cleanup"
    log "Test_metal_vfio negative test passed"
}

test_hyprland_heredoc() {
    log "Testing check_hyprland_conf_heredoc"
    local conf_file="${ROOT}/usr/share/mios/hyprland/hyprland.conf"
    if [ -f "$conf_file" ]; then
        local bak_file="${conf_file}.bak"
        cp "$conf_file" "$bak_file"
        python3 - "$conf_file" << 'PYEOF'
import sys, os
p = sys.argv[1]
try:
    os.chmod(p, 0o666)
except Exception:
    pass
val = open(p, 'r', encoding='utf-8', errors='ignore').read()
try:
    os.remove(p)
except Exception:
    pass
with open(p, 'w', encoding='utf-8') as f:
    f.write(val + '\n# INJECTED-DRIFT\n')
PYEOF

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_hyprland_conf_heredoc >/dev/null 2>&1; then
            cp "$bak_file" "$conf_file" && rm -f "$bak_file"
            die "Check_hyprland_conf_heredoc passed despite injected drift"
        fi

        cp "$bak_file" "$conf_file" && rm -f "$bak_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_hyprland_conf_heredoc >/dev/null 2>&1 \
            || die "Check_hyprland_conf_heredoc failed after restoration"
    fi
    log "Test_hyprland_heredoc negative test passed"
}

test_target_languages() {
    log "Testing check_target_languages"
    local bogus_file="${ROOT}/usr/libexec/mios/bogus_script.cpp"
    echo '// forbidden c++ file' > "$bogus_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_target_languages >/dev/null 2>&1; then
        rm -f "$bogus_file"
        die "Check_target_languages passed despite forbidden C++ file"
    fi

    rm -f "$bogus_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_target_languages >/dev/null 2>&1 \
        || die "Check_target_languages failed after cleanup"
    log "Test_target_languages negative test passed"
}

test_roadmap_index() {
    log "Testing check_roadmap_index"
    local roadmap_file="${ROOT}/ROADMAP.md"
    if [ -f "$roadmap_file" ]; then
        local bak_file="${roadmap_file}.bak"
        cp "$roadmap_file" "$bak_file"
        sed -i 's/\*\*Done\*\*: [0-9]*/\*\*Done\*\*: 99999/g' "$roadmap_file" 2>/dev/null || true

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_roadmap_index >/dev/null 2>&1; then
            cp "$bak_file" "$roadmap_file" && rm -f "$bak_file"
            die "Check_roadmap_index passed despite corrupted rollup"
        fi

        cp "$bak_file" "$roadmap_file" && rm -f "$bak_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_roadmap_index >/dev/null 2>&1 \
            || die "Check_roadmap_index failed after restoration"
    fi
    log "Test_roadmap_index negative test passed"
}

test_templates_compilation() {
    log "Testing check_templates_compilation"
    local tmpl_file="${ROOT}/usr/share/mios/templates/toml-config"
    if [ -f "$tmpl_file" ]; then
        local bak_file="${tmpl_file}.bak"
        cp "$tmpl_file" "$bak_file"
        echo 'INVALID_SYNTAX_BOGUS {{' >> "$tmpl_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_templates_compilation >/dev/null 2>&1; then
            cp "$bak_file" "$tmpl_file" && rm -f "$bak_file"
            die "Check_templates_compilation passed despite invalid template"
        fi

        cp "$bak_file" "$tmpl_file" && rm -f "$bak_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_templates_compilation >/dev/null 2>&1 \
            || die "Check_templates_compilation failed after restoration"
    fi
    log "Test_templates_compilation negative test passed"
}

test_impossible_eol() {
    log "Testing check_impossible_eol_regressions"
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    if [ -f "$toml_file" ]; then
        local bak_file="${toml_file}.bak"
        cp "$toml_file" "$bak_file"
        echo 'eol_test_pkg = ["tang"]' >> "$toml_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_impossible_eol_regressions >/dev/null 2>&1; then
            cp "$bak_file" "$toml_file" && rm -f "$bak_file"
            die "Check_impossible_eol_regressions passed despite EOL tang package"
        fi

        cp "$bak_file" "$toml_file" && rm -f "$bak_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_impossible_eol_regressions >/dev/null 2>&1 \
            || die "Check_impossible_eol_regressions failed after restoration"
    fi
    log "Test_impossible_eol negative test passed"
}

test_smoke_manifest() {
    log "Testing check_smoke_manifest"
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    if [ -f "$toml_file" ]; then
        local bak_file="${toml_file}.bak"
        cp "$toml_file" "$bak_file"
        python3 - "$toml_file" << 'PYEOF'
import sys, os
p = sys.argv[1]
try:
    os.chmod(p, 0o666)
except Exception:
    pass
val = open(p, 'r', encoding='utf-8', errors='ignore').read()
try:
    os.remove(p)
except Exception:
    pass
with open(p, 'w', encoding='utf-8') as f:
    f.write(val + '\n[testing.smoke_components]\nshims = ["usr/libexec/mios/non-existent-bogus-shim"]\n')
PYEOF

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_smoke_manifest >/dev/null 2>&1; then
            cp "$bak_file" "$toml_file" && rm -f "$bak_file"
            die "Check_smoke_manifest passed despite missing component path"
        fi

        cp "$bak_file" "$toml_file" && rm -f "$bak_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_smoke_manifest >/dev/null 2>&1 \
            || die "Check_smoke_manifest failed after restoration"
    fi
    log "Test_smoke_manifest negative test passed"
}

test_verb_templates() {
    log "Testing check_verb_templates"
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    if [ -f "$toml_file" ]; then
        local orig_val
        orig_val="$(cat "$toml_file")"
        echo "$orig_val" > "$toml_file"
        printf '\n[verbs.bogus_broken]\ncmd = "echo {invalid_placeholder"\n' >> "$toml_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_verb_templates >/dev/null 2>&1; then
            echo "$orig_val" > "$toml_file"
            die "Check_verb_templates passed despite invalid verb template"
        fi

        echo "$orig_val" > "$toml_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_verb_templates >/dev/null 2>&1 \
            || die "Check_verb_templates failed after restoration"
    fi
    log "Test_verb_templates negative test passed"
}

test_pipe_boundaries() {
    log "Testing check_pipe_boundaries"
    local manifest="${ROOT}/usr/share/mios/pipe-boundaries.manifest.json"
    if [ -f "$manifest" ]; then
        local orig_val
        orig_val="$(cat "$manifest")"
        rm -f "$manifest"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_pipe_boundaries >/dev/null 2>&1; then
            echo "$orig_val" > "$manifest"
            die "Check_pipe_boundaries passed despite missing manifest file"
        fi

        echo "$orig_val" > "$manifest"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_pipe_boundaries >/dev/null 2>&1 \
            || die "Check_pipe_boundaries failed after restoration"
    fi
    log "Test_pipe_boundaries negative test passed"
}

test_vllm_name_canonical() {
    log "Testing check_vllm_name_canonical"
    local dummy="${ROOT}/usr/lib/mios/dummy_vllm_negative_test.sh"
    echo 'MIOS_AI_VLLM_SERVED_NAME="test"' > "$dummy"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_vllm_name_canonical >/dev/null 2>&1; then
        rm -f "$dummy"
        die "Check_vllm_name_canonical passed despite legacy long name"
    fi

    rm -f "$dummy"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_vllm_name_canonical >/dev/null 2>&1 \
        || die "Check_vllm_name_canonical failed after restoration"

    log "Test_vllm_name_canonical negative test passed"
}

test_pipe_extraction_parity() {
    log "Testing check_pipe_extraction_parity"
    local test_file="${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/observability/session_events.py"
    if [ -f "$test_file" ]; then
        local orig_val
        orig_val="$(cat "$test_file")"
        printf '%s\n%s\n' "$orig_val" "import server" > "$test_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_pipe_extraction_parity >/dev/null 2>&1; then
            echo "$orig_val" > "$test_file"
            die "Check_pipe_extraction_parity passed despite forbidden import server"
        fi

        echo "$orig_val" > "$test_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_pipe_extraction_parity >/dev/null 2>&1 \
            || die "Check_pipe_extraction_parity failed after restoration"
    fi
    log "Test_pipe_extraction_parity negative test passed"
}

test_bake_plan() {
    log "Testing check_bake_plan"
    # The extra group is the catch-all: its numeric prefix shifts whenever the
    # bake sharding gains a group, so resolve it by glob instead of hardcoding.
    local plan_file
    plan_file="$(find "${ROOT}/usr/lib/mios/bake/plan.d" -maxdepth 1 -name '[0-9][0-9]-extra.list' -print -quit 2>/dev/null)"
    if [ -n "$plan_file" ] && [ -f "$plan_file" ]; then
        local bak_file="${plan_file}.bak"
        cp "$plan_file" "$bak_file"
        echo "docker.io/library/bogus-image-never-exists:latest" >> "$plan_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_plan >/dev/null 2>&1; then
            cp "$bak_file" "$plan_file" && rm -f "$bak_file"
            MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
            die "Check_bake_plan passed despite stale/invalid bake plan"
        fi

        cp "$bak_file" "$plan_file" && rm -f "$bak_file"
        MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_plan >/dev/null 2>&1 \
            || die "Check_bake_plan failed after restoration"
    fi
    log "Test_bake_plan negative test passed"
}

test_bake_ref_defaults() {
    log "Testing check_bake_ref_defaults"
    local test_sh="${ROOT}/automation/34-render-quadlets.sh"
    if [ -f "$test_sh" ]; then
        local orig_val
        orig_val="$(cat "$test_sh")"
        printf '%s\n%s\n' "$orig_val" ': "${MIOS_BUILD_BAKE_REFS_ZZZ:-}"' > "$test_sh"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_ref_defaults >/dev/null 2>&1; then
            echo "$orig_val" > "$test_sh"
            die "Check_bake_ref_defaults passed despite empty bake ref default"
        fi

        echo "$orig_val" > "$test_sh"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_ref_defaults >/dev/null 2>&1 \
            || die "Check_bake_ref_defaults failed after restoration"
    fi
    log "Test_bake_ref_defaults negative test passed"
}

test_deploy_plane() {
    log "Testing check_deploy_plane"
    local cfg="${ROOT}/usr/share/mios/ventoy/mios-kickstart.cfg"
    if [ -f "$cfg" ]; then
        local orig_val
        orig_val="$(cat "$cfg")"
        echo "$orig_val" > "$cfg"
        grep -v "MIOS_FHS_TOTAL_ROOT_MERGE=1" "$cfg" > "${cfg}.tmp" && mv "${cfg}.tmp" "$cfg"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_deploy_plane >/dev/null 2>&1; then
            echo "$orig_val" > "$cfg"
            die "Check_deploy_plane passed despite missing MIOS_FHS_TOTAL_ROOT_MERGE=1"
        fi

        echo "$orig_val" > "$cfg"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_deploy_plane >/dev/null 2>&1 \
            || die "Check_deploy_plane failed after restoration"
    fi
    log "Test_deploy_plane negative test passed"
}

test_sbom_metadata() {
    log "Testing check_sbom_metadata"
    local sbom_file="${ROOT}/usr/share/mios/artifacts/sbom/models.tsv"
    local dir
    dir="$(dirname "$sbom_file")"
    mkdir -p "$dir"
    printf "name\tversion\tsha256\turl\nmodel1\t1.0\tdeadbeef\thttps://example.com\n" > "$sbom_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_sbom_metadata >/dev/null 2>&1; then
        rm -f "$sbom_file"
        die "Check_sbom_metadata passed despite invalid sha256"
    fi

    rm -f "$sbom_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_sbom_metadata >/dev/null 2>&1 \
        || die "Check_sbom_metadata failed after restoration"
    log "Test_sbom_metadata negative test passed"
}





test_negative_coverage() {
    log "Testing check_negative_coverage"
    local checks_sh="${ROOT}/automation/98-drift-checks.sh"
    if [ -f "$checks_sh" ]; then
        local orig_val
        orig_val="$(cat "$checks_sh")"
        echo "$orig_val" > "$checks_sh"
        sed -i 's/check_pipe_extraction_parity/check_pipe_extraction_parity\n    check_bogus_uncovered_gate/' "$checks_sh"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_negative_coverage >/dev/null 2>&1; then
            echo "$orig_val" > "$checks_sh"
            die "Check_negative_coverage passed despite uncovered gate"
        fi

        echo "$orig_val" > "$checks_sh"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_negative_coverage >/dev/null 2>&1 \
            || die "Check_negative_coverage failed after restoration"
    fi
    log "Test_negative_coverage negative test passed"
}

test_guacamole_consistency() {
    log "Testing check_guacamole_consistency"
    local desktop_file="${ROOT}/usr/share/applications/mios-svc-guacamole.desktop"
    local orig_val
    orig_val="$(cat "$desktop_file")"

    # Port-agnostic injection: hardcoding the current port here means the test
    # silently stops injecting anything the moment [ports].guacamole_web moves,
    # and then "passes" for the wrong reason.
    sed -i -E 's#(localhost:)[0-9]+#\19999#g' "$desktop_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_guacamole_consistency >/dev/null 2>&1; then
        echo "$orig_val" > "$desktop_file"
        die "Check_guacamole_consistency passed despite port mismatch violation"
    fi

    echo "$orig_val" > "$desktop_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_guacamole_consistency >/dev/null 2>&1 \
        || die "Check_guacamole_consistency failed after restoration"
    log "Test_guacamole_consistency negative test passed"
}

test_cephfs_ssot() {
    log "Testing check_cephfs_ssot"
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local orig_val
    orig_val="$(cat "$toml_file")"

    sed -i 's/mount_options                   = "noatime,fsc,_netdev"/# mount_options removed/' "$toml_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cephfs_ssot >/dev/null 2>&1; then
        echo "$orig_val" > "$toml_file"
        die "Check_cephfs_ssot passed despite missing mount_options key"
    fi

    echo "$orig_val" > "$toml_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cephfs_ssot >/dev/null 2>&1 \
        || die "Check_cephfs_ssot failed after restoration"
    log "Test_cephfs_ssot negative test passed"
}

test_v2v_import_ssot() {
    log "Testing check_v2v_import_ssot"
    local wrapper_file="${ROOT}/usr/libexec/mios/mios-v2v-import"
    local orig_val
    orig_val="$(cat "$wrapper_file")"

    sed -i 's/-of {output_format}/-of broken_format/' "$wrapper_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_v2v_import_ssot >/dev/null 2>&1; then
        echo "$orig_val" > "$wrapper_file"
        die "Check_v2v_import_ssot passed despite broken wrapper output_format"
    fi

    echo "$orig_val" > "$wrapper_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_v2v_import_ssot >/dev/null 2>&1 \
        || die "Check_v2v_import_ssot failed after restoration"
    log "Test_v2v_import_ssot negative test passed"
}

test_no_hardcode_version() {
    log "Testing check_no_hardcode_version"
    local temp_script="${ROOT}/usr/libexec/mios/mios-test-temp-verpin.sh"
    rm -f "$temp_script"

    cat << 'EOF' > "$temp_script"
curl -LO https://example.com/releases/download/v1.2.3/x
EOF
    chmod +x "$temp_script"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_no_hardcode_version >/dev/null 2>&1; then
        rm -f "$temp_script"
        die "Check_no_hardcode_version passed despite hardcoded version in URL"
    fi

    rm -f "$temp_script"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_no_hardcode_version >/dev/null 2>&1 \
        || die "Check_no_hardcode_version failed after restoration"
    log "Test_no_hardcode_version negative test passed"
}

test_law_enforcers() {
    log "Testing check_law_enforcers"
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local bak_file="${toml_file}.law_bak"
    cp "$toml_file" "$bak_file"

    sed -i 's/check_usr_over_etc/check_nonexistent_bogus_law/' "$toml_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_law_enforcers >/dev/null 2>&1; then
        cp "$bak_file" "$toml_file"
        rm -f "$bak_file"
        die "Check_law_enforcers passed despite missing law enforcer"
    fi

    cp "$bak_file" "$toml_file"
    rm -f "$bak_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_law_enforcers >/dev/null 2>&1 \
        || die "Check_law_enforcers failed after restoration"
    log "Test_law_enforcers negative test passed"
}

test_usr_over_etc() {
    log "Testing check_usr_over_etc"
    local temp_shadow="${ROOT}/etc/fontconfig/conf.avail/30-mios-geist.conf"
    mkdir -p "${ROOT}/etc/fontconfig/conf.avail"
    touch "$temp_shadow"
    git add -f "$temp_shadow"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_usr_over_etc >/dev/null 2>&1; then
        git rm -f "$temp_shadow" >/dev/null 2>&1
        rm -rf "${ROOT}/etc/fontconfig"
        die "Check_usr_over_etc passed despite /etc file shadowing /usr SSOT file"
    fi

    git rm -f "$temp_shadow" >/dev/null 2>&1
    rm -rf "${ROOT}/etc/fontconfig"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_usr_over_etc >/dev/null 2>&1 \
        || die "Check_usr_over_etc failed after restoration"
    log "Test_usr_over_etc negative test passed"
}

test_projection_registry() {
    log "Testing check_projection_registry"
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local orig_val
    orig_val="$(cat "$toml_file")"

    sed -i 's/check = "check_dotfiles_projection"/check = "check_nonexistent_proj_check"/' "$toml_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_projection_registry >/dev/null 2>&1; then
        echo "$orig_val" > "$toml_file"
        die "Check_projection_registry passed despite missing projection check"
    fi

    echo "$orig_val" > "$toml_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_projection_registry >/dev/null 2>&1 \
        || die "Check_projection_registry failed after restoration"
    log "Test_projection_registry negative test passed"
}

test_bake_plan_integrity() {
    log "Testing check_bake_plan_integrity"
    # Resolve the extra catch-all list by glob -- its numeric prefix shifts
    # whenever the bake sharding gains a group (03- became 04- with 'heavy').
    local list_file
    list_file="$(find "${ROOT}/usr/lib/mios/bake/plan.d" -maxdepth 1 -name '[0-9][0-9]-extra.list' -print -quit 2>/dev/null)"
    [ -n "$list_file" ] && [ -f "$list_file" ] || die "No [0-9][0-9]-extra.list found in plan.d -- bake plan not generated?"
    local orig_val
    orig_val="$(cat "$list_file")"

    echo "docker.io/vllm/vllm-openai:latest" >> "$list_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_plan_integrity >/dev/null 2>&1; then
        echo "$orig_val" > "$list_file"
        die "Check_bake_plan_integrity passed despite firstboot token in baked group list"
    fi

    echo "$orig_val" > "$list_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_plan_integrity >/dev/null 2>&1 \
        || die "Check_bake_plan_integrity failed after restoration"
    log "Test_bake_plan_integrity negative test passed"
}

test_bake_ref_parity() {
    log "Testing check_bake_ref_defaults"
    local script_file="${ROOT}/automation/55-bake-quickshell.sh"
    if [[ -f "$script_file" ]]; then
        local orig_val
        orig_val="$(cat "$script_file")"

        sed -i 's/MIOS_BUILD_BAKE_REFS_QUICKSHELL:-v0.3.0/MIOS_BUILD_BAKE_REFS_QUICKSHELL:-v9.9.9/' "$script_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_ref_defaults >/dev/null 2>&1; then
            echo "$orig_val" > "$script_file"
            die "Check_bake_ref_defaults passed despite wrong bake_ref default"
        fi

        echo "$orig_val" > "$script_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_ref_defaults >/dev/null 2>&1 \
            || die "test_bake_ref_parity: check_bake_ref_defaults failed after restoration"
    fi
    log "Test_bake_ref_parity negative test passed"
}

test_db_seed_coverage() {
    log "Testing check_db_seed_coverage"
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local seed_script="${ROOT}/usr/libexec/mios/seed-db-config.py"
    local orig_val
    local orig_seed
    orig_val="$(cat "$toml_file")"
    orig_seed="$(cat "$seed_script")"

    echo "" >> "$toml_file"
    echo "[unseeded_bogus_test_section]" >> "$toml_file"
    echo "Key = \"value\"" >> "$toml_file"
    
    sed -i 's/kv_sections = \[k for k in data.keys()/kv_sections = \[\] # removed for test/' "$seed_script"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_db_seed_coverage >/dev/null 2>&1; then
        echo "$orig_val" > "$toml_file"
        echo "$orig_seed" > "$seed_script"
        die "Check_db_seed_coverage passed despite unseeded section in mios.toml"
    fi

    echo "$orig_val" > "$toml_file"
    echo "$orig_seed" > "$seed_script"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_db_seed_coverage >/dev/null 2>&1 \
        || die "Check_db_seed_coverage failed after restoration"
    log "Test_db_seed_coverage negative test passed"
}

test_account_column_parity() {
    log "Testing check_account_column_parity"
    local schema_file="${ROOT}/usr/share/mios/postgres/schema-init.sql"
    local orig_val
    orig_val="$(cat "$schema_file")"

    sed -i 's/name        text UNIQUE NOT NULL/-- name        text UNIQUE NOT NULL/' "$schema_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_account_column_parity >/dev/null 2>&1; then
        echo "$orig_val" > "$schema_file"
        die "Check_account_column_parity passed despite missing column in schema"
    fi

    echo "$orig_val" > "$schema_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_account_column_parity >/dev/null 2>&1 \
        || die "Check_account_column_parity failed after restoration"
    log "Test_account_column_parity negative test passed"
}


test_ssot_consumer_keys() {
    log "Testing check_ssot_consumer_keys"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local bak="${toml}.sckbak"
    cp "$toml" "$bak"

    _sck_run() {
        env MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" \
            MIOS_DRIFT_CHECK_ROOT="$ROOT" \
            bash "${ROOT}/automation/98-drift-checks.sh" check_ssot_consumer_keys \
            >/dev/null 2>&1
    }
    _sck_fail() { cp "$bak" "$toml"; rm -f "$bak"; unset -f _sck_run _sck_fail; die "$1"; }

    # (1) Breaking a key a consumer reads must FAIL. Renaming [security]'s
    # api_require_auth is exactly the T-325 defect, re-created.
    sed -i '0,/^api_require_auth /s//api_require_auth_RENAMED /' "$toml"
    _sck_run && _sck_fail "check_ssot_consumer_keys passed with api_require_auth renamed out from under its consumer"
    cp "$bak" "$toml"

    # (2) Raising the ceiling to absorb the new breakage must FAIL too.
    sed -i '0,/^api_require_auth /s//api_require_auth_RENAMED /' "$toml"
    sed -i 's/^max_unresolved = [0-9]*$/max_unresolved = 999/' "$toml"
    _sck_run && _sck_fail "check_ssot_consumer_keys passed with the ceiling raised"
    cp "$bak" "$toml"

    # (3) Deleting the register must FAIL rather than read as "no breakage".
    python3 - "$toml" <<'PYX'
import io, re, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
s = re.sub(r'\[ssot_consumers\]\n.*?\n\]\n', '', s, count=1, flags=re.S)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
PYX
    _sck_run && _sck_fail "check_ssot_consumer_keys passed with [ssot_consumers] absent"

    cp "$bak" "$toml"; rm -f "$bak"
    _sck_run || { unset -f _sck_run _sck_fail; die "check_ssot_consumer_keys failed after restoration"; }
    unset -f _sck_run _sck_fail

    log "Test_ssot_consumer_keys negative test passed"
}

test_unit_projection() {
    log "Testing check_unit_projection"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local bak="${toml}.upbak"
    cp "$toml" "$bak"

    _up_run() {
        env MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" \
            MIOS_DRIFT_CHECK_ROOT="$ROOT" \
            bash "${ROOT}/automation/98-drift-checks.sh" check_unit_projection \
            >/dev/null 2>&1
    }
    _up_fail() { cp "$bak" "$toml"; rm -f "$bak"; unset -f _up_run _up_fail; die "$1"; }

    # (1) Raising the ceiling to absorb new drift must FAIL. The ratchet only
    # comes down; a register that may grow measures nothing.
    sed -i 's/^max_drift = [0-9]*$/max_drift = 999/' "$toml"
    _up_run && _up_fail "check_unit_projection passed with a raised ceiling"
    cp "$bak" "$toml"

    # (2) Toolchain-free half: register below its own ceiling. The renderer half
    # is asserted by tests/projection.rs. See TASKS.md T-317.
    python3 - "$toml" <<'PYX'
import io, re, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
start = s.index("[unit_projection]")
end = s.index("\n]\n", start) + len("\n]\n")
block = s[start:end]
block, n = re.subn(r'\n  "[^"]+",(?=\n\])', '', block, count=1)
assert n == 1, "no register entry was removed -- the mutation would prove nothing"
io.open(p, "w", encoding="utf-8", newline="\n").write(s[:start] + block + s[end:])
PYX
    _up_run && _up_fail "check_unit_projection passed with the register below its own ceiling"
    cp "$bak" "$toml"

    # (3) An entry naming a unit [units.*] does not project must FAIL.
    sed -i '0,/^drift = \[$/s//drift = [\n  "mios-not-a-real-unit.service",/' "$toml"
    _up_run && _up_fail "check_unit_projection passed on a register entry naming no projected unit"
    cp "$bak" "$toml"

    # (4) Deleting the table must FAIL rather than read as "no debt".
    python3 - "$toml" <<'PYX'
import io, re, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
s = re.sub(r'\[unit_projection\]\n.*?\n\]\n', '', s, count=1, flags=re.S)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
PYX
    _up_run && _up_fail "check_unit_projection passed with [unit_projection] absent"

    cp "$bak" "$toml"; rm -f "$bak"
    _up_run || { unset -f _up_run _up_fail; die "check_unit_projection failed after restoration"; }
    unset -f _up_run _up_fail

    log "Test_unit_projection negative test passed"
}

test_mini_vs_hosted() {
    log "Testing check_mini_vs_hosted"
    local doc="${ROOT}/usr/share/doc/mios/reference/mini-vs-hosted.md"
    local bak="${doc}.mvhbak"
    cp "$doc" "$bak"

    # (1) A hand-edited comparison must FAIL -- the whole point is that the
    # numbers are projected, so nobody can quietly "correct" them.
    sed -i 's/| Units started |.*/| Units started | **1** | **1** |/' "$doc"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_mini_vs_hosted >/dev/null 2>&1; then
        mv "$bak" "$doc"
        die "check_mini_vs_hosted passed on a hand-edited comparison"
    fi

    # (2) A MISSING projection must FAIL rather than read as "nothing to check".
    rm -f "$doc"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_mini_vs_hosted >/dev/null 2>&1; then
        mv "$bak" "$doc"
        die "check_mini_vs_hosted passed with the comparison absent"
    fi

    mv "$bak" "$doc"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_mini_vs_hosted >/dev/null 2>&1 \
        || die "check_mini_vs_hosted failed after restoration"

    log "Test_mini_vs_hosted negative test passed"
}

test_node_pool() {
    log "Testing check_node_pool"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local backup="${toml}.npbak"
    cp "$toml" "$backup"

    # (1) An exact alias must FAIL -- four of six shipped nodes were byte-identical
    # copies of the SGLang endpoint, so the fan-out counted one backend as four.
    python3 -c 'import io,re,sys
p=sys.argv[1]
s=io.open(p,encoding="utf-8").read()
m=re.search(r"^\[nodes\.local-sglang\]\n(?:[^\[]*\n)", s, re.M)
assert m, "node anchor moved"
blk=m.group(0).replace("local-sglang","local-negtest-alias",1)
io.open(p,"w",encoding="utf-8",newline="\n").write(s[:m.end()] + blk + s[m.end():])' "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_node_pool >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_node_pool passed with two nodes on one (endpoint, model, lane)"
    fi
    cp "$backup" "$toml"

    # (2) A lane [dispatch] does not budget must FAIL: the semaphore has no bucket.
    python3 -c 'import io,re,sys
p=sys.argv[1]
s=io.open(p,encoding="utf-8").read()
m=re.search(r"^lane        = \"gpu\".*$", s, re.M)
assert m, "lane anchor moved"
io.open(p,"w",encoding="utf-8",newline="\n").write(
    s[:m.start()] + "lane        = \"negtest-quantum\"" + s[m.end():])' "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_node_pool >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_node_pool passed with a lane [dispatch].lane_priority does not budget"
    fi
    cp "$backup" "$toml"

    # (3) A baked local port must FAIL: no /etc/mios overlay can move it, so the
    # node could never be offloaded to a blade.
    python3 -c 'import io,re,sys
p=sys.argv[1]
s=io.open(p,encoding="utf-8").read()
m=re.search(r"^endpoint    = \"http://localhost:\$\{MIOS_PORT_VLLM\}/v1\"$", s, re.M)
assert m, "endpoint anchor moved"
io.open(p,"w",encoding="utf-8",newline="\n").write(
    s[:m.start()] + "endpoint    = \"http://localhost:8520/v1\"" + s[m.end():])' "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_node_pool >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_node_pool passed with an endpoint an overlay cannot move"
    fi

    mv "$backup" "$toml"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_node_pool >/dev/null 2>&1 \
        || die "check_node_pool failed after restoration"

    log "Test_node_pool negative test passed"
}

test_port_fallbacks() {
    log "Testing check_port_fallbacks"
    local probe="${ROOT}/usr/libexec/mios/mios-negtest-port-probe"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local tbak="${toml}.pfbak"
    cp "$toml" "$tbak"
    _pf_cleanup() { rm -f "$probe"; cp "$tbak" "$toml"; }

    # (1) A stale literal beside a MIOS_PORT_* name must FAIL. Four shipped
    # units pinned exactly this shape, three of them retired ports.
    printf '#!/usr/bin/env python3\nimport os\nP = os.environ.get("MIOS_PORT_AGENT_PIPE", "8640")\n' > "$probe"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_port_fallbacks >/dev/null 2>&1; then
        _pf_cleanup; rm -f "$tbak"
        die "check_port_fallbacks passed with a stale literal beside MIOS_PORT_AGENT_PIPE"
    fi

    # (2) The DOUBLE fallback -- the second literal is the one that runs.
    printf '#!/usr/bin/env python3\nimport os\nP = int(os.environ.get("MIOS_PORT_AGENT_PIPE", "8700") or 8640)\n' > "$probe"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_port_fallbacks >/dev/null 2>&1; then
        _pf_cleanup; rm -f "$tbak"
        die "check_port_fallbacks passed with a stale SECOND literal in a double fallback"
    fi

    # (3) The MIOS_<KEY>_PORT alias spelling, in a file that never says
    # MIOS_PORT_ at all -- the early-out that used to skip it.
    printf '#!/usr/bin/env python3\nimport os\nP = os.environ.get("MIOS_ARBITER_PORT", "8650")\n' > "$probe"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_port_fallbacks >/dev/null 2>&1; then
        _pf_cleanup; rm -f "$tbak"
        die "check_port_fallbacks passed with a stale literal beside the alias spelling"
    fi
    rm -f "$probe"

    # (4) The register only SHRINKS: an entry that no longer reproduces must be
    # removed, not left to rot into decoration.
    python3 -c 'import io,re,sys
p=sys.argv[1]
s=io.open(p,encoding="utf-8").read()
m=re.search(r"^stale_fallbacks = \[\]$", s, re.M)
assert m, "stale_fallbacks register not found"
io.open(p,"w",encoding="utf-8",newline="\n").write(
    s[:m.start()] + "stale_fallbacks = [\"usr/libexec/mios/no-such-file:AGENT_PIPE\"]" + s[m.end():])' "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_port_fallbacks >/dev/null 2>&1; then
        _pf_cleanup; rm -f "$tbak"
        die "check_port_fallbacks passed with a register entry that no longer reproduces"
    fi

    _pf_cleanup
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_port_fallbacks >/dev/null 2>&1 \
        || { rm -f "$tbak"; die "check_port_fallbacks failed after restoration"; }
    rm -f "$tbak"

    log "Test_port_fallbacks negative test passed"
}

test_role_ssot() {
    log "Testing check_role_ssot"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local unit="${ROOT}/usr/lib/systemd/system/mios-hybrid.target"
    local lib="${ROOT}/usr/lib/mios/blade.sh"
    local tbak="${toml}.rolebak" ubak="${unit}.rolebak" lbak="${lib}.rolebak"
    cp "$toml" "$tbak"; cp "$unit" "$ubak"; cp "$lib" "$lbak"
    _role_restore() { cp "$tbak" "$toml"; cp "$ubak" "$unit"; cp "$lbak" "$lib"; }

    # (1) A [blade].type that names no archetype must FAIL. This is the exact
    # value the retired [profile].role shipped with.
    sed -i '0,/^type = "hybrid"$/s//type = "developer"/' "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_role_ssot >/dev/null 2>&1; then
        _role_restore; rm -f "$tbak" "$ubak" "$lbak"
        die "check_role_ssot passed with [blade].type naming no archetype"
    fi
    cp "$tbak" "$toml"

    # (2) A resurrected [profile] must FAIL -- one canonical name (Law 9).
    printf '\n[profile]\nrole = "developer"\n' >> "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_role_ssot >/dev/null 2>&1; then
        _role_restore; rm -f "$tbak" "$ubak" "$lbak"
        die "check_role_ssot passed with [profile].role resurrected"
    fi
    cp "$tbak" "$toml"

    # (3) An incomplete conflict graph must FAIL. The DEFAULT role target
    # shipped conflicting with NOTHING, so switching away never stopped it.
    sed -i '/^Conflicts=/d' "$unit"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_role_ssot >/dev/null 2>&1; then
        _role_restore; rm -f "$tbak" "$ubak" "$lbak"
        die "check_role_ssot passed with a role target conflicting with nothing"
    fi
    cp "$ubak" "$unit"

    # (4) An Alias= systemd cannot install must FAIL -- two role targets shipped
    # Alias=default.target.mios-<role>, whose suffix no unit name can match.
    sed -i '$a Alias=default.target.mios-hybrid' "$unit"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_role_ssot >/dev/null 2>&1; then
        _role_restore; rm -f "$tbak" "$ubak" "$lbak"
        die "check_role_ssot passed with an Alias= whose suffix is not the unit's"
    fi
    cp "$ubak" "$unit"

    # (5) An archetype name spelled as a literal in the blade code must FAIL:
    # the archetype table is [blade.archetypes], not a case statement.
    sed -i '$a case "$ROLE" in endpoint) TARGET=x ;; esac' "$lib"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_role_ssot >/dev/null 2>&1; then
        _role_restore; rm -f "$tbak" "$ubak" "$lbak"
        die "check_role_ssot passed with an archetype hardcoded in blade.sh"
    fi

    cp "$lbak" "$lib"

    # (6) A capability every archetype grants and NO unit requires must FAIL:
    # `controller` was in exactly that state, so the controller archetype
    # behaved identically to headless.
    python3 -c 'import io,re,sys
p=sys.argv[1]
s=io.open(p,encoding="utf-8").read()
m=re.search(r"^endpoint   = \[\]$", s, re.M)
assert m, "archetype anchor moved"
io.open(p,"w",encoding="utf-8",newline="\n").write(
    s[:m.start()] + "endpoint   = []\nnegtest    = [\"negtest-decorative-cap\"]" + s[m.end():])' "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_role_ssot >/dev/null 2>&1; then
        _role_restore; rm -f "$tbak" "$ubak" "$lbak"
        die "check_role_ssot passed with a capability no unit requires"
    fi

    _role_restore
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_role_ssot >/dev/null 2>&1 \
        || { rm -f "$tbak" "$ubak" "$lbak"; die "check_role_ssot failed after restoration"; }
    rm -f "$tbak" "$ubak" "$lbak"

    log "Test_role_ssot negative test passed"
}

test_blade_karg() {
    log "Testing check_blade_karg"
    local karg="${ROOT}/usr/lib/bootc/kargs.d/05-mios-blade.toml"
    local backup="${karg}.negbak"
    cp "$karg" "$backup"

    # (1) A hand-edited karg must FAIL -- that is what makes this a projection
    # rather than a file someone tweaks and nobody notices.
    sed -i 's/mios\.blade=[a-z-]*/mios.blade=negtesthandedited/' "$karg"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_blade_karg >/dev/null 2>&1; then
        mv "$backup" "$karg"
        die "check_blade_karg passed on a hand-edited karg"
    fi
    cp "$backup" "$karg"

    # (2) A MISSING projection must FAIL rather than being read as "nothing to
    # check" -- the file's absence is exactly the state this task started in.
    rm -f "$karg"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_blade_karg >/dev/null 2>&1; then
        mv "$backup" "$karg"
        die "check_blade_karg passed with the projection absent"
    fi

    mv "$backup" "$karg"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_blade_karg >/dev/null 2>&1 \
        || die "check_blade_karg failed after restoration"

    log "Test_blade_karg negative test passed"
}

test_blade_coverage() {
    log "Testing check_blade_coverage"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local backup="${toml}.negbak"
    cp "$toml" "$backup"

    # (1) A container classified NEITHER way must FAIL -- that is the state the
    # whole activation axis was in before this gate existed. Sabotage the LIVE
    # mechanism: drop a container's [blade.requires] line while the ungated
    # register is empty, so it is gated by nothing and registered nowhere.
    python3 -c 'import io,re,sys
p=sys.argv[1]
s=io.open(p,encoding="utf-8").read()
pat=re.compile(r"^mios-searxng\s*=\s*\[[^\]]*\]\n", re.M)
assert len(pat.findall(s))==1,"blade.requires anchor moved"
io.open(p,"w",encoding="utf-8",newline="\n").write(pat.sub("", s, count=1))' "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_blade_coverage >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_blade_coverage passed with a container classified neither way"
    fi
    cp "$backup" "$toml"

    # (2) A capability no archetype grants must FAIL: nothing could activate it,
    # so the unit would be dead on every blade type.
    python3 -c 'import io,sys
p=sys.argv[1]
import re
s=io.open(p,encoding="utf-8").read()
pat=re.compile(r"^mios-llm-heavy\s*=\s*\[[^\]]*\]", re.M)
assert len(pat.findall(s))==1,"requires anchor moved"
io.open(p,"w",encoding="utf-8",newline="\n").write(
    pat.sub("mios-llm-heavy     = [\"mios-negtest-uncapability\"]", s, count=1))' "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_blade_coverage >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_blade_coverage passed with a capability no archetype grants"
    fi

    cp "$backup" "$toml"

    # (3) A seat-side unit whose port only a GATED unit dials must FAIL. The
    # coupling is an ADDRESS, so the dependency walk cannot see it: the second
    # CDP browser sat seat-side while its only client was gated off.
    python3 -c 'import io,re,sys
p=sys.argv[1]
s=io.open(p,encoding="utf-8").read()
m=re.search(r"^mios-hermes-browser-worker = \[[^\]]*\][^\n]*\n", s, re.M)
assert m, "worker-browser gate anchor moved"
s = s[:m.start()] + s[m.end():]
m2 = re.search(r'"'"'^  "mios-hermes-browser",[^\n]*\n'"'"', s, re.M)
assert m2, "seat_side anchor moved"
io.open(p,"w",encoding="utf-8",newline="\n").write(
    s[:m2.end()] + "  \"mios-hermes-browser-worker\",\n" + s[m2.end():])' "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_blade_coverage >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_blade_coverage passed with a seat-side unit only a gated unit dials"
    fi

    mv "$backup" "$toml"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_blade_coverage >/dev/null 2>&1 \
        || die "check_blade_coverage failed after restoration"

    log "Test_blade_coverage negative test passed"
}

test_ports_bound() {
    log "Testing check_ports_bound"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local backup="${toml}.negbak"
    cp "$toml" "$backup"

    # Both cases sabotage the LIVE mechanism rather than a literal copy of the
    # register's contents: anchoring on those made this test go inert the moment
    # a key drained out of it.

    # (1) A newly allocated port that nothing references and nothing registers
    # must FAIL -- otherwise the collision checker guards a number nothing binds.
    python3 -c 'import io,re,sys
p=sys.argv[1]
s=io.open(p,encoding="utf-8").read()
m=re.search(r"^\[ports\]\n", s, re.M)
assert m, "flat [ports] table not found"
io.open(p,"w",encoding="utf-8",newline="\n").write(
    s[:m.end()] + "negtest_unbound_port = 8599\n" + s[m.end():])' "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ports_bound >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_ports_bound passed with an allocated port nothing references"
    fi
    cp "$backup" "$toml"

    # (2) The register must only SHRINK: a port that IS referenced may not sit
    # in it, or the list silently rots into decoration.
    python3 -c 'import io,re,sys
p=sys.argv[1]
s=io.open(p,encoding="utf-8").read()
m=re.search(r"^unbound = \[", s, re.M)
assert m, "unbound register not found"
io.open(p,"w",encoding="utf-8",newline="\n").write(
    s[:m.end()] + "\"guacd\", " + s[m.end():])' "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ports_bound >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_ports_bound passed with a REFERENCED port still in the unbound register"
    fi

    mv "$backup" "$toml"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ports_bound >/dev/null 2>&1 \
        || die "check_ports_bound failed after restoration"

    log "Test_ports_bound negative test passed"
}

test_service_urls() {
    log "Testing check_service_urls"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local backup="${toml}.negbak"
    local reg_tail='"sglang", "ssh", "ttyd_bash", "ttyd_powershell", "vllm",'
    local reg_head='  "adguard_dns", "adguard_ui", "agent_pipe", "arbiter", "ceph_dashboard",'
    cp "$toml" "$backup"

    # (1) A port in NEITHER [urls] nor the register must FAIL. Dropping an entry
    # from the shrink-only register is exactly how a real regression looks.
    python3 -c 'import io,sys
p,old,new=sys.argv[1],sys.argv[2],sys.argv[3]
s=io.open(p,encoding="utf-8").read()
assert s.count(old)==1,"non_addressable tail anchor moved"
io.open(p,"w",encoding="utf-8",newline="\n").write(s.replace(old,new))' \
        "$toml" "$reg_tail" '"sglang", "ssh", "ttyd_bash", "ttyd_powershell",'
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_service_urls >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_service_urls passed with a port in neither [urls] nor the register"
    fi
    cp "$backup" "$toml"

    # (2) A register entry naming a port that does not exist must FAIL -- a stale
    # register is how these lists rot into decoration. The bogus name is
    # ASSEMBLED so this file never contains the literal it searches for.
    python3 -c 'import io,sys
p,old=sys.argv[1],sys.argv[2]
ghost="mios_negtest"+"_ghost_port"
s=io.open(p,encoding="utf-8").read()
assert s.count(old)==1,"register head anchor moved"
io.open(p,"w",encoding="utf-8",newline="\n").write(
    s.replace(old, old+"\n  \""+ghost+"\","))' "$toml" "$reg_head"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_service_urls >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_service_urls passed with a register entry naming no real port"
    fi

    cp "$backup" "$toml"

    # An inter-service scheme in [urls] must FAIL: the table is the
    # browser-openable surface, and a postgresql:// DSN made it mean two things.
    python3 -c 'import io,re,sys
p=sys.argv[1]
s=io.open(p,encoding="utf-8").read()
m=re.search(r"^\[urls\]\n", s, re.M)
assert m, "[urls] table not found"
io.open(p,"w",encoding="utf-8",newline="\n").write(
    s[:m.end()] + "negtest_dsn        = \"postgresql://u@localhost:5432/d\"\n" + s[m.end():])' "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_service_urls >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_service_urls passed with a non-browser scheme in [urls]"
    fi

    cp "$backup" "$toml"

    # An address with a BARE port must FAIL: an /etc/mios overlay cannot move a
    # baked number, so the service could never be offloaded.
    python3 -c 'import io,re,sys
p=sys.argv[1]
s=io.open(p,encoding="utf-8").read()
m=re.search(r"^\[urls\]\n", s, re.M)
assert m, "[urls] table not found"
io.open(p,"w",encoding="utf-8",newline="\n").write(
    s[:m.start()] + "[negtest_bare]\nendpoint = \"http://localhost:8500/v1\"\n\n" + s[m.start():])' "$toml"
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_service_urls >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_service_urls passed with an address an overlay cannot move"
    fi

    mv "$backup" "$toml"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_service_urls >/dev/null 2>&1 \
        || die "check_service_urls failed after restoration"

    log "Test_service_urls negative test passed"
}

test_greenboot() {
    log "Testing check_greenboot"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local backup="${toml}.negbak"
    cp "$toml" "$backup"

    # (1) A critical service with no health-check script anywhere must FAIL.
    # The bogus name is ASSEMBLED so this file never contains the literal --
    # the gate scans required.d for unit references, and a spelled-out name
    # here could not reach it, but keeping the idiom keeps the test honest.
    local bogus="mios-negtest""-absent"
    python3 - "$toml" "$bogus" <<'PY'
import io, sys
p, bogus = sys.argv[1], sys.argv[2]
s = io.open(p, encoding="utf-8").read()
old = 'critical_services = ["agent-pipe", "llm-light", "pgvector", "hermes"]'
assert s.count(old) == 1, "critical_services anchor moved"
io.open(p, "w", encoding="utf-8", newline="\n").write(
    s.replace(old, 'critical_services = ["agent-pipe", "llm-light", "pgvector", "hermes", "%s"]' % bogus))
PY
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_greenboot >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_greenboot passed despite a critical service with no health-check script"
    fi
    cp "$backup" "$toml"

    # (2) An EMPTY critical set must FAIL rather than pass vacuously.
    python3 - "$toml" <<'PY'
import io, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
old = 'critical_services = ["agent-pipe", "llm-light", "pgvector", "hermes"]'
assert s.count(old) == 1, "critical_services anchor moved"
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, 'critical_services = []'))
PY
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_greenboot >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_greenboot passed over an EMPTY critical set (vacuous success)"
    fi

    mv "$backup" "$toml"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_greenboot >/dev/null 2>&1 \
        || die "check_greenboot failed after restoration"

    log "Test_greenboot negative test passed"
}

test_adr_index() {
    log "Testing check_adr_index"
    local idx="${ROOT}/ADR.md"
    local backup="${idx}.negbak"
    cp "$idx" "$backup"

    printf '\n| 9999 | hand-edited row | accepted | | | |\n' >> "$idx"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_adr_index >/dev/null 2>&1; then
        mv "$backup" "$idx"
        die "check_adr_index passed despite a hand-edited ADR.md"
    fi

    mv "$backup" "$idx"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_adr_index >/dev/null 2>&1 \
        || die "check_adr_index failed after restoration"

    log "Test_adr_index negative test passed"
}

test_schema_consumers() {
    log "Testing check_schema_consumers"
    local sql="${ROOT}/usr/share/mios/postgres/schema-init.sql"
    local backup="${sql}.negbak"
    cp "$sql" "$backup"

    # A brand-new table nothing reads or writes must fail the gate.
    # The name is ASSEMBLED so this file never contains the literal: the gate
    # counts any non-doc file naming a table as a consumer, so a spelled-out
    # sabotage name here would make the gate "find" one and the test vacuous.
    local orphan="mios_negtest""_orphan_tbl"
    printf '\nCREATE TABLE IF NOT EXISTS %s (id bigint);\n' "$orphan" >> "$sql"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_schema_consumers >/dev/null 2>&1; then
        mv "$backup" "$sql"
        die "check_schema_consumers passed despite a table with no reader or writer"
    fi

    mv "$backup" "$sql"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_schema_consumers >/dev/null 2>&1 \
        || die "check_schema_consumers failed after restoration"

    log "Test_schema_consumers negative test passed"
}

test_tasks_status_parity() {
    log "Testing check_tasks_status_parity"
    local tasks="${ROOT}/TASKS.md"
    local backup="${tasks}.negbak"
    cp "$tasks" "$backup"

    # Flip ONE summary-table cell away from what that task's own section says.
    # The sabotage targets the first row whose status the gate can resolve, so
    # the test does not depend on any particular task id surviving edits.
    local tid
    tid="$(grep -m1 -oE '^\| T-[0-9]+ \| P[0-9] \| (done|done-by-code|planned|in-progress) \|' "$tasks" \
            | awk '{print $2}')"
    if [[ -z "$tid" ]]; then
        mv "$backup" "$tasks"
        die "test_tasks_status_parity found no resolvable summary row to sabotage"
    fi
    sed -i "0,/^| ${tid} | P[0-9] | [a-z/-]* |/s//| ${tid} | P9 | pending |/" "$tasks"
    sed -i "0,/^| ${tid} | P9 | pending |/s/| P9 |/| P1 |/" "$tasks"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_tasks_status_parity >/dev/null 2>&1; then
        mv "$backup" "$tasks"
        die "check_tasks_status_parity passed while the summary table contradicted ${tid}'s own Status line"
    fi
    mv "$backup" "$tasks"

    # The '?' placeholder must fail too -- it is how the drift hid for 28 rows.
    cp "$tasks" "$backup"
    sed -i "0,/^| ${tid} | P[0-9] | [a-z/-]* |/s//| ${tid} | P1 | ? |/" "$tasks"
    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_tasks_status_parity >/dev/null 2>&1; then
        mv "$backup" "$tasks"
        die "check_tasks_status_parity accepted a '?' placeholder for ${tid}"
    fi
    mv "$backup" "$tasks"

    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_tasks_status_parity >/dev/null 2>&1 \
        || die "check_tasks_status_parity failed after restoration"

    log "Test_tasks_status_parity negative test passed"
}

test_container_names() {
    log "Testing check_container_names"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local backup="${toml}.cnbak"
    cp "$toml" "$backup"

    # Drop ONE ContainerName from the SSOT: Quadlet would then name that
    # container systemd-<unit>, which no `systemctl` name matches.
    python3 - "$toml" <<'PYEOF'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
m = re.search(r'^ContainerName = "[^"]+"\n', s, re.M)
assert m, "no ContainerName to remove"
open(p, "w", encoding="utf-8").write(s[:m.start()] + s[m.end():])
PYEOF

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_container_names >/dev/null 2>&1; then
        mv "$backup" "$toml"
        die "check_container_names passed while a Quadlet declared no ContainerName"
    fi
    mv "$backup" "$toml"

    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_container_names >/dev/null 2>&1 \
        || die "check_container_names failed after restoration"

    log "Test_container_names negative test passed"
}

test_firstboot_provisioners() {
    log "Testing check_firstboot_provisioners"
    local unit="${ROOT}/usr/lib/systemd/system/mios-models-firstboot.service"
    local backup="${unit}.negbak"
    cp "$unit" "$backup"

    # Break the sentinel gate: point it at a path the fetcher never writes, so
    # the oneshot would run on every boot forever.
    sed -i 's#^ConditionPathExists=.*#ConditionPathExists=!/var/lib/mios/.not-a-real-sentinel#' "$unit"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_provisioners >/dev/null 2>&1; then
        mv "$backup" "$unit"
        die "check_firstboot_provisioners passed despite a sentinel the fetcher never writes"
    fi

    mv "$backup" "$unit"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_provisioners >/dev/null 2>&1 \
        || die "check_firstboot_provisioners failed after restoration"

    log "Test_firstboot_provisioners negative test passed"
}

test_module_length() {
    log "Testing check_module_length"
    # Two directories deep on purpose: the former -maxdepth 1 body could not
    # see a nested module, which is where every real one lives.
    local dir="${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/routing"
    mkdir -p "$dir"
    local dummy_file="${dir}/test_dummy_length.py"

    seq 1 801 > "$dummy_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_module_length >/dev/null 2>&1; then
        rm -f "$dummy_file"
        die "Check_module_length passed despite 801-line file"
    fi

    rm -f "$dummy_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_module_length >/dev/null 2>&1 \
        || die "Check_module_length failed after restoration"
    
    log "Test_module_length negative test passed"
}

test_vendored_assets_non_stub() {
    log "Testing check_vendored_assets_non_stub"
    local stub_file="${ROOT}/usr/share/mios/vendored/k3s/fake_stub.tmp"
    echo "Stub" > "$stub_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_vendored_assets_non_stub >/dev/null 2>&1; then
        rm -f "$stub_file"
        die "Check_vendored_assets_non_stub passed despite injected stub file"
    fi

    rm -f "$stub_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_vendored_assets_non_stub >/dev/null 2>&1 \
        || die "Check_vendored_assets_non_stub failed after restoration"
    log "Test_vendored_assets_non_stub negative test passed"
}

test_resolved_env_lossless() {
    log "Testing check_resolved_env_lossless"
    local base_file="${ROOT}/usr/share/mios/reference/env-baseline.txt"
    if [[ ! -f "$base_file" ]]; then
        log "Env-baseline.txt absent"
        return 0
    fi
    local backup_tmp; backup_tmp="$(mktemp)"
    cp "$base_file" "$backup_tmp"
    echo "MIOS_INJECTED_DUMMY_KEY=injected_val" >> "$base_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_resolved_env_lossless >/dev/null 2>&1; then
        cp "$backup_tmp" "$base_file"
        rm -f "$backup_tmp"
        die "Check_resolved_env_lossless passed despite injected baseline drift"
    fi

    cp "$backup_tmp" "$base_file"
    rm -f "$backup_tmp"
    local lossless_out
    if ! lossless_out=$(MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_resolved_env_lossless 2>&1); then
        # The check prints the actual +/- diff; swallowing it makes an
        # environment-dependent baseline impossible to diagnose from CI.
        printf '%s\n' "$lossless_out" | tail -n 25 >&2
        die "Check_resolved_env_lossless failed after restoration"
    fi
    log "Test_resolved_env_lossless negative test passed"
}

test_no_duplicate_value_key() {
    log "Testing check_no_duplicate_value_key"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_no_duplicate_value_key >/dev/null 2>&1 \
        || die "Check_no_duplicate_value_key failed"
    log "Test_no_duplicate_value_key passed"
}

test_no_hardcoded_ssot_literal() {
    log "Testing check_no_hardcoded_ssot_literal"
    local inj_file="${ROOT}/automation/temp_inj_test_hardcode.sh"
    echo 'echo "hardcoded fedora-99"' > "$inj_file"
    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_no_hardcoded_ssot_literal >/dev/null 2>&1; then
        rm -f "$inj_file"
        die "check_no_hardcoded_ssot_literal passed despite injected hardcoded fedora-99 literal"
    fi
    rm -f "$inj_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_no_hardcoded_ssot_literal >/dev/null 2>&1 \
        || die "Check_no_hardcoded_ssot_literal failed after restoration"
    log "Test_no_hardcoded_ssot_literal passed"
}

test_pipeline_numbering() {
    log "Testing check_pipeline_numbering"
    local f="${ROOT}/automation/98-drift-checks.sh"
    local backup; backup="$(mktemp)"
    cp "$f" "$backup"
    printf '\n# NEG-TEST [98-drift-checks]   (99) injected colliding label\n' >> "$f"
    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "$f" check_pipeline_numbering >/dev/null 2>&1; then
        cp "$backup" "$f"; rm -f "$backup"
        die "Check_pipeline_numbering passed despite an injected check label"
    fi
    cp "$backup" "$f"; rm -f "$backup"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "$f" check_pipeline_numbering >/dev/null 2>&1 \
        || die "Check_pipeline_numbering failed after restoration"
    log "Test_pipeline_numbering negative test passed"
}

test_value_aliases() {
    log "Testing check_value_aliases"
    local f="${ROOT}/usr/share/mios/reference/value-aliases.tsv"
    [[ -f "$f" ]] || { log "Value-aliases.tsv absent"; return 0; }
    local backup; backup="$(mktemp)"
    cp "$f" "$backup"
    printf 'MIOS_PG_USER\tMIOS_PGVECTOR_USER\tderive\n' >> "$f"
    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_value_aliases >/dev/null 2>&1; then
        cp "$backup" "$f"; rm -f "$backup"
        die "Check_value_aliases passed despite a derive-pair with divergent values"
    fi
    cp "$backup" "$f"; rm -f "$backup"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_value_aliases >/dev/null 2>&1 \
        || die "Check_value_aliases failed after restoration"
    log "Test_value_aliases negative test passed"
}

test_bash_phase_ratchet() {
    log "Testing check_bash_phase_ratchet"
    local dummy_script="${ROOT}/automation/99-dummy-test-phase.sh"
    touch "$dummy_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bash_phase_ratchet >/dev/null 2>&1; then
        rm -f "$dummy_script"
        die "Check_bash_phase_ratchet passed despite extra bash phase script exceeding ratchet baseline"
    fi

    rm -f "$dummy_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bash_phase_ratchet >/dev/null 2>&1 \
        || die "Check_bash_phase_ratchet failed after restoration"
    log "Test_bash_phase_ratchet negative test passed"
}

test_check_no_silent_tool_skips() {
    log "Testing check_no_silent_tool_skips..."
    local dummy="$ROOT/automation/lint-dummy-skip-test.sh"
    echo '#!/bin/bash' > "$dummy"
    echo 'command -v non_existent_tool || return 0' >> "$dummy"
    chmod +x "$dummy"

    if MIOS_DRIFT_REQUIRE_TOOLS=1 bash "$ROOT/automation/98-drift-checks.sh" check_no_silent_tool_skips >/dev/null 2>&1; then
        rm -f "$dummy"
        die "check_no_silent_tool_skips failed to detect unhandled silent tool skip"
    fi
    rm -f "$dummy"
    log "check_no_silent_tool_skips correctly caught unhandled silent tool skip"
}

test_check_negatives_are_effective() {
    log "Testing check_negatives_are_effective..."
    local neg_sh="${ROOT}/tests/drift-gate-negatives.sh"
    local bak; bak="$(mktemp)"
    cp "$neg_sh" "$bak"

    # Test 1: Inject a function that only logs a check name (no gate call execution)
    {
        echo "test_fake_ineffective_log_only() {"
        echo "    log \"Testing check_version_ssot\""
        echo "    die \"Fake failure assertion\""
        echo "}"
    } >> "$neg_sh"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_negatives_are_effective >/dev/null 2>&1; then
        cp "$bak" "$neg_sh"; rm -f "$bak"
        die "check_negatives_are_effective passed despite logging-only fake negative test"
    fi

    # Test 2: Inject a function longer than 1500 chars with valid gate call to prove full scanning
    cp "$bak" "$neg_sh"
    {
        echo "test_fake_long_effective() {"
        echo "    log \"Testing check_version_ssot...\""
        for _ in {1..50}; do
            echo "    # Padding line to ensure function body exceeds 1500 characters in length"
        done
        echo "    if ! _neg_gate check_version_ssot; then"
        echo "        die \"check_version_ssot failed\""
        echo "    fi"
        echo "}"
    } >> "$neg_sh"

    if ! MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_negatives_are_effective >/dev/null 2>&1; then
        cp "$bak" "$neg_sh"; rm -f "$bak"
        die "check_negatives_are_effective failed on long function with valid gate call (>1500 chars)"
    fi

    cp "$bak" "$neg_sh"; rm -f "$bak"
    if ! MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_negatives_are_effective >/dev/null 2>&1; then
        die "check_negatives_are_effective failed on HEAD after restoration"
    fi
    log "check_negatives_are_effective negative test passed"
}

test_pipefail_grep_lint() {
    log "Testing check_pipefail_grep_lint..."
    local neg_sh="${ROOT}/tests/drift-gate-negatives.sh"
    local bak; bak="$(mktemp)"
    cp "$neg_sh" "$bak"

    {
        echo "test_fake_pipefail_grep() {"
        echo "    cat /dev/null | grep -q \"foo\" || die \"failed\""
        echo "}"
    } >> "$neg_sh"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_pipefail_grep_lint >/dev/null 2>&1; then
        cp "$bak" "$neg_sh"; rm -f "$bak"
        die "check_pipefail_grep_lint passed despite injected piped grep reading from non-echo/printf"
    fi

    cp "$bak" "$neg_sh"; rm -f "$bak"
    if ! MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_pipefail_grep_lint >/dev/null 2>&1; then
        die "check_pipefail_grep_lint failed on HEAD after restoration"
    fi
    log "check_pipefail_grep_lint negative test passed"
}

test_check_skip_list_covered() {
    log "Testing check_skip_list_covered..."
    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_skip_list_covered >/dev/null 2>&1; then
        log "check_skip_list_covered passed on HEAD"
    else
        die "check_skip_list_covered failed on HEAD"
    fi
}

test_ai_manifests_fresh() {
    log "Testing check_ai_manifests_fresh"
    local mf="${ROOT}/tools/manifest.json"
    local backup; backup="$(mktemp)"
    cp "$mf" "$backup"
    echo '{"drift":"injected"}' > "$mf"
    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ai_manifests_fresh >/dev/null 2>&1; then
        cp "$backup" "$mf"; rm -f "$backup"
        die "check_ai_manifests_fresh passed despite injected manifest drift"
    fi
    cp "$backup" "$mf"; rm -f "$backup"
    local restored_out
    if ! restored_out=$(MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ai_manifests_fresh 2>&1); then
        printf '%s\n' "$restored_out" | tail -n 15 >&2
        die "check_ai_manifests_fresh failed after restoration"
    fi
    log "test_ai_manifests_fresh passed"
}

test_unpinned_runtime_fetches() {
    log "Testing check_unpinned_runtime_fetches"
    local probe="${ROOT}/usr/share/mios/windows/negative-probe-fetch.ps1"
    # A runtime download with no SHA-256 verification (ADR-0003).
    printf 'Invoke-WebRequest -Uri "https://example.com/x.zip" -OutFile x.zip\n' > "$probe"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_unpinned_runtime_fetches >/dev/null 2>&1; then
        rm -f "$probe"
        die "check_unpinned_runtime_fetches passed despite an unverified download"
    fi
    rm -f "$probe"

    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_unpinned_runtime_fetches >/dev/null 2>&1 \
        || die "check_unpinned_runtime_fetches failed after restoration"
    log "test_unpinned_runtime_fetches passed"
}

test_windows_exe_provenance() {
    log "Testing check_windows_exe_provenance"
    local probe="${ROOT}/usr/share/mios/windows/negative-probe-tool.exe"
    # A shipped .exe with no corresponding .cs source to build it from.
    printf 'MZ-not-a-real-binary\n' > "$probe"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_windows_exe_provenance >/dev/null 2>&1; then
        rm -f "$probe"
        die "check_windows_exe_provenance passed despite a source-less .exe"
    fi
    rm -f "$probe"

    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_windows_exe_provenance >/dev/null 2>&1 \
        || die "check_windows_exe_provenance failed after restoration"
    log "test_windows_exe_provenance passed"
}

test_ps_redirectors() {
    log "Testing check_ps_redirectors"
    # The check asserts the thin redirector .ps1 entry points stay thin.
    # Pick whichever one this tree actually has.
    local target=""
    local f
    for f in install.ps1 mios-build-local.ps1 run-pipeline.ps1; do
        if [ -f "${ROOT}/$f" ]; then target="${ROOT}/$f"; break; fi
    done
    if [ -z "$target" ]; then
        log "no redirector present -- skipping test_ps_redirectors"
        return 0
    fi

    local backup; backup="$(mktemp)"
    cp "$target" "$backup"
    # Fatten it well past the line ceiling.
    for _ in $(seq 1 120); do echo "# negative-test filler line" >> "$target"; done

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ps_redirectors >/dev/null 2>&1; then
        cp "$backup" "$target"; rm -f "$backup"
        die "check_ps_redirectors passed despite an over-long redirector"
    fi
    cp "$backup" "$target"; rm -f "$backup"

    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ps_redirectors >/dev/null 2>&1 \
        || die "check_ps_redirectors failed after restoration"
    log "test_ps_redirectors passed"
}

test_cargo_deny() {
    log "Testing check_cargo_deny"
    local policy="${ROOT}/tools/native/deny.toml"
    local backup; backup="$(mktemp)"
    cp "$policy" "$backup"
    rm -f "$policy"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cargo_deny >/dev/null 2>&1; then
        cp "$backup" "$policy"; rm -f "$backup"
        die "check_cargo_deny passed despite a missing supply-chain policy"
    fi
    cp "$backup" "$policy"; rm -f "$backup"

    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cargo_deny >/dev/null 2>&1 \
        || die "check_cargo_deny failed after restoration"
    log "test_cargo_deny passed"
}

test_powershell_parse() {
    log "Testing check_powershell_parse"

    # Check if we can actually run the parser, skip if not available
    local dry_run
    dry_run=$(bash "${ROOT}/automation/lint-powershell.sh" 2>&1 || true)
    if echo "$dry_run" | grep -q "skipping AST parse-gate"; then
        log "powershell missing or un-executable, skipping negative test"
        return 0
    fi

    local bad="${ROOT}/automation/lint-ps-negative-probe.ps1"
    # An unterminated block is an AST parse error in any PowerShell version.
    printf 'function Broken {\n' > "$bad"
    # lint-powershell.sh enumerates `git ls-files "*.ps1"`, so an UNTRACKED
    # probe is invisible and the check would pass for the wrong reason.
    # `add -N` records intent-to-add, which is enough for ls-files.
    git -C "$ROOT" add -N "$bad" >/dev/null 2>&1 || true

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_powershell_parse >/dev/null 2>&1; then
        git -C "$ROOT" rm --cached -q --force "$bad" >/dev/null 2>&1 || true
        rm -f "$bad"
        die "check_powershell_parse passed despite an unparseable .ps1"
    fi
    git -C "$ROOT" rm --cached -q --force "$bad" >/dev/null 2>&1 || true
    rm -f "$bad"

    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_powershell_parse >/dev/null 2>&1 \
        || die "check_powershell_parse failed after restoration"
    log "test_powershell_parse passed"
}

test_ports_category_schema() {
    log "Testing check_ports_category_schema"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local backup; backup="$(mktemp)"
    cp "$toml" "$backup"

    # Collide two categories by dragging one band on top of another.
    python3 - "$toml" <<'PY'
import re, sys
p = sys.argv[1]
with open(p, "r", encoding="utf-8", newline="") as fh:
    text = fh.read()
# line-ending agnostic: the file is CRLF, so a literal "\n" match silently no-ops
new, n = re.subn(r"(\[ports\.categories\.webtools\]\s*\r?\n\s*base\s*=\s*)8800",
                 r"\g<1>8700", text, count=1)
if n != 1:
    sys.exit("negative-test injection did not apply")
with open(p, "w", encoding="utf-8", newline="") as fh:
    fh.write(new)
PY

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ports_category_schema >/dev/null 2>&1; then
        cp "$backup" "$toml"; rm -f "$backup"
        die "check_ports_category_schema passed despite an injected category band collision"
    fi
    cp "$backup" "$toml"; rm -f "$backup"

    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ports_category_schema >/dev/null 2>&1 \
        || die "check_ports_category_schema failed after restoration"
    log "test_ports_category_schema passed"
}

test_globals_generated() {
    log "Testing check_globals_generated"
    local target="${ROOT}/automation/lib/globals.sh"
    local backup; backup="$(mktemp)"
    cp "$target" "$backup"

    # Hand-edit a generated constant -- exactly what the gate exists to catch.
    printf '\n[ -n "${MIOS_INJECTED_DRIFT+x}" ] || MIOS_INJECTED_DRIFT=1\n' >> "$target"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_globals_generated >/dev/null 2>&1; then
        cp "$backup" "$target"; rm -f "$backup"
        die "check_globals_generated passed despite a hand-edited generated resolver"
    fi
    cp "$backup" "$target"; rm -f "$backup"

    local restored_out
    if ! restored_out=$(MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_globals_generated 2>&1); then
        printf '%s\n' "$restored_out" | tail -n 10 >&2
        # show the first divergent line so CI names the culprit
        ( cd "$ROOT" && python3 tools/render-globals.py >/dev/null 2>&1 \
          && git --no-pager diff --unified=0 -- automation/lib/globals.sh automation/lib/globals.ps1 \
             | head -n 20 ) >&2 || true
        die "check_globals_generated failed after restoration"
    fi
    log "test_globals_generated passed"
}

_neg_gate() {
    # REQUIRE_TOOLS is forwarded deliberately: checks that shell out to a built
    # binary choose between "skip" and "fail" on it, so a test that cannot set
    # it cannot exercise the failing path -- the path that matters.
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" \
    MIOS_DRIFT_ROOT="$ROOT" \
    MIOS_DRIFT_REQUIRE_TOOLS="${MIOS_DRIFT_REQUIRE_TOOLS:-0}" \
        bash "${ROOT}/automation/98-drift-checks.sh" "$1" >/dev/null 2>&1
}

test_fleet_safety() {
    log "Testing check_fleet_safety"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local bak="${toml}.fleetbak"
    cp "$toml" "$bak"

    # Drop an accepted hazard the detector still reproduces. The register is
    # shrink-only by RETIREMENT -- the detector stops finding it -- not by
    # editing the list, so removing a live entry must fail.
    python3 - "$toml" <<'PYEOF'
import sys
p = sys.argv[1]
with open(p, "r", encoding="utf-8", newline="") as fh:
    t = fh.read()
t = t.replace('  "pacemaker-unfenced",\n', "", 1)
with open(p, "w", encoding="utf-8", newline="") as fh:
    fh.write(t)
PYEOF

    if _neg_gate check_fleet_safety; then
        cp "$bak" "$toml" && rm -f "$bak"
        die "check_fleet_safety passed with a live hazard missing from the register"
    fi

    cp "$bak" "$toml" && rm -f "$bak"
    _neg_gate check_fleet_safety || die "check_fleet_safety failed after restoration"
    log "check_fleet_safety negative test passed"
}

test_neg_gate_harness() {
    log "Testing the _neg_gate harness itself"
    _neg_gate check_gate_registry         || die "_neg_gate returned non-zero for a check that passes"
    if _neg_gate mios_negtest_no_such_check_exists; then
        die "_neg_gate returned zero for a check that does not exist"
    fi
    log "_neg_gate harness verified in both directions"
}

test_adhoc_toml_parsers() {
    log "Testing check_adhoc_toml_parsers"
    local probe="${ROOT}/tests/mios-negtest-adhoc-toml.ps1"
    cat > "$probe" <<'PS1'
# negative-test probe: a hand-rolled TOML reader, which the gate must reject
$raw = Get-Content -Raw 'mios.toml'
if ($raw -match '(?s)\[ports\](.*)') { $ports = $Matches[1] }
PS1
    if _neg_gate check_adhoc_toml_parsers; then
        rm -f "$probe"
        die "check_adhoc_toml_parsers passed despite a hand-rolled TOML parser"
    fi
    rm -f "$probe"
    _neg_gate check_adhoc_toml_parsers \
        || die "check_adhoc_toml_parsers failed after restoration"
    log "check_adhoc_toml_parsers negative test passed"
}

test_install_uninstall_symmetry() {
    log "Testing check_install_uninstall_symmetry"
    local uninst="${ROOT}/Uninstall-MiOS.ps1"
    local bak="${uninst}.negbak"
    cp "$uninst" "$bak"
    # Delete the scheduled-task sweep while [windows.owned_artifacts].task_names
    # still declares tasks -- the asymmetry the gate exists to catch.
    grep -v 'Unregister-ScheduledTask' "$bak" > "$uninst"
    if _neg_gate check_install_uninstall_symmetry; then
        cp "$bak" "$uninst" && rm -f "$bak"
        die "check_install_uninstall_symmetry passed despite a missing task sweep"
    fi
    cp "$bak" "$uninst" && rm -f "$bak"
    _neg_gate check_install_uninstall_symmetry \
        || die "check_install_uninstall_symmetry failed after restoration"
    log "check_install_uninstall_symmetry negative test passed"
}

test_ps_port_fallback_ssot() {
    log "Testing check_ps_port_fallback_ssot"
    local f="${ROOT}/usr/share/mios/windows/mios-tailscale-serve.ps1"
    local bak="${f}.negbak"
    cp "$f" "$bak"
    # Drift one last-resort literal away from mios.toml [ports].cockpit.
    sed "s/'cockpit' 8110/'cockpit' 9090/" "$bak" > "$f"
    if _neg_gate check_ps_port_fallback_ssot; then
        cp "$bak" "$f" && rm -f "$bak"
        die "check_ps_port_fallback_ssot passed despite a drifted port fallback"
    fi
    cp "$bak" "$f" && rm -f "$bak"
    _neg_gate check_ps_port_fallback_ssot \
        || die "check_ps_port_fallback_ssot failed after restoration"
    log "check_ps_port_fallback_ssot negative test passed"
}

test_github_slug_casing() {
    log "Testing check_github_slug_casing"
    local probe="${ROOT}/tests/mios-negtest-slug.txt"
    # Assembled from fragments: spelling the bad slug literally here would make
    # this very file a standing violation of the check it is testing.
    local host='raw.githubusercontent.com'
    local badorg='MiOS'
    badorg="${badorg}-DEV"
    printf 'curl https://%s/%s/mios-bootstrap/main/bootstrap.ps1\n' "$host" "$badorg" > "$probe"
    if _neg_gate check_github_slug_casing; then
        rm -f "$probe"
        die "check_github_slug_casing passed despite a non-canonical org slug"
    fi
    rm -f "$probe"
    _neg_gate check_github_slug_casing \
        || die "check_github_slug_casing failed after restoration"
    log "check_github_slug_casing negative test passed"
}

test_ps_encoding_and_bom() {
    log "Testing check_ps_encoding_and_bom"
    local probe="${ROOT}/tests/mios-negtest-bom.ps1"
    # Non-ASCII with no BOM: exactly what PowerShell 5.1 would read as ANSI.
    printf 'Write-Host "run \xE2\x94\x80\xE2\x94\x80 done"\n' > "$probe"
    if _neg_gate check_ps_encoding_and_bom; then
        rm -f "$probe"
        die "check_ps_encoding_and_bom passed despite non-ASCII with no BOM"
    fi
    rm -f "$probe"
    _neg_gate check_ps_encoding_and_bom \
        || die "check_ps_encoding_and_bom failed after restoration"
    log "check_ps_encoding_and_bom negative test passed"
}

test_secret_handling() {
    log "Testing check_secret_handling"
    local probe="${ROOT}/tests/mios-negtest-secrets.ps1"
    printf '$SecretsFile = Join-Path $env:TEMP "mios-secrets.env"\n' > "$probe"
    if _neg_gate check_secret_handling; then
        rm -f "$probe"
        die "check_secret_handling passed despite a plaintext %TEMP% secrets path"
    fi
    rm -f "$probe"
    _neg_gate check_secret_handling \
        || die "check_secret_handling failed after restoration"
    log "check_secret_handling negative test passed"
}

test_wsl_distro_resolution() {
    log "Testing check_wsl_distro_resolution"
    # The check only scans usr/share/mios/windows, so the probe must live there.
    local probe="${ROOT}/usr/share/mios/windows/mios-negtest-distro.ps1"
    printf 'wsl.exe -d podman-MiOS-DEV -- true\n' > "$probe"
    if _neg_gate check_wsl_distro_resolution; then
        rm -f "$probe"
        die "check_wsl_distro_resolution passed despite a hardcoded distro literal"
    fi
    rm -f "$probe"
    _neg_gate check_wsl_distro_resolution \
        || die "check_wsl_distro_resolution failed after restoration"
    log "check_wsl_distro_resolution negative test passed"
}

test_unit_dependency_closure() {
    log "Testing check_unit_dependency_closure"
    local probe="${ROOT}/usr/lib/systemd/system/mios-negtest-dangling.service"
    cat > "$probe" <<'UNIT'
[Unit]
Description=negative-test probe with a dependency that resolves to nothing
After=mios-this-unit-does-not-exist.service

[Service]
ExecStart=/bin/true
UNIT
    if _neg_gate check_unit_dependency_closure; then
        rm -f "$probe"
        die "check_unit_dependency_closure passed despite a dangling After= target"
    fi
    rm -f "$probe"
    _neg_gate check_unit_dependency_closure \
        || die "check_unit_dependency_closure failed after restoration"
    log "check_unit_dependency_closure negative test passed"
}

test_docs_ratchet() {
    log "Testing check_docs_ratchet"
    local probe="${ROOT}/automation/mios-negtest-narrative.sh"
    # A block that must classify MIGRATE: >= migrate_min_lines with narrative
    # signal words, so it pushes the census one past its floor.
    cat > "$probe" <<'EOF'
#!/usr/bin/env bash
# The operator hit a regression here previously and the root cause was a race.
# This was reverted once, then reinstated with a different invariant entirely.
# See ADR-0004 and Law 8 for why the projection must never be bypassed here.
# Previously the alternative was rejected because it degraded the serving lane.
# The rationale is recorded so the next reader does not repeat the experiment.
# An incident followed and the operator asked for this guard to remain in place.
true
EOF
    # The census counts GIT-TRACKED files only, so an untracked probe is
    # invisible to it and the test would pass vacuously. Stage it with -N
    # (intent-to-add) so `git ls-files` reports it without committing content.
    git -C "$ROOT" add -N -- "$probe" >/dev/null 2>&1
    if _neg_gate check_docs_ratchet; then
        git -C "$ROOT" rm -q --cached --force -- "$probe" >/dev/null 2>&1
        rm -f "$probe"
        die "check_docs_ratchet passed despite an unharvested narrative block"
    fi
    git -C "$ROOT" rm -q --cached --force -- "$probe" >/dev/null 2>&1
    rm -f "$probe"

    # Test stale references breach
    cat > "$probe" <<'EOF'
#!/usr/bin/env bash
# AI-related: non_existent_dangling_reference_xyz99.sh
true
EOF
    git -C "$ROOT" add -N -- "$probe" >/dev/null 2>&1
    if _neg_gate check_docs_ratchet; then
        git -C "$ROOT" rm -q --cached --force -- "$probe" >/dev/null 2>&1
        rm -f "$probe"
        die "check_docs_ratchet passed despite a dangling reference"
    fi
    git -C "$ROOT" rm -q --cached --force -- "$probe" >/dev/null 2>&1
    rm -f "$probe"

    _neg_gate check_docs_ratchet || die "check_docs_ratchet failed after restoration"
    log "check_docs_ratchet negative test passed"
}

test_docs_ratchet_monotone() {
    log "Testing check_docs_ratchet_monotone"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local backup; backup="$(mktemp)"
    cp "$toml" "$backup"
    # Raising a ceiling is the loosening move the gate exists to reject.
    sed -i 's/^max_unmigrated_narrative = .*/max_unmigrated_narrative = 99999/' "$toml"
    if _neg_gate check_docs_ratchet_monotone; then
        cp "$backup" "$toml"; rm -f "$backup"
        die "check_docs_ratchet_monotone passed despite a RAISED ceiling"
    fi
    cp "$backup" "$toml"
    _neg_gate check_docs_ratchet_monotone \
        || { rm -f "$backup"; die "check_docs_ratchet_monotone failed after restoration"; }

    # The durable floor: a ceiling matching HEAD but above the lowest value ever
    # recorded is still a raise, and the HEAD comparison alone cannot see it.
    local floor="${ROOT}/usr/share/mios/reference/doc-ratchet-floor.tsv"
    local fbackup; fbackup="$(mktemp)"
    cp "$floor" "$fbackup"
    sed -i 's/^max_unmigrated_narrative\t.*/max_unmigrated_narrative\t1/' "$floor"
    if _neg_gate check_docs_ratchet_monotone; then
        cp "$fbackup" "$floor"; cp "$backup" "$toml"; rm -f "$backup" "$fbackup"
        die "check_docs_ratchet_monotone passed despite a ceiling above the recorded floor"
    fi
    cp "$fbackup" "$floor"; rm -f "$fbackup"
    _neg_gate check_docs_ratchet_monotone \
        || die "check_docs_ratchet_monotone failed after floor restoration"
    log "check_docs_ratchet_monotone negative test passed (HEAD + durable floor)"
}

test_generator_host_parity() {
    log "Testing check_generator_host_parity"
    local script="${ROOT}/tools/generate-names-registry.py"
    local backup; backup="$(mktemp)"
    cp "$script" "$backup"
    sed -i 's/glob\.fnmatch\.fnmatchcase/fnmatch.fnmatch/g' "$script"
    if _neg_gate check_generator_host_parity; then
        cp "$backup" "$script"; rm -f "$backup"
        die "check_generator_host_parity passed despite non-portable fnmatch usage"
    fi
    cp "$backup" "$script"; rm -f "$backup"
    _neg_gate check_generator_host_parity || die "check_generator_host_parity failed after restoration"
    log "check_generator_host_parity negative test passed"
}

test_manual_generated() {
    log "Testing check_manual_generated"
    local doc="${ROOT}/usr/share/doc/mios/reference/ports-and-laws.md"
    local backup; backup="$(mktemp)"
    cp "$doc" "$backup"
    # Corrupt a DERIVED table cell: the gate must notice the doc no longer
    # matches mios.toml.
    sed -i 's/| admin | ssh | [0-9]* |/| admin | ssh | 9999 |/' "$doc"
    if _neg_gate check_manual_generated; then
        cp "$backup" "$doc"; rm -f "$backup"
        die "check_manual_generated passed despite a stale derived section"
    fi
    cp "$backup" "$doc"
    _neg_gate check_manual_generated || { rm -f "$backup"; die "check_manual_generated failed after restoration"; }

    # Second phase, and the load-bearing one: authored prose OUTSIDE a marker
    # must NOT move the gate. Without this a generator that owns whole files
    # would satisfy the gate -- the exact failure the marker protocol prevents.
    printf '\nAuthored paragraph the generator must never touch.\n' >> "$doc"
    if ! _neg_gate check_manual_generated; then
        cp "$backup" "$doc"; rm -f "$backup"
        die "check_manual_generated went red on prose OUTSIDE a marker"
    fi
    grep -q "Authored paragraph the generator must never touch" "$doc" || {
        cp "$backup" "$doc"; rm -f "$backup"
        die "render destroyed authored prose outside a marker"; }
    cp "$backup" "$doc"; rm -f "$backup"

    # Third phase: a missing manual chapter must turn the gate red -- the
    # chapter index in manual.md is how absence becomes visible.
    local ch
    ch="$(ls "${ROOT}"/usr/share/doc/mios/manual/ch[0-9]*.md | head -1)"
    [ -f "$ch" ] || die "no manual chapter files found to hide"
    mv "$ch" "${ch}.neg-hidden"
    if _neg_gate check_manual_generated; then
        mv "${ch}.neg-hidden" "$ch"
        die "check_manual_generated passed despite a missing chapter file"
    fi
    mv "${ch}.neg-hidden" "$ch"
    _neg_gate check_manual_generated || die "check_manual_generated failed after restoring the chapter"
    log "check_manual_generated negative test passed (all three phases)"
}

test_manual_ledger() {
    log "Testing check_manual_ledger"
    local tsv="${ROOT}/usr/share/mios/reference/manual-corpus.tsv"
    local backup; backup="$(mktemp)"
    cp "$tsv" "$backup"
    # Mutate the first data row's word count (column 5): the ledger must no
    # longer regenerate verbatim from the tracked tree.
    awk -F'\t' 'BEGIN{OFS="\t"} NR==2{$5=$5+1} {print}' "$tsv" > "${tsv}.neg" \
        && mv "${tsv}.neg" "$tsv"
    if _neg_gate check_manual_ledger; then
        cp "$backup" "$tsv"; rm -f "$backup"
        die "check_manual_ledger passed despite a hand-edited corpus ledger"
    fi
    cp "$backup" "$tsv"; rm -f "$backup"
    _neg_gate check_manual_ledger || die "check_manual_ledger failed after restoration"
    log "check_manual_ledger negative test passed"
}

test_credential_literals() {
    log "Testing check_credential_literals"
    local unit="${ROOT}/usr/share/containers/systemd/mios-searxng.container"
    local backup; backup="$(mktemp)"
    cp "$unit" "$backup"
    printf 'Environment=NEGATIVE_TEST_SECRET_KEY=hunter2\n' >> "$unit"
    if _neg_gate check_credential_literals; then
        cp "$backup" "$unit"; rm -f "$backup"
        die "check_credential_literals passed despite a new baked-in credential"
    fi
    cp "$backup" "$unit"
    _neg_gate check_credential_literals || { rm -f "$backup"; die "check_credential_literals failed after restoration"; }
    rm -f "$backup"
    log "check_credential_literals negative test passed"
}

test_redact_coverage() {
    log "Testing check_redact_coverage"
    local sql="${ROOT}/usr/share/mios/postgres/schema-init.sql"
    local backup; backup="$(mktemp)"
    cp "$sql" "$backup"
    # A new table that is in neither [security.redact] list.
    printf '\nCREATE TABLE IF NOT EXISTS negative_test_sink (id int);\n' >> "$sql"
    if _neg_gate check_redact_coverage; then
        cp "$backup" "$sql"; rm -f "$backup"
        die "check_redact_coverage passed despite an unclassified table"
    fi
    cp "$backup" "$sql"
    _neg_gate check_redact_coverage || { rm -f "$backup"; die "check_redact_coverage failed after restoration"; }
    rm -f "$backup"
    log "check_redact_coverage negative test passed"
}

test_daemon_governor() {
    log "Testing check_daemon_governor"
    local d="${ROOT}/usr/libexec/mios/mios-daemon"
    local backup; backup="$(mktemp)"
    cp "$d" "$backup"
    # An autonomous loop that never consults the host-pressure gate.
    printf '\n\ndef negative_test_loop() -> None:\n    while not _stop_event.is_set():\n        time.sleep(1)\n' >> "$d"
    if _neg_gate check_daemon_governor; then
        cp "$backup" "$d"; rm -f "$backup"
        die "check_daemon_governor passed despite an ungated autonomous loop"
    fi
    cp "$backup" "$d"
    _neg_gate check_daemon_governor || { rm -f "$backup"; die "check_daemon_governor failed after restoration"; }
    rm -f "$backup"
    log "check_daemon_governor negative test passed"
}

test_manual_links() {
    log "Testing check_manual_links"
    local doc="${ROOT}/usr/share/doc/mios/manual.md"
    local backup; backup="$(mktemp)"
    cp "$doc" "$backup"
    # Point a ToC entry at a chapter that does not exist.
    sed -i '0,/(manual\/ch01-/s//(manual\/ch01-does-not-exist.md#x)(manual\/ch01-/' "$doc"
    if _neg_gate check_manual_links; then
        cp "$backup" "$doc"; rm -f "$backup"
        die "check_manual_links passed despite a dangling ToC link"
    fi
    cp "$backup" "$doc"
    _neg_gate check_manual_links || { rm -f "$backup"; die "check_manual_links failed after restoration"; }

    # Second phase: a chapter file that the ToC never mentions must also fail.
    local orphan="${ROOT}/usr/share/doc/mios/manual/ch99-orphan-negative-test.md"
    printf '<!-- AI-hint: negative-test orphan chapter. -->\n\n# Chapter 99\n' > "$orphan"
    if _neg_gate check_manual_links; then
        rm -f "$orphan" "$backup"
        die "check_manual_links passed despite an unreachable chapter file"
    fi
    rm -f "$orphan"
    _neg_gate check_manual_links || { rm -f "$backup"; die "check_manual_links failed after orphan removal"; }
    rm -f "$backup"
    log "check_manual_links negative test passed (both phases)"
}

test_doc_port_scheme() {
    log "Testing check_doc_port_scheme"
    local doc="${ROOT}/README.md"
    local backup; backup="$(mktemp)"
    cp "$doc" "$backup"
    printf '\nA retired lane on `:11450` sneaks back in.\n' >> "$doc"
    if _neg_gate check_doc_port_scheme; then
        cp "$backup" "$doc"; rm -f "$backup"
        die "check_doc_port_scheme passed despite a retired port literal"
    fi
    cp "$backup" "$doc"
    _neg_gate check_doc_port_scheme || { rm -f "$backup"; die "check_doc_port_scheme failed after restoration"; }
    rm -f "$backup"
    log "check_doc_port_scheme negative test passed"
}

test_comment_landing() {
    log "Testing check_comment_landing"
    local tsv="${ROOT}/usr/share/mios/reference/manual-corpus.tsv"
    local backup; backup="$(mktemp)"
    cp "$tsv" "$backup"
    # Claim a block was pruned into a doc that does not carry its anchor: the
    # gate must refuse to accept a deletion whose proof does not resolve.
    printf 'tests/fixture-never-existed.sh\t1\t2\t2\t40\tfeedfacecafe\tMIGRATE\tmidsize-narrative\t\t0\tusr/share/doc/mios/manual.md\tmios-src:feedfacecafe\t40\t1\n' >> "$tsv"
    if _neg_gate check_comment_landing; then
        cp "$backup" "$tsv"; rm -f "$backup"
        die "check_comment_landing passed despite a pruned block with no landing proof"
    fi
    cp "$backup" "$tsv"; rm -f "$backup"
    _neg_gate check_comment_landing || die "check_comment_landing failed after restoration"
    log "check_comment_landing negative test passed"
}

test_blade_reconcile_schema() {
    log "Testing check_blade_reconcile_schema"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local bak; bak="$(mktemp)"; cp "$toml" "$bak"
    # Enabling divergence before origin_node/logical_ts exist is exactly the edit
    # that loses data silently on rejoin (ADR-0017 D5).
    sed -i 's/^enabled      = false.*$/enabled      = true/' "$toml"
    if _neg_gate check_blade_reconcile_schema; then
        cp "$bak" "$toml"; rm -f "$bak"
        die "check_blade_reconcile_schema passed with divergence enabled and no provenance columns"
    fi
    cp "$bak" "$toml"; rm -f "$bak"
    _neg_gate check_blade_reconcile_schema \
        || die "check_blade_reconcile_schema failed after restoration"
    log "check_blade_reconcile_schema negative test passed"
}

test_desktop_launchers() {
    log "Testing check_desktop_launchers"
    local f="${ROOT}/usr/share/applications/mios-svc-cockpit.desktop"
    [ -f "$f" ] || { log "no rendered launcher to mutate; skipping"; return 0; }
    local bak; bak="$(mktemp)"; cp "$f" "$bak"
    # Mutate a RENDERED field. Adding a stray .desktop proves nothing: the
    # renderer compares only what SSOT declares.
    sed -i 's/^Name=.*/Name=DRIFTED/' "$f"
    if _neg_gate check_desktop_launchers; then
        cp "$bak" "$f"; rm -f "$bak"
        die "check_desktop_launchers passed despite a drifted rendered launcher"
    fi
    cp "$bak" "$f"; rm -f "$bak"
    _neg_gate check_desktop_launchers || die "check_desktop_launchers failed after restoration"
    log "check_desktop_launchers negative test passed"
}

test_doc_refs_resolve() {
    log "Testing check_doc_refs_resolve"
    local probe="${ROOT}/automation/mios-negtest-docref.sh"
    # An AI-related line naming a file that does not exist is a stale reference.
    printf '#!/usr/bin/env bash\n# AI-hint: negtest probe.\n# AI-related: automation/this-file-does-not-exist-anywhere.sh\ntrue\n' > "$probe"
    git -C "$ROOT" add -N -- "$probe" >/dev/null 2>&1
    if _neg_gate check_doc_refs_resolve; then
        git -C "$ROOT" rm -q --cached --force -- "$probe" >/dev/null 2>&1; rm -f "$probe"
        die "check_doc_refs_resolve passed despite a dangling AI-related reference"
    fi
    git -C "$ROOT" rm -q --cached --force -- "$probe" >/dev/null 2>&1; rm -f "$probe"
    _neg_gate check_doc_refs_resolve || die "check_doc_refs_resolve failed after restoration"
    log "check_doc_refs_resolve negative test passed"
}

test_no_inert_ssot_tables() {
    log "Testing check_no_inert_ssot_tables"
    local toml="${ROOT}/usr/share/mios/mios.toml"
    local bak; bak="$(mktemp)"; cp "$toml" "$bak"
    # A table nothing reads is dead SSOT: it looks configurable and is not.
    # Assembled at runtime: spelling the table name literally in this .sh file
    # would make THIS file a consumer of it, and the check would rightly pass.
    local tbl="mios_negtest"; tbl="${tbl}_inert_tbl"
    printf '
[%s]
unused_key = "nothing reads this"
' "$tbl" >> "$toml"
    if _neg_gate check_no_inert_ssot_tables; then
        cp "$bak" "$toml"; rm -f "$bak"
        die "check_no_inert_ssot_tables passed despite an SSOT table with no consumer"
    fi
    cp "$bak" "$toml"; rm -f "$bak"
    _neg_gate check_no_inert_ssot_tables || die "check_no_inert_ssot_tables failed after restoration"
    log "check_no_inert_ssot_tables negative test passed"
}

test_bootstrap_sync() {
    log "Testing check_bootstrap_sync"
    local boot="${MIOS_BOOTSTRAP_ROOT:-/c/mios-bootstrap}"
    [ -d "$boot" ] || { log "bootstrap repo absent; skipping"; return 0; }
    local f="${boot}/installation/UNIFY.md"
    [ -f "$f" ] || { log "no mirrored file to mutate; skipping"; return 0; }
    local bak; bak="$(mktemp)"; cp "$f" "$bak"
    # Drift in a MIRRORED file must fail: mios.git is the authority, and the
    # whole point is that a shared surface cannot change in only one repo.
    printf '\nDRIFT PROBE\n' >> "$f"
    if _neg_gate check_bootstrap_sync; then
        cp "$bak" "$f"; rm -f "$bak"
        die "check_bootstrap_sync passed despite a mirrored file drifting in bootstrap"
    fi
    cp "$bak" "$f"; rm -f "$bak"
    _neg_gate check_bootstrap_sync || die "check_bootstrap_sync failed after restoration"
    log "check_bootstrap_sync negative test passed"
}

test_legibility_ratchet() {
    log "Testing check_legibility_ratchet"
    local probe="${ROOT}/automation/mios-negtest-bulk.sh"
    # Adding shell lines must fail: bash is glue only, and the floors only fall.
    { echo '#!/usr/bin/env bash'; for i in $(seq 1 200); do echo "true  # filler $i"; done; } > "$probe"
    git -C "$ROOT" add -N -- "$probe" >/dev/null 2>&1
    if _neg_gate check_legibility_ratchet; then
        git -C "$ROOT" rm -q --cached --force -- "$probe" >/dev/null 2>&1; rm -f "$probe"
        die "check_legibility_ratchet passed despite 200 new shell lines"
    fi
    git -C "$ROOT" rm -q --cached --force -- "$probe" >/dev/null 2>&1; rm -f "$probe"
    _neg_gate check_legibility_ratchet || die "check_legibility_ratchet failed after restoration"
    log "check_legibility_ratchet negative test passed"
}

test_resolver_differential_parity() {
    log "Testing check_resolver_differential_parity"
    local bin="" b
    for b in "${ROOT}/tools/native/target/release/mios-resolver"              "${ROOT}/tools/native/target/release/mios-resolver.exe"              "${ROOT}/tools/native/target/debug/mios-resolver"              "${ROOT}/tools/native/target/debug/mios-resolver.exe"; do
        [ -f "$b" ] && { bin="$b"; break; }
    done

    # The failure path is assertable either way: with no binary the Python and
    # Rust resolvers were never compared, so REQUIRE_TOOLS=1 must refuse rather
    # than print an advisory skip.
    if [ -n "$bin" ]; then
        mv "$bin" "${bin}.negtest"
    fi
    if MIOS_DRIFT_REQUIRE_TOOLS=1 _neg_gate check_resolver_differential_parity; then
        [ -n "$bin" ] && mv "${bin}.negtest" "$bin"
        die "check_resolver_differential_parity passed with no resolver binary under REQUIRE_TOOLS=1"
    fi
    [ -n "$bin" ] && mv "${bin}.negtest" "$bin"

    if [ -z "$bin" ]; then
        # Without a binary there is no parity to restore TO. Saying so is
        # honest; silently asserting success here would be the vacuous pass this
        # suite exists to catch.
        log "check_resolver_differential_parity: refusal path proven; parity path needs a built mios-resolver (CI builds it)"
        return 0
    fi
    MIOS_DRIFT_REQUIRE_TOOLS=0 _neg_gate check_resolver_differential_parity         || die "check_resolver_differential_parity failed after restoration"
    log "check_resolver_differential_parity negative test passed"
}

test_no_generated_prose_in_resolvers() {
    log "Testing check_no_generated_prose_in_resolvers"
    local sh_file="${ROOT}/automation/lib/globals.sh"
    local backup; backup="$(mktemp)"
    cp "$sh_file" "$backup"
    echo "# AI-hint: test prose line" >> "$sh_file"
    if _neg_gate check_no_generated_prose_in_resolvers; then
        cp "$backup" "$sh_file"; rm -f "$backup"
        die "check_no_generated_prose_in_resolvers passed despite AI-hint prose line"
    fi
    cp "$backup" "$sh_file"; rm -f "$backup"
    _neg_gate check_no_generated_prose_in_resolvers || die "check_no_generated_prose_in_resolvers failed after restoration"
    log "check_no_generated_prose_in_resolvers negative test passed"
}

test_header_integrity() {
    log "Testing check_header_integrity"
    local probe="${ROOT}/automation/mios-negtest-header.sh"
    # Exactly the damage found on main: the '#' reused as the hint's marker with
    # the interpreter left as hint TEXT, so the file has no shebang at all.
    printf '# AI-hint: !/usr/bin/env bash A probe with its shebang absorbed.\ntrue\n' > "$probe"
    git -C "$ROOT" add -N -- "$probe" >/dev/null 2>&1
    if _neg_gate check_header_integrity; then
        git -C "$ROOT" rm -q --cached --force -- "$probe" >/dev/null 2>&1; rm -f "$probe"
        die "check_header_integrity passed despite an absorbed shebang"
    fi
    git -C "$ROOT" rm -q --cached --force -- "$probe" >/dev/null 2>&1; rm -f "$probe"
    if ! _neg_gate check_header_integrity; then
        # Show WHY rather than only that it failed: a restoration failure means
        # the gate is flagging something the probe did not create.
        local violog
        violog=$(MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_header_integrity 2>&1 || true)
        echo "$violog" | grep -i 'violation' | head -5 >&2
        die "check_header_integrity failed after restoration"
    fi
    log "check_header_integrity negative test passed"
}

main() {
    if [[ $# -eq 1 && -n "$1" ]]; then
        if declare -f "$1" >/dev/null; then
            "$1"
            exit 0
        else
            die "Unknown test function: $1"
        fi
    fi
    log "Starting negative-test suite"
    test_neg_gate_harness
    test_fleet_safety
    test_ai_manifests_fresh
    test_version_ssot
    test_check_no_silent_tool_skips
    test_check_negatives_are_effective
    test_pipefail_grep_lint
    test_check_skip_list_covered
    test_resolver_equivalence
    test_eval_safety
    test_shellcheck_failure
    test_names_registry
    test_root_toml_subset
    test_toml_projection
    test_curl_retry
    test_resolver_ssot_refs
    test_nested_podman_caps
    test_bake_budget
    test_module_test_coverage
    test_router_parity
    test_council_gate_ssot
    test_agent_pipe_budgets
    test_bake_tokens
    test_bake_unresolved_image
    test_containerfile_pinned_clones
    test_firstboot_tier
    test_rechunk_budget
    test_bake_core_reconcile
    test_nested_podman_retry
    test_gate_registry
    test_adhoc_toml_parsers
    test_install_uninstall_symmetry
    test_ps_port_fallback_ssot
    test_github_slug_casing
    test_ps_encoding_and_bom
    test_secret_handling
    test_wsl_distro_resolution
    test_docs_ratchet
    test_header_integrity
    test_resolver_differential_parity
    test_generator_host_parity
    test_legibility_ratchet
    test_bootstrap_sync
    test_no_inert_ssot_tables
    test_doc_refs_resolve
    test_desktop_launchers
    test_blade_reconcile_schema
    test_docs_ratchet_monotone
    test_manual_generated
    test_manual_ledger
    test_comment_landing
    test_credential_literals
    test_redact_coverage
    test_daemon_governor
    test_manual_links
    test_doc_port_scheme
    test_unit_dependency_closure
    test_unit_dependency_closure
    test_test_hermeticity
    test_no_mkdir_in_var
    test_quadlet_privilege
    test_lint_is_final
    test_firstboot_degrade_open
    test_require_tools
    test_ssot_lint_deadkey
    test_soft_mode_not_committed
    test_oci_archive_path
    test_replaceme_mount_substitution
    test_kickstart_shell_syntax
    test_offline_install_invariant
    test_installer_family_roles
    test_bib_configs_projection
    test_ssot_lint_equivalence
    test_repo_partition_label_ssot
    test_bib_single_config_invariant
    test_chpasswd_plaintext
    test_build_artifacts_output_dir
    test_win11_vm_template_xml
    test_ipa_enroll_projection
    test_uki_cmdline_projection
    test_composefs_projection
    test_cockpit_projection
    test_chrony_ptp_dropin
    test_chrony_projection
    test_nut_projection
    test_renderer_gate_coverage
    test_bake_plan
    test_bake_ref_defaults
    test_deploy_plane
    test_sbom_metadata
    test_clevis_luks
    test_metal_vfio
    test_hyprland_heredoc
    test_target_languages
    test_roadmap_index
    test_templates_compilation
    test_impossible_eol
    test_smoke_manifest
    test_negative_coverage
    test_verb_templates
    test_pipe_boundaries
    test_vllm_name_canonical
    test_pipe_extraction_parity
    test_guacamole_consistency
    test_cephfs_ssot
    test_v2v_import_ssot
    test_no_hardcode_version
    test_law_enforcers
    test_usr_over_etc
    test_projection_registry
    test_bake_plan_integrity
    test_bake_ref_parity
    test_db_seed_coverage
    test_account_column_parity
    test_module_length
    test_firstboot_provisioners
    test_schema_consumers
    test_tasks_status_parity
    test_container_names
    test_adr_index
    test_greenboot
    test_service_urls
    test_ports_bound
    test_blade_coverage
    test_blade_karg
    test_role_ssot
    test_no_generated_prose_in_resolvers
    log "All negative tests completed successfully"
}

main "$@"


