# External Agents for Hermes

Run AGY's own agent loop through ordinary Hermes `delegate_task`, without patching Hermes core.

**Status: early, opt-in implementation.** A real model-issued foreground delegation has completed through the wrapper and returned independently verified file contents. The implementation is tested on macOS arm64 with AGY 1.4.6 and the pinned Hermes revision in [Compatibility](docs/COMPATIBILITY.md). This is not a pure executor replacement, an OS sandbox, or a claim of full native subagent parity.

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

- A compatible Hermes installation supporting delegation providers and custom external-process model-provider clients. Verified revision: `088f657ecf77674c7b8e2ededf4e3576d82e042c`.
- macOS arm64 is the live-tested platform. Linux supervision code exists but is not vendor-tested. Windows is unsupported.
- AGY 1.4.6, installed and authenticated through the vendor's supported login flow.
- `agy` on the PATH inherited by Hermes. Alternatively, use the provider's documented `HERMES_EXTERNAL_AGENTS_AGY_COMMAND` environment override with an absolute executable path. The plugin's executable setting must point to the same official CLI.
- An explicit existing workspace and local terminal policy. Remote/container/ambiguous terminal backends are refused.

This repository ships no vendor binaries or credentials. It does not inspect credential stores.

## Install

Install both registrations into the intended Hermes profile, not an unrelated profile:

```bash
hermes plugins install NomieC/hermes-external-agents/plugins/external-agents-agy --enable
hermes plugins install NomieC/hermes-external-agents/plugins/external-agents --enable
```

For a reviewed, reproducible install, pass the same immutable 40-character commit with `--ref` to both commands. Review plugin code before enabling it: Hermes plugins are trusted code, not sandboxed extensions. No third-party Python runtime dependencies are required beyond the Hermes installation.

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

## Safety and limitations

- AGY has its **own tools, global instructions, authentication and permissions**. Hermes tool allowlists do not constrain AGY's internal actions. Text task instructions are not a security boundary.
- The workspace is a working directory, not filesystem confinement. The runner requests `--sandbox`; effective OS containment is not claimed. Descendants that deliberately detach from the owned process group are outside the supervisor's containment guarantee.
- Only `plan` and `accept-edits` modes are accepted. No permission-bypass flags are used. Interactive approval escalation, image tasks and per-task tool allowlists are unsupported.
- A durable profile-local launch fence prevents automatic relaunch of the same job after failure, interruption or client recreation. Completed jobs return cached text on retry, including schema-repair attempts. A parent issuing a **new** delegation is a new job, not globally deduplicated work.
- JSON output is validated by Hermes. If the first answer fails its schema, the cached answer may remain invalid; the adapter will not repeat a mutating task just to repair formatting.
- Output and wall time are bounded. Nonzero exit, malformed/truncated streams, duplicate terminal results and empty success responses fail visibly.
- Runner cancellation is tested with fixture subprocesses. Live AGY stop fan-out, detached background completion, resume and steering are not claimed as verified. Do not use this initial version for unattended critical writes.
- Vendor usage and billing are **unknown**, not free. A host placeholder showing zero tokens/cost does not establish zero vendor usage.
- The task prompt is passed as a CLI argument and can be visible to local process inspection while AGY runs. Do not put secrets in task prompts; vendor-side logging follows AGY's own policies.
- Private cached result text is stored at `$HERMES_HOME/plugin-data/external-agents-agy/jobs.sqlite3`. The client enforces owner-only POSIX modes on its data directory and database, including existing ones; this is not encryption or protection from the same user. Protect and manage that data as task content. Raw live-test transcripts stay outside this repository.

See [Compatibility](docs/COMPATIBILITY.md), [Design](docs/design.md) and [Requirements](docs/PRD.md) for precise evidence and boundaries.

## Development and verification

```bash
python3 scripts/build_plugins.py
hermes --run-module unittest discover -s tests -v
hermes plugins validate plugins/external-agents --json
hermes plugins validate plugins/external-agents-agy --json
```

Generated plugin directories are committed so normal Git-based installation does not need a build step. Rebuild them whenever canonical source changes. Fixture tests do not call a vendor service; real probes under `research/` are separate and explicitly opt-in.

A fresh disposable end-to-end probe can be run with `research/run_live_probe.py --agy /absolute/path/to/agy` after supplying `HEA_PARENT_BASE_URL`, `HEA_PARENT_MODEL` and `HEA_PARENT_API_KEY` through the normal environment. It uses the existing AGY login, creates its own Hermes home and workspace, verifies the child result rather than trusting the parent's paraphrase, and propagates the actual test exit status. Never publish its raw logs without a privacy review.

## Author and license

Fidel Brian Dava ([NomieC](https://github.com/NomieC)). [MIT](LICENSE).

Independent project. Not an official Hermes, Nous Research, Google or OpenAI product.
