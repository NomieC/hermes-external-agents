"""Both load lifecycles ship as self-contained generated plugin directories."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_build_produces_two_self_contained_registrations(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, str(ROOT / "scripts/build_plugins.py"), "--output", temp],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = Path(temp)
            backend = output / "external-agents"
            provider = output / "external-agents-agy"
            self.assertIn("kind: backend", (backend / "plugin.yaml").read_text())
            self.assertIn("config_schema:", (backend / "plugin.yaml").read_text())
            self.assertIn("register", (backend / "__init__.py").read_text())
            self.assertIn("kind: model-provider", (provider / "plugin.yaml").read_text())
            self.assertTrue((provider / "hea_runtime/client.py").is_file())
            self.assertTrue((provider / "hea_runtime/runner.py").is_file())
            self.assertFalse(any(output.rglob("__pycache__")))
            for registration in (backend, provider):
                self.assertEqual((registration / "LICENSE").read_text(), (ROOT / "LICENSE").read_text())
                manifest = (registration / "plugin.yaml").read_text()
                self.assertIn('version: 0.2.0', manifest)
                self.assertIn('requires_hermes: ">=0.22.5"', manifest)
                readme = (registration / "README.md").read_text()
                self.assertIn("Both registrations", readme)
                self.assertIn("not a security sandbox", readme)
                self.assertIn("../../README.md", readme)
            self.assertEqual((backend / "__init__.py").read_bytes(), (ROOT / "backend.py").read_bytes())
            self.assertEqual((provider / "provider_profile.py").read_bytes(), (ROOT / "provider_profile.py").read_bytes())
            for filename in ("client.py", "runner.py"):
                self.assertEqual((provider / "hea_runtime" / filename).read_bytes(),
                                 (ROOT / "hea_runtime" / filename).read_bytes())


if __name__ == "__main__":
    unittest.main()
