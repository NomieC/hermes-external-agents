"""Opt-in AGY 1.5.x stabilization acceptance in a disposable home.

The caller creates work/probe.txt plus a failing discount.py/test_discount.py
fixture. Parent connection values come only from HEA_PARENT_* environment.
Raw evidence stays in HEA_STABILIZATION_BASE, never in the source repository.
"""
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import unittest


def delegation_result(content):
    """Read the leading tool-result JSON, allowing only the known host budget notice."""
    payload, end = json.JSONDecoder().raw_decode(content.lstrip())
    trailing = content.lstrip()[end:].strip()
    if trailing and not trailing.startswith("[SYSTEM NOTICE — run time budget nearly exhausted]"):
        raise ValueError("Unrecognized content after the delegation result")
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("Invalid delegation result shape")
    return payload


def completed_new_job(records, previous_tokens):
    """Keep coding acceptance independent of unrelated schema-probe failures."""
    new = [row for row in records if row[0] not in previous_tokens]
    if len(new) != 1 or new[0][2] != "completed" or not new[0][3]:
        raise ValueError("Expected exactly one new completed job with vendor correlation")
    return new[0]


def coding_goal(workspace):
    """Declare the authorized tool strategy before a fresh coding job starts."""
    return (
        f"Work only in the explicitly configured disposable workspace: {workspace}. "
        "Use your built-in read_file tool to read discount.py, test_discount.py and probe.txt. "
        "Copy the exact probe.txt text from read_file; do not inspect it with shell commands. "
        "The complete authorized shell command set is: python3 -m unittest -v; "
        "git status --short; git diff -- discount.py. You may prefix those commands only "
        "with cd to this exact workspace followed by &&. No other shell commands are authorized. "
        "Do not use python3 -c, python -c, cat, shell scripts or interpreter snippets to read files. "
        "Run python3 -m unittest -v and confirm the existing discount bug, then use your "
        "built-in editing tool to fix only discount.py. Do not modify tests, probe.txt or other files. "
        "Rerun python3 -m unittest -v, then use the permitted read-only Git commands if needed. "
        "Do not commit, install packages, browse, access credentials, write plan artifacts or delegate. "
        "If any tool action is denied, report that failure and stop; do not attempt alternative tools "
        "or commands to perform the denied action. Finalize with ONLY JSON: contents equal to "
        "the exact probe.txt text, changed_files equal to [\"discount.py\"], and tests_passed boolean. "
        "Your internal finish tool is permitted for structured-output finalization."
    )


def coding_parent_prompt(workspace):
    """Give the parent an exact task payload without leaking the file oracle."""
    schema = {"type": "object", "properties": {
        "contents": {"type": "string"},
        "changed_files": {"type": "array", "items": {"type": "string"}},
        "tests_passed": {"type": "boolean"}},
        "required": ["contents", "changed_files", "tests_passed"],
        "additionalProperties": False}
    task = {"goal": coding_goal(workspace), "output_schema": schema}
    return ("Use ordinary delegate_task exactly once, foreground, with exactly one task. "
            "Copy the following task object, including its output_schema, unchanged into tasks. "
            "No replacement or new delegation on failure. Do not use any other tools yourself. "
            "Return the tool result unchanged.\nTASK TO DELEGATE:\n" + json.dumps(task))


@unittest.skipUnless(os.environ.get("HEA_STABILIZATION_BASE"), "Disposable home opt-in required")
class StabilizationProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from hermes_cli.plugins import get_plugin_manager
        cls.base = Path(os.environ["HEA_STABILIZATION_BASE"])
        cls.home = Path(os.environ["HERMES_HOME"])
        cls.work = cls.base / "work"
        assert cls.home.parent == cls.base
        get_plugin_manager().discover_and_load()

    def wrapper(self, name, schema, prompt):
        from run_agent import AIAgent
        token = secrets.token_hex(16)
        body = {"hea_job": token, "hea_workspace": str(self.work), "hea_settings": {
            "executable": os.environ["HERMES_EXTERNAL_AGENTS_AGY_COMMAND"],
            "mode": "plan", "timeout_seconds": 120, "allow_external_tools": True}}
        agent = AIAgent(provider="external-agents-agy", model="agy-default",
            base_url="process://hermes-external-agents", api_key="external-process",
            command=os.environ["HERMES_EXTERNAL_AGENTS_AGY_COMMAND"], max_iterations=2,
            enabled_toolsets=[], skip_context_files=True, skip_memory=True,
            skip_background_review=True, quiet_mode=True, cwd=str(self.work),
            run_budget_seconds=135, request_overrides={"extra_body": body})
        try:
            contract = "" if schema is None else (
                "\nOUTPUT CONTRACT (machine-validated):\n"
                "Your FINAL response must be ONLY the JSON value that validates against this JSON Schema.\n" +
                json.dumps(schema))
            result = agent.run_conversation(prompt, task_id=name, system_message=contract or None)
            status = agent.client.job_status(token, agent.session_id)
            (self.base / (name + ".json")).write_text(json.dumps({"result": result, "job": status}, default=str, indent=2))
            self.assertFalse(result.get("failed"), result.get("error"))
            self.assertEqual(status["state"], "completed")
            self.assertTrue(status["conversation_id"])
            self.assertIn(status["conversation_id"], status["resume_command"])
            return result["final_response"]
        finally:
            agent.close()

    def test_01_plain_text_without_contract(self):
        response = self.wrapper("plain", None,
            "Reply with exactly HEA_PLAIN_READY. Do not use tools or make a plan artifact.")
        self.assertEqual(response.strip(), "HEA_PLAIN_READY")

    def test_02_empty_schema_is_still_json(self):
        response = self.wrapper("empty-schema", {},
            'Reply with the JSON object {"ok":true}. Do not use tools or make a plan artifact.')
        self.assertEqual(json.loads(response), {"ok": True})

    def test_03_explicit_object_schema(self):
        schema = {"type": "object", "properties": {"ok": {"type": "boolean"}},
                  "required": ["ok"], "additionalProperties": False}
        response = self.wrapper("object-schema", schema,
            'Reply with the JSON object {"ok":true} using your internal finish tool. '
            'The finish tool is permitted to finalize structured output. Do not use any other tools, '
            'access files, run commands, browse, delegate or create plan artifacts.')
        self.assertEqual(json.loads(response), {"ok": True})

    def test_04_model_delegated_coding_and_exact_read(self):
        from run_agent import AIAgent
        expected = (self.work / "probe.txt").read_text()
        tests_before = (self.work / "test_discount.py").read_bytes()
        with sqlite3.connect(self.home / "plugin-data/external-agents-agy/jobs.sqlite3") as db:
            previous_tokens = {row[0] for row in db.execute("SELECT token FROM jobs")}
        parent = AIAgent(provider=os.environ["HEA_PARENT_PROVIDER"],
            base_url=os.environ["HEA_PARENT_BASE_URL"], api_key=os.environ["HEA_PARENT_API_KEY"],
            model=os.environ["HEA_PARENT_MODEL"], max_iterations=4, enabled_toolsets=["delegation"],
            skip_context_files=True, skip_memory=True, skip_background_review=True,
            quiet_mode=True, cwd=str(self.work), run_budget_seconds=270)
        try:
            result = parent.run_conversation(coding_parent_prompt(self.work))
            (self.base / "coding-parent.json").write_text(json.dumps(result, default=str, indent=2))
            calls = [m for m in result.get("messages", []) if m.get("role") == "tool" and m.get("name") == "delegate_task"]
            self.assertEqual(len(calls), 1)
            children = delegation_result(calls[0]["content"])["results"]
            self.assertEqual(len(children), 1)
            child = children[0]
            self.assertEqual(child["route"]["provider"], "external-agents-agy")
            self.assertEqual(child["status"], "completed")
            self.assertIs(child["schema_valid"], True)
            answer = json.loads(child["summary"])
            self.assertEqual(answer["contents"], expected)
            self.assertEqual(answer["changed_files"], ["discount.py"])
            self.assertIs(answer["tests_passed"], True)
            self.assertEqual((self.work / "test_discount.py").read_bytes(), tests_before)
            self.assertEqual((self.work / "probe.txt").read_text(), expected)
            checked = subprocess.run([sys.executable, "-m", "unittest", "-v"], cwd=self.work,
                                     capture_output=True, text=True, timeout=20)
            (self.base / "coding-independent-tests.log").write_text(checked.stdout + checked.stderr)
            self.assertEqual(checked.returncode, 0)
            diff = subprocess.run(["git", "diff", "--name-only"], cwd=self.work, capture_output=True, text=True, check=True)
            self.assertEqual(diff.stdout.splitlines(), ["discount.py"])
            patch = subprocess.run(["git", "diff", "--", "discount.py"], cwd=self.work, capture_output=True, text=True, check=True)
            (self.base / "coding.diff").write_text(patch.stdout)
            with sqlite3.connect(self.home / "plugin-data/external-agents-agy/jobs.sqlite3") as db:
                records = db.execute("SELECT j.token,j.session,j.state,d.conversation_id FROM jobs j "
                                     "LEFT JOIN job_details d ON d.token=j.token").fetchall()
            coding_job = completed_new_job(records, previous_tokens)
            (self.base / "verified.json").write_text(json.dumps({"child": child, "job": coding_job,
                "independent_tests_passed": True, "only_discount_changed": True}, indent=2))
        finally:
            parent.close()


if __name__ == "__main__":
    unittest.main()
