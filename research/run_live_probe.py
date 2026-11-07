"""Run the opt-in end-to-end probe in a fresh, disposable Hermes home.

Parent connection comes only from HEA_PARENT_* environment variables. AGY uses
its own official cached login. Runtime evidence stays outside the repository.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agy", required=True, help="Official installed AGY executable")
    args = parser.parse_args()
    for name in ("HEA_PARENT_BASE_URL", "HEA_PARENT_MODEL", "HEA_PARENT_API_KEY"):
        if not os.environ.get(name):
            parser.error(f"Set {name} through your normal credential environment")
    hermes = shutil.which("hermes")
    executable = shutil.which(args.agy)
    if not hermes or not executable:
        parser.error("Both hermes and the selected AGY executable must be installed")
    directory = Path(tempfile.mkdtemp(prefix="hea-e2e-", dir=os.environ.get("TMPDIR")))
    home, work = directory / "home", directory / "work"
    home.mkdir(mode=0o700)
    work.mkdir()
    (work / "probe.txt").write_text("HEA_E2E_" + secrets.token_hex(12))
    env = dict(os.environ, HERMES_HOME=str(home), HEA_LIVE_PROBE="1",
        HERMES_SINGLE_QUERY_SESSION="1", HERMES_EXTERNAL_AGENTS_AGY_COMMAND=executable)
    subprocess.run([sys.executable, str(ROOT / "scripts/build_plugins.py"),
        "--output", str(home / "plugins")], check=True)
    # This is a newly created test fixture, never an existing user's config.
    # JSON is valid YAML and keeps research independent of optional YAML packages.
    configuration = {
        "plugins": {"enabled": ["external-agents", "external-agents-agy"],
            "isolation": "in_process", "entries": {"external-agents": {"settings": {
                "workspace": str(work), "executable": executable, "mode": "plan",
                "timeout_seconds": 240, "allow_external_tools": True}}}},
        "terminal": {"backend": "local"},
        "delegation": {"backend": "external-agents", "fallback_providers": []},
    }
    (home / "config.yaml").write_text(json.dumps(configuration, indent=2))
    env["TERMINAL_ENV"] = "local"
    env["TMPDIR"] = str(directory)
    for name in ("HERMES_KANBAN_TASK", "HERMES_KANBAN_RUN", "HERMES_KANBAN_RUN_ID"):
        env.pop(name, None)
    print(f"Disposable evidence directory: {directory}", flush=True)
    try:
        result = subprocess.run([hermes, "--run-module", "unittest", "discover",
            "-s", str(ROOT / "research"), "-p", "live_delegation_probe.py", "-v"],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=290)
    except subprocess.TimeoutExpired:
        print("Live probe exceeded its outer deadline; inspect local evidence", file=sys.stderr)
        return 1
    (directory / "live.stdout.log").write_text(result.stdout)
    (directory / "live.stderr.log").write_text(result.stderr)
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    print(json.dumps({"live_probe_exit": result.returncode, "evidence_dir": str(directory)}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
