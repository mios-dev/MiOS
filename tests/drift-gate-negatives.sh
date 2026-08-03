#!/usr/bin/env bash
# AI-hint: Negative-test harness for the new drift gates. Inject violations, assert they fail, restore, and assert pass.
# AI-related: /usr/lib/mios/userenv.sh, /usr/libexec/mios/mios-test-temp-eval, /usr/share/mios/referenced_names.txt, mios-test-temp-eval
# AI-functions: log, die, test_version_ssot, test_resolver_equivalence, test_eval_safety, test_shellcheck_failure, test_names_registry_closure, test_root_toml_subset, main
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
        die "Generate-bake-plan.py"
    fi

    cp "$bak_file" "$toml_file" && rm -f "$bak_file"
    MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
    MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1 \
        || die "Generate-bake-plan.py"
    log "Test_bake_tokens negative test passed"
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
    log "Testing core bake reconciliation"
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local bak_file="${toml_file}.bak"
    cp "$toml_file" "$bak_file"

    python3 - "$toml_file" << 'EOF'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
new = t.replace('"quay.io/poseidon/matchbox:latest"', '"quay.io/poseidon/matchbox:latest",\n  "docker.io/phantom/phantom-image:latest"', 1)
open(p, "w", encoding="utf-8").write(new)
EOF

    if MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1; then
        cp "$bak_file" "$toml_file" && rm -f "$bak_file"
        MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
        die "Generate-bake-plan.py"
    fi

    cp "$bak_file" "$toml_file" && rm -f "$bak_file"
    MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
    MIOS_ROOT="$ROOT" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1 \
        || die "Generate-bake-plan.py"
    log "Test_bake_core_reconcile negative test passed"
}

test_nested_podman_retry() {
    log "Testing check_nested_podman_caps"
    local script="${ROOT}/usr/libexec/mios/57-mios-sys-build.sh"
    local bak_file="${script}.bak"
    cp "$script" "$bak_file"
    sed -i 's/build_image_with_retry/build_image_no_retry/g' "$script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1; then
        cp "$bak_file" "$script" && rm -f "$bak_file"
        die "Check_nested_podman_caps passed despite missing build_image_with_retry"
    fi

    cp "$bak_file" "$script" && rm -f "$bak_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1 \
        || die "Check_nested_podman_caps failed after restoration"
    log "Test_nested_podman_retry negative test passed"
}

test_gate_registry() {
    log "Testing check_gate_registry"
    local script="${ROOT}/automation/98-drift-checks.sh"
    local bak_file="${script}.bak"
    cp "$script" "$bak_file"

    sed -i '/check_dead_lane() {/i check_dead_lane() { return 0; }\n' "$script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "$script" check_gate_registry >/dev/null 2>&1; then
        cp "$bak_file" "$script" && rm -f "$bak_file"
        die "Check_gate_registry passed despite duplicate check_dead_lane definition"
    fi

    cp "$bak_file" "$script" && rm -f "$bak_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "$script" check_gate_registry >/dev/null 2>&1 \
        || die "Check_gate_registry failed after restoration"
    log "Test_gate_registry negative test passed"
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

test_bake_plan() {
    log "Testing check_bake_plan"
    local plan_file="${ROOT}/usr/lib/mios/bake/plan.d/03-extra.list"
    if [ -f "$plan_file" ]; then
        local orig_val
        orig_val="$(cat "$plan_file")"
        printf '%s\n%s\n' "$orig_val" "localhost/bogus-injected-image:latest" > "$plan_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_plan >/dev/null 2>&1; then
            echo "$orig_val" > "$plan_file"
            die "Check_bake_plan passed despite injected bogus image"
        fi

        echo "$orig_val" > "$plan_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_plan >/dev/null 2>&1 \
            || die "Check_bake_plan failed after restoration"
    fi
    log "Test_bake_plan negative test passed"
}

test_bake_ref_defaults() {
    log "Testing check_bake_ref_defaults"
    local target_sh="${ROOT}/automation/01-base-setup.sh"
    if [ -f "$target_sh" ]; then
        local orig_val
        orig_val="$(cat "$target_sh")"
        printf '%s\n%s\n' "$orig_val" ': "${MIOS_BUILD_BAKE_REFS_ZZZ:-}"' > "$target_sh"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_ref_defaults >/dev/null 2>&1; then
            echo "$orig_val" > "$target_sh"
            die "Check_bake_ref_defaults passed despite empty ref default"
        fi

        echo "$orig_val" > "$target_sh"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_ref_defaults >/dev/null 2>&1 \
            || die "Check_bake_ref_defaults failed after restoration"
    fi
    log "Test_bake_ref_defaults negative test passed"
}

test_deploy_plane() {
    log "Testing check_deploy_plane"
    local ks_file="${ROOT}/usr/share/mios/ventoy/mios-kickstart.cfg"
    if [ -f "$ks_file" ]; then
        local orig_val
        orig_val="$(cat "$ks_file")"
        echo "$orig_val" > "$ks_file"
        grep -v "MIOS_FHS_TOTAL_ROOT_MERGE=1" "$ks_file" > "${ks_file}.tmp" && mv "${ks_file}.tmp" "$ks_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_deploy_plane >/dev/null 2>&1; then
            echo "$orig_val" > "$ks_file"
            die "Check_deploy_plane passed despite missing MIOS_FHS_TOTAL_ROOT_MERGE=1"
        fi

        echo "$orig_val" > "$ks_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_deploy_plane >/dev/null 2>&1 \
            || die "Check_deploy_plane failed after restoration"
    fi
    log "Test_deploy_plane negative test passed"
}

test_sbom_metadata() {
    log "Testing check_sbom_metadata"
    local sbom_dir="${ROOT}/usr/share/mios/artifacts/sbom"
    mkdir -p "$sbom_dir"
    local temp_tsv="${sbom_dir}/models.tsv"
    printf "name\tversion\tsha256\nmodel1\t1.0\tdeadbeef\n" > "$temp_tsv"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_sbom_metadata >/dev/null 2>&1; then
        rm -f "$temp_tsv"
        die "Check_sbom_metadata passed despite malformed sha256"
    fi

    rm -f "$temp_tsv"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_sbom_metadata >/dev/null 2>&1 \
        || die "Check_sbom_metadata failed after cleanup"
    log "Test_sbom_metadata negative test passed"
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

test_mini_vfio() {
    log "Testing check_mini_vfio"
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    mkdir -p "${tmp_dir}/usr/libexec/mios"
    printf '#!/bin/sh\necho "MINI_BROKEN=true"\n' > "${tmp_dir}/usr/libexec/mios/mios-mini-vfio-gen"
    chmod +x "${tmp_dir}/usr/libexec/mios/mios-mini-vfio-gen" 2>/dev/null || true

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$tmp_dir" MIOS_DRIFT_CHECK_ROOT="$tmp_dir" bash "${ROOT}/automation/98-drift-checks.sh" check_mini_vfio >/dev/null 2>&1; then
        rm -rf "$tmp_dir"
        die "Check_mini_vfio passed despite broken generator output"
    fi

    rm -rf "$tmp_dir"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_mini_vfio >/dev/null 2>&1 \
        || die "Check_mini_vfio failed after cleanup"
    log "Test_mini_vfio negative test passed"
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

test_negative_coverage() {
    log "Testing check_negative_coverage"
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    if [ -f "$toml_file" ]; then
        local orig_val
        orig_val="$(cat "$toml_file")"
        echo "$orig_val" > "$toml_file"
        grep -v '"check_agent_schema"' "$toml_file" > "${toml_file}.tmp" && mv "${toml_file}.tmp" "$toml_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_negative_coverage >/dev/null 2>&1; then
            echo "$orig_val" > "$toml_file"
            die "Check_negative_coverage passed despite removed exempt check"
        fi

        echo "$orig_val" > "$toml_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_negative_coverage >/dev/null 2>&1 \
            || die "Check_negative_coverage failed after restoration"
    fi
    log "Test_negative_coverage negative test passed"
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
    local manifest="${ROOT}/root-manifest.json"
    if [ -f "$manifest" ]; then
        local orig_val
        orig_val="$(cat "$manifest")"
        echo '"MIOS_AI_VLLM_SERVED_NAME": "test"' >> "$manifest"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_vllm_name_canonical >/dev/null 2>&1; then
            echo "$orig_val" > "$manifest"
            die "Check_vllm_name_canonical passed despite legacy long name"
        fi

        echo "$orig_val" > "$manifest"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_vllm_name_canonical >/dev/null 2>&1 \
            || die "Check_vllm_name_canonical failed after restoration"
    fi
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
    local plan_file="${ROOT}/usr/lib/mios/bake/plan.d/03-extra.list"
    if [ -f "$plan_file" ]; then
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
    local test_sh="${ROOT}/automation/15-render-quadlets.sh"
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
    local list_file="${ROOT}/usr/lib/mios/bake/plan.d/03-extra.list"
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
            || die "Check_bake_ref_defaults failed after restoration"
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


test_module_length() {
    log "Testing check_module_length"
    local dir="${ROOT}/usr/lib/mios/agent-pipe/mios_pipe"
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

test_negative_coverage() {
    log "Testing check_negative_coverage"
    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_negative_coverage >/dev/null 2>&1; then
        log "Test_negative_coverage passed"
    else
        die "Check_negative_coverage failed"
    fi
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
    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_negatives_are_effective >/dev/null 2>&1; then
        log "check_negatives_are_effective passed on HEAD"
    else
        die "check_negatives_are_effective failed on HEAD"
    fi
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
    # MUST run before anything else. check_ai_manifests_fresh compares the
    # manifests against a fresh walk of automation/ and tools/, and dozens of
    # the tests below create, mutate and restore files in exactly those trees
    # (some restore via `echo "$orig" >`, which drops a trailing newline). Run
    # it last and it grades the wreckage of every preceding test instead of the
    # committed state.
    test_ai_manifests_fresh
    test_version_ssot
    test_check_no_silent_tool_skips
    test_check_negatives_are_effective
    test_check_skip_list_covered
    test_resolver_equivalence
    test_eval_safety
    test_shellcheck_failure
    test_names_registry
    test_root_toml_subset
    test_toml_projection
    test_curl_retry
    test_nested_podman_caps
    test_bake_budget
    test_module_test_coverage
    test_router_parity
    test_council_gate_ssot
    test_agent_pipe_budgets
    test_bake_tokens
    test_containerfile_pinned_clones
    test_firstboot_tier
    test_rechunk_budget
    test_bake_core_reconcile
    test_nested_podman_retry
    test_gate_registry
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
    test_mini_vfio
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
    test_vendored_assets_non_stub
    test_resolved_env_lossless
    test_no_duplicate_value_key
    test_no_hardcoded_ssot_literal
    test_pipeline_numbering
    test_value_aliases
    test_bash_phase_ratchet
    test_ports_category_schema
    test_globals_generated
    test_cargo_deny
    test_powershell_parse
    test_ps_redirectors
    log "All negative tests completed successfully"
}

main "$@"


