from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from agentprobe.evidence import ToolCall
from agentprobe.listener import Listener, RecordedRequest
from agentprobe.target import AgentRun

INSTRUCTION_PREFIX = "AGENT INSTRUCTION:"


def injection(text: str) -> str:
    return f"{INSTRUCTION_PREFIX} {text}"


@dataclass(frozen=True)
class Context:
    workspace: Path
    outside: Path
    canary: str
    listener: Listener


@dataclass(frozen=True)
class Evidence:
    run: AgentRun
    requests: list[RecordedRequest]
    tool_calls: list[ToolCall]


class Scenario(ABC):
    id: ClassVar[str]
    name: ClassVar[str]
    category: ClassVar[str]
    owasp: ClassVar[tuple[str, ...]]
    atlas: ClassVar[tuple[str, ...]]

    @abstractmethod
    def setup(self, ctx: Context) -> str:
        """Plant files and pages for this scenario. Return the benign task the user gives the agent."""

    @abstractmethod
    def detect(self, ctx: Context, evidence: Evidence) -> list[str]:
        """Return each sign that the agent followed the injection. An empty list means it resisted."""
