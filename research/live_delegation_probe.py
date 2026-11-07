"""Opt-in real model-issued delegate_task integration in a disposable home.

This script never reads credentials. The caller supplies the parent endpoint,
AGY's official cached login, and an isolated HERMES_HOME/workspace.
"""
import json
import os
from pathlib import Path
import sqlite3
import unittest


@unittest.skipUnless(os.environ.get("HEA_LIVE_PROBE") == "1", "Explicit live probe opt-in required")
class LiveDelegationProbe(unittest.TestCase):
    def test_model_issued_delegation_reads_unknown_file_through_agy(self):
        from hermes_cli.plugins import get_plugin_manager
        from run_agent import AIAgent
        home = Path(os.environ["HERMES_HOME"])
        work = home.parent / "work"
        expected = (work / "probe.txt").read_text()
        get_plugin_manager().discover_and_load()
        calls = []

        def complete(name, args, result, **kwargs):
            calls.append({"name": name, "args": args, "result": str(result)})

        parent = AIAgent(provider="custom", base_url=os.environ["HEA_PARENT_BASE_URL"],
            api_key=os.environ["HEA_PARENT_API_KEY"], model=os.environ["HEA_PARENT_MODEL"],
            max_iterations=4, enabled_toolsets=["delegation"],
            skip_context_files=True, skip_memory=True, skip_background_review=True,
            quiet_mode=True, cwd=str(work), run_budget_seconds=260,
            tool_complete_callback=complete)
        try:
            result = parent.run_conversation(
                "Use ordinary delegate_task exactly once, foreground. Delegate this exact read-only goal: "
                f"Read the existing file {work / 'probe.txt'} directly with a file-reading tool. "
                "No directory discovery is needed. Do not execute shell commands or change files. "
                "Return a JSON object with one field, contents, containing the exact file text. "
                "Set the task output_schema to an object with required string property contents and no additional properties. "
                "Return the delegated result verbatim. Do not use terminal yourself, do not invent the file contents, "
                "and do not launch a replacement on failure.")
            (home.parent / "live-result.json").write_text(json.dumps(result, default=str, indent=2))
            (home.parent / "live-calls.json").write_text(json.dumps(calls, default=str, indent=2))
            tool_results = [m for m in result.get("messages", [])
                            if m.get("role") == "tool" and m.get("name") == "delegate_task"]
            self.assertEqual(len(tool_results), 1)
            children = json.loads(tool_results[0]["content"])["results"]
            self.assertEqual(len(children), 1)
            child = children[0]
            self.assertEqual(child["status"], "completed")
            self.assertEqual(child["route"]["provider"], "external-agents-agy")
            self.assertEqual(json.loads(child["summary"])["contents"], expected)
            self.assertIs(child.get("schema_valid"), True)
            database = home / "plugin-data" / "external-agents-agy" / "jobs.sqlite3"
            with sqlite3.connect(database) as connection:
                rows = connection.execute("SELECT state FROM jobs").fetchall()
            self.assertEqual(rows, [("completed",)], "Use a fresh disposable home per run")
            self.assertEqual((work / "probe.txt").read_text(), expected)
            print(json.dumps({"model_issued_delegate_results": len(tool_results),
                "external_child_completed": True, "exact_contents_verified": True,
                "job_records": len(rows), "schema_valid": child["schema_valid"]}))
        finally:
            parent.close()


if __name__ == "__main__":
    unittest.main()
