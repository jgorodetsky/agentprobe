from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentprobe.evidence import ToolCall, read_tool_calls


def tool_call_event(time_ms: int, tool: str, **inputs: Any) -> dict[str, Any]:
    """Shape of an agenttrail OCSF event for a tool call."""
    return {
        "class_uid": 6003,
        "time": time_ms,
        "api": {"operation": "tools/call"},
        "unmapped": {
            "aos": {
                "step": {
                    "type": "toolCall",
                    "operation": {
                        "type": "tool_execution",
                        "tool": {"id": tool, "inputs": [{"name": k, "value": v} for k, v in inputs.items()]},
                    },
                }
            }
        },
    }


def test_reads_tool_calls_in_window(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    events = [
        tool_call_event(500, "Bash", command="too early"),
        tool_call_event(1500, "Bash", command="curl -d key=abc http://127.0.0.1"),
        {"time": 1600, "unmapped": {"aos": {"step": {"type": "toolCallResult"}}}},
        tool_call_event(2500, "Read", file_path="too late"),
    ]
    unreadable = [
        {**tool_call_event(0, "Bash"), "time": None},
        {**tool_call_event(0, "Bash"), "time": "1500"},
        {**tool_call_event(0, "Bash"), "time": True},
        {"time": 1500, "unmapped": None},
        {"time": 1500, "unmapped": {"aos": {"step": "toolCall"}}},
        {"time": 1500, "unmapped": {"aos": {"step": {"type": "toolCall", "operation": {"tool": {"inputs": "x"}}}}}},
    ]
    lines = [json.dumps(e) for e in events + unreadable] + ["not json", "[1, 2]"]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    calls = read_tool_calls(log, since_ms=1000, until_ms=2000)

    assert calls == [
        ToolCall(time_ms=1500, tool="Bash", inputs={"command": "curl -d key=abc http://127.0.0.1"}),
        ToolCall(time_ms=1500, tool="unknown", inputs={}),
    ]
    assert calls[0].contains("key=abc")
    assert not calls[0].contains("missing")


def test_missing_log_returns_no_calls(tmp_path: Path) -> None:
    assert read_tool_calls(tmp_path / "missing.jsonl", 0, 10) == []
