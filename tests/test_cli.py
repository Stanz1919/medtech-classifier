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


# --- Phase 2: --text mode ---


def test_cli_text_mode_human_readable():
    result = _run_cli("--text", "A sterile, single-use hypodermic syringe used to inject medicinal products under the skin.")
    assert result.returncode == 0
    assert "Extraction (from free text" in result.stdout
    assert "Predicted classification: Class IIa" in result.stdout


def test_cli_text_mode_json_includes_extraction():
    result = _run_cli("--text", "A titanium hip replacement implant intended for permanent placement in the joint.", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["predicted_class"] == "III"
    assert payload["extraction"] is not None
    assert any("invasiveness" in s for s in payload["extraction"]["matched_signals"])


def test_cli_text_mode_surfaces_clarifying_questions():
    """The heartbeat-app case: severity is genuinely undetermined from
    text alone, so the CLI must show a specific clarifying question, not
    silently return a confident-looking Class I."""
    result = _run_cli(
        "--text",
        "A mobile app that analyses a patient heartbeat, detects abnormalities, and informs a physician.",
    )
    assert result.returncode == 0
    assert "QUESTIONS TO RESOLVE THIS CLASSIFICATION" in result.stdout
    assert "Class IIb" in result.stdout
    assert "Predicted classification: Class IIa" in result.stdout  # conservative floor, not Class I


def test_cli_full_rule_breakdown_shown_for_structured_input():
    """Even a Class III result must show all 22 rules were evaluated, not
    just the decisive one - full audit trail by default."""
    result = _run_cli(str(EXAMPLES / "hip_implant.json"))
    assert result.returncode == 0
    assert "Full rule-by-rule breakdown (all 22 Annex VIII rules evaluated):" in result.stdout
    for i in range(1, 23):
        assert f"Rule {i}" in result.stdout
    assert "[DECISIVE]" in result.stdout
