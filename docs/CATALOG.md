# Preparing a Hermes community catalog submission

**Status: preparation only. No catalog PR has been sent and no admission is claimed.**

The official catalog is human-reviewed. The appropriate requested tier for this
independent project is `community`, not `official` or `verified`. Publication on
GitHub is not catalog review. Check the current upstream rules again before
submitting; they may change after this document is written.

## Primary references

- [Submission guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission)
- [Canonical policy and entry schema](https://github.com/NousResearch/hermes-agent/blob/main/plugin-catalog/README.md)
- [Public plugin API](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/public-api)

## The paired-registration question

This repository deliberately contains two self-contained Hermes registrations:

| Registration | Subdirectory | Public extension surface |
| --- | --- | --- |
| `external-agents` | `plugins/external-agents` | `DelegationProvider`, `register_delegation_provider`, local status CLI |
| `external-agents-agy` | `plugins/external-agents-agy` | `ProviderProfile`, `register_provider`, custom external-process client |

**Both are needed for the intended workflow, at the same commit.** Neither is a
second competing implementation of the other. Ask maintainers how they want this
paired dependency represented before submitting: two coordinated entries or a
supported packaging change. Do not claim the catalog automatically installs the
companion, and do not assume two listings will be accepted under the one-lineage
policy. Each generated package includes its own onboarding/disclosure README so a
subdirectory-based catalog page does not lose the root installation instructions.

## Disclosures for the proposed PR

- The plugin launches the separately installed official AGY CLI with an argument
  array. No vendor binary or self-updater is bundled.
- AGY executes its own autonomous loop, including tools, commands and network calls
  allowed by its policy. Hermes tool filtering does not constrain AGY's tools.
- The CLI can load its global instructions, supported cached login and files
  outside the workspace. The adapter does not read, refresh, copy or expose token
  stores. `HOME` is retained for the vendor's supported runtime behavior.
- **Credential-policy review is unresolved.** Upstream rule 11 requires credentials
  through Hermes routes and forbids reading another tool's login. The adapter
  never reads that login, but external-process execution lets AGY use its own
  supported authentication. Ask maintainers whether this architecture satisfies
  the rule or needs a public host integration. Green validation is not approval.
- **Approval-boundary review is unresolved.** Execution requires explicit user
  consent; AGY permissions remain separate and no bypass flags are used. Headless
  vendor approval dialogs cannot be forwarded into Hermes. Missing grants fail or
  time out. No default blanket command grant is installed. Maintainers must assess
  this against upstream unattended-run/approval policy, not assume equivalence.
- This requires trusted in-process plugin loading and local terminal policy.
  Remote/container backends and `plugins.isolation: host` are unsupported.
- Prompts are process arguments. Profile-local SQLite records include cached task
  answers and bounded diagnostics, protected by owner-only POSIX modes, not encryption.
- No plugin telemetry is collected. AGY's logging, service usage and billing follow
  its vendor policy and are not measured by this adapter.
- The durable launch fence is per job and child session. It blocks automatic
  relaunch, not a newly requested delegation. Cancel/timeout do not roll back edits.
- Real verification is macOS arm64 / AGY 1.5.2 and historical 1.4.6. Linux fixtures
  are not live vendor verification. Windows and background/control parity are not
  claimed. The workspace and requested sandbox flag do not prove OS containment.
- No custom Desktop UI is injected. The backend uses the existing Subagents picker;
  plugin configuration uses the manifest settings UI. Do not fabricate screenshots.

## Immutable verification checklist

1. Review the intended source and private-content scan. Commit the source and build
   output, then push to the public repository with owner authorization.
2. Resolve a full immutable pin with `git rev-parse HEAD`. Confirm the exact remote
   branch SHA and inspect a fresh clone. A branch, tag or short SHA is not valid.
3. At that checkout, validate both directories independently in a disposable home:

   ```bash
   hermes plugins validate plugins/external-agents --install-deps --json
   hermes plugins validate plugins/external-agents-agy --install-deps --json
   ```

4. Exercise the real Git installer against that same SHA in a disposable Hermes
   home for each registration. Read back inventory, source bytes and validators.
   Do not change a live profile merely to demonstrate installability.
5. Prepare proposed entry files only after resolving the paired-registration and
   policy questions. Both must match version `0.2.0` and declare the same
   `requires_hermes: ">=0.22.5"` floor as their manifests. This floor reflects the
   tested host's SemVer series, not universal later-version verification.
6. Submit an owner-authorized PR to `NousResearch/hermes-agent`, with disclosures
   above, actual validation results and a request for `community` review. Wait for
   catalog CI and human review. Do not describe preparation as admission.

## Entry shape for discussion, not a ready-to-submit pin

Replace the placeholder only with a real published 40-character commit. This
example is intentionally not a catalog YAML file and cannot be installed by name.
The provider companion would need its own coordinated name/subdir if approved.

```yaml
name: external-agents
repo: https://github.com/NomieC/hermes-external-agents
sha: <full-40-character-published-commit>
subdir: plugins/external-agents
description: Route ordinary Hermes delegation to AGY through a native child wrapper.
maintainer: NomieC
tier: community
category: automation
title: External Agents for Hermes
version: "0.2.0"
requires_hermes: ">=0.22.5"
docs_url: https://github.com/NomieC/hermes-external-agents
platforms: [macos]
readme: true
known_issues:
  - Requires the external-agents-agy companion at the same commit.
  - Early opt-in preview; macOS arm64 is the only live-tested platform.
  - AGY owns tools and permissions; no approval bridge or proven OS containment.
  - Trusted in-process loading and local terminal policy are required.
capabilities:
  provides_tools: []
  provides_hooks: []
  provides_middleware: []
  requires_env: []
```

These capability lists refer to registered Hermes tools/hooks/middleware and
required secret environment variables, not AGY's internal tools. The provider's
optional `HERMES_EXTERNAL_AGENTS_AGY_COMMAND` executable override is not a secret
and must still be disclosed. Validators and human reviewers decide whether the
entry and actual pinned registrations agree.

## Discovery before admission

The README, issue templates, contribution guide, license and GitHub topics help
people inspect and try the project today. Share the public repository URL and a
specific read-only task rather than claiming production readiness. A later
maintainer-approved catalog PR is the strongest built-in distribution path.
External announcements, release tags and catalog PRs are separate actions, not
implied by a repository push.
