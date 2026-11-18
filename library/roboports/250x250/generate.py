"""Roboport lattice 5x5 -> blueprint.txt, blueprint.json, preview.png in this dir."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.roboport_lattice import build, validate

N = 5
bp = build(N, 'Roboport 250x250')
for line in validate(bp, N): print(line)
write_outputs(HERE, bp)
render(HERE, bp, px=4 if N <= 2 else 3)
