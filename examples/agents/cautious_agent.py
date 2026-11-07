"""Example agent that reads the same inputs but never follows embedded instructions. agentprobe should score it 100."""

from __future__ import annotations

import sys

from _reader import embedded_instructions, read_inputs


def main() -> None:
    prompt = sys.argv[1] if len(sys.argv) > 1 else ""
    texts = read_inputs(prompt)
    print(f"Read {len(texts)} inputs. Ignored {len(embedded_instructions(texts))} embedded instructions.")


if __name__ == "__main__":
    main()
