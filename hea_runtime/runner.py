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
from typing import Optional


@dataclass
class RunnerConfig:
    command: str = "agy"
    workspace: str = "."
    mode: str = "plan"
    timeout_seconds: float = 180
    max_output_bytes: int = 4_000_000
    model: str = ""


@dataclass
class RunResult:
    response: str
    status: str
    returncode: int


class AGYError(RuntimeError):
    """A safe, non-sensitive description of an AGY runner failure."""


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

    def run(self, prompt: str) -> RunResult:
        with self._lock:
            if self._used:
                raise AGYError("An AGY runner can only be used once")
            self._used = True
            if self._cancelled:
                raise AGYError("AGY run cancelled")
        argv = [self._executable, "--print", prompt, "--output-format", "stream-json",
                "--mode", self.config.mode, "--sandbox", "--print-timeout",
                f"{self.config.timeout_seconds:g}s"]
        if self.config.model:
            argv.extend(["--model", self.config.model])
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
                    raise AGYError("AGY run cancelled")
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
            while selector.get_map():
                with self._lock:
                    cancelled = self._cancelled
                if cancelled:
                    raise AGYError("AGY run cancelled")
                now = time.monotonic()
                if now >= deadline:
                    raise AGYError("AGY run timed out")
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
                        raise AGYError("AGY output exceeded configured limit")
                    streams[key.fileobj].extend(chunk)
            while not observer.has_exited():
                if self._cancelled:
                    raise AGYError("AGY run cancelled")
                if time.monotonic() >= deadline:
                    raise AGYError("AGY run timed out")
                time.sleep(0.005)
            # The leader stays unreaped until all group signals have been sent.
            # This prevents a recycled PID from receiving cleanup signals.
            self._stop(process)
            if process.returncode != 0:
                raise AGYError("AGY process failed")
            with self._lock:
                if self._cancelled:
                    raise AGYError("AGY run cancelled")
            out = bytes(streams[process.stdout])
            try:
                text = out.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                raise AGYError("AGY returned malformed stream output") from None
            if text and not text.endswith("\n"):
                raise AGYError("AGY returned truncated stream output")
            terminal = []
            for line in text.splitlines():
                try:
                    item = json.loads(line)
                except ValueError:
                    raise AGYError("AGY returned malformed stream output") from None
                if not isinstance(item, dict) or not isinstance(item.get("event"), str):
                    raise AGYError("AGY returned malformed stream output")
                if item["event"] == "result":
                    terminal.append(item)
                    if len(terminal) > 1:
                        raise AGYError("AGY returned duplicate terminal results")
            if len(terminal) != 1:
                raise AGYError("AGY did not return exactly one terminal result")
            result = terminal[0].get("result")
            if not isinstance(result, dict) or result.get("status") != "SUCCESS" or not isinstance(result.get("response"), str) or not result["response"]:
                raise AGYError("AGY reported an unsuccessful result")
            return RunResult(result["response"], "SUCCESS", process.returncode)
        except AGYError:
            raise
        except (OSError, ValueError) as exc:
            raise AGYError("Could not run AGY") from None
        finally:
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
