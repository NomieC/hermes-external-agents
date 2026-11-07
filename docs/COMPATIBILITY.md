# Compatibility gate report

## Current verdict: approved hybrid works

**An actual model-issued foreground `delegate_task` has completed through a native Hermes child wrapper and AGY's own agent loop.** The child returned the exact unknown file contents; its native delegation result reported `completed`, provider `external-agents-agy`, one child API call and `schema_valid=true`. The first accepted run took about 189 seconds in the external child. A repeat from a fresh disposable home, using the production executable directly and the hardened supervisor, passed in 36.323 seconds with exactly one completed job record. The parent's final paraphrase was not used as the acceptance oracle.

The implementation uses public delegation-provider and external-process model-provider APIs. It does not override tools, short-circuit execution middleware or patch Hermes core. The source host remains at its original clean revision. The live user's default and unrelated profiles have not been activated or changed by these tests.

Both generated plugin registrations pass `hermes plugins validate --json`, with no validation warnings. Two host contract probes also pass: client-construction failure is terminal under a real AIAgent, and the real host's schema-repair turn returns the cache without launching the vendor again. Two registration tests pass, including an HTTP request to the routing endpoint used by the Subagents picker. The actual desktop UI was not clicked or visually asserted. Isolated AIAgent probes emitted a bundled dashboard-auth configuration warning and, in some runs, a host subprocess ResourceWarning; passing assertions are not described as warning-free host startup. The backend is host-ready according to validation; the custom client requires **in-process** loading. Do not describe that as plugin isolation or a security sandbox.

Automated fixture/contract coverage includes durable replay refusal, result caching, session binding, settings propagation, terminal-policy refusal, malformed output, output caps, timeout, cancellation and process-group cleanup. Test commands and live opt-ins are in the README. Counts may increase during hardening; use actual suite output, not this document, as the source of the current count.

## Historical direct-executor audit

**Pure replacement of the native executor remains blocked on the audited host.** No public-API-only takeover route was identified that both replaces the executor and preserves its downstream scope, pre-tool and guardrail checks. The owner subsequently accepted a Hermes child wrapper. That supported hybrid is a different design, not a workaround that bypasses those checks.

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

## Release audit follow-up

The read-only audit found that an exited AGY leader could leave owned descendants alive in its inspected snapshot. The current supervisor observes exit without reaping, sends bounded TERM/KILL signals to the owned group before reaping, and passes a regression where the leader reports success while its child ignores TERM. This does not contain intentionally detached processes.

The cache now re-applies owner-only POSIX modes to existing plugin data directories and database files; a regression preserves the stored response while tightening previously permissive modes. Prompt contents remain CLI arguments visible to local process inspection, and retained `HOME` allows the vendor CLI to use its own supported cached login. These trust-boundary limitations are documented rather than presented as sandbox guarantees.

## Release gate status

| Gate | Status |
| --- | --- |
| Public source repository and English requirements | Published |
| Host middleware behavior | Reproduced with 8 characterization tests |
| Real AGY no-tools prompt/response | Verified independently |
| Pure executor takeover | Blocked, no longer required for the approved milestone |
| Native child wrapper + real AGY loop | Verified by model-issued foreground delegation |
| Installable registrations | Implemented; both pass host validation |
| Worker identity, replay, timeout and cancellation | Automated fixture/contract tests; no live AGY stop parity claim |
| Real delegated file read | Exact child contents independently matched |
| Real AGY file write | Verified by separate live artifact probe: exact file contents, one launch, 20.573s |
| Background completion, steering and resume | Not live-verified; not supported claims |
| Catalog admission or tagged release | Not requested or claimed |

## Accepted direction and remaining boundaries

The owner approved native Hermes child wrapping. The plugin therefore uses public routing and process-provider interfaces, not standalone replacement tools or takeover middleware. No upstream issue, pull request or security disclosure has been submitted.

Schema correction must not relaunch AGY. A completed job returns cached text; if that text fails a schema, the failure is returned instead of repeating mutations. The launch fence is scoped to a routed job token and child session, not a global deduplication service. Separate delegations are separate jobs.

Hermes reports vendor cost as unknown in the live result even though its token and USD placeholders are zero. Those placeholders must not be interpreted as actual AGY usage accounting. Live AGY cancellation, detached completion, native interactive approvals and OS containment remain unverified. The configured workspace is not confinement, and process-group supervision cannot contain a process that intentionally detaches.
