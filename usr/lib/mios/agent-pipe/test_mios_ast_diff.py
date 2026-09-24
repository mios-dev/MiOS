# AI-hint: Unit and regression test suite for Tree-Sitter & Structural AST diff engine and 2-peer review gating.
# AI-related: usr/lib/mios/agent-pipe/mios_ast_diff.py, usr/lib/mios/agent-pipe/server.py
"""
Unit tests for mios_ast_diff.
Validates cosmetic vs semantic AST diff detection across Python, Rust, Go, TypeScript, and C,
security vulnerability pattern detection, and 2-peer review merge consensus gating.
"""

import sys
import unittest

from mios_ast_diff import AstDiffEngine, TwoPeerReviewGate


class TestAstDiffEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AstDiffEngine()

    def test_python_pure_whitespace_and_comments_cosmetic(self):
        orig = """def calculate_total(a, b):
    # Sum two values
    return a + b
"""
        mod = """
def calculate_total(a, b):

    # Different comment here
    # Another line of commentary
    return a + b

"""
        res = self.engine.compute_ast_diff(orig, mod, "python")
        self.assertFalse(res["has_semantic_diff"])
        self.assertTrue(res["is_purely_cosmetic"])
        self.assertFalse(res["has_security_risks"])

    def test_python_semantic_mutation(self):
        orig = """def calculate_total(a, b):
    return a + b
"""
        mod = """def calculate_total(a, b):
    return a * b  # Logic changed from + to *
"""
        res = self.engine.compute_ast_diff(orig, mod, "python")
        self.assertTrue(res["has_semantic_diff"])
        self.assertFalse(res["is_purely_cosmetic"])
        self.assertGreaterEqual(res["mutations_count"], 1)

    def test_rust_pure_cosmetic_change(self):
        orig = """pub fn compute_sum(a: i32, b: i32) -> i32 {
    // Add numbers
    a + b
}"""
        mod = """
pub fn compute_sum(a: i32, b: i32) -> i32 {
    /* Multi-line comment
       with explanations */
    a + b
}
"""
        res = self.engine.compute_ast_diff(orig, mod, "rust")
        self.assertFalse(res["has_semantic_diff"])
        self.assertTrue(res["is_purely_cosmetic"])

    def test_rust_semantic_mutation(self):
        orig = """pub fn compute_sum(a: i32, b: i32) -> i32 {
    a + b
}"""
        mod = """pub fn compute_sum(a: i32, b: i32) -> i32 {
    a - b
}"""
        res = self.engine.compute_ast_diff(orig, mod, "rust")
        self.assertTrue(res["has_semantic_diff"])
        self.assertFalse(res["is_purely_cosmetic"])

    def test_go_semantic_and_cosmetic(self):
        orig = """func Hello(name string) string {
    return "Hello " + name
}"""
        mod_cosmetic = """// Greeting function
func Hello(name string) string {
    // Return hello greeting
    return "Hello " + name
}"""
        res_cosmetic = self.engine.compute_ast_diff(orig, mod_cosmetic, "go")
        self.assertFalse(res_cosmetic["has_semantic_diff"])
        self.assertTrue(res_cosmetic["is_purely_cosmetic"])

        mod_semantic = """func Hello(name string) string {
    return "Goodbye " + name
}"""
        res_semantic = self.engine.compute_ast_diff(orig, mod_semantic, "go")
        self.assertTrue(res_semantic["has_semantic_diff"])

    def test_typescript_function_signature_change(self):
        orig = """function fetchItem(id: number): string {
    return "item_" + id;
}"""
        mod = """function fetchItem(id: number, fallback: string): string {
    return "item_" + id;
}"""
        res = self.engine.compute_ast_diff(orig, mod, "typescript")
        self.assertTrue(res["has_semantic_diff"])

    def test_c_code_buffer_security_detection(self):
        orig = """void copy_buf(char *src) {
    char dst[64];
    strncpy(dst, src, sizeof(dst) - 1);
}"""
        mod_vuln = """void copy_buf(char *src) {
    char dst[64];
    strcpy(dst, src); // Unsafe buffer copy
}"""
        res = self.engine.compute_ast_diff(orig, mod_vuln, "c")
        self.assertTrue(res["has_semantic_diff"])
        self.assertTrue(res["has_security_risks"])
        self.assertTrue(any("strcpy" in r.lower() or "buffer" in r.lower() for r in res["security_risks"]))

    def test_eval_exec_security_detection(self):
        code_safe = "result = compute_value(expr)"
        code_unsafe = "result = eval(user_input)"
        res = self.engine.compute_ast_diff(code_safe, code_unsafe, "python")
        self.assertTrue(res["has_security_risks"])
        self.assertTrue(any("eval" in r.lower() for r in res["security_risks"]))


class TestTwoPeerReviewGate(unittest.TestCase):
    def setUp(self):
        self.gate = TwoPeerReviewGate()

    def test_review_lifecycle_and_2_peer_consensus(self):
        orig = "def add(x, y): return x + y"
        mod = "def add(x, y): return x * y"
        rec = self.gate.create_review(orig, mod, "python", patch_id="patch-101")
        self.assertEqual(rec["status"], "pending")
        self.assertFalse(rec["can_merge"])

        # Reviewer approves, but security auditor has not voted
        v1 = self.gate.submit_vote("patch-101", "reviewer", "approve", "Logic changes reviewed")
        self.assertEqual(v1["status"], "pending")
        self.assertFalse(v1["can_merge"])
        self.assertIn("security_auditor", v1.get("pending_roles", []))

        # Security auditor approves -> 2/2 consensus reached!
        v2 = self.gate.submit_vote("patch-101", "security_auditor", "approve", "No security threats found")
        self.assertEqual(v2["status"], "approved")
        self.assertTrue(v2["can_merge"])

    def test_rejection_blocks_merge(self):
        orig = "def run(): pass"
        mod = "def run(): import os; os.system('rm -rf /')"
        self.gate.create_review(orig, mod, "python", patch_id="patch-bad")

        # Reviewer approves
        self.gate.submit_vote("patch-bad", "reviewer", "approve")

        # Security auditor rejects
        v = self.gate.submit_vote("patch-bad", "security_auditor", "reject", "Malicious command execution detected")
        self.assertEqual(v["status"], "rejected")
        self.assertFalse(v["can_merge"])


if __name__ == "__main__":
    unittest.main()
