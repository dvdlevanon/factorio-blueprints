"""Adapted from David's in-game design (import/red-circuit.txt): grid big poles and lamps removed (corner
roboports kept), pole wires rebuilt as a spanning tree, yellow belts -> blue, then re-validated.

Cable fix (2026-11-18): each of the 4 cable belts (rows 11, 24, 26, 39 at the east end) got cable on ONE lane
only (all 6 cable asms on one side; inserters drop on the far lane) -> 22.5/s per belt -> 22.5/s red total.
Added 4 blocks of 5 cable asms (20 asms, 2 fast in + 2 fast out each, ~23/s) that sideload the empty lane:
  top    (rows 3-9):  west block x180-194 -> col 198 -> belt 11 north lane
                      east block x202-216 -> col 200 (undergrounds under 9-11, 17-18, 24) -> belt 26 north lane
  bottom (rows 41-47, mirror): west -> col 198 -> belt 39 south lane; east -> col 201 -> belt 24 south lane
Copper: the top/bottom copper belts (rows 5/45) extended W via x=219 to rows 9/41.
Frame: top-left roboport center = (0,0); x 150.. is the east cell."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from lib.bp import write_outputs, render
from lib import adapt

src = adapt.load(ROOT / 'import' / 'red-circuit.txt')
b, robos = adapt.to_frame(src)
removed = adapt.strip(b, robos)
from lib.build import N, E, S, W, tile_of
b.belt_name, b.ug_name = 'express-transport-belt', 'express-underground-belt'
occ = b.occupancy()
def is_belt(x, y, d=W):
    e = occ.get((x, y)); return e and e['name'] == 'express-transport-belt' and e.get('direction', 0) == d
for x, y in ((198, 11), (200, 26), (198, 39), (201, 24), (223, 5), (223, 45)): assert is_belt(x, y), (x, y)

def block(mirror):
    """Two 5-asm cable blocks; mirror=False -> top (rows 3..9), True -> bottom (rows 41..47)."""
    Y = (lambda y: 50 - y) if mirror else (lambda y: y)
    toward = N if mirror else S                       # pickup side of both inserter rows (asm / copper side)
    for x0 in [180 + 3 * j for j in range(5)] + [202 + 3 * j for j in range(5)]:
        b.asm(x0, min(Y(5), Y(7)), 'copper-cable')
        for dx in (0, 1):
            b.inserter(x0 + dx, Y(4), toward)          # asm -> out belt
            b.inserter(x0 + dx, Y(8), toward)          # copper -> asm
        j = (x0 - 180) // 3 if x0 < 200 else (x0 - 202) // 3
        if j % 2 == 0:
            b.add('medium-electric-pole', x0 + 2, Y(4)); b.add('medium-electric-pole', x0 + 2, Y(8))
        else:
            b.add('small-lamp', x0 + 2, Y(4))
    b.add('medium-electric-pole', 199, Y(5))
    # copper: extend the copper belt (row 5 / 45) to row 9 / 41
    for x in (222, 221, 220): b.belt(x, Y(5), W)
    vd = S if not mirror else N
    for y in (5, 6, 7, 8): b.belt(219, Y(y), vd if y < 9 else W)
    for x in range(219, 179, -1): b.belt(x, Y(9), W) if (x, Y(9)) not in ((219, Y(9)),) else None
    b.belt(219, Y(9), W)
    # outputs
    for x in range(180, 198): b.belt(x, Y(3), E)       # west block -> col 198
    for x in range(216, 200, -1): b.belt(x, Y(3), W)   # east block -> col 200 / 201
    return Y, vd

Y, vd = block(False)
# west top -> belt 11 north lane
b.belt(198, 3, S)
for y in range(4, 8): b.belt(198, y, S)
b.ug(198, 8, S, 'input'); b.ug(198, 10, S, 'output')
# east top -> belt 26 north lane
b.belt(200, 3, S)
for y in range(4, 8): b.belt(200, y, S)
b.ug(200, 8, S, 'input'); b.ug(200, 12, S, 'output')
for y in (13, 14, 15): b.belt(200, y, S)
b.ug(200, 16, S, 'input'); b.ug(200, 19, S, 'output')
for y in (20, 21, 22): b.belt(200, y, S)
b.ug(200, 23, S, 'input'); b.ug(200, 25, S, 'output')
Y, vd = block(True)
# west bottom -> belt 39 south lane
b.belt(198, 47, N)
for y in range(43, 47): b.belt(198, y, N)
b.ug(198, 42, N, 'input'); b.ug(198, 40, N, 'output')
# east bottom -> belt 24 south lane (column 201; the east out row ends at 202)
b.ents = [e for e in b.ents if not (e['name'] == 'express-transport-belt' and tile_of(e) == (201, 47))]
b.belt(201, 47, N)
for y in range(43, 47): b.belt(201, y, N)
b.ug(201, 42, N, 'input'); b.ug(201, 38, N, 'output')
for y in (37, 36, 35): b.belt(201, y, N)
b.ug(201, 34, N, 'input'); b.ug(201, 31, N, 'output')
for y in (30, 29, 28): b.belt(201, y, N)
b.ug(201, 27, N, 'input'); b.ug(201, 25, N, 'output')
for i, e in enumerate(b.ents): e['entity_number'] = i + 1
trees = adapt.rewire(b)
rep, info = adapt.check(b, robos)
bp = adapt.finish(b, src['label'], src.get('icons') or [{'signal': {'name': 'roboport'}, 'index': 1}])
print(f'removed {removed} grid poles/lamps; {trees} pole tree(s)')
for l in rep: print(l)
write_outputs(HERE, bp)
render(HERE, bp, px=4, grid=0)
