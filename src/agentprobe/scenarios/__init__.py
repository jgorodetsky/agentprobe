from __future__ import annotations

from agentprobe.scenarios.base import Context, Evidence, Scenario
from agentprobe.scenarios.fetch_injection import FetchInjection
from agentprobe.scenarios.file_injection import FileInjection
from agentprobe.scenarios.http_exfil import HttpExfil
from agentprobe.scenarios.output_disclosure import OutputDisclosure
from agentprobe.scenarios.path_traversal import PathTraversal
from agentprobe.scenarios.shell_injection import ShellInjection

ALL_SCENARIOS: tuple[Scenario, ...] = (
    FileInjection(),
    FetchInjection(),
    HttpExfil(),
    OutputDisclosure(),
    ShellInjection(),
    PathTraversal(),
)


def select_scenarios(ids: list[str] | None) -> list[Scenario]:
    """Return scenarios by id, in the order given. No ids returns all. Raises KeyError for an unknown id."""
    if not ids:
        return list(ALL_SCENARIOS)
    by_id = {s.id: s for s in ALL_SCENARIOS}
    for scenario_id in ids:
        if scenario_id not in by_id:
            raise KeyError(scenario_id)
    return [by_id[scenario_id] for scenario_id in ids]


__all__ = ["ALL_SCENARIOS", "Context", "Evidence", "Scenario", "select_scenarios"]
