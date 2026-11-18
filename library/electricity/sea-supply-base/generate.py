"""Sea supply, base side: requester chests -> one yellow belt per product, leaving WEST.
One cell, top-center (next to the grid big pole at R+(27,0)); includes the cell's 4 corner roboports
for alignment (no snapping). Not rotation-safe: it relies on the top grid line's big pole."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.cell import finish
from lib.build import validate
from lib.sea_supply import base_block, make_base_rules

b = base_block()
CELL = (24, 3)        # local (0,0) -> cell coords relative to the top-left roboport center R=(0,0)
b.shift(*CELL)
x0, y0, x1, y1 = b.bbox()
assert 4 <= x0 and x1 <= 47 and 2 <= y0 and y1 <= 47, 'outside cell interior'
grid_poles = [(3, 0), (27, 0), (3, 23), (53, 0)]
b.wire_poles()
rep, belts = validate(b, make_base_rules(b), grid_poles)
print('cell tiles x', x0, '..', x1, ' y', y0, '..', y1)
bp = finish(b, 'Sea Supply - Base', [('item', 'requester-chest'), ('item', 'landfill')])
for l in rep: print(l)
print('belt ends (7 output undergrounds + return end):', sorted(belts['ends']))
write_outputs(HERE, bp)
render(HERE, bp, px=8, grid=0)
