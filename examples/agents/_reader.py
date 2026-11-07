"""Input reading shared by the example agents. Stdlib only. Talks to loopback URLs only, never through a proxy."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

INSTRUCTION_PREFIX = "AGENT INSTRUCTION:"
LOOPBACK_URL = re.compile(r"http://127\.0\.0\.1:\d+[^\s\"'<>]*")

http = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def read_inputs(prompt: str) -> list[str]:
    """Read every small file under the current folder, plus any loopback URL in the prompt."""
    texts = [
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(Path.cwd().rglob("*"))
        if path.is_file() and path.stat().st_size < 100_000
    ]
    for url in LOOPBACK_URL.findall(prompt):
        with http.open(url.rstrip(".,)"), timeout=5) as resp:
            texts.append(resp.read().decode("utf-8", errors="replace"))
    return texts


def embedded_instructions(texts: list[str]) -> list[str]:
    return [
        line.split(INSTRUCTION_PREFIX, 1)[1].strip()
        for text in texts
        for line in text.splitlines()
        if INSTRUCTION_PREFIX in line
    ]
