<!-- AI-hint: Prioritized MiOS security-audit remediation plan (P0..P2) with file:line evidence and drop-in artifacts: PAT rotation + secret-store, cosign sign->VERIFY gate (CI + runtime policy.json from SSOT), SBOM digest/sha completeness, nft egress firewall from [security.egress] SSOT, and least-privilege for the Law-10 privileged Quadlets. -->
<!-- AI-related: usr/share/mios/mios.toml, .github/workflows/mios-ci.yml, usr/lib/containers/policy.json, tools/generate-cosign-policy.py, tools/generate-egress-firewall.py, usr/share/mios/security/egress.nft, usr/share/mios/artifacts/sbom/bound-images.tsv, usr/libexec/mios/mios-bake-group, automation/90-generate-sbom.sh, automation/98-drift-checks.sh, usr/share/containers/systemd/, usr/lib/fapolicyd/rules.d/, usr/libexec/mios/mios-hermes-firstboot -->

# MiOS Security Audit — Remediation Plan

**Scope:** secret handling, SBOM provenance, image signing/verification, egress firewall, privileged Quadlets (Law 10), fapolicyd, CI.
**Method:** read-only review of the tracked tree at `C:\MiOS` (branch `main`). Every claim below carries `file:line` evidence. No code was modified; drop-in artifacts are embedded for the operator/parent to land.
**Date:** 2026-07-31.

---

## Executive summary

The MiOS supply chain has the *right primitives in tree* (keyless cosign signing in CI, an nft egress generator wired to SSOT, a Syft SBOM step, an fs-verity/fapolicyd deny-by-default, a well-hardened coderun sandbox) but **the enforcement half is disabled or absent at almost every layer**. The image is signed but never verified; the SBOM's only committed artifact carries placeholder digests; the egress firewall defaults to a no-op; and the AI front door binds `0.0.0.0` with wildcard CORS behind `Network=host` pods, several running as `root`/`--privileged`.

| Control | In tree? | Enforced / gated? | Finding |
|---|---|---|---|
| Image **signing** (cosign keyless) | Yes — `mios-ci.yml:445-465` | Signs every push | OK |
| Image **verification** gate | **No** | **None** | **P0** — CI never `cosign verify`s; runtime policy is `insecureAcceptEverything` |
| Runtime trust policy | Yes — `policy.json` | **Accept-everything** | **P0** — `[security.sigstore].policy_mode="insecureAcceptEverything"` |
| SBOM digest+sha per image | Partial | **Not required** | **P1** — `bound-images.tsv` digests all literal `local`; drift-gate doesn't require sha256 |
| Egress firewall (nft, no firewalld) | Yes — generator + `egress.nft` | **mode=off (no-op)** | **P1** — ships informational ruleset only |
| Least-privilege Quadlets | Partial | Allowlist only | **P1** — `--privileged` runner/k3s, root vLLM on `0.0.0.0`+`Network=host` |
| Secret store (sealed) | **No** | Plaintext env files | **P1** — bearer keys/tokens in `0640` `/etc/mios/**` env, no TPM/systemd-creds seal |
| PAT in history | Not in current tree | n/a | **P0 (operator)** — rotate regardless; add history scan |
| fapolicyd deny-by-default | Yes — `90-mios-deny.rules` | **observe/enforce off** | **P2** — inert until operator promotes |

---

## P0 — do first (hours, blocks trust)

### P0-1 Rotate the exposed GitHub PAT + move creds to a secret store *(operator action)*

The exposed `ghp_…` is **not present in the current tracked tree or in reachable history** — `git grep -I -E 'ghp_[A-Za-z0-9]{20,}'` over `git rev-list --all` returns clean, and `automation/lib/masking.sh:27-36` already masks `GH_TOKEN`/`GITHUB_TOKEN`/`GHCR_TOKEN`/`COSIGN_PASSWORD` in logs. That does **not** clear the token: a PAT leaked in *any* historical or force-pushed/detached object, in CI logs, or in a fork remains valid until revoked.

Actions (sequenced):
1. **Revoke** the token at `github.com/settings/tokens` (or org PAT policy) — this is the actual mitigation; scrubbing history alone never invalidates a leaked secret.
2. Confirm CI does not depend on it. The pipeline authenticates with the **auto-provided `GITHUB_TOKEN`** only (`mios-ci.yml:238,422,460`) — no static PAT is referenced — so revocation is safe.
3. Run a full-history secret scan and wire it into CI (drop-in in P0-4 below).
4. For runtime secrets, adopt a **sealed secret store** rather than plaintext env (see P1-4).

### P0-2 Turn on image **verification** — the sign step is not a gate without it

CI signs every push (`.github/workflows/mios-ci.yml:445-465`, `cosign sign --yes "$tag"`), but **there is no `cosign verify` anywhere in CI** (`git grep 'cosign verify'` hits only docs, RAG chunks, and the schema — never a workflow step). A signature nobody verifies proves nothing: a broken Fulcio/Rekor round-trip, a wrong identity, or a substituted digest all still "publish."

Worse, the **runtime** trust policy accepts anything:

```jsonc
// usr/lib/containers/policy.json  (rendered by tools/generate-cosign-policy.py)
{ "default": [ { "type": "insecureAcceptEverything" } ] }
```

This is projected from SSOT:

```
usr/share/mios/mios.toml:781  [security.sigstore]
usr/share/mios/mios.toml:783  policy_mode = "insecureAcceptEverything"
usr/share/mios/mios.toml:784  allowed_identities = []
tools/generate-cosign-policy.py:19  policy_mode = "insecureAcceptEverything"   # default + SSOT passthrough
tools/generate-cosign-policy.py:26  policy_mode = sigstore.get("policy_mode", "insecureAcceptEverything")
```

So `bootc upgrade` / `podman pull` will accept an **unsigned or attacker-substituted** `ghcr.io/mios-dev/mios` image. The two halves — a CI verify gate and an SSOT-driven `sigstoreSigned` runtime policy — are the drop-ins in **Artifact A** and **Artifact B**.

> Identity note: the keyless SAN is the workflow identity `https://github.com/mios-dev/mios/.github/workflows/mios-ci.yml@refs/heads/main` with issuer `https://token.actions.githubusercontent.com`. Beware the **case-mismatch** already in tree: `.env.mios` sets `MIOS_IMAGE_NAME="ghcr.io/MiOS-DEV/mios"` while CI resolves lowercase `ghcr.io/mios-dev/mios`. Pin the verify identity to a **lowercased** regexp or verification silently never matches.

---

## P1 — high (this week)

### P1-1 SBOM completeness — every bound image + asset needs a real digest+sha

The only committed SBOM artifact is `usr/share/mios/artifacts/sbom/bound-images.tsv`, and **every digest column is the literal string `local`**, not a `sha256:…`:

```
usr/share/mios/artifacts/sbom/bound-images.tsv:2   localhost/mios-sys:latest        local   sys
usr/share/mios/artifacts/sbom/bound-images.tsv:6   quay.io/ceph/ceph:v19            local   extra
usr/share/mios/artifacts/sbom/bound-images.tsv:14  docker.io/vllm/vllm-openai:latest local  extra
...  (all 23 rows: digest = "local")
```

The bake step *can* record real digests — `usr/libexec/mios/mios-bake-group:132` runs `podman image inspect "$img" --format '{{.Digest}}'` and writes `${_digest:-unknown}` at line 134 — but the committed file is a placeholder that was never overwritten with a real bake's output. And the drift-gate does not catch it: `check_sbom_metadata` validates sha256 **format** for `models.tsv`/`binaries.tsv` (`automation/98-drift-checks.sh:4110-4113, 4126-4129`) yet for `bound-images.tsv` only checks that the field is **non-empty** (`:4137-4145`) — so `local` passes. Finally, the Syft generator is **degrade-open by design and never gates**: `automation/90-generate-sbom.sh:3` ("must NEVER fail the image build (always exits 0)"), and the CycloneDX/SPDX JSON it emits is not committed (the sbom dir contains only `bound-images.tsv`).

Fix = require a `sha256:` (or `unknown`-forbidden) digest for images at build/drift time (**Artifact C**), and ensure `mios-bake-group` writes a fully-qualified `name@sha256:…` reference so the SBOM is a real reproducibility record (ADR-0003 SBOM-not-hardcode).

### P1-2 Egress firewall ships as a no-op — turn it to enforce from SSOT

The egress design is correct and firewalld-free: `tools/generate-egress-firewall.py` renders a UID-scoped **nftables** ruleset from `[security.egress]`, always allowing loopback + tailnet `100.64.0.0/10` + WSL gw `172.16.0.0/12` + the operator allowlist. But the default is a no-op:

```
usr/share/mios/mios.toml:1096  [security.egress]
usr/share/mios/mios.toml:1097  mode  = "off"
usr/share/mios/mios.toml:1098  allow = []
usr/share/mios/security/egress.nft:13   accept   # mode=off -> no-op even if applied
```

A misled/compromised agent (`mios-ai`) can currently exfiltrate to any internet host. Flip SSOT to `enforce`, regenerate, and apply (**Artifact D**). Note the two-firewall split is intentional and acceptable: inbound port rules use firewalld (`automation/45-firewall.sh:3`), while the **agent egress** control is nft-only — the "nft, no firewalld" requirement is satisfied for egress.

### P1-3 Least-privilege the Law-10 privileged Quadlets

`[security.privileged_quadlets].root` (`mios.toml:786-808`) documents the root exceptions, gated by `check_quadlet_privilege` (`automation/98-drift-checks.sh:2971`). Two problems: (a) the **allowlist is stale/over-broad** — it lists 12 units but only 11 actually set `User=root|0` in tree (`mios-forge.container` is allowlisted yet no longer runs as root), and (b) several allowlisted units are **far more privileged than they need to be**:

| Unit | Evidence | Risk | Least-privilege move |
|---|---|---|---|
| `mios-forgejo-runner` | `:27 PodmanArgs=--privileged`, `:28 User=0`, `:29 Volume=/var/lib/containers/storage:…` | Full-priv DinD with the **host's entire container store** mounted; a CI job = host takeover | Scope to rootless nested podman; drop `--privileged` for explicit `AddCapability=` set; mount a *dedicated* storage path, not the host store |
| `mios-k3s` | `:18 PodmanArgs=--privileged` | Full privilege | Replace `--privileged` with the specific caps k3s needs (`SYS_ADMIN`, `NET_ADMIN`) + required `AddDevice=` |
| `mios-llm-heavy` | `:35 User=0`, `:28 Exec=… --host 0.0.0.0`, `:11 AddDevice=nvidia.com/gpu=all` | Root vLLM listening on **all interfaces** inside a `Network=host` pod (`mios-ai.pod:20`) | Run as non-root `User=`/`Group=815`; `--host 127.0.0.1`; `NoNewPrivileges=true`; `DropCapability=ALL` (**Artifact E**) |
| `mios-ceph`, `mios-pxe-hub` | `mios-ceph.container:17 User=root` + `:25 Delegate=yes`; `mios-pxe-hub.container:16 User=0` | Root + delegated cgroup | Keep root only where block-dev/PXE truly needs uid 0; add `NoNewPrivileges` and a minimal `DropCapability`/`AddCapability` pair |
| **All three pods** | `mios-ai.pod:20`, `mios-system.pod:19`, `mios-webtools.pod:21` = `Network=host` | Every `0.0.0.0` bind is exposed on all host NICs | Move to a defined `[networks.mios.Network]` and publish only needed ports to loopback |

The **model to emulate** is already in tree: `usr/share/containers/systemd/users/mios-coderun-sandbox@.container` — `Network=none` (`:76`), `ReadOnly=true` (`:80`), `DropCapability=ALL` (`:99`), `NoNewPrivileges=true` (`:94`), seccomp profile (`:107`), per-instance SELinux MCS (`:103`). Bring the service Quadlets toward that posture.

### P1-4 Secrets are plaintext env files, not a sealed store

Runtime secrets are generated correctly (strong entropy, tight perms) but stored as **plaintext env** with no seal:

```
usr/libexec/mios/mios-hermes-firstboot:239  api_key="$(openssl rand -hex 32)"     # 256-bit, good
usr/libexec/mios/mios-hermes-firstboot:247  umask 0077                            # tight
usr/libexec/mios/mios-hermes-firstboot:282  chmod 0640 "$ENV_FILE"                # /etc/mios/hermes/api.env
usr/libexec/mios/mios-hermes-firstboot:250  API_SERVER_HOST=0.0.0.0               # binds all NICs
usr/libexec/mios/mios-hermes-firstboot:253  API_SERVER_CORS_ORIGINS=*             # wildcard CORS
```

The same key is duplicated into `OPENAI_API_KEY`, `HERMES_API_TOKEN`, `CLAUDE_DASHBOARD_TOKEN` in one file, and the forgejo runner token rides `EnvironmentFile=/etc/mios/forge/runner-token` (`mios-forgejo-runner.container:19`). Compounding it, the agent-pipe front door does **not require** that key by default — `[security].api_require_auth = false` (`mios.toml:929`) — so the `agent_pipe` port accepts unauthenticated requests, and Hermes binds `0.0.0.0` with `CORS=*` behind `Network=host`. Recommended: seal these with **`systemd-creds` (TPM2-bound)** or `LoadCredentialEncrypted=`, set `API_SERVER_HOST=127.0.0.1`, scope CORS to the Portal origin, and turn on `api_require_auth=true` for any non-loopback bind.

---

## P2 — hardening (backlog)

- **fapolicyd is deny-by-default but inert.** `usr/lib/fapolicyd/rules.d/90-mios-deny.rules:6-9` denies `trust=0` exec under `/home`, `/var/home`, `/run/media`, `/mnt`, and `80-mios-agent-codegen.rules:59-65` carves out the coderun workspace — but the mode is off (`[security.fapolicyd_observe].enable = false`, `mios.toml:1063`). The codegen rules file itself flags (`:49-56`) that the host may not intercept in-container exec, so those `/var/home` allows may be unnecessary once enforce is promoted — audit before enabling. Promote observe → enforce per the documented rollback-tested runbook.
- **Attest the SBOM/provenance.** Add `cosign attest --type cyclonedx` (and SLSA provenance) after signing so downstream `cosign verify-attestation` can tie the SBOM to the digest (referenced gap: `usr/share/doc/mios/reference/upstream-gaps-2026-07.md:216`).
- **Opt-in prompt-injection gates ship off.** `rule_of_two_mode`, `quarantine_mode`, `principal_bind_mode` all default `off` (`mios.toml:887,916,956`). Fine as defaults, but for any multi-tenant/networked deploy, enabling `api_require_auth=true` + `principal_bind_mode=enforce` is the intended posture.

---

## Drop-in artifacts

### Artifact A — CI gate: `cosign verify` (fail the pipeline on non-verify)

Insert **after** the "Cosign keyless sign" step in `.github/workflows/mios-ci.yml` (guarded identically: `if: env.PUBLISH == 'true' && github.event_name != 'pull_request'`). It verifies every pushed tag by the workflow's own keyless identity; a mismatch or missing signature fails the job.

```yaml
      # Gate on VERIFY: a signature is only a control if we prove it verifies.
      # Uses the same keyless identity CI just signed with (Fulcio SAN = this
      # workflow ref; issuer = GitHub OIDC). Identity is lowercased to match the
      # canonical ghcr.io/mios-dev/mios (NOT the MiOS-DEV casing in .env.mios).
      - name: Cosign verify (gate publish on signature)
        if: env.PUBLISH == 'true' && github.event_name != 'pull_request'
        env:
          COSIGN_EXPERIMENTAL: '1'
        run: |
          set -euo pipefail
          source ./tools/lib/userenv.sh
          IDENTITY_RE="^https://github.com/${GITHUB_REPOSITORY,,}/\.github/workflows/mios-ci\.yml@refs/"
          ISSUER="https://token.actions.githubusercontent.com"
          while IFS= read -r tag; do
              [[ -z "$tag" ]] && continue
              echo "Verifying signature for: $tag"
              cosign verify \
                  --certificate-identity-regexp="${IDENTITY_RE}" \
                  --certificate-oidc-issuer="${ISSUER}" \
                  "$tag" >/dev/null \
                || { echo "::error::cosign verify FAILED for ${tag} -- refusing to publish unverifiable image"; exit 1; }
              echo "  verified OK: $tag"
          done <<< "${{ steps.meta.outputs.tags }}"
```

### Artifact B — Runtime trust policy from SSOT (`sigstoreSigned` keyless)

**SSOT change** (`usr/share/mios/mios.toml [security.sigstore]`):

```toml
[security.sigstore]
cosign_major = 2
# Was "insecureAcceptEverything" -- accept-everything is not a policy.
policy_mode = "sigstoreSigned"
# Keyless identity the runtime must require for the MiOS image (lowercased repo).
image_repo         = "ghcr.io/mios-dev/mios"
oidc_issuer        = "https://token.actions.githubusercontent.com"
identity_regexp    = "^https://github.com/mios-dev/mios/.github/workflows/mios-ci.yml@refs/"
fulcio_ca_path     = "/usr/share/pki/containers/fulcio_v1.crt.pem"
rekor_pubkey_path  = "/usr/share/pki/containers/rekor.pub"
```

**Generator extension** (`tools/generate-cosign-policy.py`) — emit a scoped keyless policy instead of default-accept when `policy_mode == "sigstoreSigned"`. The resulting `usr/lib/containers/policy.json` becomes:

```jsonc
{
  "default": [ { "type": "reject" } ],
  "transports": {
    "docker": {
      "ghcr.io/mios-dev/mios": [
        {
          "type": "sigstoreSigned",
          "fulcio": {
            "caPath": "/usr/share/pki/containers/fulcio_v1.crt.pem",
            "oidcIssuer": "https://token.actions.githubusercontent.com",
            "subjectEmail": ""
          },
          "rekorPublicKeyPath": "/usr/share/pki/containers/rekor.pub",
          "signedIdentity": { "type": "matchRepoDigestOrExact" }
        }
      ],
      "": [ { "type": "insecureAcceptEverything" } ]
    }
  }
}
```

> `default: reject` + an explicit accept for other transports keeps local `containers-storage:` builds working while forcing the MiOS registry image through signature verification. Because the GitHub Actions SAN is a URI (not an email), pin the identity at pull time with `cosign verify --certificate-identity-regexp=…` in the bootc/greenboot pre-upgrade hook as the authoritative check, and keep `policy.json` as the runtime backstop. `automation/49-cosign-policy.sh` already installs `fulcio_v1.crt.pem`/`rekor.pub` (`:100`), so the trust roots are present.

### Artifact C — Drift gate: bound-image SBOM digest completeness

Tighten `check_sbom_metadata` in `automation/98-drift-checks.sh` (replace the bound-images non-empty check at `:4137-4145`) so an image digest must be a real `sha256:` (or explicitly `unknown`), matching how `models.tsv`/`binaries.tsv` are already validated:

```bash
        # Check bound-images.tsv -- REQUIRE a real registry digest, not a placeholder.
        if [[ -f "$sbom_dir/bound-images.tsv" ]]; then
            while IFS=$'\t' read -r image digest group || [[ -n "$image" ]]; do
                [[ "$image" == "image" ]] && continue
                [[ -z "$image" ]] && continue
                if [[ -z "$digest" || -z "$group" ]]; then
                    bad+=("bound-images.tsv has empty fields in row for '$image'")
                elif [[ "$digest" != "unknown" && ! "$digest" =~ ^sha256:[0-9a-fA-F]{64}$ ]]; then
                    bad+=("bound-images.tsv row for '$image' has non-digest value '$digest' (want sha256:…)")
                fi
            done < "$sbom_dir/bound-images.tsv"
        fi
```

And make the bake record a fully-qualified pinned ref (`usr/libexec/mios/mios-bake-group:132-134`) so the committed TSV is a true provenance record:

```bash
        _digest="$(CONTAINERS_STORAGE_CONF="$CONF" podman --root "$STORE" \
                     image inspect "$img" --format '{{.Digest}}' 2>/dev/null || true)"
        # Emit name@sha256:… (drop any :tag) so the SBOM row is a pinned, verifiable ref.
        printf '%s\t%s\t%s\n' "${img%%:*}@${_digest:-unknown}" "${_digest:-unknown}" "$GROUP" \
            >> "$SBOM_DIR/bound-images.tsv"
```

> Localhost-built images (`localhost/mios-sys`, `mios-cuda`, `mios-crawl4ai-slim`, `mios-firecrawl`) legitimately have no registry digest; allow the sentinel `local-<content-sha>` for those but forbid the bare `local` string, so a placeholder can never masquerade as provenance.

### Artifact D — nft egress ruleset from SSOT (enforce)

Flip SSOT, regenerate, apply. This is exactly what `tools/generate-egress-firewall.py` emits for `mode="enforce"` (UID-scoped to the `mios-ai` agent; loopback/tailnet/WSL-gw always allowed):

**SSOT** (`usr/share/mios/mios.toml`):
```toml
[security.egress]
mode  = "enforce"
allow = [ "140.82.112.0/20", "185.199.108.0/22" ]   # e.g. github.com / ghcr fastly; add per deploy
```

**Regenerate + apply** (operator step; nothing is auto-applied):
```bash
python3 tools/generate-egress-firewall.py            # -> usr/share/mios/security/egress.nft
sudo nft -f /usr/share/mios/security/egress.nft      # remove: sudo nft delete table inet mios_egress
```

**Rendered `usr/share/mios/security/egress.nft` (mode=enforce):**
```nft
# GENERATED nftables egress firewall for the MiOS agent (#54). DO NOT EDIT.
# mode=enforce  agent-user=mios-ai
table inet mios_egress {
    chain output {
        type filter hook output priority filter; policy accept;
        meta skuid != "mios-ai" accept          # only the agent uid is constrained
        oifname "lo" accept
        ip daddr 127.0.0.0/8 accept
        ip6 daddr ::1 accept
        ip daddr 100.64.0.0/10 accept           # tailnet
        ip daddr 172.16.0.0/12 accept           # WSL gateway
        ip daddr { 140.82.112.0/20, 185.199.108.0/22 } accept   # [security.egress].allow
        log prefix "mios-egress-drop " drop     # everything else for mios-ai: LOG + DROP
    }
}
```

> Roll out as `mode="audit"` first (`log … accept`) to size the allowlist against real agent traffic, then promote to `enforce`. It's uid-scoped, so `web_search` keeps working: the agent reaches searxng over loopback and searxng (a different uid) reaches the internet.

### Artifact E — Least-privilege drop-in for `mios-llm-heavy.container`

Bring the root vLLM lane toward the coderun-sandbox posture. This is regenerated from `[containers.mios-llm-heavy]` in `mios.toml`, so land it as an SSOT change and re-run `tools/generate-pod-quadlets.py`:

```ini
[Container]
AddDevice=nvidia.com/gpu=all
ContainerName=mios-llm-heavy
# Was User=0 -- run as the dedicated service account, not root.
User=815
Group=815
# Was --host 0.0.0.0 behind a Network=host pod (exposed on every NIC).
# Bind loopback; the pod/reverse-proxy publishes only the needed port.
Exec=--model /models --served-model-name mios-heavy --host 127.0.0.1 --port ${MIOS_PORT_VLLM} \
     --gpu-memory-utilization 0.80 --max-model-len 8192 --kv-cache-dtype fp8 \
     --load-format dummy --enable-prefix-caching --enforce-eager
NoNewPrivileges=true
DropCapability=ALL
ReadOnly=true
Volume=/var/lib/mios/vllm/model:/models:ro,Z
Image=docker.io/vllm/vllm-openai:latest
Pod=mios-ai.pod
```

Then **remove `mios-llm-heavy.container` (and `-alt`) from `[security.privileged_quadlets].root`** (`mios.toml:801-802`) so the drift-gate proves it is no longer root, and **delete the stale `mios-forge.container` entry** (`:794`, no longer `User=root` in tree). Apply the same `User=`/`NoNewPrivileges`/`DropCapability` treatment to `mios-ceph`/`mios-pxe-hub`, and replace `PodmanArgs=--privileged` on `mios-k3s`/`mios-forgejo-runner` with an explicit minimal `AddCapability=` set.

---

## Sign-off checklist (the acceptance gate for this audit)

- [ ] **P0** PAT revoked; full-history secret scan (e.g. gitleaks) added to the `drift-gate` job and green.
- [ ] **P0** `cosign verify` step gates `build`/publish (Artifact A); `[security.sigstore].policy_mode="sigstoreSigned"` and `policy.json` no longer `insecureAcceptEverything` (Artifact B).
- [ ] **P1** `bound-images.tsv` carries `sha256:` per image; drift-gate rejects placeholder digests (Artifact C).
- [ ] **P1** `[security.egress].mode="enforce"` from SSOT allowlist; `egress.nft` applied; no firewalld in the egress path (Artifact D).
- [ ] **P1** No service Quadlet runs `--privileged` or `User=0` without a per-unit justification; vLLM/k3s/runner least-privileged; `privileged_quadlets.root` count matches the tree (Artifact E).
- [ ] **P1** Runtime bearer keys sealed (systemd-creds/TPM); `API_SERVER_HOST=127.0.0.1`; CORS scoped; `api_require_auth=true` on any non-loopback bind.
- [ ] **P2** fapolicyd promoted observe→enforce per runbook; SBOM/provenance attested (`cosign attest` + SLSA).
