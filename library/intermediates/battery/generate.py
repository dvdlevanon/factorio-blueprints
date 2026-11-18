"""Batteries: 4 modules x 48 chemical plants (lib/chem_rows.py, rows of 24) -> 1 full blue belt (45/s), WEST.
2 cells side by side. Inputs from the EAST: iron (1 full blue belt), copper (1 full blue belt),
sulfuric acid (900/s). Each input is split in two; two mixed trunks (iron | copper lanes) feed the top
and bottom pairs of modules. A 2-column gap in the plant rows clears the grid pole between the cells.
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.build import validate
from lib.cell import check_fixed, finish, corners
from lib import chem_rows

M, P = 4, 24
X_CELL = 7                     # block x + 7 = cell x (output column -3 at cell x 4)
GAP = (15, 2)                  # plants 15+ shifted by 2: block x 45..46 = cell x 52..53 (grid pole)
b, rules, g = chem_rows.build(M, P, 'battery', 'iron-plate', 'copper-plate', 'sulfuric-acid', dual=True, gap=GAP)
b.wire_poles()
rep, belts = validate(b, rules)
rep.append(chem_rows.check_fluids(b))
rep.append(chem_rows.check_belts(b, belts, g, M))
x0, y0, x1, y1 = b.bbox()
print('block', x1 - x0 + 1, 'x', y1 - y0 + 1)
b.shift(X_CELL, 2 + (46 - (y1 - y0 + 1)) // 2 - y0)
rep += check_fixed(b, 2, 1)
bp = finish(b, 'Batteries', [('item', 'battery')], corner_list=corners(2, 1))
for l in rep: print(l)
write_outputs(HERE, bp)
render(HERE, bp, px=6, grid=0)
