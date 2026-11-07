from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from agentprobe.config import TargetConfig
from agentprobe.target import run_agent


def _target(code: str, timeout: float = 10) -> TargetConfig:
    return TargetConfig(command=[sys.executable, "-c", code, "{prompt}"], timeout=timeout)


def test_passes_prompt_and_runs_in_workspace(tmp_path: Path) -> None:
    run = run_agent(_target("import os, sys; print(sys.argv[1]); print(os.getcwd())"), "hello agent", tmp_path)
    out = run.stdout.splitlines()
    assert out[0] == "hello agent"
    assert Path(out[1]).resolve() == tmp_path.resolve()
    assert run.exit_code == 0
    assert not run.timed_out


def test_passes_extra_env(tmp_path: Path) -> None:
    target = TargetConfig(
        command=[sys.executable, "-c", "import os; print(os.environ['PROBE_X'])", "{prompt}"],
        env={"PROBE_X": "set"},
    )
    assert run_agent(target, "p", tmp_path).stdout.strip() == "set"


def test_reports_exit_code_and_stderr(tmp_path: Path) -> None:
    run = run_agent(_target("import sys; sys.stderr.write('boom\\n'); sys.exit(3)"), "p", tmp_path)
    assert run.exit_code == 3
    assert "boom" in run.stderr


def test_kills_agent_on_timeout(tmp_path: Path) -> None:
    run = run_agent(_target("import time; print('started', flush=True); time.sleep(30)", timeout=0.5), "p", tmp_path)
    assert run.timed_out
    assert run.exit_code is None
    assert run.duration < 10


def test_kills_background_children_after_exit(tmp_path: Path) -> None:
    late_writer = "import pathlib, time; time.sleep(1); pathlib.Path('late.txt').write_text('x')"
    code = (
        "import subprocess, sys; "
        f"subprocess.Popen([sys.executable, '-c', {late_writer!r}], "
        "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); print('parent done')"
    )
    run = run_agent(_target(code), "p", tmp_path)
    assert run.stdout.strip() == "parent done"
    time.sleep(2)
    assert not (tmp_path / "late.txt").exists()


def test_bypasses_proxy_for_loopback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_PROXY", "corp.example")
    run = run_agent(_target("import os; print(os.environ['NO_PROXY']); print(os.environ['no_proxy'])"), "p", tmp_path)
    assert run.stdout.splitlines() == ["corp.example,127.0.0.1,localhost", "127.0.0.1,localhost"]


def test_missing_command_raises(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        run_agent(TargetConfig(command=["agentprobe-no-such-binary", "{prompt}"]), "p", tmp_path)
