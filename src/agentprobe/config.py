from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator


class ConfigError(Exception):
    pass


class TargetConfig(BaseModel):
    command: list[str]
    timeout: float = Field(default=300, gt=0)
    env: dict[str, str] = Field(default_factory=dict)

    @field_validator("command")
    @classmethod
    def _needs_prompt_placeholder(cls, command: list[str]) -> list[str]:
        if not command:
            raise ValueError("target.command must not be empty")
        if not any("{prompt}" in arg for arg in command):
            raise ValueError("target.command needs a {prompt} placeholder")
        return command


class MonitorConfig(BaseModel):
    agenttrail_jsonl: Path | None = None


class ProbeConfig(BaseModel):
    target: TargetConfig
    monitor: MonitorConfig = Field(default_factory=MonitorConfig)
    scenarios: list[str] | None = None


def load_config(path: Path) -> ProbeConfig:
    """Load target.yml. `{config_dir}` in the command expands to the config file's folder."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        raise ConfigError(f"cannot read {path}: {e}") from e

    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: expected a mapping with a `target` section")

    config_dir = str(path.resolve().parent)
    target = raw.get("target")
    if isinstance(target, dict) and isinstance(target.get("command"), list):
        target["command"] = [str(arg).replace("{config_dir}", config_dir) for arg in target["command"]]

    try:
        config = ProbeConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(str(e)) from e

    if config.monitor.agenttrail_jsonl is not None:
        config.monitor.agenttrail_jsonl = config.monitor.agenttrail_jsonl.expanduser()
    return config
