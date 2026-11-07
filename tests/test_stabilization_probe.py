"""Offline acceptance-harness regressions; these never launch a vendor agent."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hea_stabilization_probe", ROOT / "research/stabilization_probe.py")
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class StabilizationHarnessTests(unittest.TestCase):
    def test_coding_goal_declares_authorized_commands_and_file_reader(self):
        workspace = Path("/explicit workspace/fixture")
        goal = probe.coding_goal(workspace)
        self.assertIn(str(workspace), goal)
        self.assertIn("read_file", goal)
        self.assertIn("python3 -m unittest -v", goal)
        self.assertIn("git status --short", goal)
        self.assertIn("git diff -- discount.py", goal)
        self.assertIn("Do not use python3 -c", goal)
        self.assertIn("do not attempt alternative tools or commands", goal)
        self.assertIn("internal finish tool", goal)
        self.assertNotIn("skip-permissions", goal)

    def test_parent_receives_exact_task_goal_without_expected_probe_contents(self):
        prompt = probe.coding_parent_prompt(Path("/fixture"))
        task = json.loads(prompt.split("TASK TO DELEGATE:\n", 1)[1])
        self.assertEqual(task["goal"], probe.coding_goal(Path("/fixture")))
        self.assertEqual(task["output_schema"]["type"], "object")
        self.assertEqual(set(task["output_schema"]["required"]),
                         {"contents", "changed_files", "tests_passed"})
        self.assertIs(task["output_schema"]["additionalProperties"], False)
        self.assertNotIn("HEA_SCOPED_", prompt)

    def test_delegate_result_accepts_host_budget_notice_without_hiding_failure(self):
        payload = {"results": [{"status": "failed", "failure_reason": "incomplete_response"}]}
        content = json.dumps(payload) + "\n\n[SYSTEM NOTICE — run time budget nearly exhausted] Stop now."
        self.assertEqual(probe.delegation_result(content), payload)

    def test_delegate_result_rejects_unrecognized_trailing_content(self):
        with self.assertRaises(ValueError):
            probe.delegation_result('{"results": []}\n{"results": [{"status": "completed"}]}')

    def test_coding_job_check_does_not_require_unrelated_probes_to_pass(self):
        records = [("old", "schema-child", "failed", "schema-conversation"),
                   ("new", "coding-child", "completed", "coding-conversation")]
        self.assertEqual(probe.completed_new_job(records, {"old"}), records[1])
        with self.assertRaises(ValueError):
            probe.completed_new_job([("new", "coding-child", "failed", "conversation")], set())
        with self.assertRaises(ValueError):
            probe.completed_new_job(records, set())


if __name__ == "__main__":
    unittest.main()
