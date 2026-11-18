"""Roboport line 1x2 (vertical) -> blueprint.txt, blueprint.json, preview.png in this dir."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.roboport_lattice import build, validate

NX, NY = 1, 2
bp = build(NX, 'Roboport 50x100', ny=NY)
for line in validate(bp, NX, ny=NY): print(line)
write_outputs(HERE, bp)
render(HERE, bp, px=3)
