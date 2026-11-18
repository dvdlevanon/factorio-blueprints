"""Adapted from David's in-game design (import/engine.txt): grid big poles and lamps removed (corner
roboports kept), pole wires rebuilt as a spanning tree, yellow belts -> blue, then re-validated."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from lib.bp import write_outputs, render
from lib import adapt

src = adapt.load(ROOT / 'import' / 'engine.txt')
b, robos = adapt.to_frame(src)
removed = adapt.strip(b, robos)
trees = adapt.rewire(b)
rep, info = adapt.check(b, robos)
bp = adapt.finish(b, src['label'], src.get('icons') or [{'signal': {'name': 'roboport'}, 'index': 1}])
print(f'removed {removed} grid poles/lamps; {trees} pole tree(s)')
for l in rep: print(l)
write_outputs(HERE, bp)
render(HERE, bp, px=4, grid=0)
