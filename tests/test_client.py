"""Facade tests use explicit fixtures, not evidence of vendor execution."""
import tempfile
import unittest
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ClientTests(unittest.TestCase):
    def test_completed_job_is_cached_across_client_recreation(self):
        try:
            from hea_runtime.client import AGYClient
        except ImportError:
            self.fail("The external-process client has not been implemented")
        launches = []

        class FixtureRunner:
            def __init__(self, config):
                self.config = config

            def run(self, prompt):
                launches.append(prompt)
                return SimpleNamespace(response="fixture answer", status="SUCCESS", returncode=0)

            def cancel(self):
                return None

            def close(self):
                return None

        with tempfile.TemporaryDirectory() as root:
            kwargs = dict(workspace=root, data_dir=Path(root) / "private", settings={"allow_external_tools": True},
                          runner_factory=FixtureRunner)
            request = dict(model="agy-default", messages=[{"role": "user", "content": "Do one thing"}],
                           extra_body={"hea_job": "a" * 32, "hea_session": "child-one"})
            first = AGYClient(**kwargs).chat.completions.create(**request)
            second = AGYClient(**kwargs).chat.completions.create(**request)
            self.assertEqual(first.choices[0].message.content, "fixture answer")
            self.assertEqual(second.choices[0].message.content, "fixture answer")
            self.assertIsNone(first.usage)
            self.assertIsNone(first.choices[0].message.tool_calls)
            self.assertEqual(len(launches), 1)

    def test_prompt_uses_external_workspace_not_wrapper_cwd(self):
        from hea_runtime.client import AGYClient
        prompts = []

        class Runner:
            def __init__(self, config):
                pass

            def run(self, prompt):
                prompts.append(prompt)
                return SimpleNamespace(response="done", status="SUCCESS", returncode=0)

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as root:
            client = AGYClient(workspace=root, data_dir=Path(root) / "private",
                settings={"allow_external_tools": True}, runner_factory=Runner)
            client.chat.completions.create(messages=[
                {"role": "system", "content": "WORKSPACE PATH: /wrapper-only"},
                {"role": "user", "content": "Read the task file"}],
                extra_body={"hea_job": "3" * 32, "hea_session": "one"})
            self.assertIn("Execution workspace: " + str(Path(root).resolve()), prompts[0])
            self.assertIn("wrapper working-directory metadata does not change this path", prompts[0])
            self.assertIn("Do not circumvent denied actions", prompts[0])

    def test_route_settings_reach_runner_without_enabling_direct_use(self):
        from hea_runtime.client import AGYClient, ClientError
        configurations = []

        class Runner:
            def __init__(self, config):
                configurations.append(config)

            def run(self, prompt):
                return SimpleNamespace(response="done", status="SUCCESS", returncode=0)

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as root:
            client = AGYClient(workspace=root, data_dir=Path(root) / "private", runner_factory=Runner)
            request = dict(messages=[{"role": "user", "content": "Task"}], extra_body={
                "hea_job": "0" * 32, "hea_session": "child-one", "hea_workspace": root,
                "hea_settings": {"allow_external_tools": True, "executable": "fixture-agy", "mode": "accept-edits"},
            })
            self.assertEqual(client.chat.completions.create(**request).choices[0].message.content, "done")
            self.assertEqual(configurations[0].command, "fixture-agy")
            self.assertEqual(configurations[0].mode, "accept-edits")
            self.assertEqual(configurations[0].workspace, str(Path(root).resolve()))
            with self.assertRaises(ClientError):
                client.chat.completions.create(messages=request["messages"])

    def test_empty_vendor_success_is_failed_and_cannot_be_replayed(self):
        from hea_runtime.client import AGYClient, ClientError
        launches = []

        class EmptyRunner:
            def __init__(self, config):
                pass

            def run(self, prompt):
                launches.append(prompt)
                return SimpleNamespace(response="  ", status="SUCCESS", returncode=0)

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as root:
            options = dict(workspace=root, data_dir=Path(root) / "private",
                           settings={"allow_external_tools": True}, runner_factory=EmptyRunner)
            request = dict(messages=[{"role": "user", "content": "Task"}],
                           extra_body={"hea_job": "1" * 32, "hea_session": "one"})
            for _ in range(2):
                with self.assertRaises(ClientError):
                    AGYClient(**options).chat.completions.create(**request)
            self.assertEqual(len(launches), 1)

    def test_runner_failure_does_not_disclose_underlying_exception(self):
        from hea_runtime.client import AGYClient, ClientError
        class BrokenRunner:
            def __init__(self, config):
                raise RuntimeError("private-fixture-value")

        with tempfile.TemporaryDirectory() as root:
            client = AGYClient(workspace=root, data_dir=Path(root) / "private",
                settings={"allow_external_tools": True}, runner_factory=BrokenRunner)
            with self.assertRaises(ClientError) as caught:
                client.chat.completions.create(messages=[{"role": "user", "content": "Task"}],
                    extra_body={"hea_job": "2" * 32, "hea_session": "one"})
            self.assertIsNone(caught.exception.__cause__)
            self.assertTrue(caught.exception.__suppress_context__)

    def test_storage_context_closes_database_connection(self):
        import sqlite3
        from hea_runtime.client import AGYClient
        with tempfile.TemporaryDirectory() as root:
            client = AGYClient(workspace=root, data_dir=Path(root) / "private")
            with client._database() as connection:
                self.assertEqual(connection.execute("SELECT 1").fetchone()[0], 1)
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")

    def test_existing_cache_permissions_are_tightened_without_losing_rows(self):
        import stat
        from hea_runtime.client import AGYClient
        with tempfile.TemporaryDirectory() as root:
            data_dir = Path(root) / "private"
            client = AGYClient(workspace=root, data_dir=data_dir)
            with client._database() as db:
                db.execute("INSERT INTO jobs VALUES(?,?,?,?)", ("9" * 32, "owner", "completed", "saved"))
            path = data_dir / "jobs.sqlite3"
            data_dir.chmod(0o755)
            path.chmod(0o644)
            with client._database() as db:
                self.assertEqual(db.execute("SELECT response FROM jobs").fetchone()[0], "saved")
                self.assertEqual(stat.S_IMODE(data_dir.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_nontext_input_is_refused_before_any_launch(self):
        from hea_runtime.client import AGYClient, ClientError
        with tempfile.TemporaryDirectory() as root:
            client = AGYClient(workspace=root, data_dir=Path(root) / "private",
                               settings={"allow_external_tools": True},
                               runner_factory=lambda config: self.fail("Must not launch"))
            with self.assertRaisesRegex(ClientError, "text-only"):
                client.chat.completions.create(messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": "https://example.invalid/image.png"}}
                ]}], extra_body={"hea_job": "b" * 32, "hea_session": "child-one"})

    def test_failed_job_is_not_replayed_by_a_new_client(self):
        from hea_runtime.client import AGYClient, ClientError
        launches = []

        class FailingRunner:
            def __init__(self, config):
                pass

            def run(self, prompt):
                launches.append(prompt)
                raise RuntimeError("fixture error without credentials")

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as root:
            options = dict(workspace=root, data_dir=Path(root) / "private", settings={"allow_external_tools": True},
                           runner_factory=FailingRunner)
            request = dict(messages=[{"role": "user", "content": "Task"}],
                           extra_body={"hea_job": "c" * 32, "hea_session": "child-one"})
            for _ in range(2):
                with self.assertRaises(ClientError):
                    AGYClient(**options).chat.completions.create(**request)
            self.assertEqual(len(launches), 1)

    def test_cached_job_is_not_visible_to_another_session(self):
        from hea_runtime.client import AGYClient, ClientError
        with tempfile.TemporaryDirectory() as root:
            client = AGYClient(workspace=root, data_dir=Path(root) / "private", settings={"allow_external_tools": True})
            with client._database() as db:
                db.execute("INSERT INTO jobs VALUES(?,?,?,?)", ("d" * 32, "owner", "completed", "private answer"))
            with self.assertRaisesRegex(ClientError, "another child session"):
                client.chat.completions.create(messages=[{"role": "user", "content": "Task"}],
                                               extra_body={"hea_job": "d" * 32, "hea_session": "other"})

    def test_concurrent_requests_on_one_client_are_refused(self):
        import threading
        from hea_runtime.client import AGYClient, ClientError
        started, release = threading.Event(), threading.Event()
        errors = []

        class BlockingRunner:
            def __init__(self, config):
                pass

            def run(self, prompt):
                started.set()
                if not release.wait(5):
                    raise RuntimeError("fixture deadline")
                return SimpleNamespace(response="done", status="SUCCESS", returncode=0)

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as root:
            client = AGYClient(workspace=root, data_dir=Path(root) / "private", settings={"allow_external_tools": True},
                               runner_factory=BlockingRunner)
            request = dict(messages=[{"role": "user", "content": "Task"}],
                           extra_body={"hea_job": "e" * 32, "hea_session": "one"})

            def work():
                try:
                    client.chat.completions.create(**request)
                except Exception as error:
                    errors.append(error)

            thread = threading.Thread(target=work)
            thread.start()
            try:
                self.assertTrue(started.wait(3))
                with self.assertRaisesRegex(ClientError, "concurrent"):
                    client.chat.completions.create(messages=request["messages"],
                                                   extra_body={"hea_job": "f" * 32, "hea_session": "two"})
            finally:
                release.set()
                thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
