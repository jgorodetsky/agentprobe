from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from agentprobe.config import TargetConfig

LOOPBACK_HOSTS = ("127.0.0.1", "localhost")


@dataclass(frozen=True)
class AgentRun:
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    duration: float


def _text(data: str | bytes | None) -> str:
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return data or ""


def _agent_env(extra: dict[str, str]) -> dict[str, str]:
    env = {**os.environ, **extra}
    # keep listener traffic off any configured HTTP proxy
    for key in ("NO_PROXY", "no_proxy"):
        env[key] = ",".join(filter(None, [env.get(key, ""), *LOOPBACK_HOSTS]))
    return env


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run_agent(target: TargetConfig, prompt: str, workspace: Path) -> AgentRun:
    """Run the agent command once in `workspace`. Raises OSError if the command cannot start."""
    command = [arg.replace("{prompt}", prompt) for arg in target.command]
    start = time.monotonic()

    # own process group, so the agent and anything it spawned can be killed together
    proc = subprocess.Popen(
        command,
        cwd=workspace,
        env=_agent_env(target.env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    timed_out = False
    try:
        try:
            stdout, stderr = proc.communicate(timeout=target.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_group(proc.pid)
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired as e:  # pragma: no cover
                # a grandchild in its own session still holds the pipes
                stdout, stderr = _text(e.stdout), _text(e.stderr)
                proc.kill()
                for pipe in (proc.stdout, proc.stderr):
                    if pipe:
                        pipe.close()
                proc.wait()
    finally:
        _kill_group(proc.pid)

    return AgentRun(
        stdout=_text(stdout),
        stderr=_text(stderr),
        exit_code=None if timed_out else proc.returncode,
        timed_out=timed_out,
        duration=time.monotonic() - start,
    )
