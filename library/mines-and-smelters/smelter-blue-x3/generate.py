"""Smelter blue x3: see lib/smelter.py for the layout."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib import smelter

if __name__ == '__main__':
    smelter.main('blue', 3, HERE)
