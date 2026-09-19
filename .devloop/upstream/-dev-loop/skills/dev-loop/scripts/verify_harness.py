#!/usr/bin/env python3
"""
scripts/verify_harness.py
Two-sided verification runner with automated mutation testing.
"""
import subprocess
import sys
from typing import Callable, List, Tuple

def run_two_sided_test(
    test_cmd: List[str],
    mutator: Callable[[], None],
    reverter: Callable[[], None],
    expected_failure_needle: str
) -> Tuple[bool, str]:
    """
    Executes a positive control, applies an intentional defect,
    asserts failure, and reverts state.
    """
    # 1. Positive Control
    pos = subprocess.run(test_cmd, capture_output=True, text=True)
    if pos.returncode != 0:
        return False, f"Positive control failed unexpectedly:\n{pos.stderr or pos.stdout}"
    
    # 2. Plant Negative Control
    try:
        mutator()
        neg = subprocess.run(test_cmd, capture_output=True, text=True)
        if neg.returncode == 0:
            return False, "Negative control passed! Test suite failed to catch planted defect."
        
        output = (neg.stderr + "\n" + neg.stdout)
        if expected_failure_needle not in output:
            return False, f"Negative control failed for wrong reason. Missing needle: '{expected_failure_needle}'"
    finally:
        reverter()
        
    # 3. Post-Revert Verification
    post = subprocess.run(test_cmd, capture_output=True, text=True)
    if post.returncode != 0:
        return False, "Failed to restore working state after negative control."
        
    return True, "Two-sided validation passed successfully."

if __name__ == "__main__":
    print("[dev-loop] Verify harness ready.")
