"""Text-only process facade with a durable at-most-once launch fence.

Vendor tools run inside AGY, never as Hermes tool calls. Native tool restrictions
are not a sandbox for that external agent. This adapter requires explicit consent.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
import re
import sqlite3
import threading
import shlex
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any


class ClientError(RuntimeError):
    """A terminal, non-replayable external-agent request error."""

    def __init__(self, message, code="execution_failed"):
        super().__init__(message)
        self.code = code


def _default_runner(config):
    from .runner import AGYRunner, RunnerConfig
    return AGYRunner(RunnerConfig(**vars(config)))


class AGYClient:
    HERMES_SKIP_TRANSPORT_WRAP = True
    HERMES_SKIP_ASYNC_WRAP = True

    def __init__(self, *, workspace, data_dir, settings=None, runner_factory=None, **kwargs):
        self.api_key = "external-process"
        self.base_url = "process://hermes-external-agents"
        self.workspace = str(Path(workspace).resolve())
        self.data_dir = Path(data_dir)
        self.settings = dict(settings or {})
        self.runner_factory = runner_factory or _default_runner
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.is_closed = False
        self._cancelled = threading.Event()
        self._runner_lock = threading.Lock()
        self._request_lock = threading.Lock()
        self._active = None

    @contextmanager
    def _database(self):
        self.data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.data_dir.chmod(0o700)
        path = self.data_dir / "jobs.sqlite3"
        fd = os.open(path, os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        db = sqlite3.connect(path, timeout=5)
        try:
            with db:
                db.execute("CREATE TABLE IF NOT EXISTS jobs (token TEXT PRIMARY KEY, session TEXT NOT NULL, "
                           "state TEXT NOT NULL, response TEXT)")
                db.execute("CREATE TABLE IF NOT EXISTS job_details (token TEXT PRIMARY KEY, "
                           "workspace TEXT, executable TEXT, conversation_id TEXT, error_code TEXT, "
                           "error_message TEXT, duration_seconds REAL, progress TEXT)")
                yield db
        finally:
            db.close()

    def job_status(self, token, session):
        """Owner-bound diagnostic lookup; never returns prompts or cached response text."""
        with self._database() as db:
            row = db.execute("SELECT session,state FROM jobs WHERE token=?", (token,)).fetchone()
            if not row:
                raise ClientError("Unknown external-agent job.")
            if row[0] != session:
                raise ClientError("External-agent job belongs to another child session.")
            details = db.execute("SELECT workspace,executable,conversation_id,error_code,error_message,"
                                 "duration_seconds,progress FROM job_details WHERE token=?", (token,)).fetchone()
        result = dict(token=token, session=session, state=row[1])
        if details:
            result.update(zip(("workspace", "executable", "conversation_id", "error_code", "error_message",
                               "duration_seconds", "progress"), details))
            result["progress"] = json.loads(result["progress"] or "{}")
            if result["conversation_id"]:
                result["resume_command"] = ("cd " + shlex.quote(result["workspace"]) + " && " +
                    shlex.join([result["executable"], "--mode", "plan", "--conversation", result["conversation_id"]]))
        return result

    def _progress(self, token, session, progress):
        with self._database() as db:
            db.execute("UPDATE job_details SET conversation_id=COALESCE(?,conversation_id),progress=? "
                       "WHERE token=? AND EXISTS (SELECT 1 FROM jobs WHERE token=? AND session=?)",
                       (progress.get("conversation_id"), json.dumps(progress), token, token, session))

    @staticmethod
    def _output_schema(messages, response_format=None):
        # Public text contract appended by Hermes. The routing interface does not
        # expose output_schema; never reach into a live child's private attributes.
        if isinstance(response_format, dict) and response_format.get("type") == "json_schema":
            description = response_format.get("json_schema")
            schema = description.get("schema") if isinstance(description, dict) else None
            if not isinstance(schema, dict):
                raise ClientError("Cannot read the requested JSON output contract; no execution was attempted.")
            return schema
        marker = "OUTPUT CONTRACT (machine-validated):\n"
        for message in messages or []:
            if not isinstance(message, dict) or message.get("role") != "system":
                continue
            content = message.get("content")
            if not isinstance(content, str) or marker not in content:
                continue
            tail = content.rsplit(marker, 1)[1]
            for match in re.finditer(r"(?m)^\s*\{", tail):
                try:
                    schema, _ = json.JSONDecoder().raw_decode(tail[match.start():].lstrip())
                except ValueError:
                    continue
                if isinstance(schema, dict):
                    return schema
            raise ClientError("Cannot read the host JSON output contract; no execution was attempted.")
        return None

    @staticmethod
    def _prompt(messages, workspace, schema=None):
        output = ("Return ONLY a JSON value satisfying the supplied output contract, with no prose or fences. "
                  if schema is not None else "Return your final report as plain text. ")
        parts = ["You are the external AGY worker for a Hermes delegated task. "
                 "Use your own available tools to complete the task. " + output +
                 "Do not emit Hermes tool-call blocks or ask Hermes to repeat actions you already took. "
                 "Do not circumvent denied actions; report missing permissions and stop.\n"
                 f"Execution workspace: {workspace}\n"
                 "This is the explicitly configured external workspace; "
                 "wrapper working-directory metadata does not change this path. "
                 "Resolve task-relative paths here unless the task supplies another explicit path."]

        if schema is not None:
            parts.append("JSON output schema: " + json.dumps(schema, ensure_ascii=False))
        for message in messages or []:
            if not isinstance(message, dict):
                raise ClientError("External Agents accepts text-only messages.")
            content = message.get("content")
            if isinstance(content, list):
                if any(not isinstance(part, dict) or part.get("type") != "text" or
                       not isinstance(part.get("text"), str) for part in content):
                    raise ClientError("External Agents accepts text-only messages.")
                content = "\n".join(part["text"] for part in content)
            if content is not None and not isinstance(content, str):
                raise ClientError("External Agents accepts text-only messages.")
            if isinstance(content, str) and content.strip():
                parts.append(str(message.get("role", "context")) + ":\n" + content)
        return "\n\n".join(parts)

    @staticmethod
    def _completion(text, model):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=text, tool_calls=None,
                                                              reasoning=None, reasoning_content=None,
                                                              reasoning_details=None), finish_reason="stop")],
            usage=None, model=model,
        )

    def _create(self, **kwargs):
        if not self._request_lock.acquire(blocking=False):
            raise ClientError("External-agent client cannot accept concurrent requests.")
        try:
            return self._create_once(**kwargs)
        finally:
            self._request_lock.release()

    def _create_once(self, *, model="agy-default", messages=None, extra_body=None, stream=False, **kwargs):
        if self.is_closed or self._cancelled.is_set():
            raise ClientError("External-agent client was cancelled or closed; task was not replayed.")
        body = extra_body if isinstance(extra_body, dict) else {}
        settings = dict(self.settings)
        route_settings = body.get("hea_settings")
        if isinstance(route_settings, dict):
            settings.update(route_settings)
        workspace = body.get("hea_workspace", self.workspace)
        if not isinstance(workspace, str) or not Path(workspace).is_dir():
            raise ClientError("External Agents requires an existing workspace.")
        workspace = str(Path(workspace).resolve())
        if settings.get("allow_external_tools") is not True:
            raise ClientError("Enable allow_external_tools only after accepting AGY's separate tool/permission boundary.")
        if stream:
            raise ClientError("External Agents does not support response streaming in this version.")
        token, session = body.get("hea_job"), body.get("hea_session")
        if not isinstance(token, str) or not re.fullmatch(r"[a-f0-9]{32}", token):
            raise ClientError("Missing trusted delegation job token; direct model use is unsupported.")
        if not isinstance(session, str) or not session or len(session) > 256:
            raise ClientError("Missing child session identity.")
        schema = self._output_schema(messages, kwargs.get("response_format"))
        prompt = self._prompt(messages, workspace, schema)
        with self._database() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT session,state,response FROM jobs WHERE token=?", (token,)).fetchone()
            if row:
                if row[0] != session:
                    raise ClientError("External-agent job belongs to another child session.")
                if row[1] == "completed":
                    return self._completion(row[2], model)
                details = db.execute("SELECT error_code,error_message FROM job_details WHERE token=?", (token,)).fetchone()
                if details and details[1]:
                    raise ClientError(details[1], details[0] or "execution_failed")
                raise ClientError("External-agent job already started or failed; automatic replay is refused.")
            db.execute("INSERT INTO jobs(token,session,state) VALUES(?,?,'started')", (token, session))
            db.execute("INSERT INTO job_details(token,workspace,executable) VALUES(?,?,?)",
                       (token, workspace, settings.get("executable", "agy")))
        config = SimpleNamespace(command=settings.get("executable", "agy"), workspace=workspace,
                                 mode=settings.get("mode", "plan"),
                                 timeout_seconds=settings.get("timeout_seconds", 180),
                                 max_output_bytes=settings.get("max_output_bytes", 4_000_000),
                                 model="" if model == "agy-default" else model, json_schema=schema,
                                 event_callback=lambda event: self._progress(token, session, event))
        runner = None
        started = time.monotonic()
        try:
            runner = self.runner_factory(config)
            with self._runner_lock:
                self._active = runner
                if self._cancelled.is_set():
                    runner.cancel()
            result = runner.run(prompt)
            if self._cancelled.is_set():
                raise ClientError("External-agent task was cancelled; automatic replay is refused.", "cancelled")
            if (result.status != "SUCCESS" or result.returncode != 0 or
                    not isinstance(result.response, str) or not result.response.strip()):
                raise ClientError("External agent did not return a successful terminal result.")
            with self._database() as db:
                db.execute("UPDATE jobs SET state='completed', response=? WHERE token=?", (result.response, token))
            with self._database() as db:
                db.execute("UPDATE job_details SET duration_seconds=? WHERE token=?",
                           (time.monotonic() - started, token))
            return self._completion(result.response, model)
        except Exception as error:
            from .runner import AGYError
            code = error.code if isinstance(error, (ClientError, AGYError)) else "execution_failed"
            messages = {"timeout": "AGY run timed out; actions may already have run. Automatic replay is refused.",
                        "cancelled": "AGY run cancelled; actions may already have run. Automatic replay is refused.",
                        "output_limit": "AGY output exceeded its limit. Automatic replay is refused.",
                        "protocol_error": "AGY returned invalid stream metadata. Automatic replay is refused."}
            message = messages.get(code, "External AGY execution failed; no automatic replay. Check CLI login and plugin settings.")
            with self._database() as db:
                db.execute("UPDATE jobs SET state='failed' WHERE token=?", (token,))
                db.execute("UPDATE job_details SET error_code=?,error_message=?,duration_seconds=? WHERE token=?",
                           (code, message, time.monotonic() - started, token))
            raise ClientError(message, code) from None
        finally:
            with self._runner_lock:
                self._active = None
            if runner is not None:
                runner.close()

    def cancel(self):
        self._cancelled.set()
        with self._runner_lock:
            if self._active is not None:
                self._active.cancel()

    def close(self):
        self.is_closed = True
        self.cancel()
