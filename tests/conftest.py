from __future__ import annotations

import sys
import urllib.request
from collections.abc import Callable, Iterator
from functools import partial
from pathlib import Path

import pytest

from agentprobe import runner
from agentprobe.config import ProbeConfig, TargetConfig
from agentprobe.listener import Listener

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES


@pytest.fixture
def agent_config() -> Callable[[str], ProbeConfig]:
    def build(agent: str) -> ProbeConfig:
        script = EXAMPLES / "agents" / f"{agent}.py"
        return ProbeConfig(target=TargetConfig(command=[sys.executable, str(script), "{prompt}"], timeout=30))

    return build


@pytest.fixture
def fetch() -> Callable:
    """urlopen that ignores HTTP_PROXY, so tests reach the loopback listener behind a proxy too."""
    return partial(urllib.request.build_opener(urllib.request.ProxyHandler({})).open, timeout=5)


@pytest.fixture
def listener() -> Iterator[Listener]:
    with Listener() as server:
        yield server


@pytest.fixture(autouse=True)
def no_settle_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "AGENTTRAIL_SETTLE_SECONDS", 0)
