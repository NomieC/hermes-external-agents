# Compatibility gate report

## Current verdict: approved hybrid works

**An actual model-issued foreground `delegate_task` has completed through a native Hermes child wrapper and AGY's own agent loop.** The child returned the exact unknown file contents; its native delegation result reported `completed`, provider `external-agents-agy`, one child API call and `schema_valid=true`. The first accepted run took about 189 seconds in the external child. A repeat from a fresh disposable home, using the production executable directly and the hardened supervisor, passed in 36.323 seconds with exactly one completed job record. The parent's final paraphrase was not used as the acceptance oracle.

The implementation uses public delegation-provider and external-process model-provider APIs. It does not override tools, short-circuit execution middleware or patch Hermes core. The source host remains at its original clean revision. These historical isolated tests did not activate the live profile. The owner later installed both published registrations into the default profile and selected External Agents in the picker; current local stabilization has not updated those installed copies. Unrelated profiles were not changed.

Both generated plugin registrations pass `hermes plugins validate --json`, with no validation warnings. Two host contract probes also pass: client-construction failure is terminal under a real AIAgent, and the real host's schema-repair turn returns the cache without launching the vendor again. Two registration tests pass, including an HTTP request to the routing endpoint used by the Subagents picker. That registration probe did not click the desktop UI. The owner subsequently confirmed that the installed backend was visible in the picker; this is not a UI lifecycle parity test. Isolated AIAgent probes emitted a bundled dashboard-auth configuration warning and, in some runs, a host subprocess ResourceWarning; passing assertions are not described as warning-free host startup. The backend is host-ready according to validation; the custom client requires **in-process** loading. Do not describe that as plugin isolation or a security sandbox.

Automated fixture/contract coverage includes durable replay refusal, result caching, session binding, settings propagation, terminal-policy refusal, malformed output, output caps, timeout, cancellation and process-group cleanup. Test commands and live opt-ins are in the README. Counts may increase during hardening; use actual suite output, not this document, as the source of the current count.

## AGY 1.5.2 stabilization evidence

The following pre-publication checks used disposable Hermes homes/workspaces on the same macOS arm64 host. At that checkpoint, the installed registrations matched the earlier published `d456cb97f5c277c04b12e21025477f64cbf3af5c` source; neither installed code nor AGY permission settings were updated by stabilization. The owner switched the live delegation backend back to Default for independent native reviews. Publishing the 0.2.0 source does not update an installed plugin or activate a backend.

Both 0.2.0 manifests declare `requires_hermes: ">=0.22.5"`, based on the tested host's SemVer series and inspection of that release's public provider interfaces. This is a conservative declared floor, not a claim that the unmodified 0.22.5 release or all later revisions have passed the live probes. Exact tested host: `v0.22.5+2996.g088f657`, revision below.

| Gate | Observed result |
| --- | --- |
| Offline fixture/contract suite | 49 tests passed after the explicit command-contract harness regressions; the earlier independent review used the 47-test checkpoint |
| Real host provider contracts | 3 tests passed: factory failure is terminal, timeout has the correct nonretryable reason, and schema repair does not relaunch the vendor |
| Generated-source parity and manifests | Canonical/runtime copies matched; both manifests validated with empty warning lists |
| Plain-text AIAgent wrapper | Exact marker returned, one completed job; external job duration 92.658 seconds |
| Empty JSON schema `{}` | Exact `{"ok":true}` returned, one completed job; external job duration 69.767 seconds |
| Explicit object schema, direct runner | Exact `{"ok":true}` returned with the internal `finish` tool permitted; one launch, 46.374 seconds, reaped |
| Explicit object schema, native AIAgent wrapper | Exact `{"ok":true}` returned, one completed correlated job; job duration 59.688 seconds, unittest elapsed 61.743 seconds |
| Real early timeout and cancel-after-init | Both lifecycle probes passed; one launch each, terminal code persisted, owned process reaped, recreation refused replay |
| Public status CLI | Executed in a disposable profile against a copy of real job state; exact conversation metadata returned, cached answer excluded, job records unchanged |
| Initial disposable model-delegated coding | **Blocked by vendor shell permission.** Actual child provider was `external-agents-agy`; it read the three fixture files, but AGY denied the test command. No source change occurred in that initial workspace |
| Fresh coding with session-only command grants | AGY ran the failing tests, fixed only the discount calculation, and reran all three tests successfully. Independent tests also passed and the test file was unchanged. That delegated job still failed because a subsequent, ungranted `git status` was denied; this remains partial coding evidence |
| Fresh model-delegated coding with an explicit command contract | **Passed end to end.** The child used `external-agents-agy`, returned `completed` and `schema_valid=true`, and the durable correlated job was completed. One vendor launch; baseline two failures, source-only fix, three passing tests, and independent tests passed. The exact unknown file contents matched; tests and marker were unchanged. Acceptance unittest: 84.023 seconds |

These are separate checkpoints, not retroactive changes to failed jobs. The initial explicit-object success used a direct native child wrapper. In the initial model-issued coding attempt, the parent's actual tool arguments contained `output_schema: {}` rather than the requested object shape; the child failed with `schema_valid=false`, and a host schema-repair call reused the terminal job without relaunching AGY. That initial workspace retained its two test failures. The later successful coding run is described below. No failed workspace was retried and no permission denial was bypassed.

### Session-scoped permission follow-up

After explicit owner approval to continue permission setup, a new disposable home and workspace were created; no failed workspace was replayed. A private executable launcher forwarded the runner's arguments to the official AGY 1.5.2 binary with its supported `--settings` flag. That session retained `toolPermission: request-review` and disabled non-workspace file access. Its allow rules covered `python3 -m unittest -v` and navigation to that exact workspace, not generic Python, all commands, or automatic approval. No persistent permission grant or live-profile change was made.

The actual model-issued child used `external-agents-agy`. Vendor history showed the baseline command exiting one with two failing tests, the source edit changing the discount addition to subtraction, and the second test command exiting zero with all three tests passing. Independent post-run tests also passed, with the original test file unchanged. The vendor then requested `git status`, which was outside the allowlist and was denied. The child returned `failed` with `schema_valid=false`; the acceptance unittest exited one after 191.700 seconds. The durable job state remained failed, and the launcher recorded exactly one AGY invocation. Vendor history also contained capacity errors earlier in that same invocation; they are not extra launches by the plugin.

This first follow-up proves that session-only grants enabled real coding work while an uncovered command remained blocked; it was not complete delegated coding acceptance. The initial additional-Git consent prompt received no answer, so work stopped at that checkpoint. The owner later explicitly approved read-only Git grants for one new fixture. In that separate run, tests and `git status --short` succeeded, but an ungranted `python3 -c` file-inspection command was denied. That job also remains failed. Neither failed workspace was replayed and generic Python access was not granted.

### Successful explicit-command-contract coding acceptance

After renewed owner authorization, one fresh disposable fixture used an immutable source snapshot and the same previously approved test/navigation/Git session grants. The task declared the complete permitted shell command set before launch, required the built-in `read_file` tool for all three files, prohibited interpreter snippets, and instructed the worker to stop on any denial. These task instructions are not permission enforcement or OS containment.

The actual parent issued exactly one ordinary `delegate_task` containing exactly one task; its goal matched the prepared contract. The correlated vendor history showed three `read_file` calls, failing baseline tests, one built-in edit to `discount.py`, passing tests, `git status --short`, and `git diff -- discount.py`. No permission denial was observed. The native child reported provider `external-agents-agy`, model `agy-default`, `completed`, `schema_valid=true`, and one API call. The durable job was completed with an exact vendor conversation ID. The launcher recorded one AGY invocation; its owned process was no longer present after completion.

Independent checks confirmed the unknown marker contents matched exactly, only `discount.py` changed, tests and marker were unchanged, and all three fixture tests passed. The inner acceptance unittest exited zero in 84.023 seconds; the launcher unittest exited zero in 85.353 seconds. The full offline suite then passed 49 tests. The source snapshot hashes still matched both the frozen files and current canonical implementation at verification.

**Schema qualification:** despite being given an explicit object schema, the parent's actual tool arguments again contained `output_schema: {}`. The returned JSON fields and exact values passed the independent acceptance assertions, but this run does not prove that the parent preserved the requested schema or that the coding task exercised AGY's explicit-object `--json-schema` path. The separate direct/wrapper object-schema gates above remain the evidence for that path. Do not replay this successful mutating job merely to obtain a different schema argument.

Persistent AGY permission keys remained at defaults and the saved Hermes backend remained Default. At that acceptance checkpoint, verification was local-source only, without commit, push, installed-code update, or live-profile activation. It establishes this bounded coding workflow, not general unattended coding readiness.

### Independent review checkpoint

Two read-only native review children completed together under the Default backend, using `cx-luna`. The code reviewer independently ran the 47-test offline suite and reported no concrete regression in the reviewed diff; this is not a security certification. The evidence reviewer inspected the saved artifacts and ran the separate eight-test host middleware characterization. Its invocation of the three provider-contract tests skipped without explicit opt-in, so that review is not evidence of those three tests running.

After the reviews, the supervising parent explicitly reran all three provider contracts in a new disposable home: all passed. It also ran each plugin validator separately: each process exited zero and returned `ok: true` with an empty warning list. This resolves the evidence review's ambiguity about a combined terminal command's status. The parent separately checked installed source against the published commit and the clean host revision; these are parent verification results, not checks performed by the two reviewers. Native review results omitted an explicit route field, so native execution is supported by the fresh Default configuration and normal child/tool traces, not by an invented route value.

### Failures that informed the checks

- AGY 1.5.2 rejects `--json-schema {}` at argument parsing because the root must declare `type: object`. The adapter now sends object-root schemas through the vendor flag; empty and non-object schemas remain unchanged in the JSON-only prompt and host validator.
- An earlier object-schema probe forbade **all** tools. Vendor history showed an ordinary JSON answer followed by a request to use the internal `finish` tool, and the run timed out. A new, nonmutating probe explicitly permitted `finish` while still forbidding file access, shell commands and other tools; both the runner and native AIAgent wrapper succeeded. This is a prompt-contract interaction, not evidence that increasing timeouts fixes hangs.
- A launcher attempt used an unsupported `hermes --run-script` invocation and exited before running the acceptance script. Replacement unittest launchers propagated their real exit status. The failed combined acceptance run remains failed, not retroactively green.
- The coding probe initially tried to parse an entire tool message as JSON even though Hermes appended a run-budget notice. Its parser now permits that known host suffix, rejects unrecognized trailing data, and still reports the child's failed status. Coding-job acceptance no longer depends on unrelated schema jobs succeeding.

Isolated host startup still emitted the bundled dashboard-auth configuration warning and a Python subprocess `ResourceWarning`. Passing assertions and empty manifest warnings are not a warning-free host-startup claim. Exact conversation IDs, local paths, vendor logs and raw task transcripts remain private. Background completion, native UI stop fan-out, write-phase cancellation, interactive approval escalation and OS containment are still outside verified capability.

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
| Worker identity, replay, timeout and cancellation | Fixture/host contracts plus AGY 1.5.2 early-stop probes; no write-phase or native UI stop parity claim |
| Real delegated file read | Exact child contents independently matched |
| Real AGY file write | Verified by separate live artifact probe: exact file contents, one launch, 20.573s |
| Background completion, steering and resume | Not live-verified; not supported claims |
| Catalog admission or tagged release | Not requested or claimed |

## Accepted direction and remaining boundaries

The owner approved native Hermes child wrapping. The plugin therefore uses public routing and process-provider interfaces, not standalone replacement tools or takeover middleware. No upstream issue, pull request or security disclosure has been submitted.

Schema correction must not relaunch AGY. A completed job returns cached text; if that text fails a schema, the failure is returned instead of repeating mutations. The launch fence is scoped to a routed job token and child session, not a global deduplication service. Separate delegations are separate jobs.

Hermes reports vendor cost as unknown in the live result even though its token and USD placeholders are zero. Those placeholders must not be interpreted as actual AGY usage accounting. Historical release checks did not verify live cancellation. Current development additionally verifies an early AGY timeout and cancel-after-init with reaping and no replay, not cancellation during writes or native UI fan-out. Detached completion, native interactive approvals and OS containment remain unverified. The configured workspace is not confinement, and process-group supervision cannot contain a process that intentionally detaches.
