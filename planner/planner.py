"""Compatibility entry point: python planner/planner.py <domain> <problem> <output>."""
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from planner.cli import main
from planner.search import boand_star


if __name__ == "__main__":
    main(sys.argv, len(sys.argv))
