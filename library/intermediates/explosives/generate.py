"""Explosives: 4 modules x 24 chemical plants (lib/chem_rows.py) -> 1 full blue belt (45/s), WEST.
Inputs from the EAST: sulfur (blue belt, 22.5/s used), coal (blue belt, 22.5/s used), water (225/s).
Sulfur and coal merge onto one trunk (one lane each) that splitters hand to the 4 modules.
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.build import validate
from lib.cell import check_fixed, finish
from lib import chem_rows

M = 4
b, rules, g = chem_rows.build(M, 12, 'explosives', 'sulfur', 'coal', 'water')
b.wire_poles()
rep, belts = validate(b, rules)
rep.append(chem_rows.check_fluids(b))
rep.append(chem_rows.check_belts(b, belts, g, M))
x0, y0, x1, y1 = b.bbox()
print('block', x1 - x0 + 1, 'x', y1 - y0 + 1)
b.shift(4 - x0, 2 + (46 - (y1 - y0 + 1)) // 2 - y0)          # 1 cell, fixed orientation
rep += check_fixed(b, 1, 1)
bp = finish(b, 'Explosives', [('item', 'explosives')])
for l in rep: print(l)
write_outputs(HERE, bp)
render(HERE, bp, px=8, grid=0)
