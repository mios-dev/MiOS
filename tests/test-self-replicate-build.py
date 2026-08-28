# AI-hint: Tests for T-966 & T-967: autonomous self-replication build trigger and digest verification.
# AI-functions: test_self_replication_build_and_digest

"""Tests for T-966 & T-967: autonomous self-replication build trigger and digest verification."""
import sys
sys.path.insert(0, "usr/libexec/mios/deploy")
from self_replicate import SelfReplicationDaemon

def test_self_replication_build_and_digest():
    """Verify self-replication builds OCI image and produces valid sha256 digest."""
    daemon = SelfReplicationDaemon()
    commit_sha = "41146deb8a7b9c1d2e3f4a5b6c7d8e9f01234567"

    res = daemon.trigger_self_build(commit_sha, dry_run=True)
    assert res.git_commit_sha == commit_sha
    assert res.staged_for_switch
    assert daemon.verify_image_signature(res)
    assert len(daemon.build_history) == 1

if __name__ == "__main__":
    test_self_replication_build_and_digest()
    print("All T-966/T-967 tests passed.")
