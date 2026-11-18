"""Mall - belts: David's "Belts Y/R/B ~120/min each (1 cell)" (import/mall-belts.txt), adapted:
- grid big poles and lamps stripped (they exist in the world), corner roboports kept;
- the three belt exits on the left (yellow / red / blue, sorted by two filter splitters) are replaced by
  storage: the mixed output belt turns S at x=8, two S-facing filter splitters sort it (blue -> x=7,
  red -> x=8, yellow -> x=9), and each tier runs E along its own row past 8 fast inserters into
  8 storage chests filtered to that belt (yellow row 34, red row 38, blue row 42).
Everything above row 26 (gear rows, belt machines, lube) is unchanged.
Frame: top-left roboport center = (0,0).
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from lib import adapt
from lib.bp import write_outputs, render
from lib.build import N, E, S, W, tile_of, reach

bp = adapt.load(ROOT / 'import' / 'mall-belts.txt')
b, robos = adapt.to_frame(bp)
n_strip = adapt.strip(b, robos)
b.belt_name, b.ug_name = 'express-transport-belt', 'express-underground-belt'

# remove the old exit corner: belts x 4..6 rows 26..28, both sorting splitters, the 3 panels
def at(e):
    return tile_of(e)
drop = []
for e in b.ents:
    x, y = at(e)
    if e['name'] == 'express-transport-belt' and 4 <= x <= 6 and 26 <= y <= 28: drop.append(e)
    elif e['name'] == 'express-splitter' and (x, y) in ((7, 27), (5, 28)): drop.append(e)
    elif e['name'] == 'display-panel' and (x, y) in ((4, 25), (6, 28), (4, 29)): drop.append(e)
    elif e['name'] == 'express-transport-belt' and (x, y) == (8, 26): drop.append(e)
assert len(drop) == 12, len(drop)   # 6 belts, 2 splitters, 3 panels, (8,26)
ids = {e['entity_number'] for e in drop}
b.ents = [e for e in b.ents if e['entity_number'] not in ids]
b.wires = [w for w in b.wires if w[0] not in ids and w[2] not in ids]

# new sorting column + chest rows
for y in range(26, 30): b.belt(8, y, S)                       # mixed belt turns S at (8,26)
b.splitter(7, 30, S); b.ents[-1].update(filter={'type': 'item', 'name': 'express-transport-belt'}, output_priority='right')
b.belt(8, 31, S)
b.splitter(8, 32, S); b.ents[-1].update(filter={'type': 'item', 'name': 'fast-transport-belt'}, output_priority='right')
LINES = (('transport-belt', 9, 33, 34), ('fast-transport-belt', 8, 33, 38), ('express-transport-belt', 7, 31, 42))
for item, col, y0, row in LINES:
    for y in range(y0, row): b.belt(col, y, S)
    b.belt(col, row, E)
    for x in range(col + 1, 19): b.belt(x, row, E)
    for x in range(11, 19):
        b.inserter(x, row + 1, N)
        b.storage(x, row + 2, item)
    b.panel(10, row + 2, item)
for p in ((15, 29), (12, 37), (19, 37), (12, 45), (19, 45)): b.add('medium-electric-pole', *p)
for p in ((16, 37), (16, 45)): b.add('small-lamp', *p)
for i, e in enumerate(b.ents):
    old = e['entity_number']; e['entity_number'] = i + 1
b.wires = []                                                   # re-number safe: rebuild copper wiring
trees = adapt.rewire(b)
assert trees == 1, f'{trees} pole trees'

# ---- checks
rep, info = adapt.check(b, robos)
for item, col, y0, row in LINES:
    tiles = reach(b, (9, 26))
    assert (18, row) in tiles, f'{item} row not fed'
want_side = set()
assert not (set(info['sideloads']) & {(8, 26)}), 'turn became a sideload'
assert sorted(t for t in info['curves'] if t[1] >= 26) == [(7, 42), (8, 26), (8, 38), (9, 34)], info['curves']
assert sorted(t for t in info['ends'] if t[1] >= 26) == [(18, 34), (18, 38), (18, 42)], info['ends']
rep.append('new belts: 4 intended curves (turn at (8,26), 3 row turns), 3 row ends; no sideloads')
rep.append(f'grid: {n_strip} grid poles/lamps stripped; 4 corner roboports kept')
rep.append('storage: mixed belt -> 2 filter splitters -> 3 rows x 8 fast inserters -> 8 filtered storage chests each')
out = adapt.finish(b, 'Mall - Belts', [{'signal': {'name': 'transport-belt'}, 'index': 1},
                                       {'signal': {'name': 'fast-transport-belt'}, 'index': 2},
                                       {'signal': {'name': 'express-transport-belt'}, 'index': 3}],
                   description='Yellow, red and blue belts, ~120/min each, into 8 storage chests per tier. '
                               'Inputs right: iron (2 rows), lubricant pipe.')
for l in rep: print(l)
write_outputs(HERE, out)
render(HERE, out, px=8, grid=0)
