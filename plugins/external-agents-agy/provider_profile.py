"""Public model-provider seam for AGY; no host internals are imported."""
from pathlib import Path
from types import SimpleNamespace
import importlib

from hermes_constants import get_hermes_home
from providers.base import ProviderProfile


def load_client_class():
    # Installed as a package submodule; source-checkout imports support unit tests.
    name = f"{__package__}.hea_runtime.client" if __package__ else "hea_runtime.client"
    return importlib.import_module(name).AGYClient


def terminal_error(error, **context):
    # Keep terminal classification without mislabelling process failures as HTTP 400s.
    code = getattr(error, "code", "execution_failed")
    reason = "timeout" if code == "timeout" else "incomplete_response"
    return {"reason": reason, "retryable": False, "should_fallback": False,
            "should_rotate_credential": False, "message": "External Agents stopped; automatic replay is disabled.",
            "error_context": {"external_agent_code": code}}


class UnavailableClient:
    HERMES_SKIP_TRANSPORT_WRAP = True
    HERMES_SKIP_ASYNC_WRAP = True

    def __init__(self):
        self.api_key = "external-process"
        self.base_url = "process://hermes-external-agents"
        self.is_closed = False
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        name = f"{__package__}.hea_runtime.client" if __package__ else "hea_runtime.client"
        error_class = importlib.import_module(name).ClientError
        raise error_class("External Agents client is unavailable; no fallback or execution was attempted.")

    def cancel(self):
        pass

    def close(self):
        self.is_closed = True


class AGYProfile(ProviderProfile):
    def __init__(self):
        super().__init__(name="external-agents-agy", display_name="External Agents: AGY",
            description="AGY's own agent loop inside a Hermes child wrapper.",
            auth_type="external_process", process_command="agy",
            process_command_env_vars=("HERMES_EXTERNAL_AGENTS_AGY_COMMAND",),
            base_url="process://hermes-external-agents", supports_streaming=False,
            supports_health_check=False, supports_model_listing=False,
            fallback_models=("agy-default",), classify_api_error=terminal_error)

    def build_extra_body(self, *, session_id=None, **context):
        return {"hea_session": session_id} if session_id else {}

    def create_client(self, **kwargs):
        # Do not raise into the host's factory fallback. Defer settings validation
        # and every subprocess side effect until create(), under the launch fence.
        try:
            client_class = load_client_class()
            return client_class(workspace=str(Path.cwd()),
                data_dir=get_hermes_home() / "plugin-data" / "external-agents-agy",
                settings={}, **{k: v for k, v in kwargs.items() if k not in ("workspace", "data_dir", "settings")})
        except Exception:
            return UnavailableClient()
