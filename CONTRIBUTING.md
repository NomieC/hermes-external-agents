# Contributing

Thanks for helping make external delegation easier to inspect and reproduce.
This is an early, opt-in integration, not a general unattended worker service.

## Useful contributions

- Minimal, sanitized compatibility reports from a trusted disposable workspace.
- Regressions for supervision, replay refusal, JSON contracts and job ownership.
- Clearer setup instructions and failure explanations.
- Adapter proposals that preserve ordinary `delegate_task` and public Hermes APIs.

Open an issue before a new runtime, dependency or architectural change. AGY is the
only implemented adapter. Linux fixture CI does not establish live AGY support.

## Develop

Use a compatible Hermes installation (declared floor `>=0.22.5`; exact tested
revision in [Compatibility](docs/COMPATIBILITY.md)). No additional Python package
installation is needed. Clone the repository and work on a branch:

```bash
git clone https://github.com/NomieC/hermes-external-agents.git
cd hermes-external-agents
git switch -c fix/describe-your-change
python3 scripts/build_plugins.py
hermes --run-module unittest discover -s tests -v
git diff --check
```

Canonical files are `backend.py`, `provider_profile.py` and `hea_runtime/`.
`plugins/` is generated and committed for direct Git installation. Change the
canonical source, rebuild, and include both in the PR. Update builder metadata
rather than editing generated manifests by hand. The packaging test verifies the
build, license, version/floor and package onboarding.

Fixture CI runs the client, runner, packaging and acceptance-harness regression
files with standard-library Python on macOS and Linux. It does **not** run the
Hermes-backed backend/provider tests or live vendor probes. The full command above
requires Hermes's actual environment; a plain system interpreter may lack host
modules or dependencies. Report the exact command and real exit status.

Validate each registration in a disposable Hermes home with:

```bash
hermes plugins validate plugins/external-agents --install-deps --json
hermes plugins validate plugins/external-agents-agy --install-deps --json
```

`--install-deps` is the catalog gate. This repository declares no extra Python
dependencies; never mutate a user's Hermes environment to work around a failure.

## Pull-request checklist

- Add a failing regression before fixing behavior; run the relevant tests and full suite.
- Use public extension points; no core patches, private helper calls or runtime rebinding.
- Preserve fail-closed behavior, explicit consent, profile-local state and no automatic replay.
- Do not widen permissions, copy authentication files, add binaries, or silently fall back.
- Document externally visible behavior and distinguish fixture evidence from live checks.
- Include test commands/results and inspect the staged diff for private content.
- Keep changes focused. Never commit `.env`, local evidence, vendor logs, jobs databases or credentials.

## Live tests need separate consent

`research/` contains explicitly opt-in host and vendor probes. Some host research
imports internals to characterize behavior; that is not a production API example.
Live AGY uses the official CLI login, can access tools/network and may incur vendor
usage. Run only after reviewing scope in an intentionally disposable workspace.
Do not replay a failed or successful mutating job merely to improve a report.

Do not upload raw transcripts. Provide sanitized assertions and limitations instead.
Report vulnerabilities through [SECURITY.md](SECURITY.md), not a public bug template.
All contributions are under the repository's [MIT license](LICENSE).
