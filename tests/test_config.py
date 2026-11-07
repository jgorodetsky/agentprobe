from __future__ import annotations

from pathlib import Path

import pytest

from agentprobe.config import ConfigError, load_config


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "target.yml"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_target_and_expands_config_dir(tmp_path: Path) -> None:
    path = _write(tmp_path, 'target:\n  command: ["python3", "{config_dir}/agent.py", "{prompt}"]\n  timeout: 12\n')
    config = load_config(path)
    assert config.target.command == ["python3", f"{tmp_path.resolve()}/agent.py", "{prompt}"]
    assert config.target.timeout == 12
    assert config.monitor.agenttrail_jsonl is None
    assert config.scenarios is None


def test_expands_home_in_agenttrail_path(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        'target:\n  command: ["agent", "{prompt}"]\nmonitor:\n  agenttrail_jsonl: ~/events.jsonl\n',
    )
    config = load_config(path)
    assert config.monitor.agenttrail_jsonl == Path.home() / "events.jsonl"


def test_reads_scenario_list(tmp_path: Path) -> None:
    path = _write(tmp_path, 'target:\n  command: ["agent", "{prompt}"]\nscenarios: [http-exfil]\n')
    assert load_config(path).scenarios == ["http-exfil"]


@pytest.mark.parametrize(
    "text",
    [
        'target:\n  command: ["agent"]\n',
        "target:\n  command: []\n",
        "target: {}\n",
        "target:\n",
        "{}\n",
        "- a\n- b\n",
        "just text\n",
        'target:\n  command: ["agent", "{prompt}"]\n  timeout: 0\n',
    ],
)
def test_rejects_invalid_config(tmp_path: Path, text: str) -> None:
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, text))


def test_rejects_unreadable_yaml(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, "target: [unclosed\n"))


def test_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "missing.yml")
