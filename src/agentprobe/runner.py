from __future__ import annotations

import secrets
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from agentprobe.config import ProbeConfig
from agentprobe.evidence import read_tool_calls
from agentprobe.listener import Listener
from agentprobe.scenarios import Context, Evidence, Scenario
from agentprobe.target import AgentRun, run_agent

# agenttrail ships events to its collector after the hook fires, so give the log a moment to catch up
AGENTTRAIL_SETTLE_SECONDS = 2.0
OUTPUT_EXCERPT_CHARS = 1000


class Status(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


@dataclass
class ScenarioResult:
    scenario: Scenario
    status: Status
    reasons: list[str] = field(default_factory=list)
    error: str = ""
    duration: float = 0.0
    tool_calls: int = 0
    output: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.scenario.id,
            "name": self.scenario.name,
            "category": self.scenario.category,
            "owasp": list(self.scenario.owasp),
            "atlas": list(self.scenario.atlas),
            "status": self.status.value,
            "reasons": self.reasons,
            "error": self.error,
            "duration_seconds": round(self.duration, 2),
            "tool_calls": self.tool_calls,
            "output": self.output,
        }


@dataclass
class ProbeReport:
    command: list[str]
    started_at: str
    results: list[ScenarioResult]

    def count(self, status: Status) -> int:
        return sum(1 for r in self.results if r.status == status)

    @property
    def score(self) -> int | None:
        """Share of scored scenarios the agent resisted, 0-100. None when every scenario errored."""
        passed, failed = self.count(Status.PASS), self.count(Status.FAIL)
        if passed + failed == 0:
            return None
        return round(100 * passed / (passed + failed))


def new_canary() -> str:
    return f"sk_live_{secrets.token_hex(16)}"


def _status(run: AgentRun, reasons: list[str]) -> tuple[Status, str]:
    if reasons:
        return Status.FAIL, ""
    if run.timed_out:
        return Status.ERROR, "agent timed out"
    if run.exit_code != 0:
        last_line = run.stderr.strip().splitlines()[-1:] or [""]
        return Status.ERROR, f"agent exited with code {run.exit_code}: {last_line[0]}".rstrip(": ")
    return Status.PASS, ""


def run_scenario(config: ProbeConfig, scenario: Scenario, listener: Listener) -> ScenarioResult:
    with tempfile.TemporaryDirectory(prefix="agentprobe-") as tmp:
        root = Path(tmp).resolve()
        workspace, outside = root / "workspace", root / "outside"
        workspace.mkdir()
        outside.mkdir()
        listener.reset()
        ctx = Context(workspace=workspace, outside=outside, canary=new_canary(), listener=listener)
        prompt = scenario.setup(ctx)

        since_ms = int(time.time() * 1000)
        try:
            run = run_agent(config.target, prompt, workspace)
        except OSError as e:
            return ScenarioResult(scenario, Status.ERROR, error=f"cannot start agent: {e}")
        until_ms = int(time.time() * 1000)

        tool_calls = []
        log = config.monitor.agenttrail_jsonl
        if log is not None:
            time.sleep(AGENTTRAIL_SETTLE_SECONDS)
            tool_calls = read_tool_calls(log, since_ms, until_ms)

        reasons = scenario.detect(ctx, Evidence(run=run, requests=listener.requests(), tool_calls=tool_calls))
        status, error = _status(run, reasons)
        output = run.stdout[:OUTPUT_EXCERPT_CHARS]
        return ScenarioResult(scenario, status, reasons, error, run.duration, len(tool_calls), output)


def run_probe(
    config: ProbeConfig,
    scenarios: list[Scenario],
    on_result: Callable[[int, int, ScenarioResult], None] | None = None,
) -> ProbeReport:
    started_at = datetime.now(UTC).isoformat(timespec="seconds")
    results: list[ScenarioResult] = []
    with Listener() as listener:
        for scenario in scenarios:
            result = run_scenario(config, scenario, listener)
            results.append(result)
            if on_result:
                on_result(len(results), len(scenarios), result)
    return ProbeReport(command=config.target.command, started_at=started_at, results=results)
