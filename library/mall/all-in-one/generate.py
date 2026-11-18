"""Mall - all in one: David's own design (import/mall-all-in-one.txt), unchanged except:
- shifted onto the roboport grid at the offset where none of its tiles hits a grid roboport, big pole or
  lamp (searched over all 50x50 offsets: (22, 31) mod 50 is the only collision-free one);
- the corner roboports of the 7x2 cells it covers added (8x3 = 24) so it aligns on the existing grid; the
  left input belts start on the grid line at x 48-49, left of the first roboport column.
No other change, no re-validation of the design itself.
"""
import sys, json, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from lib.bp import decode, encode, render, write_outputs
import lib.bp as B
from lib.build import BP
import lib.build as LB
LB.SIZE.update({'assembling-machine-2': 3, 'oil-refinery': 5, 'steel-chest': 1, 'storage-chest': 1, 'pump': 1})
B.SIZES.update({'assembling-machine-2': (3, 3), 'oil-refinery': (5, 5), 'steel-chest': (1, 1), 'storage-chest': (1, 1)})
B.COLORS.update({'assembling-machine-2': (110, 115, 140), 'steel-chest': (150, 150, 160), 'pump': (80, 80, 100)})

obj = decode((ROOT / 'import' / 'mall-all-in-one.txt').read_text())
bp = obj['blueprint']
b = BP(); b.ents = bp['entities']

def tiles(e):
    if e['name'] == 'pump':                                     # 1x2
        x, y = e['position']['x'], e['position']['y']
        if e.get('direction', 0) in (0, 8): return [(math.floor(x), math.floor(y - .5)), (math.floor(x), math.floor(y + .5))]
        return [(math.floor(x - .5), math.floor(y)), (math.floor(x + .5), math.floor(y))]
    return b.tiles(e)

def grid_mod():
    G = set()
    for i in range(-2, 2):
        for j in range(-2, 2): G.add((i % 50, j % 50))
    for px, py in ((3, 0), (27, 0), (3, 23)):
        for i in (-1, 0):
            for j in (-1, 0): G.add(((px + i) % 50, (py + j) % 50))
    for lx, ly in ((2.5, -1.5), (26.5, 1.5)): G.add((math.floor(lx) % 50, math.floor(ly) % 50))
    return G
G = grid_mod()
T = [t for e in b.ents for t in tiles(e)]
hits = sorted((sum(((x + ox) % 50, (y + oy) % 50) in G for x, y in T), ox, oy) for ox in range(50) for oy in range(50))
n, ox, oy = hits[0]
assert n == 0, hits[:3]
x0 = min(x for x, _ in T); y0 = min(y for _, y in T)
dx = ox + 50 * math.ceil((2 - (x0 + ox)) / 50) if False else ox - 50 * math.floor((x0 + ox) / 50)
dy = oy - 50 * math.floor((y0 + oy) / 50)
for e in b.ents:
    e['position'] = {'x': e['position']['x'] + dx, 'y': e['position']['y'] + dy}
T = [t for e in b.ents for t in tiles(e)]
xs = [x for x, _ in T]; ys = [y for _, y in T]
assert all(((x % 50), (y % 50)) not in G for x, y in T)
cx0, cx1 = 50 * math.floor(min(xs) / 50), 50 * math.ceil(max(xs) / 50)
if min(xs) % 50 >= 46: cx0 += 50          # only the grid line (left inputs) lies left of the first column
cy0, cy1 = 50 * math.floor(min(ys) / 50), 50 * math.ceil(max(ys) / 50)
occ = set(T)
nxt = max(e['entity_number'] for e in b.ents) + 1
added = 0
for rx in range(cx0, cx1 + 1, 50):
    for ry in range(cy0, cy1 + 1, 50):
        rt = {(rx + i, ry + j) for i in range(-2, 2) for j in range(-2, 2)}
        assert not rt & occ, (rx, ry)
        b.ents.append({'entity_number': nxt, 'name': 'roboport', 'position': {'x': rx, 'y': ry},
                       'request_filters': {'sections': [{'index': 1}]}})
        nxt += 1; added += 1
print(f'offset ({ox},{oy}) mod 50, 0 grid hits; mall x {min(xs)}..{max(xs)}, y {min(ys)}..{max(ys)}; '
      f'cells {(cx1 - cx0) // 50}x{(cy1 - cy0) // 50}; roboports added {added}')
write_outputs(HERE, bp)
render(HERE, bp, px=3, grid=50)
