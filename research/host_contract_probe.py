"""Research-only host behavior probe, not a plugin or replacement executor.

Run under Hermes' installation-bound Python, with an isolated HERMES_HOME.
Internal host calls here are test instrumentation, never a proposed public API.
No monkey-patches, LLM calls, external commands, or native children are used.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from agent.tool_executor import _run_agent_tool_execution_middleware
from hermes_cli.plugins import get_plugin_manager


_PLUGIN = '''
MODE = {mode!r}
EVENTS = []


def policy(**kwargs):
    EVENTS.append("pre_tool_call")
    if MODE == "pre_block":
        return {{"action": "block", "message": "probe pre-hook denied"}}


def execute(tool_name, args, next_call, **kwargs):
    EVENTS.append("middleware")
    if MODE == "short_circuit":
        return '{{"research_intercepted": true}}'
    if MODE == "raise":
        raise RuntimeError("intentional research middleware failure")
    return next_call(args)


def register(ctx):
    ctx.register_hook("pre_tool_call", policy)
    ctx.register_middleware("tool_execution", execute)
'''


class HostContractProbe(unittest.TestCase):
    """Characterize policy ordering, without executing actual delegated work."""

    def run_pipeline(self, mode, *, scope_block=None, guardrail_allows=True):
        scratch = Path(os.environ["TMPDIR"]).resolve()
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hea-host-", dir=scratch) as directory:
            home = Path(directory)
            plugin = home / "plugins" / "compat_probe"
            plugin.mkdir(parents=True)
            (plugin / "plugin.yaml").write_text(
                "name: compat_probe\nversion: 0.0.1\n", encoding="utf-8"
            )
            (plugin / "__init__.py").write_text(_PLUGIN.format(mode=mode), encoding="utf-8")
            (home / "config.yaml").write_text(
                "plugins:\n  enabled: [compat_probe]\n", encoding="utf-8"
            )
            previous_home = os.environ.get("HERMES_HOME")
            os.environ["HERMES_HOME"] = str(home)
            manager = get_plugin_manager()
            try:
                manager.discover_and_load()
                module = manager._plugins["compat_probe"].module
                self.assertIsNotNone(module, "Research plugin did not load")
                assert module is not None
                events = module.EVENTS

                def before_call(name, args):
                    events.append("guardrail")
                    return SimpleNamespace(allows_execution=guardrail_allows)

                def native_dispatch(args):
                    events.append("native_dispatch_stub")
                    return json.dumps({"native_stub": True})

                agent = SimpleNamespace(
                    session_id="research-session",
                    quiet_mode=True,
                    tool_progress_callback=None,
                    tool_start_callback=None,
                    _checkpoint_mgr=SimpleNamespace(enabled=False),
                    _touch_activity=lambda label: None,
                    _tool_guardrails=SimpleNamespace(before_call=before_call),
                    _guardrail_block_result=lambda decision: json.dumps({"error": "probe guardrail denied"}),
                )
                state = _run_agent_tool_execution_middleware(
                    agent,
                    function_name="delegate_task",
                    function_args={"tasks": [{"goal": "research only"}]},
                    effective_task_id="research-task",
                    tool_call_id="research-call",
                    execute=native_dispatch,
                    scope_block=scope_block,
                )
                return state, list(events)
            finally:
                manager.unload()
                if previous_home is None:
                    os.environ.pop("HERMES_HOME", None)
                else:
                    os.environ["HERMES_HOME"] = previous_home

    def test_short_circuit_does_not_enter_scope_gate(self):
        state, events = self.run_pipeline("short_circuit", scope_block="probe scope denied")
        self.assertEqual(json.loads(state.result), {"research_intercepted": True})
        self.assertFalse(state.dispatched)
        self.assertFalse(state.blocked)
        self.assertEqual(events, ["middleware"])

    def test_short_circuit_does_not_enter_pre_hook(self):
        state, events = self.run_pipeline("short_circuit")
        self.assertFalse(state.dispatched)
        self.assertNotIn("pre_tool_call", events)

    def test_short_circuit_does_not_enter_guardrail(self):
        state, events = self.run_pipeline("short_circuit", guardrail_allows=False)
        self.assertFalse(state.blocked)
        self.assertNotIn("guardrail", events)

    def test_continuation_preserves_scope_denial(self):
        state, events = self.run_pipeline("continue", scope_block="probe scope denied")
        self.assertEqual(json.loads(state.result), {"error": "probe scope denied"})
        self.assertTrue(state.blocked)
        self.assertEqual(events, ["middleware"])

    def test_continuation_preserves_pre_hook_denial(self):
        state, events = self.run_pipeline("pre_block")
        self.assertEqual(json.loads(state.result), {"error": "probe pre-hook denied"})
        self.assertTrue(state.blocked)
        self.assertEqual(events, ["middleware", "pre_tool_call"])

    def test_continuation_preserves_guardrail_denial(self):
        state, events = self.run_pipeline("continue", guardrail_allows=False)
        self.assertEqual(json.loads(state.result), {"error": "probe guardrail denied"})
        self.assertTrue(state.blocked)
        self.assertEqual(events, ["middleware", "pre_tool_call", "guardrail"])

    def test_continuation_reaches_native_callback(self):
        state, events = self.run_pipeline("continue")
        self.assertEqual(json.loads(state.result), {"native_stub": True})
        self.assertEqual(events, ["middleware", "pre_tool_call", "guardrail", "native_dispatch_stub"])

    def test_middleware_exception_falls_through_to_native_callback(self):
        state, events = self.run_pipeline("raise")
        self.assertEqual(json.loads(state.result), {"native_stub": True})
        self.assertEqual(events, ["middleware", "pre_tool_call", "guardrail", "native_dispatch_stub"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
