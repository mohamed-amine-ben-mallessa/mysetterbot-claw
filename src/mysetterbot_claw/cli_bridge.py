"""
cli_bridge.py — thin, safe bridge to the mysetterbot-claw / clinstagram CLI.

Every Instagram *action* goes through the CLI binary (which owns the OS-keychain
session). We never touch credentials here. We just build argv, run it, and parse
the standard JSON envelope: { exit_code, data, backend_used } | { exit_code, error }.

stdout is JSON; stderr is human noise — we ignore stderr for parsing.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Optional, Sequence

# Exit codes documented by the CLI's agent-info manifest.
EXIT_MEANING = {
    0: "success",
    1: "user_error",
    2: "auth_error",          # session expired -> `msbc auth login`
    3: "rate_limited",        # back off and retry
    4: "api_error",           # transient upstream
    5: "challenge_required",  # 2FA / checkpoint
    6: "policy_blocked",      # growth gate / compliance mode
    7: "capability_unavailable",
}


class CliError(Exception):
    def __init__(self, exit_code: int, message: str, remediation: str = ""):
        self.exit_code = exit_code
        self.meaning = EXIT_MEANING.get(exit_code, "unknown")
        self.remediation = remediation
        super().__init__(message)


@dataclass
class CliResult:
    ok: bool
    exit_code: int
    data: Any = None
    backend_used: Optional[str] = None
    error: Optional[str] = None
    remediation: Optional[str] = None
    raw: str = ""


def _find_binary() -> str:
    """Locate the CLI. Override with MSBC_CLI env var."""
    override = os.environ.get("MSBC_CLI")
    if override:
        return override
    for name in ("msbc", "clinstagram", "msbc.exe", "clinstagram.exe"):
        found = shutil.which(name)
        if found:
            return found
    # last resort: pip user-scripts on Windows
    return "clinstagram"


def run_cli(
    args: Sequence[str],
    *,
    timeout: int = 60,
    enable_growth: bool = False,
    account: str = "",
    backend: str = "",
    dry_run: bool = False,
) -> CliResult:
    """
    Run the CLI with a JSON envelope. Global flags MUST precede the subcommand:
        <bin> --json [--account X] [--backend Y] [--enable-growth-actions] [--dry-run] <subcommand...>
    """
    binary = _find_binary()
    argv = [binary, "--json"]
    if account:
        argv += ["--account", account]
    if backend:
        argv += ["--backend", backend]
    if enable_growth:
        argv += ["--enable-growth-actions"]
    if dry_run:
        argv += ["--dry-run"]
    argv += [str(a) for a in args]

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        proc = subprocess.run(
            argv, capture_output=True, timeout=timeout, env=env,
        )
    except FileNotFoundError:
        raise CliError(1, f"CLI binary not found ({binary}). Install mysetterbot-claw-cli / clinstagram.")
    except subprocess.TimeoutExpired:
        raise CliError(4, f"CLI timed out after {timeout}s: {' '.join(argv[1:])}")

    out = proc.stdout.decode("utf-8", "replace").strip()
    err = proc.stderr.decode("utf-8", "replace").strip()

    # Parse the JSON envelope. The CLI prints JSON to stdout on --json.
    parsed: Any = None
    if out:
        try:
            parsed = json.loads(out)
        except json.JSONDecodeError:
            # not JSON: surface raw output as an error for visibility
            parsed = None

    if isinstance(parsed, dict) and "exit_code" in parsed:
        code = parsed.get("exit_code", proc.returncode)
        if parsed.get("error"):
            return CliResult(
                ok=False, exit_code=code, error=parsed["error"],
                remediation=parsed.get("remediation"), raw=out,
            )
        return CliResult(
            ok=(code == 0), exit_code=code,
            data=parsed.get("data"), backend_used=parsed.get("backend_used"),
            raw=out,
        )

    # No envelope — fall back to process return code.
    if proc.returncode == 0 and parsed is not None:
        return CliResult(ok=True, exit_code=0, data=parsed, raw=out)
    return CliResult(
        ok=False, exit_code=proc.returncode or 1,
        error=(out or err or "CLI produced no output"), raw=out,
    )
