"""Public delegation routing only; Hermes retains child orchestration."""
from pathlib import Path
import os
import secrets
import shutil

from agent.delegation_provider import DelegationProvider, DelegationRouteError


class ExternalAgentsBackend(DelegationProvider):
    @property
    def name(self):
        return "external-agents"

    @property
    def display_name(self):
        return "External Agents"

    @property
    def summary(self):
        return "AGY runs the task inside a native Hermes child wrapper."

    def __init__(self, get_setting, get_terminal_backend=None):
        self.get_setting = get_setting
        self.get_terminal_backend = get_terminal_backend or self._terminal_backend

    @staticmethod
    def _terminal_backend():
        from hermes_cli.config import load_config_readonly
        terminal = load_config_readonly().get("terminal", {})
        configured = terminal.get("backend", "local") if isinstance(terminal, dict) else "unknown"
        inherited = os.environ.get("TERMINAL_ENV", "local")
        # Refuse ambiguous or conflicting policy rather than escaping a remote sandbox.
        return "local" if configured == inherited == "local" else "nonlocal"

    def description(self, config):
        return ("External Agents uses AGY's own tools and permissions, not Hermes toolset filtering. "
                "Text-only tasks; no live steering or resume. A failed job is never automatically replayed.")

    def route_task(self, task, config):
        if self.get_terminal_backend() != "local":
            raise DelegationRouteError("External Agents requires an explicit local terminal policy; remote/container policies are unsupported.")
        if task.get("images") or task.get("toolsets"):
            raise DelegationRouteError("External Agents cannot enforce per-task toolsets or accept images.")
        if self.get_setting("allow_external_tools", False) is not True:
            raise DelegationRouteError("Accept AGY's separate tool boundary in External Agents plugin settings first.")
        workspace = self.get_setting("workspace", "")
        if not isinstance(workspace, str) or not workspace or not Path(workspace).expanduser().is_dir():
            raise DelegationRouteError("Set an existing, explicit workspace in External Agents plugin settings.")
        executable = self.get_setting("executable", "agy")
        if not isinstance(executable, str) or not shutil.which(executable):
            raise DelegationRouteError("Install AGY and set its executable in External Agents settings.")
        mode = self.get_setting("mode", "plan")
        timeout = self.get_setting("timeout_seconds", 180)
        cap = self.get_setting("max_output_bytes", 4_000_000)
        if mode not in ("plan", "accept-edits"):
            raise DelegationRouteError("Use plan or accept-edits mode.")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 1 <= timeout <= 3600:
            raise DelegationRouteError("Set timeout_seconds between 1 and 3600.")
        if isinstance(cap, bool) or not isinstance(cap, int) or not 1024 <= cap <= 16_000_000:
            raise DelegationRouteError("Set max_output_bytes between 1024 and 16000000.")
        settings = dict(executable=executable, mode=mode, timeout_seconds=timeout,
                        max_output_bytes=cap, allow_external_tools=True)
        return {"provider": "external-agents-agy", "model": "agy-default", "fallback_providers": [],
                "label": "AGY external worker", "api_mode": "chat_completions",
                "request_overrides": {"extra_body": {"hea_job": secrets.token_hex(16),
                    "hea_workspace": str(Path(workspace).expanduser().resolve()), "hea_settings": settings}}}


def setup_cli(parser):
    commands = parser.add_subparsers(dest="external_agents_action", required=True)
    status = commands.add_parser("status", help="Read a job's owner-bound local diagnostics; never launch AGY")
    status.add_argument("--job", required=True)
    status.add_argument("--session", required=True, help="Exact Hermes child session, not the parent session")


def handle_cli(args):
    import json
    from providers import get_provider_profile
    profile = get_provider_profile("external-agents-agy")
    if profile is None:
        raise SystemExit("Enable the external-agents-agy registration in this profile first.")
    client = profile.create_client()
    if client is None:
        raise SystemExit("External-agent diagnostic client is unavailable; no execution was attempted.")
    if not callable(getattr(client, "job_status", None)):
        client.close()
        raise SystemExit("External-agent diagnostic client is unavailable; no execution was attempted.")
    try:
        print(json.dumps(client.job_status(args.job, args.session), indent=2))
    finally:
        client.close()


def register(ctx):
    ctx.register_delegation_provider(ExternalAgentsBackend(ctx.get_config))
    ctx.register_cli_command(name="external-agents", help="Inspect local external-agent jobs",
                             setup_fn=setup_cli, handler_fn=handle_cli)
