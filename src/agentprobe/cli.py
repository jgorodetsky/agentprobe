from __future__ import annotations

import sys
from pathlib import Path

import click

from agentprobe import __version__
from agentprobe.config import ConfigError, load_config
from agentprobe.report import render_line, render_summary, write_reports
from agentprobe.runner import run_probe
from agentprobe.scenarios import ALL_SCENARIOS, select_scenarios


@click.group()
@click.version_option(__version__, prog_name="agentprobe")
def main() -> None:
    """Security evaluation for AI agents."""


@main.command("list")
def list_scenarios() -> None:
    """List the attack scenarios."""
    for s in ALL_SCENARIOS:
        click.echo(f"{s.id:<20} {s.name:<46} {', '.join(s.owasp):<24} {', '.join(s.atlas)}")


@main.command()
@click.option(
    "--config",
    "config_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to target.yml.",
)
@click.option("--scenario", "scenario_ids", multiple=True, help="Run only this scenario id. Repeat for more.")
@click.option("--min-score", type=click.IntRange(0, 100), default=None, help="Exit 1 if the score is below this.")
@click.option(
    "--out",
    "out_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("agentprobe-report"),
    show_default=True,
    help="Folder for report.json and report.md.",
)
def run(config_path: Path, scenario_ids: tuple[str, ...], min_score: int | None, out_dir: Path) -> None:
    """Run attack scenarios against the agent in target.yml."""
    try:
        config = load_config(config_path)
    except ConfigError as e:
        raise click.ClickException(str(e)) from e

    try:
        scenarios = select_scenarios(list(scenario_ids) or config.scenarios)
    except KeyError as e:
        raise click.BadParameter(
            f"unknown scenario {e.args[0]!r}. Run `agentprobe list`.", param_hint="--scenario"
        ) from e

    click.echo(f"\n  Target: {' '.join(config.target.command)}\n")
    report = run_probe(config, scenarios, on_result=lambda i, n, r: click.echo(render_line(i, n, r)))
    _, md_path = write_reports(report, out_dir)

    click.echo("")
    click.echo(render_summary(report))
    click.echo(f"  Report: {md_path}\n")

    if min_score is not None and (report.score is None or report.score < min_score):
        click.echo(f"  Score is below --min-score {min_score}.", err=True)
        sys.exit(1)
