# External Agents for Hermes

**Keep Hermes as the orchestrator. Let AGY do the work.**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Fixture CI](https://github.com/NomieC/hermes-external-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/NomieC/hermes-external-agents/actions/workflows/ci.yml)

Run Antigravity's own agent loop behind ordinary Hermes `delegate_task`. Same parent workflow, real AGY tools, no Hermes core fork.

- **Native entry point:** use the existing Subagents backend picker, not a replacement delegation tool.
- **Real external execution:** AGY reads, edits and runs tools; Hermes delivers the child's final result.
- **No automatic replay:** a durable job fence prevents host retries from launching the same job again.
- **Inspectable source:** MIT-licensed Python, no bundled vendor binary and no additional Python dependencies.

**Early preview, opt-in.** Foreground file-reading and a bounded coding workflow have passed real end-to-end checks on macOS arm64, including AGY 1.5.2. This is not general unattended coding readiness, an OS sandbox, or full native subagent parity. [Read the exact evidence and limits →](docs/COMPATIBILITY.md)

[Try it](#install) · [First task](#try-a-first-task) · [Permissions](#headless-agy-command-permissions) · [Contribute](CONTRIBUTING.md) · [Report a bug](https://github.com/NomieC/hermes-external-agents/issues/new?template=bug_report.yml)

> Independent community project. Not an official Hermes, Nous Research or Google product. Not currently admitted to the Hermes plugin catalog.

## How it works

```text
Hermes parent
  -> ordinary delegate_task
  -> native Hermes child lifecycle wrapper
  -> External Agents custom process-provider client
  -> AGY's autonomous loop and tools
  <- final text returned through native delegation
```

Hermes owns the child lifecycle and completion delivery. AGY performs the actual work. Vendor tool calls are **not** translated into Hermes tool calls or executed twice.

One repository contains two self-contained registrations, using Hermes's public extension interfaces:

| Registration | Purpose |
| --- | --- |
| `external-agents` | Delegation backend; appears as **External Agents** in the existing Subagents picker |
| `external-agents-agy` | In-process model-provider client; launches and supervises the real AGY CLI |

The original direct-executor middleware approach was rejected because it could bypass downstream checks. The approved hybrid does not intercept tool middleware. The [historical audit](docs/COMPATIBILITY.md#historical-direct-executor-audit) remains available.

## Requirements

- Hermes `>=0.22.5` with delegation providers and custom external-process model-provider clients. This is the declared compatibility floor, not a claim that every later release is tested. Verified host: `v0.22.5+2996.g088f657`, revision `088f657ecf77674c7b8e2ededf4e3576d82e042c`; see [Compatibility](docs/COMPATIBILITY.md).
- macOS arm64 is the live-tested platform. Linux supervision code exists but is not vendor-tested. Windows is unsupported.
- AGY installed and authenticated through the vendor's supported login flow. Historical acceptance used 1.4.6; current development also exercises 1.5.2. See the compatibility report for exact gates.
- `agy` on the PATH inherited by Hermes. Alternatively, use the provider's documented `HERMES_EXTERNAL_AGENTS_AGY_COMMAND` environment override with an absolute executable path. The plugin's executable setting must point to the same official CLI.
- An explicit existing workspace and local terminal policy. Remote/container/ambiguous terminal backends are refused.

This repository ships no vendor binaries or credentials. It does not inspect credential stores.

## Install

Install both registrations into the intended Hermes profile, not an unrelated profile:

```bash
hermes plugins install NomieC/hermes-external-agents/plugins/external-agents-agy --enable
hermes plugins install NomieC/hermes-external-agents/plugins/external-agents --enable
```

**Both registrations are required, from the same commit.** For a reviewed, reproducible install, add `--ref <full-40-character-commit>` to both commands. The commands above use the repository default branch, not a catalog-reviewed pin. To inspect first, replace `--enable` with `--no-enable`. Review plugin code before enabling it: Hermes plugins are trusted code, not sandboxed extensions. No third-party Python runtime dependencies are required beyond the Hermes installation.

Then configure **Settings → Plugins → External Agents**:

1. **workspace**: an existing directory intentionally available to AGY.
2. **executable**: the official `agy` executable, preferably an absolute path.
3. **mode**: start with `plan`; select `accept-edits` only for explicitly authorized writes.
4. **timeout_seconds**: default 180; slower tool tasks may need 240 or more.
5. **max_output_bytes**: combined stdout/stderr cap, default 4,000,000.
6. **allow_external_tools**: enable only after accepting AGY's separate tool and permission boundary.

The custom provider client requires **in-process** plugin loading. If the profile uses `plugins.isolation: host`, do not weaken that policy silently: this version cannot run under that policy. For a profile where you explicitly accept trusted in-process plugins, set `hermes config set plugins.isolation in_process`.

Set **Settings → Model → Subagents → Backend → External Agents** and start a new conversation. Keep the primary parent provider unchanged. The AGY provider is not supported as a direct primary-chat provider.

CLI equivalent for settings uses `hermes config set plugins.entries.external-agents.settings.<key> <value>`. Select the backend with `hermes config set delegation.backend external-agents`. A local policy can be set with `hermes config set terminal.backend local`; do not change a remote/container policy merely to bypass the adapter's refusal.

To return to native Hermes delegation, select **Default** or run:

```bash
hermes config set delegation.backend default
```

Start a new conversation after changing the backend. An existing conversation may retain its earlier delegation snapshot; do not grant external consent merely to work around a stale route.

## Try a first task

Use a disposable, trusted workspace with a small `hello.txt` file containing a value you can check. Configure that directory, leave the mode at `plan`, and start a **new** Hermes conversation after selecting the backend.

Ask Hermes:

> Use ordinary delegate_task once with one foreground task. Ask the child to read hello.txt from the configured workspace with its built-in file reader, make no edits, run no shell commands, and return its exact contents. Do not start another delegation if it fails.

Compare the child's returned text with the file yourself. A successful read proves that task path, not filesystem confinement. The existing vendor permission policy still applies; stop on a denial rather than trying another tool to perform the same action.

**Before a coding task:** review the source, declare allowed edits and expected test/Git commands, and arrange intentional AGY command permissions before launch. `accept-edits` is not shell approval. The [permission section](#headless-agy-command-permissions) explains why this matters.

### What has actually been checked?

| Capability | Evidence | Boundary |
| --- | --- | --- |
| Ordinary foreground delegation | Real model-issued child, exact unseen file contents | Hermes still creates the lifecycle wrapper |
| Bounded coding | One launch, source-only fix, independent tests passed | Trusted disposable fixture and narrow, prearranged command grants |
| JSON output | Direct runner and native wrapper object-schema probes | The successful model-issued coding task sent `{}`, not the requested object shape |
| Timeout and cancellation | Fixture coverage plus real early-stop probes | No write-phase or native UI stop parity claim |
| Other CLIs / operating systems | Not live-verified | AGY only; macOS arm64 is the live-tested platform |

See [Compatibility](docs/COMPATIBILITY.md) for failed checkpoints as well as successful ones. Fixture CI is not evidence of vendor execution.

## Safety and limitations

- AGY has its **own tools, global instructions, authentication and permissions**. Hermes tool allowlists do not constrain AGY's internal actions. Text task instructions are not a security boundary.
- The workspace is a working directory, not filesystem confinement. The runner requests `--sandbox`; effective OS containment is not claimed. Descendants that deliberately detach from the owned process group are outside the supervisor's containment guarantee.
- Only `plan` and `accept-edits` modes are accepted. No permission-bypass flags are used. `accept-edits` does not automatically authorize shell commands: earlier coding jobs failed on uncovered test or verification commands. A later, separately authorized fresh fixture completed end to end with predeclared commands, built-in file reads and narrow session grants; see the [exact evidence and schema qualification](docs/COMPATIBILITY.md#successful-explicit-command-contract-coding-acceptance). This is a bounded coding workflow, not general unattended readiness. Interactive approval escalation, image tasks and plugin-enforced per-task tool allowlists are unsupported.
- A durable profile-local launch fence prevents automatic relaunch of the same job after failure, interruption or client recreation. Completed jobs return cached text on retry, including schema-repair attempts. A parent issuing a **new** delegation is a new job, not globally deduplicated work.
- JSON output is validated by Hermes. The adapter forwards its system-text output contract (or standard `response_format`) from the first call and does not ask for plain text at the same time. AGY 1.5.2 only accepts root `type: object` in `--json-schema`; `{}` and other roots stay in the JSON-only prompt contract and rely on host validation, without narrowing the schema. The object-schema path uses AGY's internal `finish` tool: a no-files/no-shell task must permit that finalization tool rather than prohibit all tools. If the first answer fails its schema, the cached answer may remain invalid; the adapter will not repeat a mutating task just to repair formatting.
- Output and wall time are bounded. Nonzero exit, malformed/truncated streams, duplicate terminal results and empty success responses fail visibly.
- Fixture subprocesses cover cancellation and owned-group cleanup. Real AGY 1.5.2 probes also cover timeout and cancellation just after stream initialization, including reaping and durable replay refusal. These early-stop checks do not establish cancellation during writes, native UI stop fan-out, detached background completion, live attach or steering. Do not use this initial version for unattended critical writes.
- Vendor usage and billing are **unknown**, not free. A host placeholder showing zero tokens/cost does not establish zero vendor usage.
- The task prompt is passed as a CLI argument and can be visible to local process inspection while AGY runs. Do not put secrets in task prompts; vendor-side logging follows AGY's own policies. AGY uses its own network services and may load global instructions, supported cached login and files outside the workspace under its own permissions. This plugin does not collect telemetry or read token stores; that does not mean AGY is offline or credential-free.
- Private cached result text is stored at `$HERMES_HOME/plugin-data/external-agents-agy/jobs.sqlite3`. The client enforces owner-only POSIX modes on its data directory and database, including existing ones; this is not encryption or protection from the same user. Protect and manage that data as task content. Raw live-test transcripts stay outside this repository.

See [Compatibility](docs/COMPATIBILITY.md), [Design](docs/design.md) and [Requirements](docs/PRD.md) for precise evidence and boundaries.

## Headless AGY command permissions

`accept-edits` approves workspace edits, not every shell command. Under AGY's default `toolPermission: request-review`, an uncovered command still needs vendor approval. The runner uses noninteractive print mode with closed stdin; this version cannot relay AGY's approval dialog to Hermes. Configure intentional, narrow grants before submitting an authorized task, not after a failed job in order to replay it.

AGY's official [settings reference](https://antigravity.google/docs/settings?tab=cli), [permission guide](https://antigravity.google/docs/permissions?tab=cli), and [settings schema](https://antigravity.google/schemas/v1/settings.json) describe `permissions.allow`, `permissions.ask`, `permissions.deny` and the session-only `--settings` flag. Rules use `action(target)`, such as `command(python3 -m unittest -v)`. Deny takes precedence over Ask, which takes precedence over Allow; `strict` still requests review. Do not delete existing restrictions or change to global auto-approval to make a headless task pass.

For a trusted, disposable fixture, a user-reviewed launcher can pass `--settings` for that one invocation while retaining `request-review` and non-workspace access restrictions. This is a vendor configuration mechanism, not a new built-in plugin setting. It grants command patterns for the session, not an OS security boundary. A test command executes code from its test suite, so even a narrow `unittest` grant is unsafe for untrusted source; review the fixture and command semantics first. A command that changes directory may require that exact workspace navigation to be covered as well. Do not grant generic Python execution, all commands, or access to unrelated paths.

No permanent grant is installed by the plugin. Project-scoped grants can instead be managed with AGY's interactive `/permissions` interface. Verify the actual installed AGY version, effective rules and a fresh disposable job before claiming a permission workflow works.

## Local job diagnostics

After installing the corresponding reviewed source version, inspect an exact job in the intended profile:

```bash
hermes external-agents status --job <job-token> --session <hermes-child-session-id>
```

This command reads local job state, duration, a bounded error code/message, safe progress metadata and the vendor conversation ID. It never launches AGY or returns the cached task answer. The session must match the stored **child**, not its parent. The command is a local-owner diagnostic interface, not authentication against another process running as the same OS user.

New executions capture the exact conversation ID from AGY's NDJSON stream; there is no guess based on the latest workspace conversation. A returned `resume_command` opens that exact vendor thread in `plan` mode. Opening/resuming it is a deliberate user action, not live attach or adapter reconnection. Do not resume a still-running job or assume timeout/cancel rolled back earlier actions. Legacy jobs retain their replay fence and cached answers but do not acquire missing historical metadata.

Timeout, cancellation, output-limit and protocol failures remain terminal. Recreating a client preserves the recorded failure and refuses another launch. Hermes's generic provider-failure copy may still say that a request was rejected; inspect its `failure_reason`, the safe `Provider said` detail and local job diagnostics for the actual failure. No core copy overrides are installed.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Backend is missing | Install and enable both registrations; confirm the correct profile and compatible Hermes version |
| Executable unavailable | Set an absolute official CLI path and the matching `HERMES_EXTERNAL_AGENTS_AGY_COMMAND` override if needed; desktop PATH may differ from your shell |
| Consent or local-terminal refusal | Review the boundary intentionally; do not disable a remote/container policy to get past the check |
| Test or Git command denied | AGY owns that approval. Stop the job and inspect the policy; Hermes cannot relay the vendor dialog |
| JSON validation fails | Inspect the child result. Cached text is reused; the adapter will not replay mutations to fix formatting |
| Timeout or cancel | Inspect the exact local job. Prior actions are not rolled back; do not assume a fresh task is safe to replay |

For a bug report, include sanitized versions, child status, expected result and a minimal trusted reproduction. Never upload your configuration, cached jobs database or raw vendor logs. [Security reporting](SECURITY.md).

## Development and verification

```bash
python3 scripts/build_plugins.py
hermes --run-module unittest discover -s tests -v
hermes plugins validate plugins/external-agents --install-deps --json
hermes plugins validate plugins/external-agents-agy --install-deps --json
```

Generated plugin directories are committed so normal Git-based installation does not need a build step. Rebuild them whenever canonical source changes. Fixture tests do not call a vendor service; real probes under `research/` are separate and explicitly opt-in.

A fresh disposable end-to-end probe can be run with `research/run_live_probe.py --agy /absolute/path/to/agy` after supplying `HEA_PARENT_BASE_URL`, `HEA_PARENT_MODEL` and `HEA_PARENT_API_KEY` through the normal environment. It uses the existing AGY login, creates its own Hermes home and workspace, verifies the child result rather than trusting the parent's paraphrase, and propagates the actual test exit status. Never publish its raw logs without a privacy review.

## Help others try it

Small, reproducible reports are more useful than broad compatibility claims. Try the first read-only task in a trusted disposable workspace, then share your sanitized Hermes/AGY versions, platform, result and limitations in [Issues](https://github.com/NomieC/hermes-external-agents/issues). Contributions for tests, onboarding and new adapters are welcome; see [Contributing](CONTRIBUTING.md).

The next distribution route is a **community** listing in the official Hermes catalog. Admission requires a reviewed, pinned upstream PR; publication of this repository is not admission. The [catalog preparation guide](docs/CATALOG.md) records the paired-plugin design, required disclosures and unresolved policy questions. No catalog PR has been sent.

## Author and license

Fidel Brian Dava ([NomieC](https://github.com/NomieC)). [MIT](LICENSE).

Independent project. Not an official Hermes, Nous Research, Google or OpenAI product.
