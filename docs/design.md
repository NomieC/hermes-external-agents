# Hybrid integration design

## Approved architecture

```text
Parent Hermes -> ordinary delegate_task -> native Hermes child AIAgent
              -> External Agents process provider -> AGY native agent loop
              <- one terminal text result <- native delegation completion
```

This milestone explicitly accepts the Hermes child wrapper. It does not replace the core executor, intercept tool execution middleware, override native tools, or bridge vendor tool calls back into Hermes.

## Public extension doors

- Register an External Agents `DelegationProvider` so the existing Subagents picker lists it.
- Route to a registered `ProviderProfile` with `auth_type=external_process` and a custom `create_client`.
- Use the provider's public request hooks to carry stable task/session identity to its OpenAI-shaped facade.
- Expose configuration through the plugin manifest's schema under Settings > Plugins.
- Keep integration/contract research under `research/`, separate from production runtime code.

## Initial capability boundary

One adapter: AGY's actual `stream-json` print protocol, not ACP. Initial verified platform target is macOS/POSIX; other platforms remain unsupported until tested. Modes are `plan` and explicit `accept-edits`; no dangerous permission bypass or automatic permission mode. Streaming, resume, interactive approvals, reliable steering, and per-tool vendor progress are not initial acceptance claims. A native Hermes stop must cancel the subprocess; host UI features do not imply vendor capability parity.

External execution is an explicit trust boundary. Hermes tool allowlists do not constrain AGY's internal tools. A workspace is a launch directory, not a security sandbox. The runner requests `--sandbox`, but enforcement must not be claimed without a separate containment test. Require explicit acceptance of this boundary before launching; refuse remote/container terminal policies rather than executing on the local host by surprise. Vendor authentication uses supported cached CLI login only; never inspect token stores.

## Replay safety

Generate a plugin-owned job token once when routing each task. Bind it to the child session and active profile home. Claim the token durably before starting an external process. A cached result may be returned on a host retry, but a started, interrupted, failed or unrecognized task is never automatically relaunched. Schema correction must not repeat filesystem mutations. Store only bounded private job records in plugin-owned data, never in the public repository. Unknown token usage/cost is unknown, not zero vendor billing.

## Supervision

Launch argv without a shell and pass a minimal environment. Bound stdout/stderr and wall-clock time. Success requires exit code zero plus exactly one terminal SUCCESS record with a valid response. Cancellation is sticky and safe during process startup. The request thread owns pipe cleanup and reaping; cancellation signals only the owned process group.

## Surgical file plan

- NEW: `hea_runtime/runner.py`, bounded AGY subprocess and NDJSON validation.
- NEW: `hea_runtime/client.py`, OpenAI-shaped facade, durable replay fence and cancellation.
- NEW: plugin entry point, manifest and provider/delegation contracts after packaging verification.
- NEW: unit, fixture-subprocess and isolated host integration tests.
- MODIFY: README, PRD and compatibility report to distinguish historical direct-executor blocker from approved hybrid progress.
- UNCHANGED: Hermes core, live default profile configuration and all unrelated profiles.

## Acceptance sequence

1. Observe RED then GREEN for each runtime slice.
2. Discover and validate the plugin in a disposable Hermes home.
3. Run an actual parent model-issued delegate_task through an unmodified host.
4. Independently check a real AGY-created tiny artifact and verify one process launch.
5. Exercise missing command, unsuccessful result, timeout, cancellation, replay and parallel ownership.
6. Verify the registered backend appears through the same routing endpoint the Subagents page reads.
7. Keep live profile activation separate from isolated testing. Do not claim install/activation, release or catalog admission without exact evidence.
