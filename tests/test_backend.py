"""Host-backed public registration/route contract tests; no inference."""
import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BackendTests(unittest.TestCase):
    def test_status_cli_is_read_only_and_requires_child_ownership(self):
        import argparse
        import contextlib
        import io
        import json
        from unittest.mock import patch
        from types import SimpleNamespace
        spec = importlib.util.spec_from_file_location("hea_backend_cli_test", ROOT / "backend.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        registered = []
        ctx = SimpleNamespace(get_config=lambda key, default=None: default,
            register_delegation_provider=lambda provider: None,
            register_cli_command=lambda **kwargs: registered.append(kwargs))
        module.register(ctx)
        self.assertEqual(registered[0]["name"], "external-agents")
        parser = argparse.ArgumentParser()
        registered[0]["setup_fn"](parser)
        args = parser.parse_args(["status", "--job", "a" * 32, "--session", "child-one"])
        calls = []
        client = SimpleNamespace(job_status=lambda token, session: calls.append((token, session)) or
            {"token": token, "session": session, "state": "failed", "error_code": "timeout"},
            close=lambda: calls.append("closed"))
        output = io.StringIO()
        with patch("providers.get_provider_profile", return_value=SimpleNamespace(create_client=lambda: client)):
            with contextlib.redirect_stdout(output):
                registered[0]["handler_fn"](args)
        self.assertEqual(json.loads(output.getvalue())["error_code"], "timeout")
        self.assertEqual(calls, [("a" * 32, "child-one"), "closed"])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["status", "--job", "a" * 32])
        with patch("providers.get_provider_profile", return_value=SimpleNamespace(create_client=lambda: None)):
            with self.assertRaisesRegex(SystemExit, "unavailable"):
                registered[0]["handler_fn"](args)

    def test_nonlocal_terminal_policy_refuses_local_external_execution(self):
        spec = importlib.util.spec_from_file_location("hea_backend_policy_test", ROOT / "backend.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from agent.delegation_provider import DelegationRouteError
        with tempfile.TemporaryDirectory() as workspace:
            settings = {"workspace": workspace, "allow_external_tools": True, "executable": sys.executable}
            for policy in ("ssh", "docker", "auto", "modal"):
                with self.subTest(policy=policy):
                    backend = module.ExternalAgentsBackend(
                        lambda key, default=None: settings.get(key, default),
                        get_terminal_backend=lambda: policy)
                    with self.assertRaisesRegex(DelegationRouteError, "local terminal"):
                        backend.route_task({"goal": "Task"}, {})

    def test_registered_route_is_an_explicit_nonfallback_agy_job(self):
        spec = importlib.util.spec_from_file_location("hea_backend_test", ROOT / "backend.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as workspace:
            provider = module.ExternalAgentsBackend(lambda key, default=None: {
                "workspace": workspace, "allow_external_tools": True,
                "executable": sys.executable,
            }.get(key, default))
            config = {"provider": "custom", "base_url": "https://must-not-inherit.invalid", "fallback_providers": ["custom"]}
            route = provider.route_task({"goal": "Read the workspace", "index": 0}, config)
            self.assertEqual(route["provider"], "external-agents-agy")
            self.assertEqual(route["model"], "agy-default")
            self.assertEqual(route["fallback_providers"], [])
            self.assertNotIn("base_url", route)
            body = route["request_overrides"]["extra_body"]
            self.assertRegex(body["hea_job"], re.compile("^[a-f0-9]{32}$"))
            self.assertEqual(body["hea_workspace"], str(Path(workspace).resolve()))
            self.assertTrue(body["hea_settings"]["allow_external_tools"])
            next_route = provider.route_task({"goal": "Another task", "index": 1}, config)
            self.assertNotEqual(body["hea_job"], next_route["request_overrides"]["extra_body"]["hea_job"])
            from agent.delegation_provider import DelegationRouteError
            provider = module.ExternalAgentsBackend(lambda key, default=None: default)
            with self.assertRaises(DelegationRouteError):
                provider.route_task({"goal": "Task"}, {})


if __name__ == "__main__":
    unittest.main()
