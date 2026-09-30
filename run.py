"""Run one experiment or all of them: `uv run run.py` / `uv run run.py 03`."""

import importlib
import pathlib
import sys

EXPERIMENTS = sorted(p.stem for p in pathlib.Path("experiments").glob("e*.py"))


def main() -> None:
    sys.path.insert(0, "experiments")
    wanted = sys.argv[1:]
    for name in EXPERIMENTS:
        if wanted and not any(w in name for w in wanted):
            continue
        importlib.import_module(name).main()


if __name__ == "__main__":
    main()
