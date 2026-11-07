"""Text-only process facade with a durable at-most-once launch fence.

Vendor tools run inside AGY, never as Hermes tool calls. Native tool restrictions
are not a sandbox for that external agent. This adapter requires explicit consent.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
import re
import sqlite3
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any


class ClientError(RuntimeError):
    """A terminal, non-replayable external-agent request error."""


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
                yield db
        finally:
            db.close()

    @staticmethod
    def _prompt(messages, workspace):
        parts = ["You are the external AGY worker for a Hermes delegated task. "
                 "Use your own available tools to complete the task. Return your final report as plain text. "
                 "Do not emit Hermes tool-call blocks or ask Hermes to repeat actions you already took. "
                 "Do not circumvent denied actions; report missing permissions and stop.\n"
                 f"Execution workspace: {workspace}\n"
                 "This is the explicitly configured external workspace; "
                 "wrapper working-directory metadata does not change this path. "
                 "Resolve task-relative paths here unless the task supplies another explicit path."]

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
        prompt = self._prompt(messages, workspace)
        with self._database() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT session,state,response FROM jobs WHERE token=?", (token,)).fetchone()
            if row:
                if row[0] != session:
                    raise ClientError("External-agent job belongs to another child session.")
                if row[1] == "completed":
                    return self._completion(row[2], model)
                raise ClientError("External-agent job already started or failed; automatic replay is refused.")
            db.execute("INSERT INTO jobs(token,session,state) VALUES(?,?,'started')", (token, session))
        config = SimpleNamespace(command=settings.get("executable", "agy"), workspace=workspace,
                                 mode=settings.get("mode", "plan"),
                                 timeout_seconds=settings.get("timeout_seconds", 180),
                                 max_output_bytes=settings.get("max_output_bytes", 4_000_000),
                                 model="" if model == "agy-default" else model)
        runner = None
        try:
            runner = self.runner_factory(config)
            with self._runner_lock:
                self._active = runner
                if self._cancelled.is_set():
                    runner.cancel()
            result = runner.run(prompt)
            if self._cancelled.is_set():
                raise ClientError("External-agent task was cancelled; automatic replay is refused.")
            if (result.status != "SUCCESS" or result.returncode != 0 or
                    not isinstance(result.response, str) or not result.response.strip()):
                raise ClientError("External agent did not return a successful terminal result.")
            with self._database() as db:
                db.execute("UPDATE jobs SET state='completed', response=? WHERE token=?", (result.response, token))
            return self._completion(result.response, model)
        except Exception as error:
            with self._database() as db:
                db.execute("UPDATE jobs SET state='failed' WHERE token=?", (token,))
            if isinstance(error, ClientError):
                raise
            raise ClientError("External AGY execution failed; no automatic replay. Check CLI login and plugin settings.") from None
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
