# Compatibility gate report

## Verdict

**Transparent replacement of ordinary `delegate_task` is blocked on the audited host.** No public-API-only route was identified that both replaces the native executor and preserves its downstream scope, pre-tool and guardrail checks. This repository does not install a takeover middleware or claim that standalone tools satisfy this requirement.

This is an integration-contract finding, not a claim of an OS sandbox escape or a Hermes security vulnerability. Hermes explicitly treats installed plugins as trusted code with full agent privileges. See [the host security policy](https://github.com/NousResearch/hermes-agent/blob/088f657ecf77674c7b8e2ededf4e3576d82e042c/SECURITY.md#25-plugin-trust-model).

## Audited environment

| Component | Observed value |
| --- | --- |
| Hermes source revision | `088f657ecf77674c7b8e2ededf4e3576d82e042c` |
| Hermes source branch | `main`, clean before and after the checks |
| Platform | macOS, arm64 |
| Python used by the installation launcher | 3.14 |
| AGY CLI | `1.4.6` |
| Parent verification timestamp | `2026-11-06T11:34:37Z` |

Only this host was examined. No Linux, Windows, future-version or native UI parity support is claimed.

## Source-level evidence

All references below are pinned to the audited revision.

1. [Sequential dispatch selects `agent._dispatch_delegate_task`](https://github.com/NousResearch/hermes-agent/blob/088f657ecf77674c7b8e2ededf4e3576d82e042c/agent/tool_executor.py#L1683-L1698). Registry override alone does not replace this path. The [shared inline executor table](https://github.com/NousResearch/hermes-agent/blob/088f657ecf77674c7b8e2ededf4e3576d82e042c/agent/inline_tool_executors.py#L285-L320) also contains delegation dispatch.
2. [Scope, plugin pre-hooks and guardrails are inside `_dispatch_authorized_once`](https://github.com/NousResearch/hermes-agent/blob/088f657ecf77674c7b8e2ededf4e3576d82e042c/agent/tool_executor.py#L689-L759).
3. [Tool execution middleware wraps the authorized continuation](https://github.com/NousResearch/hermes-agent/blob/088f657ecf77674c7b8e2ededf4e3576d82e042c/agent/tool_executor.py#L789-L826). A middleware that returns a replacement result without calling the continuation does not enter those checks. Calling the continuation preserves checks but runs the already-selected native callback.
4. [An execution middleware exception before continuation falls through](https://github.com/NousResearch/hermes-agent/blob/088f657ecf77674c7b8e2ededf4e3576d82e042c/hermes_cli/middleware.py#L161-L214). Catching expected adapter errors does not create a host-level guarantee against every native fallback.

Official contract references: [middleware](https://hermes-agent.nousresearch.com/docs/developer-guide/middleware), [delegation providers](https://hermes-agent.nousresearch.com/docs/developer-guide/delegation-provider-plugin), [subagent lifecycle](https://hermes-agent.nousresearch.com/docs/developer-guide/subagent-lifecycle-api).

## Executed host behavior probe

[`research/host_contract_probe.py`](../research/host_contract_probe.py) loaded a temporary plugin using normal discovery. The plugin registered its hook and middleware through public registration APIs. The harness called the real host pipeline with a minimal agent and a non-executing native callback stub.

**Result: 8 tests passed.**

| Probe | Observed behavior |
| --- | --- |
| Short-circuit with a supplied scope denial | Replacement result returned; scope denial was not entered |
| Short-circuit with a pre-tool hook registered | Hook was not called |
| Short-circuit with a denying guardrail | Guardrail was not called |
| Continuation with a scope denial | Blocked; stub was not called |
| Continuation with a denying pre-tool hook | Blocked; stub was not called |
| Continuation with a denying guardrail | Blocked; stub was not called |
| Allowed continuation | Native callback stub was called |
| Middleware exception before continuation | Native callback stub was called |

These tests characterize existing behavior. Passing them means the compatibility blocker was reproduced, **not** that takeover succeeded. They do not exercise a model-issued foreground/background delegation, native child creation, approval UI, cancellation or an external worker through Hermes.

The harness imports host internals only for research instrumentation. Those imports are not proposed plugin APIs and must not be copied into a release implementation. It does not monkey-patch host code, call an LLM, launch a native child or execute a CLI.

### Reproduce

Use the audited installation, a disposable Hermes home and an explicitly selected scratch directory. Run from this repository:

```bash
export TMPDIR="${XDG_CACHE_HOME:-$HOME/.cache}/hermes-external-agents-probes"
mkdir -p "$TMPDIR/launch-home"
HERMES_HOME="$TMPDIR/launch-home" hermes --run-module unittest discover \
  -s "$PWD/research" -p host_contract_probe.py -v
```

The probe creates and removes a separate temporary home per case. Leave the launch home disposable. A later host revision may legitimately change these characterization results and requires a fresh audit.

The executed run printed a bundled dashboard-auth configuration warning during temporary-home discovery. The intentional middleware-failure case also printed its expected warning. Neither warning was suppressed or presented as a clean production-plugin validation.

## Independently repeated live AGY smoke

The parent process independently launched AGY with an argument array, no shell interpolation, in an empty disposable workspace. Only a small allowlist of ordinary environment variables was inherited; vendor authentication used the CLI's existing supported login state. No credential store was read by the harness.

Invocation shape, with machine-specific executable and log paths omitted:

```text
agy --print <no-tools, no-file-access marker prompt>
    --output-format stream-json --mode plan --sandbox
    --print-timeout 60s --log-file <local scratch path>
```

The outer supervisor also imposed a 90-second deadline with process-group cleanup on timeout. That cleanup branch was not triggered and is not a cancellation-test claim.

Observed result:

- Exit code: `0`.
- Event discriminator: `event`, not `type`.
- Event sequence: `init`, `step_update`, `step_update`, `step_update`, `result`.
- Step types: `user_input`, `agent_response`, `agent_response`.
- Init permission mode: `request-review`.
- Final status: `SUCCESS`.
- Final response, after stripping its trailing newline: `HERMES_EXTERNAL_AGENT_SMOKE_OK`.
- Workspace: still empty after execution.
- Stderr: empty.

Raw stdout, stderr, vendor logs and conversation identifiers stay local and are not published. This proves one real prompt/response path, not editing, enforced read-only containment, safe cancellation, resumability or plugin integration. `--sandbox` was requested; effective OS containment was not independently demonstrated.

### Pitfalls found during verification

An earlier parent smoke incorrectly looked for a `type` discriminator. Its validator rejected the run even though the CLI returned a successful marker response. Inspection of record shapes identified the real `event` field, and a new live run was executed with that schema.

That earlier invocation also combined `--disable-slash-commands` with `--mode plan`. AGY warned: `--mode plan has no effect while slash command expansion is disabled.` The accepted repeat removed `--disable-slash-commands`; no permission-bypass option was used. An adapter must verify effective mode rather than treating requested flags as evidence of policy enforcement.

## Release gate status

| Gate | Status |
| --- | --- |
| Public source repository and English requirements | Published |
| Host middleware behavior | Reproduced with 8 characterization tests |
| Real AGY no-tools prompt/response | Verified independently |
| Authorization-preserving default delegation replacement | Blocked |
| Installable product plugin | Not implemented |
| Worker ownership, timeout/cancel races, recovery | Not verified |
| Real delegated file artifact | Not verified |
| Catalog admission or release | Not requested or claimed |

## Decision required before implementation continues

1. Preserve the original requirement: pursue a supported post-authorization executor extension upstream, then ship the adapter entirely as a plugin. This requires host support that has not been established; no local core patch is proposed.
2. Explicitly narrow the first release to standalone external-agent tools using ordinary plugin dispatch. This can remain plugin-only but is **not** a transparent replacement for native `delegate_task`.

Neither option is silently selected. No upstream issue, pull request or security disclosure has been submitted by this project.
