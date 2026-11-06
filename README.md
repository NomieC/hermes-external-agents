# External Agents for Hermes

A plugin-only integration project for delegating Hermes work to external agent CLIs instead of changing the model of a native Hermes child.

**Status: compatibility research and implementation in progress. Not a released plugin.** No support claim is made until real dispatch, authorization, process supervision and external CLI tests pass. See [the product requirements](docs/PRD.md).

## Goal

Keep Hermes as the orchestrator while an external CLI owns the delegated agent loop. The initial target is Antigravity CLI (AGY). No Hermes source patches, forks or monkey-patches are permitted.

## Compatibility gates

- Prove that a public plugin API can intercept ordinary delegation without bypassing authorization.
- Verify safe, structured AGY execution, failure detection and cancellation.
- Keep worker ownership bound to the parent session and Hermes profile.
- Exercise real artifacts independently; fixture tests are not evidence of a live vendor run.
- Disclose unsupported behavior instead of silently using native delegation.

Hermes execution middleware is documented as fail-open. Strict no-fallback behavior and native subagent UI/lifecycle parity are **not currently guaranteed**. The project will not hide these limitations behind a wrapper.

## Development principles

- Public Hermes APIs only.
- No direct reads of credential stores or copying tokens.
- No permission-bypass CLI flags.
- Disposable development homes and workspaces.
- Capability-based adapters, honest compatibility claims, opt-in telemetry only.

## Author

Fidel Brian Dava ([NomieC](https://github.com/NomieC)). An independent project, not an official Hermes, Nous Research, Google or OpenAI product.
