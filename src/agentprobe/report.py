from __future__ import annotations

import json
from pathlib import Path

from agentprobe import __version__
from agentprobe.runner import ProbeReport, ScenarioResult, Status


def _score_text(report: ProbeReport) -> str:
    return "n/a" if report.score is None else f"{report.score}/100"


def render_line(index: int, total: int, result: ScenarioResult) -> str:
    lines = [f"  [{index}/{total}] {result.scenario.name:<46} {result.status.value}"]
    lines += [f"         - {reason}" for reason in result.reasons]
    if result.error:
        lines.append(f"         - {result.error}")
    return "\n".join(lines)


def render_summary(report: ProbeReport) -> str:
    return (
        f"  Score: {_score_text(report)}  "
        f"({report.count(Status.PASS)} passed, {report.count(Status.FAIL)} failed, {report.count(Status.ERROR)} errors)"
    )


def to_json(report: ProbeReport) -> str:
    data = {
        "agentprobe_version": __version__,
        "started_at": report.started_at,
        "target_command": report.command,
        "score": report.score,
        "results": [r.to_dict() for r in report.results],
    }
    return json.dumps(data, indent=2) + "\n"


def to_markdown(report: ProbeReport) -> str:
    lines = [
        "# agentprobe report",
        "",
        f"- Target: `{' '.join(report.command)}`",
        f"- Started: {report.started_at}",
        f"- Score: {_score_text(report)}",
        "",
        "| # | Scenario | OWASP | MITRE ATLAS | Result | Evidence |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(report.results, 1):
        evidence = "; ".join(r.reasons) or r.error or "-"
        lines.append(
            f"| {i} | {r.scenario.name} | {', '.join(r.scenario.owasp)} | {', '.join(r.scenario.atlas)} "
            f"| {r.status.value} | {evidence} |"
        )
    lines += [
        "",
        "PASS means the agent resisted. FAIL means it followed the injected instruction.",
        "report.json holds the first 1,000 characters of each answer.",
        "",
    ]
    return "\n".join(lines)


def write_reports(report: ProbeReport, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path, md_path = out_dir / "report.json", out_dir / "report.md"
    json_path.write_text(to_json(report), encoding="utf-8")
    md_path.write_text(to_markdown(report), encoding="utf-8")
    return json_path, md_path
