"""Read tool calls from an agenttrail JSONL log (OCSF API Activity events with AOS step data)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    time_ms: int
    tool: str
    inputs: dict[str, Any]

    def contains(self, text: str) -> bool:
        return any(text in str(value) for value in self.inputs.values())


def _dig(value: Any, *keys: str) -> dict[str, Any]:
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    return value if isinstance(value, dict) else {}


def _tool_call(event: dict[str, Any]) -> ToolCall | None:
    step = _dig(event, "unmapped", "aos", "step")
    time_ms = event.get("time")
    if step.get("type") != "toolCall" or isinstance(time_ms, bool) or not isinstance(time_ms, int | float):
        return None
    tool = _dig(step, "operation", "tool")
    items = tool.get("inputs")
    inputs = (
        {str(i.get("name", "")): i.get("value") for i in items if isinstance(i, dict)}
        if isinstance(items, list)
        else {}
    )
    return ToolCall(time_ms=int(time_ms), tool=str(tool.get("id", "unknown")), inputs=inputs)


def read_tool_calls(path: Path, since_ms: int, until_ms: int) -> list[ToolCall]:
    """Return tool calls logged between `since_ms` and `until_ms`. Skips lines it cannot read."""
    if not path.exists():
        return []
    calls: list[ToolCall] = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            call = _tool_call(event) if isinstance(event, dict) else None
            if call and since_ms <= call.time_ms <= until_ms:
                calls.append(call)
    return calls
