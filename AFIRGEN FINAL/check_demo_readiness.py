#!/usr/bin/env python3
"""Quick demo readiness checker for AFIRGen.

Runs deterministic checks available in constrained environments and reports
whether the repository is demo-ready, plus known blockers for full production
readiness.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"


@dataclass
class CheckResult:
    name: str
    command: str
    passed: bool
    output: str
    warning: bool = False



def run_check(name: str, command: str, cwd: Path) -> CheckResult:
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        text=True,
        capture_output=True,
    )
    out = (proc.stdout + "\n" + proc.stderr).strip()
    return CheckResult(name=name, command=command, passed=proc.returncode == 0, output=out)



def main() -> int:
    results: list[CheckResult] = []

    results.append(run_check("Frontend stable suite", "npm test -- --runInBand", FRONTEND))
    results.append(
        run_check(
            "Frontend unmasked stable suite",
            "npx jest --runInBand --testPathIgnorePatterns='/node_modules/'",
            FRONTEND,
        )
    )
    results.append(run_check("Docker config validator", "python validate_docker_config.py", ROOT))
    results.append(run_check("Rate limiting validator", "python validate_rate_limiting.py", ROOT))
    results.append(
        run_check(
            "Backend syntax compile",
            "python -m py_compile 'main backend/agentv5.py' 'cors_middleware.py' 'model_loader.py'",
            ROOT,
        )
    )

    if shutil.which("docker") is None:
        results.append(
            CheckResult(
                name="Docker CLI availability",
                command="docker compose config -q",
                passed=False,
                output="docker command not found in environment",
                warning=True,
            )
        )
    else:
        results.append(run_check("Docker compose parse", "docker compose config -q", ROOT))

    security = run_check(
        "Runtime security test (requires running backend)",
        "python test_security.py",
        ROOT,
    )
    if (not security.passed) and ("Cannot connect to server" in security.output):
        security.warning = True
    results.append(security)

    print("=" * 78)
    print("AFIRGen Demo Readiness Report")
    print("=" * 78)

    demo_ok = True
    for r in results:
        if r.passed:
            mark = "✅"
        elif r.warning:
            mark = "⚠️"
        else:
            mark = "❌"
        print(f"{mark} {r.name}")
        print(f"   cmd: {r.command}")
        if not r.passed:
            demo_ok = False if not r.warning else demo_ok
            snippet = "\n".join(r.output.splitlines()[-5:])
            print(f"   note: {snippet}")

    print("\n" + "-" * 78)
    if demo_ok:
        print("DEMO STATUS: READY (stable frontend + static backend validations passed)")
    else:
        print("DEMO STATUS: NOT READY (one or more required checks failed)")
    print("PRODUCTION STATUS: requires runtime checks with backend service + Docker")

    return 0 if demo_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
