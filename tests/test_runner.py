import json
import os
import tempfile
import time
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hea_runtime.runner import AGYError, AGYRunner, RunResult, RunnerConfig


SUCCESS = "print(json.dumps({'event':'result','result':{'status':'SUCCESS','response':'ok'}}), flush=True)\n"


class RunnerTests(unittest.TestCase):
    def make_runner(self, root, body, **config):
        command = root / "agy-fixture"
        command.write_text("#!/usr/bin/env python3\nimport json, os, signal, sys, time\n" + body)
        command.chmod(0o755)
        return AGYRunner(RunnerConfig(command=str(command), workspace=str(root), **config))

    def test_nonzero_exit_fails_without_disclosing_stderr(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            runner = self.make_runner(Path(temp), "sys.stderr.write('private-token-marker')\nsys.exit(7)\n")
            with self.assertRaisesRegex(RuntimeError, "AGY process failed") as caught:
                runner.run("hello")
            self.assertNotIn("private-token-marker", str(caught.exception))

    def test_successful_stream_returns_response_and_uses_expected_argv(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            root = Path(temp)
            args_file = root / "args.json"
            body = (f"open({str(args_file)!r}, 'w').write(json.dumps(sys.argv[1:]))\n"
                    "print(json.dumps({'event':'init'}), flush=True)\n" + SUCCESS)
            runner = self.make_runner(root, body, model="model-x")
            result = runner.run("hello")
            self.assertEqual(result, RunResult(response="ok", status="SUCCESS", returncode=0))
            self.assertEqual(json.loads(args_file.read_text()), ["--print", "hello", "--output-format", "stream-json", "--mode", "plan", "--sandbox", "--print-timeout", "180s", "--model", "model-x"])
            self.assertEqual(runner.launch_count, 1)

    def test_empty_schema_uses_prompt_contract_not_unsupported_vendor_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args_file = root / "args.json"
            runner = self.make_runner(root,
                f"open({str(args_file)!r}, 'w').write(json.dumps(sys.argv[1:]))\n" + SUCCESS,
                json_schema={})
            runner.run("Return JSON")
            argv = json.loads(args_file.read_text())
            self.assertNotIn("--json-schema", argv)

    def test_object_schema_reaches_vendor_argv(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args_file = root / "args.json"
            schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
            runner = self.make_runner(root,
                f"open({str(args_file)!r}, 'w').write(json.dumps(sys.argv[1:]))\n" + SUCCESS,
                json_schema=schema)
            runner.run("Return JSON")
            argv = json.loads(args_file.read_text())
            self.assertEqual(json.loads(argv[argv.index("--json-schema") + 1]), schema)

    def test_vendor_terminal_timeout_has_timeout_code(self):
        with tempfile.TemporaryDirectory() as temp:
            runner = self.make_runner(Path(temp),
                "print(json.dumps({'event':'result','result':{'status':'ERROR','response':'',"
                "'finished_reason':'print_timeout','error':'private detail'}}), flush=True)\nsys.exit(3)\n")
            with self.assertRaises(AGYError) as caught:
                runner.run("x")
            self.assertEqual(caught.exception.code, "timeout")
            self.assertNotIn("private", str(caught.exception))

    def test_real_ndjson_newline_is_accepted(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            root = Path(temp)
            command = root / "agy-real-newline"
            payload = json.dumps({"event": "result", "result": {
                "status": "SUCCESS", "response": "real line ending"}}).encode() + bytes([10])
            command.write_text(chr(10).join([
                "#!/usr/bin/env python3", "import sys",
                f"sys.stdout.buffer.write({payload!r})", ""]))
            command.chmod(0o755)
            runner = AGYRunner(RunnerConfig(command=str(command), workspace=str(root)))
            self.assertEqual(runner.run("x").response, "real line ending")

    def test_timeout_stops_process(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            runner = self.make_runner(Path(temp), "time.sleep(10)\n", timeout_seconds=0.15)
            started = time.monotonic()
            with self.assertRaisesRegex(AGYError, "timed out"):
                runner.run("x")
            self.assertLess(time.monotonic() - started, 2)

    def test_timeout_retains_stream_session_and_sanitized_progress(self):
        cid = "12345678-1234-4234-8234-123456789abc"
        with tempfile.TemporaryDirectory() as temp:
            updates = []
            body = (f"print(json.dumps({{'event':'init','conversation_id':{cid!r}}}), flush=True)\n"
                    "print(json.dumps({'event':'step_update','step_update':{'step_index':2,"
                    "'step_type':'tool','state':'completed','text_delta':'private text'}}), flush=True)\n"
                    "time.sleep(10)\n")
            runner = self.make_runner(Path(temp), body, timeout_seconds=2,
                                      event_callback=updates.append)
            with self.assertRaises(AGYError) as caught:
                runner.run("private prompt")
            self.assertEqual(getattr(caught.exception, "code", None), "timeout")
            self.assertEqual(runner.conversation_id, cid)
            self.assertEqual(updates[-1]["step_index"], 2)
            self.assertEqual(updates[-1]["state"], "completed")
            self.assertNotIn("private", json.dumps(updates))
            self.assertGreater(runner.duration_seconds, 0)

    def test_progress_drops_unknown_metadata_values(self):
        with tempfile.TemporaryDirectory() as temp:
            updates = []
            runner = self.make_runner(Path(temp),
                "print(json.dumps({'event':'step_update','step_update':{'step_index':1,"
                "'step_type':'secretvalue','state':'privatevalue','tool_name':'private-tool'}}), flush=True)\n" + SUCCESS,
                event_callback=updates.append)
            runner.run("x")
            self.assertEqual(updates[0], {"event": "step_update", "conversation_id": None, "step_index": 1})

    def test_inconsistent_conversation_identity_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            body = ("print(json.dumps({'event':'init','conversation_id':'12345678-1234-4234-8234-123456789abc'}), flush=True)\n"
                    "print(json.dumps({'event':'step_update','step_update':{'conversation_id':'22345678-1234-4234-8234-123456789abc'}}), flush=True)\n" + SUCCESS)
            runner = self.make_runner(Path(temp), body)
            with self.assertRaises(AGYError) as caught:
                runner.run("x")
            self.assertEqual(caught.exception.code, "protocol_error")

    def test_output_limit_is_enforced_while_streaming(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            root = Path(temp)
            marker = root / "continued"
            body = ("sys.stdout.write('x' * 2000000)\nsys.stdout.flush()\n"
                    f"open({str(marker)!r}, 'w').write('yes')\n" + SUCCESS)
            runner = self.make_runner(root, body, max_output_bytes=1024)
            with self.assertRaisesRegex(AGYError, "output exceeded"):
                runner.run("x")
            self.assertFalse(marker.exists(), "child continued after output cap should have been detected")

    def test_duplicate_terminal_results_fail(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            runner = self.make_runner(Path(temp), SUCCESS + SUCCESS)
            with self.assertRaisesRegex(AGYError, "duplicate terminal"):
                runner.run("x")

    def test_malformed_and_truncated_utf8_ndjson_fail(self):
        for payload in (b'{bad}\n', b'{"event":"init"}', b'{"event":"init"}\n\xff\n'):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
                runner = self.make_runner(Path(temp), f"sys.stdout.buffer.write({payload!r})\n")
                with self.assertRaises(AGYError):
                    runner.run("x")

    def test_truncated_stream_has_protocol_error_code(self):
        with tempfile.TemporaryDirectory() as temp:
            runner = self.make_runner(Path(temp), "sys.stdout.write('{\"event\":\"init\"}')\n")
            with self.assertRaises(AGYError) as caught:
                runner.run("x")
            self.assertEqual(caught.exception.code, "protocol_error")

    def test_failed_final_result_fails(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            runner = self.make_runner(Path(temp), "print(json.dumps({'event':'result','result':{'status':'ERROR','response':'secret'}}))\n")
            with self.assertRaisesRegex(AGYError, "unsuccessful"):
                runner.run("x")

    def test_cancel_before_run_prevents_launch(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            runner = self.make_runner(Path(temp), SUCCESS)
            runner.cancel()
            with self.assertRaisesRegex(AGYError, "cancelled"):
                runner.run("x")
            self.assertEqual(runner.launch_count, 0)

    def test_cancel_during_run_is_prompt_even_when_sigterm_ignored(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            root = Path(temp)
            marker = root / "ready"
            body = f"signal.signal(signal.SIGTERM, signal.SIG_IGN)\nopen({str(marker)!r}, 'w').write('ready')\ntime.sleep(10)\n"
            runner = self.make_runner(root, body, timeout_seconds=8)
            errors = []
            import threading
            thread = threading.Thread(target=lambda: self._run_capture(runner, errors))
            thread.start()
            deadline = time.monotonic() + 2
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            started = time.monotonic()
            runner.cancel()
            thread.join(2)
            self.assertFalse(thread.is_alive(), "cancelled run did not return promptly")
            self.assertLess(time.monotonic() - started, 2)
            self.assertTrue(errors and isinstance(errors[0], AGYError))

    @staticmethod
    def _run_capture(runner, errors):
        try:
            runner.run("x")
        except Exception as exc:
            errors.append(exc)

    def test_descendant_is_stopped_when_leader_exits_after_success(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            root = Path(temp)
            marker = root / "descendant-escaped"
            body = ("child = os.fork()\n"
                    "if child == 0:\n"
                    "    signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                    "    time.sleep(0.8)\n"
                    f"    open({str(marker)!r}, 'w').write('escaped')\n"
                    "    os._exit(0)\n" + SUCCESS)
            runner = self.make_runner(root, body)
            self.assertEqual(runner.run("x").response, "ok")
            time.sleep(1)
            self.assertFalse(marker.exists(), "owned descendant survived its leader")

    def test_repeated_run_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            runner = self.make_runner(Path(temp), SUCCESS)
            runner.run("x")
            with self.assertRaisesRegex(AGYError, "only be used once"):
                runner.run("x")

    def test_missing_binary_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            with self.assertRaisesRegex(AGYError, "not found"):
                AGYRunner(RunnerConfig(command="definitely-no-such-agy-executable", workspace=temp))

    def test_environment_is_scrubbed(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            root = Path(temp)
            output = root / "env.json"
            runner = self.make_runner(root, f"open({str(output)!r}, 'w').write(json.dumps(dict(os.environ)))\n" + SUCCESS)
            old = os.environ.get("AGY_PRIVATE_MARKER")
            os.environ["AGY_PRIVATE_MARKER"] = "secret"
            try:
                runner.run("x")
            finally:
                if old is None:
                    os.environ.pop("AGY_PRIVATE_MARKER", None)
                else:
                    os.environ["AGY_PRIVATE_MARKER"] = old
            self.assertNotIn("AGY_PRIVATE_MARKER", json.loads(output.read_text()))


if __name__ == "__main__":
    unittest.main()
