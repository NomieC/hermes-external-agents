"""Read-only discovery and routing HTTP contract probe in a disposable home."""
import unittest


class RegistrationProbe(unittest.TestCase):
    def test_public_registration_route_and_client_load(self):
        from hermes_cli.plugins import get_plugin_manager
        from agent.delegation_registry import get_active_provider
        from hermes_cli.config import load_config_readonly
        from providers import get_provider_profile
        manager = get_plugin_manager()
        manager.discover_and_load()
        config = load_config_readonly()
        backend = get_active_provider(config["delegation"])
        profile = get_provider_profile("external-agents-agy")
        self.assertEqual(backend.name, "external-agents")
        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertEqual(profile.auth_type, "external_process")
        route = backend.route_task({"goal": "registration-only"}, config["delegation"])
        self.assertEqual(route["provider"], profile.name)
        self.assertEqual(route["fallback_providers"], [])
        client = profile.create_client(command="agy")
        assert client is not None
        try:
            self.assertEqual(client.__class__.__name__, "AGYClient")
        finally:
            client.close()
        rows = [row for row in manager.list_plugins() if row.get("name", "").startswith("external-agents")]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row.get("enabled") and not row.get("error") for row in rows))

    def test_subagents_picker_routing_endpoint_exposes_backend(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from hermes_cli.web_routers.delegation import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            response = client.get("/api/delegation/routing")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["configured"], "external-agents")
        self.assertIsNone(payload["blocked_reason"])
        rows = [row for row in payload["backends"] if row["name"] == "external-agents"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["label"], "External Agents")
        self.assertTrue(rows[0]["available"])


if __name__ == "__main__":
    unittest.main()
