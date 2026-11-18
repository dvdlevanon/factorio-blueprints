"""Mine 250x250: see lib/mine.py for the layout."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib import mine

if __name__ == '__main__':
    mine.main(5, HERE)
