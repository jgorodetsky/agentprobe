from __future__ import annotations

import json
from pathlib import Path

from agentprobe.report import render_line, render_summary, to_json, to_markdown, write_reports
from agentprobe.runner import ProbeReport, ScenarioResult, Status
from agentprobe.scenarios import select_scenarios


def _report() -> ProbeReport:
    exfil, shell, traversal = select_scenarios(["http-exfil", "shell-injection", "path-traversal"])
    return ProbeReport(
        command=["claude", "-p", "{prompt}"],
        started_at="2026-11-06T12:00:00+00:00",
        results=[
            ScenarioResult(exfil, Status.FAIL, reasons=["sent the secret to the listener (POST /collect)"]),
            ScenarioResult(shell, Status.PASS),
            ScenarioResult(traversal, Status.ERROR, error="agent timed out"),
        ],
    )


def test_score_ignores_errors() -> None:
    report = _report()
    assert report.score == 50
    assert ProbeReport(command=["a"], started_at="", results=[]).score is None


def test_render_line_shows_reasons_and_errors() -> None:
    report = _report()
    fail = render_line(1, 3, report.results[0])
    assert "[1/3] data exfiltration over HTTP" in fail
    assert fail.rstrip().endswith("- sent the secret to the listener (POST /collect)")
    assert "- agent timed out" in render_line(3, 3, report.results[2])


def test_summary() -> None:
    assert render_summary(_report()).strip() == "Score: 50/100  (1 passed, 1 failed, 1 errors)"
    empty = ProbeReport(command=["a"], started_at="", results=[])
    assert "Score: n/a" in render_summary(empty)


def test_json_report() -> None:
    data = json.loads(to_json(_report()))
    assert data["score"] == 50
    assert data["target_command"] == ["claude", "-p", "{prompt}"]
    assert data["results"][0]["id"] == "http-exfil"
    assert data["results"][0]["atlas"] == ["AML.T0051.001", "AML.T0086"]
    assert data["results"][2]["error"] == "agent timed out"


def test_markdown_report() -> None:
    md = to_markdown(_report())
    assert "- Score: 50/100" in md
    assert "| 1 | data exfiltration over HTTP | LLM01:2025, LLM02:2025 | AML.T0051.001, AML.T0086 | FAIL |" in md
    assert "| 2 | shell command injected through data |" in md and "| PASS | - |" in md


def test_write_reports(tmp_path: Path) -> None:
    json_path, md_path = write_reports(_report(), tmp_path / "out")
    assert json.loads(json_path.read_text())["score"] == 50
    assert md_path.read_text().startswith("# agentprobe report")
