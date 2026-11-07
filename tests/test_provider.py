"""Test public external-process factory with explicit failing fixtures."""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class ProviderTests(unittest.TestCase):
    def test_timeout_classification_is_terminal_but_not_malformed(self):
        spec = importlib.util.spec_from_file_location("hea_provider_timeout_test", ROOT / "provider_profile.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from hea_runtime.client import ClientError
        verdict = module.terminal_error(ClientError("AGY run timed out", "timeout"))
        self.assertEqual(verdict["reason"], "timeout")
        self.assertFalse(verdict["retryable"])
        self.assertFalse(verdict["should_fallback"])
        self.assertFalse(verdict["should_rotate_credential"])

    def test_factory_returns_a_terminal_error_client_not_standard_fallback(self):
        spec = importlib.util.spec_from_file_location("hea_provider_test", ROOT / "provider_profile.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from hea_runtime.client import ClientError
        with patch.object(module, "load_client_class", side_effect=RuntimeError("fixture factory failure")):
            client = module.AGYProfile().create_client(command="missing-fixture")
        with self.assertRaises(ClientError):
            client.chat.completions.create(messages=[])
        self.assertFalse(client.is_closed)
        client.cancel()
        client.close()
        self.assertTrue(client.is_closed)
        profile = module.AGYProfile()
        self.assertEqual(profile.auth_type, "external_process")
        self.assertEqual(profile.process_command_env_vars, ("HERMES_EXTERNAL_AGENTS_AGY_COMMAND",))
        self.assertEqual(profile.build_extra_body(session_id="child-one"), {"hea_session": "child-one"})
        verdict = profile.classify_api_error(ClientError("fixture"), model="agy-default")
        self.assertFalse(verdict["retryable"])
        self.assertFalse(verdict["should_fallback"])


if __name__ == "__main__":
    unittest.main()
