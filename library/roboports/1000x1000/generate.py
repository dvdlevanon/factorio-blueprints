"""Roboport lattice 20x20 -> blueprint.txt, blueprint.json, preview.png in this dir."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.roboport_lattice import build, validate

N = 20
bp = build(N, 'Roboport 1000x1000')
for line in validate(bp, N): print(line)
write_outputs(HERE, bp)
render(HERE, bp, px=2 if N <= 10 else 1)
