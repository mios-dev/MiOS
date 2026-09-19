# CHECKLISTS

## Pre-commit (every commit)
- [ ] `git diff --cached --stat` read; only owned/intended paths staged (no `git add -A`).
- [ ] `adapters.py secrets --wt .` (gitleaks) clean.
- [ ] Lockfile/manifest changed? → `adapters.py deps --wt .` clean (osv-scanner / pip-audit / cargo-audit / npm audit / govulncheck).
- [ ] Non-empty, parseable files (`py_compile`, `bash -n`, `tsc --noEmit`, `json.load` …).
- [ ] Commit message: what broke, why this fix, both controls; `Task-Id:` trailer.

## Pre-merge (every lane / PR)
- [ ] Positive control exit 0; negative control non-zero AND names the planted violation AND restored the tree.
- [ ] Full gate exactly as CI; mutation gate on diff files if configured (`mutation_cmd`).
- [ ] Ownership audit: diff touches only `owned_paths`.
- [ ] No suppression/baseline/threshold changes without an ADR or task note.
- [ ] Report `status` is true (`done` only if all of the above).

## Dependency add / bump
- [ ] Installed version read from the lockfile; docs checked for THAT version.
- [ ] `osv-scanner` / ecosystem audit clean; provenance/signature checked where available (npm provenance, sigstore, SLSA).
- [ ] Separate commit; ADR if the choice is architectural.

## Release
- [ ] CHANGELOG.md (Keep a Changelog) updated; version bumped per policy.
- [ ] Integration suite green on base; tag/publish confirmed by operator (irreversible).

## Session end / before compaction
- [ ] `adapters.py ledger --status … --next …` written; tasks.jsonl current; uncommitted work parked as a patch or committed.
