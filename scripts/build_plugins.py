"""Build the two documented Hermes registrations from one source repository."""
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BACKEND_MANIFEST = """name: external-agents
version: 0.2.0
requires_hermes: ">=0.22.5"
manifest_version: 2
api_version: 1
kind: backend
author: Fidel Brian Dava
license: MIT
homepage: https://github.com/NomieC/hermes-external-agents
description: "Route ordinary delegate_task to AGY, wrapped by a native Hermes child."
config_schema:
  workspace:
    type: str
    default: ""
    description: "Explicit existing working directory. This is not a security sandbox."
  executable:
    type: str
    default: agy
    description: "AGY executable path; cached vendor login is managed by AGY."
  mode:
    type: str
    default: plan
    description: "plan or accept-edits. AGY owns tool permissions; Hermes restrictions do not carry over."
  timeout_seconds:
    type: int
    default: 180
    description: "Hard process deadline, 1 to 3600 seconds."
  max_output_bytes:
    type: int
    default: 4000000
    description: "Combined stdout/stderr cap, 1024 to 16000000 bytes."
  allow_external_tools:
    type: bool
    default: false
    description: "Explicit consent: AGY uses its own tools and vendor authentication, outside Hermes tool filtering."
"""
PROVIDER_MANIFEST = """name: external-agents-agy
version: 0.2.0
requires_hermes: ">=0.22.5"
manifest_version: 2
api_version: 1
kind: model-provider
author: Fidel Brian Dava
license: MIT
homepage: https://github.com/NomieC/hermes-external-agents
description: "In-process AGY protocol client. Not a sandbox or direct primary-chat provider."
"""


PACKAGE_README = """# External Agents for Hermes: {name}

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
"""


def build(output):
    output = Path(output).resolve()
    for name in ("external-agents", "external-agents-agy"):
        target = output / name
        target.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "LICENSE", target / "LICENSE")
        (target / "README.md").write_text(PACKAGE_README.format(name=name))
    backend, provider = output / "external-agents", output / "external-agents-agy"
    (backend / "plugin.yaml").write_text(BACKEND_MANIFEST)
    (backend / "__init__.py").write_text((ROOT / "backend.py").read_text())
    (provider / "plugin.yaml").write_text(PROVIDER_MANIFEST)
    (provider / "provider_profile.py").write_text((ROOT / "provider_profile.py").read_text())
    (provider / "__init__.py").write_text(
        '"""Discovered through the documented model-provider lifecycle."""\n'
        'from providers import register_provider\n'
        'from .provider_profile import AGYProfile\n\nregister_provider(AGYProfile())\n')
    runtime = provider / "hea_runtime"
    runtime.mkdir(exist_ok=True)
    (runtime / "__init__.py").write_text('"""AGY transport implementation."""\n')
    for name in ("client.py", "runner.py"):
        shutil.copyfile(ROOT / "hea_runtime" / name, runtime / name)
    print(f"Built backend and model-provider registrations in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "plugins"))
    build(parser.parse_args().output)
