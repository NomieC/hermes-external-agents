"""Opt-in real AGY file-write smoke; never evidence of full Hermes delegation.

Run with HEA_LIVE_WRITE=1 and HEA_AGY_COMMAND set to the official executable.
The vendor's supported cached login must already work. No secrets are read here.
"""
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@unittest.skipUnless(os.environ.get("HEA_LIVE_WRITE") == "1", "Explicit write-probe opt-in required")
class LiveArtifactProbe(unittest.TestCase):
    def test_real_agy_creates_and_independently_verifies_tiny_artifact(self):
        from hea_runtime.runner import AGYRunner, RunnerConfig
        with tempfile.TemporaryDirectory(prefix="hea-artifact-", dir=os.environ.get("TMPDIR")) as directory:
            workspace = Path(directory)
            expected = "HEA_ARTIFACT_" + secrets.token_hex(12)
            runner = AGYRunner(RunnerConfig(command=os.environ["HEA_AGY_COMMAND"],
                workspace=directory, mode="accept-edits", timeout_seconds=240))
            try:
                result = runner.run(
                    f"Create exactly one new text file named artifact.txt in {directory}. "
                    f"Its complete contents must be exactly {expected}, with no trailing newline. "
                    "Use your own file-writing tool. No shell commands, network calls, or other file changes. "
                    "Return a short confirmation after writing. If permission is denied, stop and report it.")
                self.assertEqual(result.status, "SUCCESS")
                self.assertEqual(result.returncode, 0)
                self.assertTrue(result.response.strip())
                self.assertEqual((workspace / "artifact.txt").read_text(), expected)
                self.assertEqual({p.name for p in workspace.iterdir()}, {"artifact.txt"})
                self.assertEqual(runner.launch_count, 1)
                print(json.dumps({"artifact_verified": True, "launches": runner.launch_count,
                    "vendor_response_nonempty": bool(result.response.strip())}))
            finally:
                runner.close()


if __name__ == "__main__":
    unittest.main()
