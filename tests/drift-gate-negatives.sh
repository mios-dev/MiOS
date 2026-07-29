#!/usr/bin/env bash
# AI-hint: Negative-test harness for the new drift gates. Inject violations, assert they fail, restore, and assert pass.
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
    echo "$orig_val" > "$version_file"

    # Inject violation
    rm -f "$version_file"
    echo "9.9.9" > "$version_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_version_ssot >/dev/null 2>&1; then
        rm -f "$version_file"
        echo "$orig_val" > "$version_file"
        die "check_version_ssot passed despite version drift violation!"
    fi

    # Restore and verify green
    rm -f "$version_file"
    echo "$orig_val" > "$version_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_version_ssot >/dev/null 2>&1 \
        || die "check_version_ssot failed after restoration!"
    log "check_version_ssot negative test passed."
}

# 2. Test check_resolver_twin_equivalence
test_resolver_equivalence() {
    log "Testing check_resolver_twin_equivalence..."
    local userenv_file="${ROOT}/usr/lib/mios/userenv.sh"
    local bak_file="${userenv_file}.bak"
    cp "$userenv_file" "$bak_file"

    # Inject violation
    echo 'export MIOS_AI_TEST_TEMP="invalid-drift-val"' >> "$userenv_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_resolver_twin_equivalence >/dev/null 2>&1; then
        cp "${ROOT}/tools/lib/userenv.sh" "$userenv_file" && rm -f "$bak_file"
        die "check_resolver_twin_equivalence passed despite mismatch!"
    fi

    # Restore and verify green
    cp "${ROOT}/tools/lib/userenv.sh" "$userenv_file" && rm -f "$bak_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_resolver_twin_equivalence >/dev/null 2>&1 \
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
test_names_registry() {
    log "Testing check_names_registry..."
    local reg_file="${ROOT}/usr/share/mios/names.generated.txt"
    [[ -f "$reg_file" ]] || python3 "$ROOT/tools/generate-names-registry.py" >/dev/null 2>&1 || true
    local bak_file="${reg_file}.bak"
    cp "$reg_file" "$bak_file"

    # Inject violation: add a dummy fake entry to names.generated.txt
    echo "fake_drip.key MIOS_FAKE_TEST_VARIABLE_DRIP" >> "$reg_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_names_registry >/dev/null 2>&1; then
        cp "$bak_file" "$reg_file" && rm -f "$bak_file"
        python3 "$ROOT/tools/generate-names-registry.py" >/dev/null 2>&1 || true
        die "check_names_registry passed despite stale names.generated.txt!"
    fi

    # Restore and verify green
    cp "$bak_file" "$reg_file" && rm -f "$bak_file"
    python3 "$ROOT/tools/generate-names-registry.py" >/dev/null 2>&1 || true
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_names_registry >/dev/null 2>&1 \
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
        echo "$orig_val" > "$root_toml"
    else
        created=1
        : > "$root_toml"
    fi

    # Inject violation: add a new unrecognized key not in canonical toml
    cat << 'EOF' >> "$root_toml"
[meta.nonexistent_drift_test_section]
fake_key_drift_assertion = "drift"
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_root_toml_subset >/dev/null 2>&1; then
        if [[ $created -eq 1 ]]; then rm -f "$root_toml"; else rm -f "$root_toml" && echo "$orig_val" > "$root_toml"; fi
        die "check_root_toml_subset passed despite invalid key injection!"
    fi

    # Restore (or remove the temp file we created) and verify green
    if [[ $created -eq 1 ]]; then rm -f "$root_toml"; else rm -f "$root_toml" && echo "$orig_val" > "$root_toml"; fi
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_root_toml_subset >/dev/null 2>&1 \
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
    local orig_val
    orig_val="$(cat "$root_toml")"
    echo "$orig_val" > "$root_toml"

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

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_toml_projection >/dev/null 2>&1; then
        rm -f "$root_toml"
        echo "$orig_val" > "$root_toml"
        die "check_toml_projection passed despite injected [colors] drift!"
    fi

    # Restore and verify green.
    rm -f "$root_toml"
    echo "$orig_val" > "$root_toml"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_toml_projection >/dev/null 2>&1 \
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

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_curl_retry >/dev/null 2>&1; then
        rm -f "$temp_script"
        die "check_curl_retry passed despite unretried curl fetch!"
    fi

    rm -f "$temp_script"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_curl_retry >/dev/null 2>&1 \
        || die "check_curl_retry failed after restoration!"
    log "check_curl_retry negative test passed."
}

# 9. Test check_nested_podman_caps (check 65)
test_nested_podman_caps() {
    log "Testing check_nested_podman_caps..."
    local doc_file="${ROOT}/usr/share/doc/mios/reference/nested-podman-caps.md"
    local orig_val
    orig_val="$(cat "$doc_file")"
    rm -f "$doc_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1; then
        rm -f "$doc_file"
        echo "$orig_val" > "$doc_file"
        die "check_nested_podman_caps passed despite missing reference doc!"
    fi

    rm -f "$doc_file"
    echo "$orig_val" > "$doc_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1 \
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
        echo "$orig_val" > "$sbom_tsv"
    else
        mkdir -p "$(dirname "$sbom_tsv")"
    fi

    # Inject violation: add 35 fake sidecar image rows (> 30 threshold)
    rm -f "$sbom_tsv"
    {
        echo "$orig_val"
        for i in $(seq 1 35); do
            echo "image_${i}	quay.io/mios/fake_${i}:latest	1.0GB"
        done
    } > "$sbom_tsv"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_budget >/dev/null 2>&1; then
        rm -f "$sbom_tsv"
    echo "$orig_val" > "$sbom_tsv"
        die "check_bake_budget passed despite exceeding sidecar threshold!"
    fi

    rm -f "$sbom_tsv"
    echo "$orig_val" > "$sbom_tsv"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_budget >/dev/null 2>&1 \
        || die "check_bake_budget failed after restoration!"
    log "check_bake_budget negative test passed."
}

# 11. Test check_module_test_coverage (check 11)
test_module_test_coverage() {
    log "Testing check_module_test_coverage..."
    local temp_submodule="${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/identity/temp_untested_mod.py"
    echo "# Temp untested submodule" > "$temp_submodule"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_module_test_coverage >/dev/null 2>&1; then
        rm -f "$temp_submodule"* "${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/identity/__pycache__/temp_untested_mod"* 2>/dev/null || true
        die "check_module_test_coverage passed despite missing submodule sibling test!"
    fi

    rm -f "$temp_submodule"* "${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/identity/__pycache__/temp_untested_mod"* 2>/dev/null || true
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_module_test_coverage >/dev/null 2>&1 \
        || die "check_module_test_coverage failed after restoration!"
    log "check_module_test_coverage negative test passed."
}

# 12. Test check_router_parity
test_router_parity() {
    log "Testing check_router_parity..."
    local temp_mod="${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/routing/temp_unmapped_router_branch.py"
    echo 'def _bogus_intent_branch(intent):' > "$temp_mod"
    echo '    if intent == "unmapped_bogus_intent": return True' >> "$temp_mod"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_router_parity >/dev/null 2>&1; then
        rm -f "$temp_mod"* "${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/routing/__pycache__/temp_unmapped_router_branch"* 2>/dev/null || true
        die "check_router_parity passed despite unmapped intent branch in routing code!"
    fi

    rm -f "$temp_mod"* "${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/routing/__pycache__/temp_unmapped_router_branch"* 2>/dev/null || true
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_router_parity >/dev/null 2>&1 \
        || die "check_router_parity failed after restoration!"
    log "check_router_parity negative test passed."
}

# 13. Test check_council_gate_ssot
test_council_gate_ssot() {
    log "Testing check_council_gate_ssot..."
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local orig_val
    orig_val="$(cat "$toml_file")"
    echo "$orig_val" > "$toml_file"

    # Temporarily remove a key from [agent_pipe.council]
    python3 - "$toml_file" << 'EOF'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
new = t.replace('diversity_threshold         = 0.92', '# diversity_threshold disabled', 1)
open(p, "w", encoding="utf-8").write(new)
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_council_gate_ssot >/dev/null 2>&1; then
        rm -f "$toml_file"
        echo "$orig_val" > "$toml_file"
        die "check_council_gate_ssot passed despite missing diversity_threshold key in [agent_pipe.council]!"
    fi

    rm -f "$toml_file"
    echo "$orig_val" > "$toml_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_council_gate_ssot >/dev/null 2>&1 \
        || die "check_council_gate_ssot failed after restoration!"
    log "check_council_gate_ssot negative test passed."
}

# 14. Test check_agent_pipe_budgets (/131)
test_agent_pipe_budgets() {
    log "Testing check_agent_pipe_budgets..."
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    local orig_val
    orig_val="$(cat "$toml_file")"
    echo "$orig_val" > "$toml_file"

    # Temporarily remove swarm_max_width key from [dispatch]
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
        die "check_agent_pipe_budgets passed despite missing swarm_max_width key!"
    fi

    rm -f "$toml_file"
    echo "$orig_val" > "$toml_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_agent_pipe_budgets >/dev/null 2>&1 \
        || die "check_agent_pipe_budgets failed after restoration!"
    log "check_agent_pipe_budgets negative test passed."
}

# 15. Test check_bake_plan with bogus firstboot token
test_bake_tokens() {
    log "Testing check_bake_plan with bogus firstboot token..."
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

    if MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1; then
        cp "$bak_file" "$toml_file" && rm -f "$bak_file"
        MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
        die "generate-bake-plan.py --check passed despite bogus unmatched firstboot token!"
    fi

    cp "$bak_file" "$toml_file" && rm -f "$bak_file"
    MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
    MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1 \
        || die "generate-bake-plan.py --check failed after restoration!"
    log "test_bake_tokens negative test passed."
}
# 16. Test check_containerfile_pinned_clones
test_containerfile_pinned_clones() {
    log "Testing check_containerfile_pinned_clones..."
    local temp_containerfile="${ROOT}/usr/share/mios/sys/Containerfile.testtemp"

    cat << 'EOF' > "$temp_containerfile"
FROM alpine
RUN git clone https://github.com/example/unpinned-repo.git /tmp/unpinned
EOF

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_containerfile_pinned_clones >/dev/null 2>&1; then
        rm -f "$temp_containerfile"
        die "check_containerfile_pinned_clones passed despite unpinned git clone!"
    fi

    rm -f "$temp_containerfile"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_containerfile_pinned_clones >/dev/null 2>&1 \
        || die "check_containerfile_pinned_clones failed after restoration!"
    log "check_containerfile_pinned_clones negative test passed."
}

# 17. Test check_firstboot_tier
test_firstboot_tier() {
    log "Testing check_firstboot_tier..."
    local fb_list="${ROOT}/usr/lib/mios/bake/plan.d/firstboot.list"
    local orig_val
    orig_val="$(cat "$fb_list")"
    echo "$orig_val" > "$fb_list"

    rm -f "$fb_list"
    printf '%s\n%s\n' "$orig_val" "docker.io/unmatched/bogus-image:latest" > "$fb_list"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_tier >/dev/null 2>&1; then
        rm -f "$fb_list"
        echo "$orig_val" > "$fb_list"
        die "check_firstboot_tier passed despite unmatched firstboot.list entry!"
    fi

    rm -f "$fb_list"
    echo "$orig_val" > "$fb_list"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_tier >/dev/null 2>&1 \
        || die "check_firstboot_tier failed after restoration!"
    log "check_firstboot_tier negative test passed."
}

# 18. Test check_rechunk_budget
test_rechunk_budget() {
    log "Testing check_rechunk_budget..."
    local script="${ROOT}/automation/build/rechunk.sh"
    local orig_val
    orig_val="$(cat "$script")"
    rm -f "$script"
    echo "$orig_val" > "$script"
    sed -i 's/rechunk_max_layers/unused_key/g' "$script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_rechunk_budget >/dev/null 2>&1; then
        rm -f "$script"
        echo "$orig_val" > "$script"
        die "check_rechunk_budget passed despite missing rechunk_max_layers!"
    fi

    rm -f "$script"
    echo "$orig_val" > "$script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_rechunk_budget >/dev/null 2>&1 \
        || die "check_rechunk_budget failed after restoration!"
    log "check_rechunk_budget negative test passed."
}

# 19. Test core bake reconciliation
test_bake_core_reconcile() {
    log "Testing core bake reconciliation..."
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

    if MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1; then
        cp "$bak_file" "$toml_file" && rm -f "$bak_file"
        MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
        die "generate-bake-plan.py --check passed despite phantom ref added to core!"
    fi

    cp "$bak_file" "$toml_file" && rm -f "$bak_file"
    MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
    MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" --check >/dev/null 2>&1 \
        || die "generate-bake-plan.py --check failed after restoration!"
    log "test_bake_core_reconcile negative test passed."
}

# 20. Test check_nested_podman_caps
test_nested_podman_retry() {
    log "Testing check_nested_podman_caps..."
    local script="${ROOT}/usr/libexec/mios/57-mios-sys-build.sh"
    local orig_val
    orig_val="$(cat "$script")"
    echo "$orig_val" > "$script"
    sed -i 's/build_image_with_retry/build_image_no_retry/g' "$script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1; then
        rm -f "$script"
        echo "$orig_val" > "$script"
        die "check_nested_podman_caps passed despite missing build_image_with_retry!"
    fi

    rm -f "$script"
    echo "$orig_val" > "$script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nested_podman_caps >/dev/null 2>&1 \
        || die "check_nested_podman_caps failed after restoration!"
    log "test_nested_podman_retry negative test passed."
}

# 21. Test check_gate_registry
test_gate_registry() {
    log "Testing check_gate_registry..."
    local script="${ROOT}/automation/98-drift-checks.sh"
    local orig_val
    orig_val="$(cat "$script")"
    echo "$orig_val" > "$script"

    sed -i '/check_dead_lane() {/i check_dead_lane() { return 0; }\n' "$script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "$script" check_gate_registry >/dev/null 2>&1; then
        rm -f "$script"
        echo "$orig_val" > "$script"
        die "check_gate_registry passed despite duplicate check_dead_lane definition!"
    fi

    rm -f "$script"
    echo "$orig_val" > "$script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "$script" check_gate_registry >/dev/null 2>&1 \
        || die "check_gate_registry failed after restoration!"
    log "test_gate_registry negative test passed."
}

# 22. Test check_test_hermeticity
test_test_hermeticity() {
    log "Testing check_test_hermeticity..."
    local temp_test="${ROOT}/tests/test_fake_live_resource.py"

    cat << 'EOF' > "$temp_test"
import psycopg
def test_live():
    conn = psycopg.connect("dbname=mios user=mios")
EOF

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_test_hermeticity >/dev/null 2>&1; then
        rm -f "$temp_test"
        die "check_test_hermeticity passed despite unguarded psycopg.connect call!"
    fi

    rm -f "$temp_test"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_test_hermeticity >/dev/null 2>&1 \
        || die "check_test_hermeticity failed after restoration!"
    log "test_test_hermeticity negative test passed."
}

# 23. Test check_no_mkdir_in_var
test_no_mkdir_in_var() {
    log "Testing check_no_mkdir_in_var..."
    local temp_script="${ROOT}/automation/99-fake-var-mkdir.sh"
    echo 'mkdir -p /var/log/fake_test' > "$temp_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_no_mkdir_in_var >/dev/null 2>&1; then
        rm -f "$temp_script"
        die "check_no_mkdir_in_var passed despite imperative /var mkdir!"
    fi

    rm -f "$temp_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_no_mkdir_in_var >/dev/null 2>&1 \
        || die "check_no_mkdir_in_var failed after restoration!"
    log "test_no_mkdir_in_var negative test passed."
}

# 24. Test check_quadlet_privilege
test_quadlet_privilege() {
    log "Testing check_quadlet_privilege..."
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
        die "check_quadlet_privilege passed despite un-allowlisted User=root!"
    fi

    rm -f "$temp_q"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_quadlet_privilege >/dev/null 2>&1 \
        || die "check_quadlet_privilege failed after restoration!"
    log "test_quadlet_privilege negative test passed."
}

# 25. Test check_lint_is_final
test_lint_is_final() {
    log "Testing check_lint_is_final..."
    local cf="${ROOT}/Containerfile"
    local orig_val
    orig_val="$(cat "$cf")"
    echo "$orig_val" > "$cf"
    sed -i '/RUN bootc container lint/d' "$cf"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_lint_is_final >/dev/null 2>&1; then
        rm -f "$cf"
        echo "$orig_val" > "$cf"
        die "check_lint_is_final passed despite missing bootc container lint!"
    fi

    rm -f "$cf"
    echo "$orig_val" > "$cf"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_lint_is_final >/dev/null 2>&1 \
        || die "check_lint_is_final failed after restoration!"
    log "test_lint_is_final negative test passed."
}

# 26. Test check_firstboot_degrade_open
test_firstboot_degrade_open() {
    log "Testing check_firstboot_degrade_open..."
    local temp_fb="${ROOT}/usr/libexec/mios/mios-fake-firstboot.sh"
    cat << 'EOF' > "$temp_fb"
#!/usr/bin/env bash
set -e
echo "no degrade open escape here"
EOF

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_degrade_open >/dev/null 2>&1; then
        rm -f "$temp_fb"
        die "check_firstboot_degrade_open passed despite set -e without degrade escape!"
    fi

    rm -f "$temp_fb"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_firstboot_degrade_open >/dev/null 2>&1 \
        || die "check_firstboot_degrade_open failed after restoration!"
    log "test_firstboot_degrade_open negative test passed."
}

# 27. Test MIOS_DRIFT_REQUIRE_TOOLS
test_require_tools() {
    log "Testing MIOS_DRIFT_REQUIRE_TOOLS..."
    local tmp_bin="${ROOT}/tmp_no_python"
    mkdir -p "$tmp_bin"

    if MIOS_DRIFT_REQUIRE_TOOLS=1 PATH="$tmp_bin" bash "${ROOT}/automation/98-drift-checks.sh" check_cli_eval_safety >/dev/null 2>&1; then
        rm -rf "$tmp_bin"
        die "check_cli_eval_safety passed despite missing python3 when MIOS_DRIFT_REQUIRE_TOOLS=1!"
    fi

    rm -rf "$tmp_bin"
    log "test_require_tools negative test passed."
}

# 28. Test 97-ssot-lint.sh deadkey
test_ssot_lint_deadkey() {
    log "Testing 97-ssot-lint.sh dead-key injection..."
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
        die "97-ssot-lint.sh passed despite dead key injection!"
    fi

    rm -f "$temp_q"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/97-ssot-lint.sh" >/dev/null 2>&1 \
        || die "97-ssot-lint.sh failed after restoration!"
    log "test_ssot_lint_deadkey negative test passed."
}

# 29. Test check_soft_mode_not_committed
test_soft_mode_not_committed() {
    log "Testing check_soft_mode_not_committed..."
    local gha_file="${ROOT}/.github/workflows/mios-ci.yml"
    local orig_val
    orig_val="$(cat "$gha_file")"
    printf '%s\n%s\n' "$orig_val" "MIOS_DRIFT_CHECK_SOFT=1" > "$gha_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_soft_mode_not_committed >/dev/null 2>&1; then
        rm -f "$gha_file"
        echo "$orig_val" > "$gha_file"
        die "check_soft_mode_not_committed passed despite committed MIOS_DRIFT_CHECK_SOFT=1!"
    fi

    rm -f "$gha_file"
    echo "$orig_val" > "$gha_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_soft_mode_not_committed >/dev/null 2>&1 \
        || die "check_soft_mode_not_committed failed after restoration!"
    log "test_soft_mode_not_committed negative test passed."
}

# 30. Test check_oci_archive_path
test_oci_archive_path() {
    log "Testing check_oci_archive_path..."
    local stage_script="${ROOT}/usr/libexec/mios/mios-stage-oci-archive"
    local orig_val
    orig_val="$(cat "$stage_script")"
    rm -f "$stage_script"
    echo "$orig_val" > "$stage_script"
    sed -i 's/mios-latest\.tar/mios-mismatched-name\.tar/g' "$stage_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_oci_archive_path >/dev/null 2>&1; then
        rm -f "$stage_script"
        echo "$orig_val" > "$stage_script"
        die "check_oci_archive_path passed despite producer/consumer path mismatch!"
    fi

    rm -f "$stage_script"
    echo "$orig_val" > "$stage_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_oci_archive_path >/dev/null 2>&1 \
        || die "check_oci_archive_path failed after restoration!"
    log "test_oci_archive_path negative test passed."
}

# 31. Test check_replaceme_mount_substitution
test_replaceme_mount_substitution() {
    log "Testing check_replaceme_mount_substitution..."
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
        die "check_replaceme_mount_substitution passed despite raw-mounted REPLACEME template!"
    fi

    rm -f "$justfile"
    echo "$orig_val" > "$justfile"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_replaceme_mount_substitution >/dev/null 2>&1 \
        || die "check_replaceme_mount_substitution failed after restoration!"
    log "test_replaceme_mount_substitution negative test passed."
}

# 32. Test check_kickstart_shell_syntax
test_kickstart_shell_syntax() {
    log "Testing check_kickstart_shell_syntax..."
    local cfg="${ROOT}/usr/share/mios/ventoy/mios-kickstart.cfg"
    local orig_val
    orig_val="$(cat "$cfg")"
    echo "$orig_val" > "$cfg"

    rm -f "$cfg"
    echo "$orig_val" > "$cfg"
    cat << 'EOF' >> "$cfg"
%post
if [ true ]; then
  echo "missing fi"
%end
EOF

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_kickstart_shell_syntax >/dev/null 2>&1; then
        rm -f "$cfg"
        echo "$orig_val" > "$cfg"
        die "check_kickstart_shell_syntax passed despite invalid bash syntax in %post!"
    fi

    rm -f "$cfg"
    echo "$orig_val" > "$cfg"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_kickstart_shell_syntax >/dev/null 2>&1 \
        || die "check_kickstart_shell_syntax failed after restoration!"
    log "test_kickstart_shell_syntax negative test passed."
}

# 33. Test check_offline_install_invariant
test_offline_install_invariant() {
    log "Testing check_offline_install_invariant..."
    local install_script="${ROOT}/tools/install.sh"
    local orig_val
    orig_val="$(cat "$install_script")"
    rm -f "$install_script"
    echo "$orig_val" > "$install_script"

    echo "podman pull ghcr.io/ublue-os/ucore-hci:latest" >> "$install_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_offline_install_invariant >/dev/null 2>&1; then
        rm -f "$install_script"
        echo "$orig_val" > "$install_script"
        die "check_offline_install_invariant passed despite injected podman pull!"
    fi

    rm -f "$install_script"
    echo "$orig_val" > "$install_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_offline_install_invariant >/dev/null 2>&1 \
        || die "check_offline_install_invariant failed after restoration!"
    log "test_offline_install_invariant negative test passed."
}

# 34. Test check_installer_family_roles
test_installer_family_roles() {
    log "Testing check_installer_family_roles..."
    local s_script="${ROOT}/install.sh"
    local orig_val
    orig_val="$(cat "$s_script")"
    rm -f "$s_script"
    echo "$orig_val" > "$s_script"

    sed -i 's/MIOS_INSTALLER_ROLE=root-overlay-redirector/MIOS_INSTALLER_ROLE=bootc-baremetal-disk-installer/g' "$s_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_installer_family_roles >/dev/null 2>&1; then
        rm -f "$s_script"
        echo "$orig_val" > "$s_script"
        die "check_installer_family_roles passed despite duplicate role marker!"
    fi

    rm -f "$s_script"
    echo "$orig_val" > "$s_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_installer_family_roles >/dev/null 2>&1 \
        || die "check_installer_family_roles failed after restoration!"
    log "test_installer_family_roles negative test passed."
}

# 35. Test check_bib_configs_projection
test_bib_configs_projection() {
    log "Testing check_bib_configs_projection..."
    local bib_file="${ROOT}/config/artifacts/bib.toml"
    local orig_val
    orig_val="$(cat "$bib_file")"
    rm -f "$bib_file"
    echo "$orig_val" > "$bib_file"

    sed -i 's/minsize = "80 GiB"/minsize = "999 GiB"/g' "$bib_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bib_configs_projection >/dev/null 2>&1; then
        rm -f "$bib_file"
        echo "$orig_val" > "$bib_file"
        die "check_bib_configs_projection passed despite unprojected minsize edit!"
    fi

    rm -f "$bib_file"
    echo "$orig_val" > "$bib_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bib_configs_projection >/dev/null 2>&1 \
        || die "check_bib_configs_projection failed after restoration!"
    log "test_bib_configs_projection negative test passed."
}

# 36. Test check_ssot_lint_equivalence
test_ssot_lint_equivalence() {
    log "Testing check_ssot_lint_equivalence..."
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ssot_lint_equivalence >/dev/null 2>&1 \
        || die "check_ssot_lint_equivalence failed!"
    log "test_ssot_lint_equivalence negative test passed."
}

# 37. Test check_repo_partition_label_ssot
test_repo_partition_label_ssot() {
    log "Testing check_repo_partition_label_ssot..."
    local install_script="${ROOT}/tools/install.sh"
    local orig_val
    orig_val="$(cat "$install_script")"
    rm -f "$install_script"
    echo "$orig_val" > "$install_script"

    sed -i 's/MiOS-Repo/MiOS-MismatchedLabel/g' "$install_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_repo_partition_label_ssot >/dev/null 2>&1; then
        rm -f "$install_script"
        echo "$orig_val" > "$install_script"
        die "check_repo_partition_label_ssot passed despite label mismatch!"
    fi

    rm -f "$install_script"
    echo "$orig_val" > "$install_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_repo_partition_label_ssot >/dev/null 2>&1 \
        || die "check_repo_partition_label_ssot failed after restoration!"
    log "test_repo_partition_label_ssot negative test passed."
}

# 38. Test check_bib_single_config_invariant
test_bib_single_config_invariant() {
    log "Testing check_bib_single_config_invariant..."
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
        die "check_bib_single_config_invariant passed despite double config mount!"
    fi

    rm -f "$justfile"
    echo "$orig_val" > "$justfile"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bib_single_config_invariant >/dev/null 2>&1 \
        || die "check_bib_single_config_invariant failed after restoration!"
    log "test_bib_single_config_invariant negative test passed."
}

# 39. Test mios-hardcode-lint plaintext chpasswd
test_chpasswd_plaintext() {
    log "Testing mios-hardcode-lint plaintext chpasswd..."
    local autorun_script="${ROOT}/usr/share/mios/ventoy/autorun/01-sysrescue-firstboot.sh"
    local bak_file="${autorun_script}.bak"
    cp "$autorun_script" "$bak_file"

    echo 'echo "root:hardcodedpass" | chpasswd' >> "$autorun_script"

    if python3 "${ROOT}/usr/libexec/mios/mios-hardcode-lint" "${ROOT}" >/dev/null 2>&1; then
        cp "$bak_file" "$autorun_script" && rm -f "$bak_file"
        die "mios-hardcode-lint passed despite plaintext chpasswd injection!"
    fi

    cp "$bak_file" "$autorun_script" && rm -f "$bak_file"
    python3 "${ROOT}/usr/libexec/mios/mios-hardcode-lint" "${ROOT}" >/dev/null 2>&1 \
        || die "mios-hardcode-lint failed after restoration!"
    log "test_chpasswd_plaintext negative test passed."
}

# 40. Test check_build_artifacts_output_dir
test_build_artifacts_output_dir() {
    log "Testing check_build_artifacts_output_dir..."
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
        die "check_build_artifacts_output_dir passed despite stray output/ path!"
    fi

    rm -f "$justfile"
    echo "$orig_val" > "$justfile"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_build_artifacts_output_dir >/dev/null 2>&1 \
        || die "check_build_artifacts_output_dir failed after restoration!"
    log "test_build_artifacts_output_dir negative test passed."
}

# 41. Test check_win11_vm_template_xml
test_win11_vm_template_xml() {
    log "Testing check_win11_vm_template_xml..."
    local xml_file="${ROOT}/tools/win11-secureboot-template.xml"
    local orig_val
    orig_val="$(cat "$xml_file")"
    rm -f "$xml_file"
    echo "$orig_val" > "$xml_file"

    echo '<invalid_xml>unclosed tag' >> "$xml_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_win11_vm_template_xml >/dev/null 2>&1; then
        rm -f "$xml_file"
        echo "$orig_val" > "$xml_file"
        die "check_win11_vm_template_xml passed despite invalid XML!"
    fi

    rm -f "$xml_file"
    echo "$orig_val" > "$xml_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_win11_vm_template_xml >/dev/null 2>&1 \
        || die "check_win11_vm_template_xml failed after restoration!"
    log "test_win11_vm_template_xml negative test passed."
}

# 42. Test check_ipa_enroll_projection
test_ipa_enroll_projection() {
    log "Testing check_ipa_enroll_projection..."
    local target_file="${ROOT}/etc/mios/ipa-enroll.env"
    [[ -f "$target_file" ]] || { mkdir -p "$(dirname "$target_file")"; MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-ipa-enroll-env.py" >/dev/null 2>&1 || true; }

    echo 'MIOS_IPA_REALM="MUTATED.REALM"' >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ipa_enroll_projection >/dev/null 2>&1; then
        MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-ipa-enroll-env.py" >/dev/null 2>&1 || true
        die "check_ipa_enroll_projection passed despite mutated target file!"
    fi

    MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-ipa-enroll-env.py" >/dev/null 2>&1 || true
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_ipa_enroll_projection >/dev/null 2>&1 \
        || die "check_ipa_enroll_projection failed after restoration!"
    log "test_ipa_enroll_projection negative test passed."
}

# 43. Test check_uki_cmdline_projection
test_uki_cmdline_projection() {
    log "Testing check_uki_cmdline_projection..."
    local target_file="${ROOT}/usr/lib/kernel/cmdline"
    [[ -f "$target_file" ]] || { mkdir -p "$(dirname "$target_file")"; MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-uki-cmdline.py" >/dev/null 2>&1 || true; }

    echo 'mutated_bogus_karg=1' >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_uki_cmdline_projection >/dev/null 2>&1; then
        MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-uki-cmdline.py" >/dev/null 2>&1 || true
        die "check_uki_cmdline_projection passed despite mutated cmdline!"
    fi

    MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-uki-cmdline.py" >/dev/null 2>&1 || true
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_uki_cmdline_projection >/dev/null 2>&1 \
        || die "check_uki_cmdline_projection failed after restoration!"
    log "test_uki_cmdline_projection negative test passed."
}

# 44. Test check_composefs_projection
test_composefs_projection() {
    log "Testing check_composefs_projection..."
    local target_file="${ROOT}/usr/lib/ostree/prepare-root.conf"
    local orig_val
    orig_val="$(cat "$target_file")"
    echo "$orig_val" > "$target_file"

    echo '[composefs]' > "$target_file"
    echo 'enabled = off' >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_composefs_projection >/dev/null 2>&1; then
        echo "$orig_val" > "$target_file"
        die "check_composefs_projection passed despite mutated prepare-root.conf!"
    fi

    echo "$orig_val" > "$target_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_composefs_projection >/dev/null 2>&1 \
        || die "check_composefs_projection failed after restoration!"
    log "test_composefs_projection negative test passed."
}

# 45. Test check_cockpit_projection
test_cockpit_projection() {
    log "Testing check_cockpit_projection..."
    local target_file="${ROOT}/etc/cockpit/cockpit.conf"
    [[ -f "$target_file" ]] || { mkdir -p "$(dirname "$target_file")"; MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-cockpit-conf.py" >/dev/null 2>&1 || true; }

    echo 'AllowUnencrypted = false' >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cockpit_projection >/dev/null 2>&1; then
        MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-cockpit-conf.py" >/dev/null 2>&1 || true
        die "check_cockpit_projection passed despite mutated cockpit.conf!"
    fi

    MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-cockpit-conf.py" >/dev/null 2>&1 || true
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_cockpit_projection >/dev/null 2>&1 \
        || die "check_cockpit_projection failed after restoration!"
    log "test_cockpit_projection negative test passed."
}

# 46. Test check_chrony_ptp_dropin
test_chrony_ptp_dropin() {
    log "Testing check_chrony_ptp_dropin..."
    local dropin_script="${ROOT}/usr/libexec/mios/mios-chrony-ptp-dropin"
    local orig_val
    orig_val="$(cat "$dropin_script")"
    rm -f "$dropin_script"
    echo "$orig_val" > "$dropin_script"

    echo 'syntax error ((((' >> "$dropin_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_chrony_ptp_dropin >/dev/null 2>&1; then
        rm -f "$dropin_script"
        echo "$orig_val" > "$dropin_script"
        die "check_chrony_ptp_dropin passed despite syntax error!"
    fi

    rm -f "$dropin_script"
    echo "$orig_val" > "$dropin_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_chrony_ptp_dropin >/dev/null 2>&1 \
        || die "check_chrony_ptp_dropin failed after restoration!"
    log "test_chrony_ptp_dropin negative test passed."
}

# 47. Test check_chrony_projection
test_chrony_projection() {
    log "Testing check_chrony_projection..."
    local target_file="${ROOT}/etc/chrony.conf"
    local orig_val
    orig_val="$(cat "$target_file")"
    rm -f "$target_file"
    echo "$orig_val" > "$target_file"

    echo "server 199.99.99.99 iburst" >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_chrony_projection >/dev/null 2>&1; then
        rm -f "$target_file"
        echo "$orig_val" > "$target_file"
        die "check_chrony_projection passed despite mutated chrony.conf!"
    fi

    rm -f "$target_file"
    echo "$orig_val" > "$target_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_chrony_projection >/dev/null 2>&1 \
        || die "check_chrony_projection failed after restoration!"
    log "test_chrony_projection negative test passed."
}

# 48. Test check_nut_projection
test_nut_projection() {
    log "Testing check_nut_projection..."
    local target_file="${ROOT}/etc/ups/ups.conf"
    local orig_val
    orig_val="$(cat "$target_file")"
    rm -f "$target_file"
    echo "$orig_val" > "$target_file"

    echo "driver = bogus" >> "$target_file"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nut_projection >/dev/null 2>&1; then
        rm -f "$target_file"
        echo "$orig_val" > "$target_file"
        die "check_nut_projection passed despite mutated ups.conf!"
    fi

    rm -f "$target_file"
    echo "$orig_val" > "$target_file"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_nut_projection >/dev/null 2>&1 \
        || die "check_nut_projection failed after restoration!"
    log "test_nut_projection negative test passed."
}

# 49. Test check_renderer_gate_coverage
test_renderer_gate_coverage() {
    log "Testing check_renderer_gate_coverage..."
    local bogus_script="${ROOT}/automation/99-bogus-render.sh"
    echo '#!/usr/bin/env bash' > "$bogus_script"
    echo 'echo "bogus render"' >> "$bogus_script"
    chmod +x "$bogus_script"

    if MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_renderer_gate_coverage >/dev/null 2>&1; then
        rm -f "$bogus_script"
        die "check_renderer_gate_coverage passed despite unmapped 99-bogus-render.sh!"
    fi

    rm -f "$bogus_script"
    MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_renderer_gate_coverage >/dev/null 2>&1 \
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
        printf '%s\n%s\n' "$orig_val" "localhost/bogus-injected-image:latest" > "$plan_file"

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
        printf '%s\n%s\n' "$orig_val" ': "${MIOS_BUILD_BAKE_REFS_ZZZ:-}"' > "$target_sh"

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

# 52. Test check_deploy_plane
test_deploy_plane() {
    log "Testing check_deploy_plane..."
    local ks_file="${ROOT}/usr/share/mios/ventoy/mios-kickstart.cfg"
    if [ -f "$ks_file" ]; then
        local orig_val
        orig_val="$(cat "$ks_file")"
        echo "$orig_val" > "$ks_file"
        grep -v "MIOS_FHS_TOTAL_ROOT_MERGE=1" "$ks_file" > "${ks_file}.tmp" && mv "${ks_file}.tmp" "$ks_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_deploy_plane >/dev/null 2>&1; then
            echo "$orig_val" > "$ks_file"
            die "check_deploy_plane passed despite missing MIOS_FHS_TOTAL_ROOT_MERGE=1!"
        fi

        echo "$orig_val" > "$ks_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_deploy_plane >/dev/null 2>&1 \
            || die "check_deploy_plane failed after restoration!"
    fi
    log "test_deploy_plane negative test passed."
}

# 53. Test check_sbom_metadata
test_sbom_metadata() {
    log "Testing check_sbom_metadata..."
    local sbom_dir="${ROOT}/usr/share/mios/artifacts/sbom"
    mkdir -p "$sbom_dir"
    local temp_tsv="${sbom_dir}/models.tsv"
    printf "name\tversion\tsha256\nmodel1\t1.0\tdeadbeef\n" > "$temp_tsv"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_sbom_metadata >/dev/null 2>&1; then
        rm -f "$temp_tsv"
        die "check_sbom_metadata passed despite malformed sha256!"
    fi

    rm -f "$temp_tsv"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_sbom_metadata >/dev/null 2>&1 \
        || die "check_sbom_metadata failed after cleanup!"
    log "test_sbom_metadata negative test passed."
}

# 54. Test check_clevis_luks
test_clevis_luks() {
    log "Testing check_clevis_luks..."
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    mkdir -p "${tmp_dir}/usr/share/mios"
    echo '[identity]' > "${tmp_dir}/usr/share/mios/mios.toml"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$tmp_dir" bash "${ROOT}/automation/98-drift-checks.sh" check_clevis_luks >/dev/null 2>&1; then
        rm -rf "$tmp_dir"
        die "check_clevis_luks passed despite malformed SSOT!"
    fi

    rm -rf "$tmp_dir"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_clevis_luks >/dev/null 2>&1 \
        || die "check_clevis_luks failed after cleanup!"
    log "test_clevis_luks negative test passed."
}

# 55. Test check_mini_vfio
test_mini_vfio() {
    log "Testing check_mini_vfio..."
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    mkdir -p "${tmp_dir}/usr/share/mios"
    echo '[identity]' > "${tmp_dir}/usr/share/mios/mios.toml"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$tmp_dir" bash "${ROOT}/automation/98-drift-checks.sh" check_mini_vfio >/dev/null 2>&1; then
        rm -rf "$tmp_dir"
        die "check_mini_vfio passed despite malformed SSOT!"
    fi

    rm -rf "$tmp_dir"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_mini_vfio >/dev/null 2>&1 \
        || die "check_mini_vfio failed after cleanup!"
    log "test_mini_vfio negative test passed."
}

# 56. Test check_hyprland_conf_heredoc
test_hyprland_heredoc() {
    log "Testing check_hyprland_conf_heredoc..."
    local conf_file="${ROOT}/usr/share/mios/hyprland/hyprland.conf"
    if [ -f "$conf_file" ]; then
        local orig_val
        orig_val="$(cat "$conf_file")"
        printf '%s\n%s\n' "$orig_val" "# INJECTED-DRIFT" > "$conf_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_hyprland_conf_heredoc >/dev/null 2>&1; then
            echo "$orig_val" > "$conf_file"
            die "check_hyprland_conf_heredoc passed despite injected drift!"
        fi

        echo "$orig_val" > "$conf_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_hyprland_conf_heredoc >/dev/null 2>&1 \
            || die "check_hyprland_conf_heredoc failed after restoration!"
    fi
    log "test_hyprland_heredoc negative test passed."
}

# 57. Test check_target_languages
test_target_languages() {
    log "Testing check_target_languages..."
    local bogus_file="${ROOT}/usr/libexec/mios/bogus_script.rb"
    echo 'puts "ruby disallowed"' > "$bogus_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_target_languages >/dev/null 2>&1; then
        rm -f "$bogus_file"
        die "check_target_languages passed despite disallowed ruby script!"
    fi

    rm -f "$bogus_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_target_languages >/dev/null 2>&1 \
        || die "check_target_languages failed after cleanup!"
    log "test_target_languages negative test passed."
}

# 58. Test check_roadmap_index
test_roadmap_index() {
    log "Testing check_roadmap_index..."
    local roadmap_file="${ROOT}/ROADMAP.md"
    if [ -f "$roadmap_file" ]; then
        local orig_val
        orig_val="$(cat "$roadmap_file")"
        echo "$orig_val" > "$roadmap_file"
        sed -i 's/\*\*Done\*\*: [0-9]*/\*\*Done\*\*: 99999/g' "$roadmap_file" 2>/dev/null || true

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_roadmap_index >/dev/null 2>&1; then
            echo "$orig_val" > "$roadmap_file"
            die "check_roadmap_index passed despite corrupted rollup!"
        fi

        echo "$orig_val" > "$roadmap_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_roadmap_index >/dev/null 2>&1 \
            || die "check_roadmap_index failed after restoration!"
    fi
    log "test_roadmap_index negative test passed."
}

# 59. Test check_templates_compilation
test_templates_compilation() {
    log "Testing check_templates_compilation..."
    local tmpl_file="${ROOT}/usr/share/mios/templates/toml-config"
    if [ -f "$tmpl_file" ]; then
        local orig_val
        orig_val="$(cat "$tmpl_file")"
        printf '%s\n%s\n' "$orig_val" 'INVALID_SYNTAX_BOGUS {{' > "$tmpl_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_templates_compilation >/dev/null 2>&1; then
            echo "$orig_val" > "$tmpl_file"
            die "check_templates_compilation passed despite invalid template!"
        fi

        echo "$orig_val" > "$tmpl_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_templates_compilation >/dev/null 2>&1 \
            || die "check_templates_compilation failed after restoration!"
    fi
    log "test_templates_compilation negative test passed."
}

# 60. Test check_impossible_eol_regressions
test_impossible_eol() {
    log "Testing check_impossible_eol_regressions..."
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    if [ -f "$toml_file" ]; then
        local orig_val
        orig_val="$(cat "$toml_file")"
        printf '%s\n%s\n' "$orig_val" 'eol_test_pkg = ["tang"]' > "$toml_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_impossible_eol_regressions >/dev/null 2>&1; then
            echo "$orig_val" > "$toml_file"
            die "check_impossible_eol_regressions passed despite EOL tang package!"
        fi

        echo "$orig_val" > "$toml_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_impossible_eol_regressions >/dev/null 2>&1 \
            || die "check_impossible_eol_regressions failed after restoration!"
    fi
    log "test_impossible_eol negative test passed."
}

# 61. Test check_smoke_manifest
test_smoke_manifest() {
    log "Testing check_smoke_manifest..."
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    if [ -f "$toml_file" ]; then
        local orig_val
        orig_val="$(cat "$toml_file")"
        printf '%s\n%s\n' "$orig_val" 'shims = ["usr/libexec/mios/non-existent-bogus-shim"]' > "$toml_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_smoke_manifest >/dev/null 2>&1; then
            echo "$orig_val" > "$toml_file"
            die "check_smoke_manifest passed despite missing component path!"
        fi

        echo "$orig_val" > "$toml_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_smoke_manifest >/dev/null 2>&1 \
            || die "check_smoke_manifest failed after restoration!"
    fi
    log "test_smoke_manifest negative test passed."
}

# 62. Test check_negative_coverage
test_negative_coverage() {
    log "Testing check_negative_coverage..."
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    if [ -f "$toml_file" ]; then
        local orig_val
        orig_val="$(cat "$toml_file")"
        echo "$orig_val" > "$toml_file"
        grep -v '"check_agent_schema"' "$toml_file" > "${toml_file}.tmp" && mv "${toml_file}.tmp" "$toml_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_negative_coverage >/dev/null 2>&1; then
            echo "$orig_val" > "$toml_file"
            die "check_negative_coverage passed despite removed exempt check!"
        fi

        echo "$orig_val" > "$toml_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_negative_coverage >/dev/null 2>&1 \
            || die "check_negative_coverage failed after restoration!"
    fi
    log "test_negative_coverage negative test passed."
}

# 63. Test check_verb_templates
test_verb_templates() {
    log "Testing check_verb_templates..."
    local toml_file="${ROOT}/usr/share/mios/mios.toml"
    if [ -f "$toml_file" ]; then
        local orig_val
        orig_val="$(cat "$toml_file")"
        echo "$orig_val" > "$toml_file"
        printf '\n[verbs.bogus_broken]\ncmd = "echo {invalid_placeholder"\n' >> "$toml_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_verb_templates >/dev/null 2>&1; then
            echo "$orig_val" > "$toml_file"
            die "check_verb_templates passed despite invalid verb template!"
        fi

        echo "$orig_val" > "$toml_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_verb_templates >/dev/null 2>&1 \
            || die "check_verb_templates failed after restoration!"
    fi
    log "test_verb_templates negative test passed."
}

# 64. Test check_pipe_boundaries
test_pipe_boundaries() {
    log "Testing check_pipe_boundaries..."
    local manifest="${ROOT}/usr/share/mios/pipe-boundaries.manifest.json"
    if [ -f "$manifest" ]; then
        local orig_val
        orig_val="$(cat "$manifest")"
        rm -f "$manifest"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_pipe_boundaries >/dev/null 2>&1; then
            echo "$orig_val" > "$manifest"
            die "check_pipe_boundaries passed despite missing manifest file!"
        fi

        echo "$orig_val" > "$manifest"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_pipe_boundaries >/dev/null 2>&1 \
            || die "check_pipe_boundaries failed after restoration!"
    fi
    log "test_pipe_boundaries negative test passed."
}

# 65. Test check_vllm_name_canonical
test_vllm_name_canonical() {
    log "Testing check_vllm_name_canonical..."
    local manifest="${ROOT}/root-manifest.json"
    if [ -f "$manifest" ]; then
        local orig_val
        orig_val="$(cat "$manifest")"
        echo '"MIOS_AI_VLLM_SERVED_NAME": "test"' >> "$manifest"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_vllm_name_canonical >/dev/null 2>&1; then
            echo "$orig_val" > "$manifest"
            die "check_vllm_name_canonical passed despite legacy long name!"
        fi

        echo "$orig_val" > "$manifest"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_vllm_name_canonical >/dev/null 2>&1 \
            || die "check_vllm_name_canonical failed after restoration!"
    fi
    log "test_vllm_name_canonical negative test passed."
}

# 66. Test check_pipe_extraction_parity
test_pipe_extraction_parity() {
    log "Testing check_pipe_extraction_parity..."
    local test_file="${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/observability/session_events.py"
    if [ -f "$test_file" ]; then
        local orig_val
        orig_val="$(cat "$test_file")"
        printf '%s\n%s\n' "$orig_val" "import server" > "$test_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_pipe_extraction_parity >/dev/null 2>&1; then
            echo "$orig_val" > "$test_file"
            die "check_pipe_extraction_parity passed despite forbidden import server!"
        fi

        echo "$orig_val" > "$test_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_pipe_extraction_parity >/dev/null 2>&1 \
            || die "check_pipe_extraction_parity failed after restoration!"
    fi
    log "test_pipe_extraction_parity negative test passed."
}

# 67. Test check_bake_plan
test_bake_plan() {
    log "Testing check_bake_plan..."
    local plan_file="${ROOT}/usr/lib/mios/bake/plan.d/03-extra.list"
    if [ -f "$plan_file" ]; then
        local bak_file="${plan_file}.bak"
        cp "$plan_file" "$bak_file"
        echo "docker.io/library/bogus-image-never-exists:latest" >> "$plan_file"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_plan >/dev/null 2>&1; then
            cp "$bak_file" "$plan_file" && rm -f "$bak_file"
            MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
            die "check_bake_plan passed despite stale/invalid bake plan!"
        fi

        cp "$bak_file" "$plan_file" && rm -f "$bak_file"
        MIOS_ROOT="$ROOT" python3 "${ROOT}/tools/generate-bake-plan.py" >/dev/null 2>&1 || true
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_plan >/dev/null 2>&1 \
            || die "check_bake_plan failed after restoration!"
    fi
    log "test_bake_plan negative test passed."
}

# 68. Test check_bake_ref_defaults
test_bake_ref_defaults() {
    log "Testing check_bake_ref_defaults..."
    local test_sh="${ROOT}/automation/15-render-quadlets.sh"
    if [ -f "$test_sh" ]; then
        local orig_val
        orig_val="$(cat "$test_sh")"
        printf '%s\n%s\n' "$orig_val" ': "${MIOS_BUILD_BAKE_REFS_ZZZ:-}"' > "$test_sh"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_ref_defaults >/dev/null 2>&1; then
            echo "$orig_val" > "$test_sh"
            die "check_bake_ref_defaults passed despite empty bake ref default!"
        fi

        echo "$orig_val" > "$test_sh"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_bake_ref_defaults >/dev/null 2>&1 \
            || die "check_bake_ref_defaults failed after restoration!"
    fi
    log "test_bake_ref_defaults negative test passed."
}

# 69. Test check_deploy_plane
test_deploy_plane() {
    log "Testing check_deploy_plane..."
    local cfg="${ROOT}/usr/share/mios/ventoy/mios-kickstart.cfg"
    if [ -f "$cfg" ]; then
        local orig_val
        orig_val="$(cat "$cfg")"
        echo "$orig_val" > "$cfg"
        grep -v "MIOS_FHS_TOTAL_ROOT_MERGE=1" "$cfg" > "${cfg}.tmp" && mv "${cfg}.tmp" "$cfg"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_deploy_plane >/dev/null 2>&1; then
            echo "$orig_val" > "$cfg"
            die "check_deploy_plane passed despite missing MIOS_FHS_TOTAL_ROOT_MERGE=1!"
        fi

        echo "$orig_val" > "$cfg"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_deploy_plane >/dev/null 2>&1 \
            || die "check_deploy_plane failed after restoration!"
    fi
    log "test_deploy_plane negative test passed."
}

# 70. Test check_sbom_metadata
test_sbom_metadata() {
    log "Testing check_sbom_metadata..."
    local sbom_file="${ROOT}/usr/share/mios/artifacts/sbom/models.tsv"
    local dir
    dir="$(dirname "$sbom_file")"
    mkdir -p "$dir"
    printf "name\tversion\tsha256\turl\nmodel1\t1.0\tdeadbeef\thttps://example.com\n" > "$sbom_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_sbom_metadata >/dev/null 2>&1; then
        rm -f "$sbom_file"
        die "check_sbom_metadata passed despite invalid sha256!"
    fi

    rm -f "$sbom_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_sbom_metadata >/dev/null 2>&1 \
        || die "check_sbom_metadata failed after restoration!"
    log "test_sbom_metadata negative test passed."
}

# 71. Test check_clevis_luks
test_clevis_luks() {
    log "Testing check_clevis_luks..."
    local gen_script="${ROOT}/usr/libexec/mios/mios-clevis-luks-gen"
    if [ -f "$gen_script" ]; then
        local bak_file="${gen_script}.bak"
        cp "$gen_script" "$bak_file"
        python3 -c "import sys, os; os.chmod(sys.argv[1], 0o666); open(sys.argv[1], 'w').write('echo \"BROKEN\"\n')" "$gen_script"
        python3 -c "import sys, os; os.chmod(sys.argv[1], 0o755)" "$gen_script" 2>/dev/null || true

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_clevis_luks >/dev/null 2>&1; then
            cp "$bak_file" "$gen_script" && rm -f "$bak_file"
            python3 -c "import sys, os; os.chmod(sys.argv[1], 0o755)" "$gen_script" 2>/dev/null || true
            die "check_clevis_luks passed despite broken generator script!"
        fi

        cp "$bak_file" "$gen_script" && rm -f "$bak_file"
        python3 -c "import sys, os; os.chmod(sys.argv[1], 0o755)" "$gen_script" 2>/dev/null || true
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_clevis_luks >/dev/null 2>&1 \
            || die "check_clevis_luks failed after restoration!"
    fi
    log "test_clevis_luks negative test passed."
}

# 72. Test check_mini_vfio
test_mini_vfio() {
    log "Testing check_mini_vfio..."
    local gen_script="${ROOT}/usr/libexec/mios/mios-mini-vfio-gen"
    if [ -f "$gen_script" ]; then
        local bak_file="${gen_script}.bak"
        cp "$gen_script" "$bak_file"
        python3 -c "import sys, os; os.chmod(sys.argv[1], 0o666); open(sys.argv[1], 'w').write('echo \"BROKEN\"\n')" "$gen_script"
        python3 -c "import sys, os; os.chmod(sys.argv[1], 0o755)" "$gen_script" 2>/dev/null || true

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_mini_vfio >/dev/null 2>&1; then
            cp "$bak_file" "$gen_script" && rm -f "$bak_file"
            python3 -c "import sys, os; os.chmod(sys.argv[1], 0o755)" "$gen_script" 2>/dev/null || true
            die "check_mini_vfio passed despite broken generator script!"
        fi

        cp "$bak_file" "$gen_script" && rm -f "$bak_file"
        python3 -c "import sys, os; os.chmod(sys.argv[1], 0o755)" "$gen_script" 2>/dev/null || true
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_mini_vfio >/dev/null 2>&1 \
            || die "check_mini_vfio failed after restoration!"
    fi
    log "test_mini_vfio negative test passed."
}

# 73. Test check_hyprland_conf_heredoc
test_hyprland_heredoc() {
    log "Testing check_hyprland_conf_heredoc..."
    local conf="${ROOT}/usr/share/mios/hyprland/hyprland.conf"
    if [ -f "$conf" ]; then
        local orig_val
        orig_val="$(cat "$conf")"
        printf '%s\n%s\n' "$orig_val" "# INJECTED-DRIFT" > "$conf"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_hyprland_conf_heredoc >/dev/null 2>&1; then
            echo "$orig_val" > "$conf"
            die "check_hyprland_conf_heredoc passed despite injected drift!"
        fi

        echo "$orig_val" > "$conf"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_hyprland_conf_heredoc >/dev/null 2>&1 \
            || die "check_hyprland_conf_heredoc failed after restoration!"
    fi
    log "test_hyprland_heredoc negative test passed."
}

# 74. Test check_target_languages
test_target_languages() {
    log "Testing check_target_languages..."
    local bogus_file="${ROOT}/usr/libexec/mios/bogus_lang_test.cpp"
    echo "// forbidden c++ file" > "$bogus_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_target_languages >/dev/null 2>&1; then
        rm -f "$bogus_file"
        die "check_target_languages passed despite forbidden C++ file!"
    fi

    rm -f "$bogus_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_target_languages >/dev/null 2>&1 \
        || die "check_target_languages failed after restoration!"
    log "test_target_languages negative test passed."
}

# 75. Test check_roadmap_index
test_roadmap_index() {
    log "Testing check_roadmap_index..."
    local rmap="${ROOT}/ROADMAP.md"
    if [ -f "$rmap" ]; then
        local orig_val
        orig_val="$(cat "$rmap")"
        echo "$orig_val" > "$rmap"
        sed -i 's/\*\*Done\*\*: [0-9]*/\*\*Done\*\*: 99999/g' "$rmap"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_roadmap_index >/dev/null 2>&1; then
            echo "$orig_val" > "$rmap"
            die "check_roadmap_index passed despite corrupted roadmap count!"
        fi

        echo "$orig_val" > "$rmap"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_roadmap_index >/dev/null 2>&1 \
            || die "check_roadmap_index failed after restoration!"
    fi
    log "test_roadmap_index negative test passed."
}

# 76. Test check_templates_compilation
test_templates_compilation() {
    log "Testing check_templates_compilation..."
    local tpl="${ROOT}/usr/share/mios/templates/toml-config"
    if [ -f "$tpl" ]; then
        local orig_val
        orig_val="$(cat "$tpl")"
        printf '%s\n%s\n' "$orig_val" "{{ invalid syntax placeholder" > "$tpl"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_templates_compilation >/dev/null 2>&1; then
            echo "$orig_val" > "$tpl"
            die "check_templates_compilation passed despite syntax error!"
        fi

        echo "$orig_val" > "$tpl"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_templates_compilation >/dev/null 2>&1 \
            || die "check_templates_compilation failed after restoration!"
    fi
    log "test_templates_compilation negative test passed."
}

# 77. Test check_impossible_eol_regressions
test_impossible_eol_regressions() {
    log "Testing check_impossible_eol_regressions..."
    local toml="${ROOT}/usr/share/mios/mios.toml"
    if [ -f "$toml" ]; then
        local orig_val
        orig_val="$(cat "$toml")"
        printf '%s\n%s\n' "$orig_val" 'eol_packages = ["tang"]' > "$toml"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_impossible_eol_regressions >/dev/null 2>&1; then
            echo "$orig_val" > "$toml"
            die "check_impossible_eol_regressions passed despite forbidden EOL package!"
        fi

        echo "$orig_val" > "$toml"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_impossible_eol_regressions >/dev/null 2>&1 \
            || die "check_impossible_eol_regressions failed after restoration!"
    fi
    log "test_impossible_eol negative test passed."
}

test_pipe_extraction_parity() {
    log "Testing check_pipe_extraction_parity..."
    local temp_file="${ROOT}/usr/lib/mios/agent-pipe/mios_pipe/temp_forbidden_import.py"
    echo "import server" > "$temp_file"

    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_pipe_extraction_parity >/dev/null 2>&1; then
        rm -f "$temp_file"
        die "check_pipe_extraction_parity passed despite mios_pipe importing server!"
    fi

    rm -f "$temp_file"
    MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_pipe_extraction_parity >/dev/null 2>&1 \
        || die "check_pipe_extraction_parity failed after restoration!"
    log "check_pipe_extraction_parity negative test passed."
}

test_smoke_manifest() {
    log "Testing check_smoke_manifest..."
    local toml="${ROOT}/usr/share/mios/mios.toml"
    if [ -f "$toml" ]; then
        local bak_file="${toml}.bak"
        cp "$toml" "$bak_file"
        echo '[testing.smoke_components]' >> "$toml"
        echo 'shims = ["nonexistent/path/to/shim"]' >> "$toml"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_smoke_manifest >/dev/null 2>&1; then
            cp "$bak_file" "$toml" && rm -f "$bak_file"
            die "check_smoke_manifest passed despite nonexistent shim path!"
        fi

        cp "$bak_file" "$toml" && rm -f "$bak_file"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_smoke_manifest >/dev/null 2>&1 \
            || die "check_smoke_manifest failed after restoration!"
    fi
    log "test_smoke_manifest negative test passed."
}

test_negative_coverage() {
    log "Testing check_negative_coverage..."
    local checks_sh="${ROOT}/automation/98-drift-checks.sh"
    if [ -f "$checks_sh" ]; then
        local orig_val
        orig_val="$(cat "$checks_sh")"
        echo "$orig_val" > "$checks_sh"
        sed -i 's/check_pipe_extraction_parity/check_pipe_extraction_parity\n    check_bogus_uncovered_gate/' "$checks_sh"

        if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_negative_coverage >/dev/null 2>&1; then
            echo "$orig_val" > "$checks_sh"
            die "check_negative_coverage passed despite uncovered gate!"
        fi

        echo "$orig_val" > "$checks_sh"
        MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_CHECK_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" check_negative_coverage >/dev/null 2>&1 \
            || die "check_negative_coverage failed after restoration!"
    fi
    log "test_negative_coverage negative test passed."
}

main() {
    log "Starting negative-test suite..."
    test_version_ssot
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
    test_impossible_eol_regressions
    test_smoke_manifest
    test_negative_coverage
    test_verb_templates
    test_pipe_boundaries
    test_vllm_name_canonical
    test_pipe_extraction_parity
    log "All negative tests completed successfully!"
}

main "$@"
