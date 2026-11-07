# External Agents for Hermes: external-agents-agy

Run AGY's own agent loop behind ordinary Hermes delegation, without a core fork.
This registration is part of [External Agents for Hermes](../../README.md).

**Both registrations are required, at the same reviewed commit:**
`external-agents` routes native child tasks; `external-agents-agy` runs AGY.
See the [full installation and first-task guide](../../README.md#install) before enabling either one.

Early opt-in preview. Tested live on macOS arm64 with AGY 1.5.2; historical
checks used 1.4.6. Declared Hermes floor: >=0.22.5; the exact verified host and
limitations are in [Compatibility](../../docs/COMPATIBILITY.md).

AGY owns its own tools, permissions, global instructions and supported login.
It can run commands and contact vendor network services. The plugin does not
read token stores, but AGY may use its own cached login. A workspace is
not a security sandbox; Hermes tool filters do not constrain AGY's tools.
Explicit consent and local, in-process loading are required. Headless vendor
approvals cannot be relayed to Hermes. Failed jobs are not automatically replayed.
Prompts are visible in CLI arguments; private task results are cached locally.

Read [security boundaries](../../SECURITY.md) and [catalog disclosures](../../docs/CATALOG.md).
No telemetry, self-updater or vendor binaries are included. MIT licensed.
Independent community project; not an official Hermes/Nous/Google integration
and not currently admitted to the Hermes plugin catalog.
