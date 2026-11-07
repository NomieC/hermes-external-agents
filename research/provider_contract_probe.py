"""Host lifecycle probes with explicit fixture clients, not live vendor evidence.

Run only in a disposable HERMES_HOME with HEA_CONTRACT_PROBE=1. Production
code uses public APIs; the schema validation helper below is research-only
instrumentation of the audited host contract.
"""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@unittest.skipUnless(os.environ.get("HEA_CONTRACT_PROBE") == "1", "Disposable home opt-in required")
class ProviderContractProbe(unittest.TestCase):
    def profile_module(self):
        spec = importlib.util.spec_from_file_location("hea_contract_profile", ROOT / "provider_profile.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from providers import register_provider
        register_provider(module.AGYProfile())
        return module

    def agent(self, workspace, **kwargs):
        from run_agent import AIAgent
        return AIAgent(provider="external-agents-agy", model="agy-default",
            base_url="process://hermes-external-agents", api_key="external-process",
            command=sys.executable, max_iterations=3, enabled_toolsets=[],
            skip_context_files=True, skip_memory=True, skip_background_review=True,
            quiet_mode=True, cwd=str(workspace), run_budget_seconds=20, **kwargs)

    def test_factory_failure_is_terminal_under_real_host_agent(self):
        module = self.profile_module()
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as workspace:
            patcher = patch.object(module, "load_client_class", side_effect=RuntimeError("fixture factory failure"))
            patcher.start()
            self.addCleanup(patcher.stop)
            agent = self.agent(workspace)
            try:
                result = agent.run_conversation("No external execution is expected in this fixture.")
                self.assertTrue(result.get("failed") or result.get("error"), result)
                self.assertIsInstance(agent.client, module.UnavailableClient)
                self.assertIn("unavailable", str(result).lower())
            finally:
                agent.close()

    def test_real_host_schema_repair_returns_cache_without_vendor_replay(self):
        module = self.profile_module()
        from hea_runtime.client import AGYClient
        from tools.delegate_tool_child_run import _validate_child_output_schema
        launches = []

        class FixtureRunner:
            def __init__(self, config):
                pass

            def run(self, prompt):
                launches.append(prompt)
                return SimpleNamespace(response="fixture non-JSON result", status="SUCCESS", returncode=0)

            def close(self):
                pass

            def cancel(self):
                pass

        class FixtureClient(AGYClient):
            def __init__(self, **kwargs):
                super().__init__(runner_factory=FixtureRunner, **kwargs)

        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as workspace:
            body = {"hea_job": "9" * 32, "hea_workspace": workspace,
                    "hea_settings": {"allow_external_tools": True}}
            patcher = patch.object(module, "load_client_class", return_value=FixtureClient)
            patcher.start()
            self.addCleanup(patcher.stop)
            agent = self.agent(workspace, request_overrides={"extra_body": body})
            try:
                setattr(agent, "_delegate_output_schema", {"type": "object", "required": ["contents"],
                    "properties": {"contents": {"type": "string"}}})
                result = agent.run_conversation("Return the fixture answer.")
                self.assertEqual(len(launches), 1)
                outcome = _validate_child_output_schema(agent, result, 0, "fixture-task", None)
                self.assertEqual(len(launches), 1, "Schema repair repeated vendor execution")
                self.assertIs(outcome.valid, False)
            finally:
                agent.close()


if __name__ == "__main__":
    unittest.main()
