from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from agentprobe import __version__
from agentprobe.cli import main


def _run(*args: str):
    return CliRunner().invoke(main, list(args))


def test_version() -> None:
    result = _run("--version")
    assert result.exit_code == 0
    assert __version__ in result.output


def test_list() -> None:
    result = _run("list")
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    assert len(lines) == 6
    assert lines[2].startswith("http-exfil")
    assert "AML.T0086" in lines[2]


def test_run_vulnerable_example(examples_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "report"
    result = _run("run", "--config", str(examples_dir / "fake-vulnerable.yml"), "--out", str(out))
    assert result.exit_code == 0, result.output
    assert "Score: 0/100" in result.output
    assert (out / "report.json").exists() and (out / "report.md").exists()


def test_min_score_gate_fails(examples_dir: Path, tmp_path: Path) -> None:
    result = _run(
        "run", "--config", str(examples_dir / "fake-vulnerable.yml"), "--min-score", "70", "--out", str(tmp_path)
    )
    assert result.exit_code == 1


def test_safe_example_meets_gate(examples_dir: Path, tmp_path: Path) -> None:
    result = _run("run", "--config", str(examples_dir / "fake-safe.yml"), "--min-score", "100", "--out", str(tmp_path))
    assert result.exit_code == 0, result.output
    assert "Score: 100/100" in result.output


def test_single_scenario(examples_dir: Path, tmp_path: Path) -> None:
    result = _run(
        "run", "--config", str(examples_dir / "fake-safe.yml"), "--scenario", "http-exfil", "--out", str(tmp_path)
    )
    assert result.exit_code == 0, result.output
    assert "[1/1] data exfiltration over HTTP" in result.output


def test_unknown_scenario(examples_dir: Path, tmp_path: Path) -> None:
    result = _run("run", "--config", str(examples_dir / "fake-safe.yml"), "--scenario", "nope", "--out", str(tmp_path))
    assert result.exit_code == 2
    assert "unknown scenario 'nope'" in result.output


def test_invalid_config(tmp_path: Path) -> None:
    config = tmp_path / "bad.yml"
    config.write_text('target:\n  command: ["agent"]\n', encoding="utf-8")
    result = _run("run", "--config", str(config), "--out", str(tmp_path / "out"))
    assert result.exit_code == 1
    assert "{prompt} placeholder" in result.output
