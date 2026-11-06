# Product Requirements

## Problem and outcome

Native Hermes delegation normally creates Hermes child agents. This project aims to offer installable external execution using the agent loop of a vendor CLI, initially AGY, without requiring users to patch Hermes.

## Scope approved by the owner

- Independently distributable plugin repository with English-first documentation.
- Public plugin APIs only, no core changes or runtime monkey-patching.
- External CLI workers: launch, observe, result and cancellation.
- Default native-delegation takeover only if host authorization is preserved.
- Real CLI smoke checks, contract/security tests and truthful compatibility metadata.
- GitHub repository under NomieC for portfolio review.

## P0 acceptance criteria

1. The unmodified supported Hermes installation can load the plugin through normal discovery.
2. At least one real AGY task runs safely and its actual result is independently checked.
3. Scope, permission, ownership, timeout and cancellation checks have explicit tests.
4. Ordinary delegation takeover is either proven safe or marked blocked. Standalone tools do not silently count as fulfilling takeover.
5. Missing dependencies/auth and unsupported policy requests return explicit errors.
6. Secrets, credentials and personal machine paths never enter release sources.
7. No hidden native fallback, fabricated vendor responses or invented usage figures are presented as success.

## Research gates

- Public tool execution middleware can replace tool execution but is documented fail-open.
- A short-circuit may precede the host's downstream authorization callback. This requires behavior tests and public API audit before enabling takeover.
- Registry tool override is public and permission-gated, but native delegation uses special inline dispatch; a registry-only replacement is not assumed effective.
- CLI install/auth and model access belong to the user through official vendor workflows.

## Exclusions for the first version

Dashboard, marketplace admission, broad multi-CLI/OS claims, automatic write-task replay, private credential discovery, unattended permission bypass and autonomous publishing of runtime artifacts.

## Current gate outcome

The [compatibility report](COMPATIBILITY.md) records the executed host probes and independent live AGY smoke. Default takeover is blocked on the audited revision. No production plugin has been implemented or installed; narrowing the release to standalone tools requires an explicit owner decision.

## Release policy

Implementation, automated verification, live CLI verification and release readiness are separate states. A blocker at a required gate is reported explicitly. Publishing this research repository does not imply a release or catalog admission.
