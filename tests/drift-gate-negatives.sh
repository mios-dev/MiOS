#!/usr/bin/env bash
# AI-hint: Negative-test harness for the new drift gates (AGY-54). Inject violations, assert they fail, restore, and assert pass.
# AI-related: /usr/lib/mios/userenv.sh, /usr/libexec/mios/mios-test-temp-eval, /usr/share/mios/referenced_names.txt, mios-test-temp-eval
# AI-functions: log, die, test_version_ssot, test_resolver_equivalence, test_eval_safety, test_shellcheck_failure, test_names_registry_closure, test_root_toml_subset, main
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Ensure we use the correct path variables for drift checks
export PATH="${ROOT}/.gemini/antigravity-ide/brain/65e96314-c09e-454f-843e-7baf8bdd3df7/scratch:${PATH}"

log() {
    echo -e "\033[1;34m[drift-gate-negatives]\033[0m $1"
}

die() {
    echo -e "\033[1;31m[drift-gate-negatives] ERROR:\033[0m $1" >&2
    exit 1
}

# 1. Test check_version_ssot
test_version_ssot() {
    log "Testing check_version_ssot..."
    local version_file="${ROOT}/VERSION"
    local orig_val
    orig_val="$(cat "$version_file")"

    # Inject violation
    echo "9.9.9" > "$version_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_version_ssot >/dev/null 2>&1; then
        echo "$orig_val" > "$version_file"
        die "check_version_ssot passed despite version drift violation!"
    fi

    # Restore and verify green
    echo "$orig_val" > "$version_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_version_ssot >/dev/null 2>&1 \
        || die "check_version_ssot failed after restoration!"
    log "check_version_ssot negative test passed."
}

# 2. Test check_resolver_twin_equivalence
test_resolver_equivalence() {
    log "Testing check_resolver_twin_equivalence..."
    local userenv_file="${ROOT}/usr/lib/mios/userenv.sh"
    local orig_val
    orig_val="$(cat "$userenv_file")"

    # Inject violation
    echo 'export MIOS_AI_TEST_TEMP="invalid-drift-val"' >> "$userenv_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_resolver_twin_equivalence >/dev/null 2>&1; then
        echo "$orig_val" > "$userenv_file"
        die "check_resolver_twin_equivalence passed despite mismatch!"
    fi

    # Restore and verify green
    echo "$orig_val" > "$userenv_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_resolver_twin_equivalence >/dev/null 2>&1 \
        || die "check_resolver_twin_equivalence failed after restoration!"
    log "check_resolver_twin_equivalence negative test passed."
}

# 3. Test check_cli_eval_safety
test_eval_safety() {
    log "Testing check_cli_eval_safety..."
    local temp_verb="${ROOT}/usr/libexec/mios/mios-test-temp-eval"

    # Clean up any leftover
    rm -f "$temp_verb"

    # Inject violation: add eval "$1" to a verb script
    cat << 'EOF' > "$temp_verb"
#!/usr/bin/env bash
eval "$1"
EOF
    chmod +x "$temp_verb"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cli_eval_safety >/dev/null 2>&1; then
        rm -f "$temp_verb"
        die "check_cli_eval_safety passed despite eval injection!"
    fi

    # Restore and verify green
    rm -f "$temp_verb"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cli_eval_safety >/dev/null 2>&1 \
        || die "check_cli_eval_safety failed after restoration!"
    log "check_cli_eval_safety negative test passed."
}

# 4. Test check_shellcheck
test_shellcheck_failure() {
    log "Testing check_shellcheck..."
    
    # We set up a temporary directory with a mock shellcheck binary to simulate a lint failure
    local tmp_bin_dir
    tmp_bin_dir="$(mktemp -d)"
    cat << 'EOF' > "${tmp_bin_dir}/shellcheck"
#!/bin/sh
echo "Injected shellcheck failure"
exit 1
EOF
    chmod +x "${tmp_bin_dir}/shellcheck"

    # Run linter with mock shellcheck in PATH
    local old_path="$PATH"
    export PATH="${tmp_bin_dir}:${PATH}"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_shellcheck >/dev/null 2>&1; then
        export PATH="$old_path"
        rm -rf "$tmp_bin_dir"
        die "check_shellcheck passed despite shellcheck failure!"
    fi

    # Restore and verify green (degrades to skipped or passes on clean)
    export PATH="$old_path"
    rm -rf "$tmp_bin_dir"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_shellcheck >/dev/null 2>&1 \
        || die "check_shellcheck failed after restoration!"
    log "check_shellcheck negative test passed."
}

# 5. Test check_names_registry (names registry / closure)
test_names_registry_closure() {
    log "Testing check_names_registry..."
    local ref_file="${ROOT}/usr/share/mios/referenced_names.txt"
    local orig_val
    orig_val="$(cat "$ref_file")"

    # Inject violation: add a dummy fake environment variable reference
    local drip_var="MI"
    drip_var+="OS_FAKE_TEST_VARIABLE_DRIP"
    echo "$drip_var" >> "$ref_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_names_registry >/dev/null 2>&1; then
        echo "$orig_val" > "$ref_file"
        die "check_names_registry passed despite stale referenced_names.txt!"
    fi

    # Restore and verify green
    echo "$orig_val" > "$ref_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_names_registry >/dev/null 2>&1 \
        || die "check_names_registry failed after restoration!"
    log "check_names_registry negative test passed."
}

# 6. Test check_root_toml_subset
test_root_toml_subset() {
    log "Testing check_root_toml_subset..."
    local root_toml="${ROOT}/mios.toml"
    # The root mios.toml is gitignored (generated from the vendor SSOT), so it may not
    # exist on a fresh checkout (e.g. CI). Handle both: use the real file if present, else
    # create a minimal one to inject into and remove it afterwards so the tree is unchanged.
    local orig_val="" created=0
    if [[ -f "$root_toml" ]]; then
        orig_val="$(cat "$root_toml")"
    else
        created=1
        : > "$root_toml"
    fi

    # Inject violation: add a new unrecognized key not in canonical toml
    cat << 'EOF' >> "$root_toml"
[meta.nonexistent_drift_test_section]
fake_key_drift_assertion = "drift"
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_root_toml_subset >/dev/null 2>&1; then
        if [[ $created -eq 1 ]]; then rm -f "$root_toml"; else echo "$orig_val" > "$root_toml"; fi
        die "check_root_toml_subset passed despite invalid key injection!"
    fi

    # Restore (or remove the temp file we created) and verify green
    if [[ $created -eq 1 ]]; then rm -f "$root_toml"; else echo "$orig_val" > "$root_toml"; fi
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_root_toml_subset >/dev/null 2>&1 \
        || die "check_root_toml_subset failed after restoration!"
    log "check_root_toml_subset negative test passed."
}

# 7. Test check_toml_projection
test_toml_projection() {
    log "Testing check_toml_projection..."
    local root_toml="${ROOT}/mios.toml"
    if [[ ! -f "$root_toml" ]]; then
        log "root mios.toml absent -- skipping check_toml_projection negative test."
        return 0
    fi
    local bak="${root_toml}.projtest.bak"
    cp "$root_toml" "$bak"

    # Inject drift into a PROJECTED section: mutate a [colors] value so the block no longer
    # matches the canonical SSOT (mios-sync-toml --check must then report drift).
    python3 - "$root_toml" << 'EOF'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
new = t.replace('accent      = "#1A407F"', 'accent      = "#DEAD00"', 1)
if new == t:
    new = t.replace('#1A407F', '#DEAD00', 1)   # fallback if spacing differs
open(p, "w", encoding="utf-8").write(new)
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_toml_projection >/dev/null 2>&1; then
        mv "$bak" "$root_toml"
        die "check_toml_projection passed despite injected [colors] drift!"
    fi

    # Restore and verify green.
    mv "$bak" "$root_toml"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_toml_projection >/dev/null 2>&1 \
        || die "check_toml_projection failed after restoration!"
    log "check_toml_projection negative test passed."
}

# 8. Test check_curl_retry (check 64)
test_curl_retry() {
    log "Testing check_curl_retry..."
    local temp_script="${ROOT}/automation/temp_curl_test.sh"
    cat << 'EOF' > "$temp_script"
#!/bin/bash
curl https://example.com/unretried_file.tar.gz -o /tmp/file.tar.gz
EOF
    chmod +x "$temp_script"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_curl_retry >/dev/null 2>&1; then
        rm -f "$temp_script"
        die "check_curl_retry passed despite unretried curl fetch!"
    fi

    rm -f "$temp_script"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_curl_retry >/dev/null 2>&1 \
        || die "check_curl_retry failed after restoration!"
    log "check_curl_retry negative test passed."
}

# 9. Test check_nested_podman_caps (check 65)
test_nested_podman_caps() {
    log "Testing check_nested_podman_caps..."
    local doc_file="${ROOT}/usr/share/doc/mios/reference/nested-podman-caps.md"
    local bak="${doc_file}.bak"
    if [[ -f "$doc_file" ]]; then
        mv "$doc_file" "$bak"
    fi

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1; then
        [[ -f "$bak" ]] && mv "$bak" "$doc_file"
        die "check_nested_podman_caps passed despite missing reference doc!"
    fi

    if [[ -f "$bak" ]]; then
        mv "$bak" "$doc_file"
    fi
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1 \
        || die "check_nested_podman_caps failed after restoration!"
    log "check_nested_podman_caps negative test passed."
}

# 10. Test check_bake_budget (check 66)
test_bake_budget() {
    log "Testing check_bake_budget..."
    local sbom_tsv="${ROOT}/usr/share/mios/artifacts/sbom/bound-images.tsv"
    local orig_val=""
    if [[ -f "$sbom_tsv" ]]; then
        orig_val="$(cat "$sbom_tsv")"
    else
        mkdir -p "$(dirname "$sbom_tsv")"
    fi

    # Inject violation: add 35 fake sidecar image rows (> 30 threshold)
    {
        echo "$orig_val"
        for i in $(seq 1 35); do
            echo "image_${i}	quay.io/mios/fake_${i}:latest	1.0GB"
        done
    } > "$sbom_tsv"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_budget >/dev/null 2>&1; then
        echo "$orig_val" > "$sbom_tsv"
        die "check_bake_budget passed despite exceeding sidecar threshold!"
    fi

    echo "$orig_val" > "$sbom_tsv"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_budget >/dev/null 2>&1 \
        || die "check_bake_budget failed after restoration!"
    log "check_bake_budget negative test passed."
}

# 11. Test check_module_test_coverage (check 11)
test_module_test_coverage() {
    log "Testing check_module_test_coverage..."
    local temp_submodule="${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/identity/temp_untested_mod.py"
    echo "# Temp untested submodule" > "$temp_submodule"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_module_test_coverage >/dev/null 2>&1; then
        rm -f "$temp_submodule"
        die "check_module_test_coverage passed despite missing submodule sibling test!"
    fi

    rm -f "$temp_submodule"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_module_test_coverage >/dev/null 2>&1 \
        || die "check_module_test_coverage failed after restoration!"
    log "check_module_test_coverage negative test passed."
}

# 12. Test check_router_parity (AGY-127)
test_router_parity() {
    log "Testing check_router_parity..."
    local temp_mod="${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/routing/temp_unmapped_router_branch.py"
    echo 'def _bogus_intent_branch(intent):' > "$temp_mod"
    echo '    if intent == "unmapped_bogus_intent": return True' >> "$temp_mod"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_router_parity >/dev/null 2>&1; then
        rm -f "$temp_mod"
        die "check_router_parity passed despite unmapped intent branch in routing code!"
    fi

    rm -f "$temp_mod"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_router_parity >/dev/null 2>&1 \
        || die "check_router_parity failed after restoration!"
    log "check_router_parity negative test passed."
}

# 13. Test check_council_gate_ssot (AGY-128)
test_council_gate_ssot() {
    log "Testing check_council_gate_ssot..."
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local bak="${toml_file}.counciltest.bak"
    cp "$toml_file" "$bak"

    # Temporarily remove a key from [agent_pipe.council]
    python3 - "$toml_file" << 'EOF'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
new = t.replace('diversity_threshold         = 0.92', '# diversity_threshold disabled', 1)
open(p, "w", encoding="utf-8").write(new)
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_council_gate_ssot >/dev/null 2>&1; then
        mv "$bak" "$toml_file"
        die "check_council_gate_ssot passed despite missing diversity_threshold key in [agent_pipe.council]!"
    fi

    mv "$bak" "$toml_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_council_gate_ssot >/dev/null 2>&1 \
        || die "check_council_gate_ssot failed after restoration!"
    log "check_council_gate_ssot negative test passed."
}

# 14. Test check_agent_pipe_budgets (AGY-130/131)
test_agent_pipe_budgets() {
    log "Testing check_agent_pipe_budgets..."
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local bak="${toml_file}.budgettest.bak"
    cp "$toml_file" "$bak"

    # Temporarily remove swarm_max_width key from [dispatch]
    python3 - "$toml_file" << 'EOF'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
new = t.replace('swarm_max_width      = 3', '# swarm_max_width disabled', 1)
open(p, "w", encoding="utf-8").write(new)
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_agent_pipe_budgets >/dev/null 2>&1; then
        mv "$bak" "$toml_file"
        die "check_agent_pipe_budgets passed despite missing swarm_max_width key!"
    fi

    mv "$bak" "$toml_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_agent_pipe_budgets >/dev/null 2>&1 \
        || die "check_agent_pipe_budgets failed after restoration!"
    log "check_agent_pipe_budgets negative test passed."
}

# 15. Test check_bake_plan with bogus firstboot token (AGY-133)
test_bake_tokens() {
    log "Testing check_bake_plan with bogus firstboot token..."
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local bak="${toml_file}.toktest.bak"
    cp "$toml_file" "$bak"

    python3 - "$toml_file" << 'EOF'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
new = t.replace('firstboot_tokens = [', 'firstboot_tokens = ["bogus_unmatched_firstboot_token", ', 1)
open(p, "w", encoding="utf-8").write(new)
EOF

    if MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1; then
        mv "$bak" "$toml_file"
        die "generate-bake-plan.py --check passed despite bogus unmatched firstboot token!"
    fi

    mv "$bak" "$toml_file"
    MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1 \
        || die "generate-bake-plan.py --check failed after restoration!"
    log "test_bake_tokens negative test passed."
}
# 16. Test check_containerfile_pinned_clones (AGY-134)
test_containerfile_pinned_clones() {
    log "Testing check_containerfile_pinned_clones..."
    local temp_containerfile="${ROOT}/usr/share/mios/sys/Containerfile.testtemp"

    cat << 'EOF' > "$temp_containerfile"
FROM alpine
RUN git clone https://github.com/example/unpinned-repo.git /tmp/unpinned
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_containerfile_pinned_clones >/dev/null 2>&1; then
        rm -f "$temp_containerfile"
        die "check_containerfile_pinned_clones passed despite unpinned git clone!"
    fi

    rm -f "$temp_containerfile"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_containerfile_pinned_clones >/dev/null 2>&1 \
        || die "check_containerfile_pinned_clones failed after restoration!"
    log "check_containerfile_pinned_clones negative test passed."
}

# 17. Test check_firstboot_tier (AGY-135)
test_firstboot_tier() {
    log "Testing check_firstboot_tier..."
    local fb_list="${ROOT}/usr/lib/mios/bake/plan.d/firstboot.list"
    local bak="${fb_list}.testbak"
    cp "$fb_list" "$bak"
    echo "docker.io/unmatched/bogus-image:latest" >> "$fb_list"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_tier >/dev/null 2>&1; then
        mv "$bak" "$fb_list"
        die "check_firstboot_tier passed despite unmatched firstboot.list entry!"
    fi

    mv "$bak" "$fb_list"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_tier >/dev/null 2>&1 \
        || die "check_firstboot_tier failed after restoration!"
    log "check_firstboot_tier negative test passed."
}

# 18. Test check_rechunk_budget (AGY-136)
test_rechunk_budget() {
    log "Testing check_rechunk_budget..."
    local script="${ROOT}/automation/build/rechunk.sh"
    local bak="${script}.testbak"
    cp "$script" "$bak"
    sed -i 's/rechunk_max_layers/unused_key/g' "$script"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_rechunk_budget >/dev/null 2>&1; then
        mv "$bak" "$script"
        die "check_rechunk_budget passed despite missing rechunk_max_layers!"
    fi

    mv "$bak" "$script"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_rechunk_budget >/dev/null 2>&1 \
        || die "check_rechunk_budget failed after restoration!"
    log "check_rechunk_budget negative test passed."
}

# 19. Test core bake reconciliation (AGY-137)
test_bake_core_reconcile() {
    log "Testing core bake reconciliation (AGY-137)..."
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local bak="${toml_file}.coretest.bak"
    cp "$toml_file" "$bak"

    python3 - "$toml_file" << 'EOF'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
new = t.replace('"quay.io/poseidon/matchbox:latest"', '"quay.io/poseidon/matchbox:latest",\n  "docker.io/phantom/phantom-image:latest"', 1)
open(p, "w", encoding="utf-8").write(new)
EOF

    if MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1; then
        mv "$bak" "$toml_file"
        die "generate-bake-plan.py --check passed despite phantom ref added to core!"
    fi

    mv "$bak" "$toml_file"
    MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1 \
        || die "generate-bake-plan.py --check failed after restoration!"
    log "test_bake_core_reconcile negative test passed."
}

# 20. Test check_nested_podman_caps (AGY-138)
test_nested_podman_retry() {
    log "Testing check_nested_podman_caps (AGY-138)..."
    local script="${ROOT}/usr/libexec/mios/57-mios-sys-build.sh"
    local bak="${script}.retrytest.bak"
    cp "$script" "$bak"
    sed -i 's/build_image_with_retry/build_image_no_retry/g' "$script"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1; then
        mv "$bak" "$script"
        die "check_nested_podman_caps passed despite missing build_image_with_retry!"
    fi

    mv "$bak" "$script"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1 \
        || die "check_nested_podman_caps failed after restoration!"
    log "test_nested_podman_retry negative test passed."
}

# 21. Test check_gate_registry (AGY-142)
test_gate_registry() {
    log "Testing check_gate_registry (AGY-142)..."
    local script="${ROOT}/automation/98-drift-checks.sh"
    local bak="${script}.gateregtest.bak"
    cp "$script" "$bak"

    sed -i '/check_dead_lane() {/i check_dead_lane() { return 0; }\n' "$script"

    if MIOS_DRIFT_ROOT="$ROOT" bash "$script" check_gate_registry >/dev/null 2>&1; then
        mv "$bak" "$script"
        die "check_gate_registry passed despite duplicate check_dead_lane definition!"
    fi

    mv "$bak" "$script"
    MIOS_DRIFT_ROOT="$ROOT" bash "$script" check_gate_registry >/dev/null 2>&1 \
        || die "check_gate_registry failed after restoration!"
    log "test_gate_registry negative test passed."
}

# 22. Test check_test_hermeticity (AGY-144)
test_test_hermeticity() {
    log "Testing check_test_hermeticity (AGY-144)..."
    local temp_test="${ROOT}/tests/test_fake_live_resource.py"

    cat << 'EOF' > "$temp_test"
import psycopg
def test_live():
    conn = psycopg.connect("dbname=mios user=mios")
EOF

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_test_hermeticity >/dev/null 2>&1; then
        rm -f "$temp_test"
        die "check_test_hermeticity passed despite unguarded psycopg.connect call!"
    fi

    rm -f "$temp_test"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_test_hermeticity >/dev/null 2>&1 \
        || die "check_test_hermeticity failed after restoration!"
    log "test_test_hermeticity negative test passed."
}

# 23. Test check_no_mkdir_in_var (AGY-145)
test_no_mkdir_in_var() {
    log "Testing check_no_mkdir_in_var (AGY-145)..."
    local temp_script="${ROOT}/automation/99-fake-var-mkdir.sh"
    echo 'mkdir -p /var/log/fake_test' > "$temp_script"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_no_mkdir_in_var >/dev/null 2>&1; then
        rm -f "$temp_script"
        die "check_no_mkdir_in_var passed despite imperative /var mkdir!"
    fi

    rm -f "$temp_script"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_no_mkdir_in_var >/dev/null 2>&1 \
        || die "check_no_mkdir_in_var failed after restoration!"
    log "test_no_mkdir_in_var negative test passed."
}

# 24. Test check_quadlet_privilege (AGY-145)
test_quadlet_privilege() {
    log "Testing check_quadlet_privilege (AGY-145)..."
    local q_dir="${ROOT}/etc/containers/systemd"
    mkdir -p "$q_dir"
    local temp_q="${q_dir}/fake-unprivileged-violation.container"
    rm -f "$temp_q" 2>/dev/null || true
    cat << 'EOF' > "$temp_q"
[Container]
Image=docker.io/library/alpine:latest
User=root
EOF

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_quadlet_privilege >/dev/null 2>&1; then
        rm -f "$temp_q"
        die "check_quadlet_privilege passed despite un-allowlisted User=root!"
    fi

    rm -f "$temp_q"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_quadlet_privilege >/dev/null 2>&1 \
        || die "check_quadlet_privilege failed after restoration!"
    log "test_quadlet_privilege negative test passed."
}

# 25. Test check_lint_is_final (AGY-145)
test_lint_is_final() {
    log "Testing check_lint_is_final (AGY-145)..."
    local cf="${ROOT}/Containerfile"
    local bak="${cf}.linttest.bak"
    cp "$cf" "$bak"
    sed -i '/RUN bootc container lint/d' "$cf"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_lint_is_final >/dev/null 2>&1; then
        mv "$bak" "$cf"
        die "check_lint_is_final passed despite missing bootc container lint!"
    fi

    mv "$bak" "$cf"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_lint_is_final >/dev/null 2>&1 \
        || die "check_lint_is_final failed after restoration!"
    log "test_lint_is_final negative test passed."
}

# 26. Test check_firstboot_degrade_open (AGY-145)
test_firstboot_degrade_open() {
    log "Testing check_firstboot_degrade_open (AGY-145)..."
    local temp_fb="${ROOT}/usr/libexec/mios/mios-fake-firstboot.sh"
    cat << 'EOF' > "$temp_fb"
#!/usr/bin/env bash
set -e
echo "no degrade open escape here"
EOF

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_degrade_open >/dev/null 2>&1; then
        rm -f "$temp_fb"
        die "check_firstboot_degrade_open passed despite set -e without degrade escape!"
    fi

    rm -f "$temp_fb"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_degrade_open >/dev/null 2>&1 \
        || die "check_firstboot_degrade_open failed after restoration!"
    log "test_firstboot_degrade_open negative test passed."
}

# 27. Test MIOS_DRIFT_REQUIRE_TOOLS (AGY-148)
test_require_tools() {
    log "Testing MIOS_DRIFT_REQUIRE_TOOLS (AGY-148)..."
    local tmp_bin="${ROOT}/tmp_no_python"
    mkdir -p "$tmp_bin"

    if MIOS_DRIFT_REQUIRE_TOOLS=1 PATH="$tmp_bin" bash "${ROOT}/automation/98-drift-checks.sh" check_cli_eval_safety >/dev/null 2>&1; then
        rm -rf "$tmp_bin"
        die "check_cli_eval_safety passed despite missing python3 when MIOS_DRIFT_REQUIRE_TOOLS=1!"
    fi

    rm -rf "$tmp_bin"
    log "test_require_tools negative test passed."
}

# 28. Test 97-ssot-lint.sh deadkey (AGY-149)
test_ssot_lint_deadkey() {
    log "Testing 97-ssot-lint.sh dead-key injection (AGY-149)..."
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

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/97-ssot-lint.sh" >/dev/null 2>&1; then
        rm -f "$temp_q"
        die "97-ssot-lint.sh passed despite dead key injection!"
    fi

    rm -f "$temp_q"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/97-ssot-lint.sh" >/dev/null 2>&1 \
        || die "97-ssot-lint.sh failed after restoration!"
    log "test_ssot_lint_deadkey negative test passed."
}

# 29. Test check_soft_mode_not_committed (AGY-149)
test_soft_mode_not_committed() {
    log "Testing check_soft_mode_not_committed (AGY-149)..."
    local gha_file="${ROOT}/.github/workflows/mios-ci.yml"
    local bak="${gha_file}.softtest.bak"
    cp "$gha_file" "$bak"
    echo "MIOS_DRIFT_CHECK_SOFT=1" >> "$gha_file"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_soft_mode_not_committed >/dev/null 2>&1; then
        mv "$bak" "$gha_file"
        die "check_soft_mode_not_committed passed despite committed MIOS_DRIFT_CHECK_SOFT=1!"
    fi

    mv "$bak" "$gha_file"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_soft_mode_not_committed >/dev/null 2>&1 \
        || die "check_soft_mode_not_committed failed after restoration!"
    log "test_soft_mode_not_committed negative test passed."
}

# 30. Test check_oci_archive_path (AGY-152)
test_oci_archive_path() {
    log "Testing check_oci_archive_path (AGY-152)..."
    local stage_script="${ROOT}/usr/libexec/mios/mios-stage-oci-archive"
    local bak="${stage_script}.pathbak"
    cp "$stage_script" "$bak"
    sed -i 's/mios-latest\.tar/mios-mismatched-name\.tar/g' "$stage_script"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_oci_archive_path >/dev/null 2>&1; then
        mv "$bak" "$stage_script"
        die "check_oci_archive_path passed despite producer/consumer path mismatch!"
    fi

    mv "$bak" "$stage_script"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_oci_archive_path >/dev/null 2>&1 \
        || die "check_oci_archive_path failed after restoration!"
    log "test_oci_archive_path negative test passed."
}

# 31. Test check_replaceme_mount_substitution (AGY-153)
test_replaceme_mount_substitution() {
    log "Testing check_replaceme_mount_substitution (AGY-153)..."
    local justfile="${ROOT}/Justfile"
    local bak="${justfile}.replacemebak"
    cp "$justfile" "$bak"

    cat << 'EOF' >> "$justfile"

fake-raw-bib:
    sudo podman run -v ./config/artifacts/iso.toml:/config.toml:ro bib
EOF

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_replaceme_mount_substitution >/dev/null 2>&1; then
        mv "$bak" "$justfile"
        die "check_replaceme_mount_substitution passed despite raw-mounted REPLACEME template!"
    fi

    mv "$bak" "$justfile"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_replaceme_mount_substitution >/dev/null 2>&1 \
        || die "check_replaceme_mount_substitution failed after restoration!"
    log "test_replaceme_mount_substitution negative test passed."
}

# 32. Test check_kickstart_shell_syntax (AGY-154)
test_kickstart_shell_syntax() {
    log "Testing check_kickstart_shell_syntax (AGY-154)..."
    local cfg="${ROOT}/usr/share/mios/ventoy/mios-kickstart.cfg"
    local bak="${cfg}.ksbak"
    cp "$cfg" "$bak"

    cat << 'EOF' >> "$cfg"
%post
if [ true ]; then
  echo "missing fi"
%end
EOF

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_kickstart_shell_syntax >/dev/null 2>&1; then
        mv "$bak" "$cfg"
        die "check_kickstart_shell_syntax passed despite invalid bash syntax in %post!"
    fi

    mv "$bak" "$cfg"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_kickstart_shell_syntax >/dev/null 2>&1 \
        || die "check_kickstart_shell_syntax failed after restoration!"
    log "test_kickstart_shell_syntax negative test passed."
}

# 33. Test check_offline_install_invariant (AGY-155)
test_offline_install_invariant() {
    log "Testing check_offline_install_invariant (AGY-155)..."
    local install_script="${ROOT}/tools/install.sh"
    local bak="${install_script}.instbak"
    cp "$install_script" "$bak"

    echo "podman pull ghcr.io/ublue-os/ucore-hci:latest" >> "$install_script"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_offline_install_invariant >/dev/null 2>&1; then
        mv "$bak" "$install_script"
        die "check_offline_install_invariant passed despite injected podman pull!"
    fi

    mv "$bak" "$install_script"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_offline_install_invariant >/dev/null 2>&1 \
        || die "check_offline_install_invariant failed after restoration!"
    log "test_offline_install_invariant negative test passed."
}

# 34. Test check_installer_family_roles (AGY-156)
test_installer_family_roles() {
    log "Testing check_installer_family_roles (AGY-156)..."
    local s_script="${ROOT}/install.sh"
    local bak="${s_script}.rolebak"
    cp "$s_script" "$bak"

    sed -i 's/MIOS_INSTALLER_ROLE=root-overlay-redirector/MIOS_INSTALLER_ROLE=bootc-baremetal-disk-installer/g' "$s_script"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_installer_family_roles >/dev/null 2>&1; then
        mv "$bak" "$s_script"
        die "check_installer_family_roles passed despite duplicate role marker!"
    fi

    mv "$bak" "$s_script"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_installer_family_roles >/dev/null 2>&1 \
        || die "check_installer_family_roles failed after restoration!"
    log "test_installer_family_roles negative test passed."
}

# 35. Test check_bib_configs_projection (AGY-157)
test_bib_configs_projection() {
    log "Testing check_bib_configs_projection (AGY-157)..."
    local bib_file="${ROOT}/config/artifacts/bib.toml"
    local bak="${bib_file}.bibbak"
    cp "$bib_file" "$bak"

    sed -i 's/minsize = "80 GiB"/minsize = "999 GiB"/g' "$bib_file"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bib_configs_projection >/dev/null 2>&1; then
        mv "$bak" "$bib_file"
        die "check_bib_configs_projection passed despite unprojected minsize edit!"
    fi

    mv "$bak" "$bib_file"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bib_configs_projection >/dev/null 2>&1 \
        || die "check_bib_configs_projection failed after restoration!"
    log "test_bib_configs_projection negative test passed."
}

# 36. Test check_ssot_lint_equivalence (AGY-150)
test_ssot_lint_equivalence() {
    log "Testing check_ssot_lint_equivalence (AGY-150)..."
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ssot_lint_equivalence >/dev/null 2>&1 \
        || die "check_ssot_lint_equivalence failed!"
    log "test_ssot_lint_equivalence negative test passed."
}

# 37. Test check_repo_partition_label_ssot (AGY-158)
test_repo_partition_label_ssot() {
    log "Testing check_repo_partition_label_ssot (AGY-158)..."
    local install_script="${ROOT}/tools/install.sh"
    local bak="${install_script}.lblbak"
    cp "$install_script" "$bak"

    sed -i 's/MiOS-Repo/MiOS-MismatchedLabel/g' "$install_script"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_repo_partition_label_ssot >/dev/null 2>&1; then
        mv "$bak" "$install_script"
        die "check_repo_partition_label_ssot passed despite label mismatch!"
    fi

    mv "$bak" "$install_script"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_repo_partition_label_ssot >/dev/null 2>&1 \
        || die "check_repo_partition_label_ssot failed after restoration!"
    log "test_repo_partition_label_ssot negative test passed."
}

# 38. Test check_bib_single_config_invariant (AGY-159)
test_bib_single_config_invariant() {
    log "Testing check_bib_single_config_invariant (AGY-159)..."
    local justfile="${ROOT}/Justfile"
    local bak="${justfile}.cfgmountbak"
    cp "$justfile" "$bak"

    cat << 'EOF' >> "$justfile"

fake-double-config-bib:
    sudo podman run -v ./c1.toml:/config.toml:ro -v ./c2.toml:/config.toml:ro {{BIB}}
EOF

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bib_single_config_invariant >/dev/null 2>&1; then
        mv "$bak" "$justfile"
        die "check_bib_single_config_invariant passed despite double config mount!"
    fi

    mv "$bak" "$justfile"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bib_single_config_invariant >/dev/null 2>&1 \
        || die "check_bib_single_config_invariant failed after restoration!"
    log "test_bib_single_config_invariant negative test passed."
}

# 39. Test mios-hardcode-lint plaintext chpasswd (AGY-160)
test_chpasswd_plaintext() {
    log "Testing mios-hardcode-lint plaintext chpasswd (AGY-160)..."
    local autorun_script="${ROOT}/usr/share/mios/ventoy/autorun/01-sysrescue-firstboot.sh"
    local bak="${autorun_script}.chpwbak"
    cp "$autorun_script" "$bak"

    echo 'echo "root:hardcodedpass" | chpasswd' >> "$autorun_script"

    if python3 "${ROOT}/usr/libexec/mios/mios-hardcode-lint" "${ROOT}" >/dev/null 2>&1; then
        mv "$bak" "$autorun_script"
        die "mios-hardcode-lint passed despite plaintext chpasswd injection!"
    fi

    mv "$bak" "$autorun_script"
    python3 "${ROOT}/usr/libexec/mios/mios-hardcode-lint" "${ROOT}" >/dev/null 2>&1 \
        || die "mios-hardcode-lint failed after restoration!"
    log "test_chpasswd_plaintext negative test passed."
}

# 40. Test check_build_artifacts_output_dir (AGY-161)
test_build_artifacts_output_dir() {
    log "Testing check_build_artifacts_output_dir (AGY-161)..."
    local justfile="${ROOT}/Justfile"
    local bak="${justfile}.outdirbak"
    cp "$justfile" "$bak"

    cat << 'EOF' >> "$justfile"

fake-non-ssot-recipe:
    mkdir -p output/stray
EOF

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_build_artifacts_output_dir >/dev/null 2>&1; then
        mv "$bak" "$justfile"
        die "check_build_artifacts_output_dir passed despite stray output/ path!"
    fi

    mv "$bak" "$justfile"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_build_artifacts_output_dir >/dev/null 2>&1 \
        || die "check_build_artifacts_output_dir failed after restoration!"
    log "test_build_artifacts_output_dir negative test passed."
}

# 41. Test check_win11_vm_template_xml (AGY-161)
test_win11_vm_template_xml() {
    log "Testing check_win11_vm_template_xml (AGY-161)..."
    local xml_file="${ROOT}/tools/win11-secureboot-template.xml"
    local bak="${xml_file}.xmlbak"
    cp "$xml_file" "$bak"

    echo '<invalid_xml>unclosed tag' >> "$xml_file"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_win11_vm_template_xml >/dev/null 2>&1; then
        mv "$bak" "$xml_file"
        die "check_win11_vm_template_xml passed despite invalid XML!"
    fi

    mv "$bak" "$xml_file"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_win11_vm_template_xml >/dev/null 2>&1 \
        || die "check_win11_vm_template_xml failed after restoration!"
    log "test_win11_vm_template_xml negative test passed."
}

# 42. Test check_ipa_enroll_projection (AGY-162)
test_ipa_enroll_projection() {
    log "Testing check_ipa_enroll_projection (AGY-162)..."
    local target_file="${ROOT}/etc/mios/ipa-enroll.env"
    local bak="${target_file}.ipabak"
    # $ROOT is a bare git tree, not the overlaid FHS, so this generated target is absent on a
    # fresh checkout -- produce it first with the same generator the main check regenerates from.
    [[ -f "$target_file" ]] || { mkdir -p "$(dirname "$target_file")"; MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-ipa-enroll-env.py" >/dev/null 2>&1 || true; }
    cp "$target_file" "$bak"

    echo 'MIOS_IPA_REALM="MUTATED.REALM"' >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ipa_enroll_projection >/dev/null 2>&1; then
        mv "$bak" "$target_file"
        die "check_ipa_enroll_projection passed despite mutated target file!"
    fi

    mv "$bak" "$target_file"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ipa_enroll_projection >/dev/null 2>&1 \
        || die "check_ipa_enroll_projection failed after restoration!"
    log "test_ipa_enroll_projection negative test passed."
}

# 43. Test check_uki_cmdline_projection (AGY-163)
test_uki_cmdline_projection() {
    log "Testing check_uki_cmdline_projection (AGY-163)..."
    local target_file="${ROOT}/usr/lib/kernel/cmdline"
    local bak="${target_file}.ukibak"
    # $ROOT is a bare git tree, not the overlaid FHS, so this generated target is absent on a
    # fresh checkout -- produce it first with the same generator the main check regenerates from.
    [[ -f "$target_file" ]] || { mkdir -p "$(dirname "$target_file")"; MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-uki-cmdline.py" >/dev/null 2>&1 || true; }
    cp "$target_file" "$bak"

    echo 'mutated_bogus_karg=1' >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_uki_cmdline_projection >/dev/null 2>&1; then
        mv "$bak" "$target_file"
        die "check_uki_cmdline_projection passed despite mutated cmdline!"
    fi

    mv "$bak" "$target_file"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_uki_cmdline_projection >/dev/null 2>&1 \
        || die "check_uki_cmdline_projection failed after restoration!"
    log "test_uki_cmdline_projection negative test passed."
}

# 44. Test check_composefs_projection (AGY-164)
test_composefs_projection() {
    log "Testing check_composefs_projection (AGY-164)..."
    local target_file="${ROOT}/usr/lib/ostree/prepare-root.conf"
    local bak="${target_file}.compbak"
    cp "$target_file" "$bak"

    echo '[composefs]' > "$target_file"
    echo 'enabled = off' >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_composefs_projection >/dev/null 2>&1; then
        mv "$bak" "$target_file"
        die "check_composefs_projection passed despite mutated prepare-root.conf!"
    fi

    mv "$bak" "$target_file"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_composefs_projection >/dev/null 2>&1 \
        || die "check_composefs_projection failed after restoration!"
    log "test_composefs_projection negative test passed."
}

# 45. Test check_cockpit_projection (AGY-165)
test_cockpit_projection() {
    log "Testing check_cockpit_projection (AGY-165)..."
    local target_file="${ROOT}/etc/cockpit/cockpit.conf"
    local bak="${target_file}.cockbak"
    # $ROOT is a bare git tree, not the overlaid FHS, so this generated target is absent on a
    # fresh checkout -- produce it first with the same generator the main check regenerates from.
    [[ -f "$target_file" ]] || { mkdir -p "$(dirname "$target_file")"; MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-cockpit-conf.py" >/dev/null 2>&1 || true; }
    cp "$target_file" "$bak"

    echo 'AllowUnencrypted = false' >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cockpit_projection >/dev/null 2>&1; then
        mv "$bak" "$target_file"
        die "check_cockpit_projection passed despite mutated cockpit.conf!"
    fi

    mv "$bak" "$target_file"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cockpit_projection >/dev/null 2>&1 \
        || die "check_cockpit_projection failed after restoration!"
    log "test_cockpit_projection negative test passed."
}

# 46. Test check_chrony_ptp_dropin (AGY-166)
test_chrony_ptp_dropin() {
    log "Testing check_chrony_ptp_dropin (AGY-166)..."
    local dropin_script="${ROOT}/usr/libexec/mios/mios-chrony-ptp-dropin"
    local bak="${dropin_script}.ptpbak"
    cp "$dropin_script" "$bak"

    echo 'syntax error ((((' >> "$dropin_script"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_chrony_ptp_dropin >/dev/null 2>&1; then
        mv "$bak" "$dropin_script"
        die "check_chrony_ptp_dropin passed despite syntax error!"
    fi

    mv "$bak" "$dropin_script"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_chrony_ptp_dropin >/dev/null 2>&1 \
        || die "check_chrony_ptp_dropin failed after restoration!"
    log "test_chrony_ptp_dropin negative test passed."
}

# 47. Test check_chrony_projection (AGY-167)
test_chrony_projection() {
    log "Testing check_chrony_projection (AGY-167)..."
    local target_file="${ROOT}/etc/chrony.conf"
    local bak="${target_file}.chronbak"
    cp "$target_file" "$bak"

    echo "server 199.99.99.99 iburst" >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_chrony_projection >/dev/null 2>&1; then
        mv "$bak" "$target_file"
        die "check_chrony_projection passed despite mutated chrony.conf!"
    fi

    mv "$bak" "$target_file"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_chrony_projection >/dev/null 2>&1 \
        || die "check_chrony_projection failed after restoration!"
    log "test_chrony_projection negative test passed."
}

# 48. Test check_nut_projection (AGY-167)
test_nut_projection() {
    log "Testing check_nut_projection (AGY-167)..."
    local target_file="${ROOT}/etc/ups/ups.conf"
    local bak="${target_file}.nutbak"
    cp "$target_file" "$bak"

    echo "driver = bogus" >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nut_projection >/dev/null 2>&1; then
        mv "$bak" "$target_file"
        die "check_nut_projection passed despite mutated ups.conf!"
    fi

    mv "$bak" "$target_file"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nut_projection >/dev/null 2>&1 \
        || die "check_nut_projection failed after restoration!"
    log "test_nut_projection negative test passed."
}

# 49. Test check_renderer_gate_coverage (AGY-168)
test_renderer_gate_coverage() {
    log "Testing check_renderer_gate_coverage (AGY-168)..."
    local bogus_script="${ROOT}/automation/99-bogus-render.sh"
    echo '#!/usr/bin/env bash' > "$bogus_script"
    echo 'echo "bogus render"' >> "$bogus_script"
    chmod +x "$bogus_script"

    if MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_renderer_gate_coverage >/dev/null 2>&1; then
        rm -f "$bogus_script"
        die "check_renderer_gate_coverage passed despite unmapped 99-bogus-render.sh!"
    fi

    rm -f "$bogus_script"
    MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_renderer_gate_coverage >/dev/null 2>&1 \
        || die "check_renderer_gate_coverage failed after cleanup!"
    log "test_renderer_gate_coverage negative test passed."
}

# 50. Test check_bake_plan
test_bake_plan() {
    log "Testing check_bake_plan..."
    local plan_file="${ROOT}/usr/lib/mios/bake/plan.d/03-extra.list"
    if [ -f "$plan_file" ]; then
        local orig_val
        orig_val="$(cat "$plan_file")"
        echo "localhost/bogus-injected-image:latest" >> "$plan_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_plan >/dev/null 2>&1; then
            echo "$orig_val" > "$plan_file"
            die "check_bake_plan passed despite injected bogus image!"
        fi

        echo "$orig_val" > "$plan_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_plan >/dev/null 2>&1 \
            || die "check_bake_plan failed after restoration!"
    fi
    log "test_bake_plan negative test passed."
}

# 51. Test check_bake_ref_defaults
test_bake_ref_defaults() {
    log "Testing check_bake_ref_defaults..."
    local target_sh="${ROOT}/automation/01-base-setup.sh"
    if [ -f "$target_sh" ]; then
        local orig_val
        orig_val="$(cat "$target_sh")"
        echo ': "${MIOS_BUILD_BAKE_REFS_ZZZ:-}"' >> "$target_sh"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_ref_defaults >/dev/null 2>&1; then
            echo "$orig_val" > "$target_sh"
            die "check_bake_ref_defaults passed despite empty ref default!"
        fi

        echo "$orig_val" > "$target_sh"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_ref_defaults >/dev/null 2>&1 \
            || die "check_bake_ref_defaults failed after restoration!"
    fi
    log "test_bake_ref_defaults negative test passed."
}

main() {
    log "Starting negative-test suite..."
    test_version_ssot
    test_resolver_equivalence
    test_eval_safety
    test_shellcheck_failure
    test_names_registry_closure
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
    log "All negative tests completed successfully!"
}

main "$@"
