"""Opt-in, nonmutating real AGY timeout/cancel probes, separate from UI parity.

Set HEA_LIFECYCLE_PROBE=1, HEA_AGY and HEA_LIFECYCLE_DIR to explicit scratch
paths. AGY uses its supported login. No credential stores are inspected.
"""
import json
import os
from pathlib import Path
import secrets
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@unittest.skipUnless(os.environ.get("HEA_LIFECYCLE_PROBE") == "1", "Explicit live opt-in required")
class LiveLifecycleProbe(unittest.TestCase):
    def exercise(self, kind):
        from hea_runtime.client import AGYClient, ClientError
        from hea_runtime.runner import AGYRunner, RunnerConfig
        base = Path(os.environ["HEA_LIFECYCLE_DIR"])
        base.mkdir(mode=0o700, parents=True, exist_ok=True)
        work = base / kind
        work.mkdir()
        runners = []
        token = secrets.token_hex(16)
        session = "live-lifecycle-" + kind
        client = None

        def factory(config):
            original = config.event_callback

            def callback(event):
                original(event)
                if kind == "cancelled" and event["event"] == "init":
                    assert client is not None
                    client.cancel()

            config.event_callback = callback
            runner = AGYRunner(RunnerConfig(**vars(config)))
            runners.append(runner)
            return runner

        settings = {"allow_external_tools": True, "executable": os.environ["HEA_AGY"],
                    "mode": "plan", "timeout_seconds": 10 if kind == "timeout" else 30}
        client = AGYClient(workspace=work, data_dir=base / "private", settings=settings, runner_factory=factory)
        request = dict(messages=[{"role": "user", "content":
            "Reply with HEA_LIFECYCLE_READY. Do not use any tools, access files, execute commands or create a plan artifact."}],
            extra_body={"hea_job": token, "hea_session": session})
        try:
            with self.assertRaises(ClientError) as caught:
                client.chat.completions.create(**request)
            self.assertEqual(caught.exception.code, kind)
            self.assertEqual(len(runners), 1)
            self.assertEqual(runners[0].launch_count, 1)
            self.assertIsNone(runners[0]._process, "Owned subprocess was not reaped")
            status = client.job_status(token, session)
            self.assertEqual(status["state"], "failed")
            self.assertEqual(status["error_code"], kind)
            retry = AGYClient(workspace=work, data_dir=base / "private", settings=settings, runner_factory=factory)
            try:
                with self.assertRaises(ClientError) as repeated:
                    retry.chat.completions.create(**request)
                self.assertEqual(repeated.exception.code, kind)
                self.assertEqual(len(runners), 1, "Terminal job was replayed")
            finally:
                retry.close()
            (base / (kind + ".json")).write_text(json.dumps({"job": status,
                "launches": 1, "reaped": True, "replay_refused": True}, indent=2))
            self.assertEqual(list(work.iterdir()), [])
        finally:
            client.close()

    def test_real_timeout_no_replay(self):
        self.exercise("timeout")

    def test_real_cancel_after_init_no_replay(self):
        self.exercise("cancelled")


if __name__ == "__main__":
    unittest.main()
