# Security policy

## Reporting

Do not put credentials, private prompts, cached task output, local configuration,
vendor conversation identifiers or exploit details in a public issue.

Use this repository's **Security → Report a vulnerability** private reporting
option if available. If it is unavailable, open an issue titled **Private security
contact requested** with only a request for a private channel, no vulnerability
details. The maintainer can arrange disclosure before you send sensitive material.
There is no guaranteed response SLA or bug bounty.

Include the affected commit/version, a minimal sanitized reproduction, impact and
whether the issue concerns this plugin, Hermes, or the external CLI. Avoid using
real credentials or private source to demonstrate an issue.

## Supported scope

This is an experimental project. Fixes target the current `main` source; there is
no promise of backports. MIT's warranty disclaimer applies. Validation and review
are not a security certification. The exact observed compatibility is documented
in [Compatibility](docs/COMPATIBILITY.md).

## Trust boundaries

- Hermes plugins are trusted Python code loaded in-process, not sandboxed extensions.
- AGY runs its own agent loop and tool permissions. Hermes tool allowlists do not
  confine those tools. A task prompt is guidance, not access control.
- The configured workspace and `--sandbox` request do not establish OS confinement.
  Owned process groups are supervised; intentionally detached processes are not contained.
- AGY uses its own supported authentication, global instructions, files and network
  services. This adapter does not read, refresh or copy vendor token stores.
- The prompt is a process argument visible to local process inspection. Vendor
  logging/storage follows the vendor's policy. Do not include secrets in tasks.
- Plugin-owned cached results are task content. Owner-only POSIX file modes are
  not encryption or a boundary against the same operating-system user.
- The durable fence is per routed job and child session. It prevents automatic
  relaunch of that job, not separate newly requested delegations. Timeout/cancel
  do not roll back actions. A denial must not be circumvented with another tool.
- Headless vendor approval prompts cannot be forwarded to Hermes. Configure narrow
  intentional grants before authorized work; no blanket auto-approval is installed.
- Do not use this preview for untrusted repositories or unattended critical writes.

No vendor binary, self-updater or plugin telemetry is included. Review both
registrations at the same immutable commit before enabling them.
