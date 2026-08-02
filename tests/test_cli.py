"""End-to-end tests for the CLI harness itself (cli.py), as opposed to
the rules engine it wraps. Runs the actual entry point as a subprocess
against the example JSON files so we're testing exactly what a user
would run from the command line.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "cli.py"
EXAMPLES = REPO_ROOT / "examples"


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_json_output_hip_implant():
    result = _run_cli(str(EXAMPLES / "hip_implant.json"), "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["predicted_class"] == "III"
    assert any(r["rule_id"] == "Rule 8" for r in payload["triggered_rules"])
    assert "not real regulatory or legal advice" in payload["disclaimer"]


def test_cli_json_output_hypodermic_syringe():
    result = _run_cli(str(EXAMPLES / "hypodermic_syringe.json"), "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["predicted_class"] == "IIa"


def test_cli_human_readable_report_contains_disclaimer():
    result = _run_cli(str(EXAMPLES / "hip_implant.json"))
    assert result.returncode == 0
    assert "Predicted classification: Class III" in result.stdout
    assert "This is an educational/demonstration tool" in result.stdout


def test_cli_reads_from_stdin():
    data = (EXAMPLES / "hip_implant.json").read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(CLI), "--json"],
        cwd=REPO_ROOT,
        input=data,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["predicted_class"] == "III"


def test_cli_rejects_unknown_attribute_field():
    result = _run_cli("-")
    result = subprocess.run(
        [sys.executable, str(CLI)],
        cwd=REPO_ROOT,
        input=json.dumps({"not_a_real_field": True}),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Unknown DeviceAttributes field" in result.stderr


def test_cli_rejects_invalid_json():
    result = subprocess.run(
        [sys.executable, str(CLI)],
        cwd=REPO_ROOT,
        input="{not valid json",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Invalid JSON input" in result.stderr
