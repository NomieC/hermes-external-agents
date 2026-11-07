"""Safe, bounded subprocess execution for the AGY CLI.

AGY's ``--sandbox`` flag is requested, but is not evidence of OS-level
containment. Callers must not treat this runner as a security sandbox.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable
import uuid


@dataclass
class RunnerConfig:
    command: str = "agy"
    workspace: str = "."
    mode: str = "plan"
    timeout_seconds: float = 180
    max_output_bytes: int = 4_000_000
    model: str = ""
    json_schema: Optional[dict] = None
    event_callback: Optional[Callable[[dict], None]] = None


@dataclass
class RunResult:
    response: str
    status: str
    returncode: int


class AGYError(RuntimeError):
    """Only locally authored, bounded error messages may cross this boundary."""

    def __init__(self, message, code="execution_failed"):
        super().__init__(message)
        self.code = code


class _ExitObserver:
    """Observe exit without reaping, keeping the process-group id owned."""

    def __init__(self, process):
        self.process = process
        self.exited = False
        self.libc = None
        if not hasattr(os, "waitid"):
            # CPython on Darwin exposes wait flags but not os.waitid. Use the
            # system call without decoding platform-dependent siginfo fields.
            import ctypes
            import sys
            if sys.platform != "darwin":
                raise AGYError("This POSIX platform cannot safely supervise AGY process groups")
            self.libc = ctypes.CDLL(None, use_errno=True)
            self.libc.waitid.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_int]
            self.libc.waitid.restype = ctypes.c_int

    def has_exited(self):
        if not self.exited:
            flags = os.WEXITED | os.WNOHANG | os.WNOWAIT
            if self.libc is None:
                self.exited = os.waitid(os.P_PID, self.process.pid, flags) is not None
            else:
                import ctypes
                info = ctypes.create_string_buffer(256)
                if self.libc.waitid(os.P_PID, self.process.pid, ctypes.byref(info), flags) != 0:
                    raise AGYError("Could not observe AGY process exit")
                self.exited = any(info.raw)
        return self.exited

    def close(self):
        pass


class AGYRunner:
    def __init__(self, config: RunnerConfig):
        self.config = config
        self.launch_count = 0
        self.conversation_id = None
        self.last_progress = {}
        self.duration_seconds = 0.0
        self._lock = threading.RLock()
        self._cancelled = False
        self._used = False
        self._process: Optional[subprocess.Popen] = None
        if os.name == "nt":
            raise AGYError("AGY runner supports POSIX platforms only")
        if config.mode not in ("plan", "accept-edits"):
            raise AGYError("Unsupported AGY mode")
        if config.timeout_seconds <= 0 or config.max_output_bytes <= 0:
            raise AGYError("Timeout and output limit must be positive")
        workspace = Path(config.workspace).expanduser()
        if not workspace.is_dir():
            raise AGYError("Workspace must be an existing directory")
        self._workspace = str(workspace.resolve())
        resolved = shutil.which(config.command)
        if resolved is None or not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
            raise AGYError("AGY executable was not found or is not executable")
        self._executable = os.path.abspath(resolved)

    def _event(self, item):
        event = item.get("event")
        payload = item.get(event, {})
        candidate = item.get("conversation_id") or (payload.get("conversation_id") if isinstance(payload, dict) else None)
        if candidate is not None:
            try:
                valid = str(uuid.UUID(candidate)) == candidate
            except (ValueError, TypeError, AttributeError):
                valid = False
            if not valid or (self.conversation_id and candidate != self.conversation_id):
                raise AGYError("AGY returned inconsistent conversation identity", "protocol_error")
            self.conversation_id = candidate
        progress = {"event": event, "conversation_id": self.conversation_id}
        if event == "step_update" and isinstance(payload, dict):
            # Metadata only: never persist prompts, reasoning, file content or tool arguments.
            index = payload.get("step_index")
            if isinstance(index, int) and not isinstance(index, bool) and 0 <= index <= 1_000_000:
                progress["step_index"] = index
            allowed = {
                "step_type": {"user_input", "agent_response", "tool", "tool_call", "tool_result"},
                "state": {"DONE", "RUNNING", "PENDING", "ERROR", "CANCELLED", "FAILED",
                          "completed", "running", "pending", "failed", "cancelled"},
            }
            for key, values in allowed.items():
                value = payload.get(key)
                if isinstance(value, str) and value in values:
                    progress[key] = value
        self.last_progress = progress
        if self.config.event_callback:
            self.config.event_callback(dict(progress))

    def run(self, prompt: str) -> RunResult:
        started = time.monotonic()
        with self._lock:
            if self._used:
                raise AGYError("An AGY runner can only be used once")
            self._used = True
            if self._cancelled:
                raise AGYError("AGY run cancelled", "cancelled")
        argv = [self._executable, "--print", prompt, "--output-format", "stream-json",
                "--mode", self.config.mode, "--sandbox", "--print-timeout",
                f"{self.config.timeout_seconds:g}s"]
        if self.config.model:
            argv.extend(["--model", self.config.model])
        # AGY 1.5.x rejects {} / non-object roots before opening a conversation.
        # Those contracts remain in the prompt and are validated by Hermes.
        if self.config.json_schema is not None and self.config.json_schema.get("type") == "object":
            argv.extend(["--json-schema", json.dumps(self.config.json_schema, ensure_ascii=False)])
        env = {k: v for k, v in os.environ.items() if k in {
            "HOME", "PATH", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE",
            "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE",
        }}
        process = None
        selector = None
        observer = None
        try:
            with self._lock:
                if self._cancelled:
                    raise AGYError("AGY run cancelled", "cancelled")
                process = subprocess.Popen(argv, cwd=self._workspace, env=env,
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    start_new_session=True, bufsize=0)
                self._process = process
                self.launch_count += 1
            observer = _ExitObserver(process)
            import selectors
            selector = selectors.DefaultSelector()
            streams = {process.stdout: bytearray(), process.stderr: bytearray()}
            for stream in streams:
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ)
            deadline = time.monotonic() + self.config.timeout_seconds
            total = 0
            eof_deadline = None
            pending = bytearray()
            while selector.get_map():
                with self._lock:
                    cancelled = self._cancelled
                if cancelled:
                    raise AGYError("AGY run cancelled", "cancelled")
                now = time.monotonic()
                if now >= deadline:
                    raise AGYError("AGY run timed out", "timeout")
                if observer.has_exited() and eof_deadline is None:
                    # Descendants may inherit pipes; don't wait for them indefinitely.
                    eof_deadline = min(deadline, now + 0.25)
                if eof_deadline is not None and now >= eof_deadline:
                    break
                events = selector.select(min(0.05, deadline-now,
                                             max(0.001, eof_deadline-now) if eof_deadline else 0.05))
                for key, _ in events:
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    total += len(chunk)
                    if total > self.config.max_output_bytes:
                        raise AGYError("AGY output exceeded configured limit", "output_limit")
                    streams[key.fileobj].extend(chunk)
                    if key.fileobj is process.stdout:
                        pending.extend(chunk)
                        while b"\n" in pending:
                            line, _, remaining = pending.partition(b"\n")
                            pending = bytearray(remaining)
                            try:
                                item = json.loads(line.decode("utf-8", errors="strict"))
                            except (ValueError, UnicodeDecodeError):
                                raise AGYError("AGY returned malformed stream output", "protocol_error") from None
                            if not isinstance(item, dict) or not isinstance(item.get("event"), str):
                                raise AGYError("AGY returned malformed stream output", "protocol_error")
                            if item["event"] in ("init", "step_update", "result"):
                                self._event(item)
            while not observer.has_exited():
                if self._cancelled:
                    raise AGYError("AGY run cancelled", "cancelled")
                if time.monotonic() >= deadline:
                    raise AGYError("AGY run timed out", "timeout")
                time.sleep(0.005)
            # The leader stays unreaped until all group signals have been sent.
            # This prevents a recycled PID from receiving cleanup signals.
            self._stop(process)
            with self._lock:
                if self._cancelled:
                    raise AGYError("AGY run cancelled", "cancelled")
            out = bytes(streams[process.stdout])
            try:
                text = out.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                raise AGYError("AGY returned malformed stream output", "protocol_error") from None
            if text and not text.endswith("\n"):
                raise AGYError("AGY returned truncated stream output", "protocol_error")
            terminal = []
            for line in text.splitlines():
                try:
                    item = json.loads(line)
                except ValueError:
                    raise AGYError("AGY returned malformed stream output", "protocol_error") from None
                if not isinstance(item, dict) or not isinstance(item.get("event"), str):
                    raise AGYError("AGY returned malformed stream output", "protocol_error")
                if item["event"] == "result":
                    terminal.append(item)
                    if len(terminal) > 1:
                        raise AGYError("AGY returned duplicate terminal results", "protocol_error")
            if len(terminal) != 1:
                if process.returncode != 0:
                    raise AGYError("AGY process failed")
                raise AGYError("AGY did not return exactly one terminal result", "protocol_error")
            result = terminal[0].get("result")
            if isinstance(result, dict) and result.get("status") != "SUCCESS" and result.get("finished_reason") == "print_timeout":
                raise AGYError("AGY run timed out", "timeout")
            if process.returncode != 0:
                raise AGYError("AGY process failed")
            if not isinstance(result, dict) or result.get("status") != "SUCCESS" or not isinstance(result.get("response"), str) or not result["response"]:
                raise AGYError("AGY reported an unsuccessful result")
            return RunResult(result["response"], "SUCCESS", process.returncode)
        except AGYError:
            raise
        except (OSError, ValueError) as exc:
            raise AGYError("Could not run AGY") from None
        finally:
            self.duration_seconds = time.monotonic() - started
            if selector is not None:
                selector.close()
            if observer is not None:
                observer.close()
            if process is not None:
                self._stop(process)
                for stream in (process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()
                with self._lock:
                    if self._process is process:
                        self._process = None

    def _stop(self, process: subprocess.Popen) -> None:
        with self._lock:
            if process.returncode is not None:
                return
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except PermissionError:
                if not _ExitObserver(process).has_exited():
                    raise AGYError("Could not stop AGY process group") from None
            # Do not reap the leader during the grace period. Its owned PID
            # pins the group identity, including when descendants ignore TERM.
            time.sleep(0.15)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except PermissionError:
                if not _ExitObserver(process).has_exited():
                    raise AGYError("Could not stop AGY process group") from None
            process.wait(timeout=0.5)

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            process = self._process
            if process is not None and process.returncode is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass

    def close(self) -> None:
        self.cancel()
