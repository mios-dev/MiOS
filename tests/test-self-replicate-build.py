# AI-hint: Tests for T-966 & T-967: autonomous self-replication build trigger and digest verification.
# AI-functions: test_build_context_ignores_generated_artifacts, test_build_context_preserves_tracked_sources, test_self_replication_build_and_digest

"""Tests for T-966 & T-967: autonomous self-replication build trigger and digest verification."""
import sys
import subprocess
import tempfile
from pathlib import Path
sys.path.insert(0, "usr/libexec/mios/deploy")
from self_replicate import SelfReplicationDaemon

def test_build_context_ignores_generated_artifacts():
    """Nested build output and cache symlinks cannot become OCI payloads."""
    root = Path(__file__).resolve().parents[1]
    rules = set((root / ".containerignore").read_text().splitlines())
    for pattern in ("**/target", "**/target/**", "**/__pycache__", "**/__pycache__/**", "**/*.pyc"):
        assert pattern in rules, f"missing recursive container exclusion: {pattern}"
    assert (root / ".dockerignore").resolve() == root / ".containerignore", "container engines must share one ignore policy"

def test_self_replication_build_and_digest():
    """Verify self-replication builds OCI image and produces valid sha256 digest."""
    daemon = SelfReplicationDaemon()
    commit_sha = "41146deb8a7b9c1d2e3f4a5b6c7d8e9f01234567"

    res = daemon.trigger_self_build(commit_sha, dry_run=True)
    assert res.git_commit_sha == commit_sha
    assert res.staged_for_switch
    assert daemon.verify_image_signature(res)
    assert len(daemon.build_history) == 1

def test_build_context_preserves_tracked_sources():
    """Image gates see canonical artifact paths and omitted tracked consumers."""
    root = Path(__file__).resolve().parents[1]
    recipe = (root / "Containerfile").read_text()
    assert "/ctx/config/artifacts/" in recipe, "artifact recipes must retain their source path"
    assert "/ctx/bib-configs" not in recipe, "renamed artifacts invalidate source gates"
    restore = "git -C /tmp/build ls-files --deleted -z | git -C /tmp/build checkout-index -z --stdin"
    assert restore in recipe, "partial image context must restore omitted tracked consumers"
    assert recipe.index(restore) < recipe.index("miosd drift-check"), "restore sources before evaluating drift"
    with tempfile.TemporaryDirectory() as directory:
        fixture = Path(directory)
        subprocess.run(["git", "init", "--quiet", directory], check=True)
        omitted = fixture / "omitted consumer.sh"
        retained = fixture / "copied consumer.sh"
        omitted.write_text("tracked source")
        retained.write_text("original source")
        subprocess.run(["git", "-C", directory, "add", "--", omitted.name, retained.name], check=True)
        omitted.unlink()
        retained.write_text("copied operator edit")
        private = fixture / "private-cache"
        private.write_text("untracked cache")
        missing = subprocess.check_output(["git", "-C", directory, "ls-files", "--deleted", "-z"])
        subprocess.run(["git", "-C", directory, "checkout-index", "-z", "--stdin"], input=missing, check=True)
        assert omitted.read_text() == "tracked source"
        assert retained.read_text() == "copied operator edit", "restoration must retain copied edits"
        assert private.read_text() == "untracked cache", "restoration must not modify untracked files"

if __name__ == "__main__":
    test_build_context_ignores_generated_artifacts()
    test_build_context_preserves_tracked_sources()
    test_self_replication_build_and_digest()
    print("All T-966/T-967 tests passed.")
