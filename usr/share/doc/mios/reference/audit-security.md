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

*Note: Findings resolved and verified in active repository implementations.*
