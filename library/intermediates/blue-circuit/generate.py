"""Blue circuits 15/s with their own sulfuric acid. Adapted from David's designs
(import/blue-circuit.txt, 2x2 cells, and import/sulfuric-acid.txt, 1 cell, 80/s max):
- grid big poles and lamps removed (corner roboports kept), yellow belts -> blue, pole wires rebuilt;
- the acid block goes into a new cell right of blue's top-right cell, 2 rows higher than in its own
  blueprint so blue's top-cell input belts (rows 18, 20, 28, 36, 38) pass under it;
- acid output (pipe-to-ground at (104,17) facing W) -> pipe (103,17) -> underground up to (103,10) ->
  underground W to (99,10) -> pipe (98,10) -> blue's acid inlet (pipe-to-ground (97,10) facing E);
- blue's top-cell input belts extended to x=147, their panels moved there; internal panels removed.
Frame: blue's top-left roboport center = (0,0).
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from lib.bp import write_outputs, render
from lib.build import N, E, S, W, tile_of
from lib import adapt

blue_src = adapt.load(ROOT / 'import' / 'blue-circuit.txt')
acid_src = adapt.load(ROOT / 'import' / 'sulfuric-acid.txt')
b, robos = adapt.to_frame(blue_src)
adapt.strip(b, robos)
a, arobos = adapt.to_frame(acid_src)
adapt.strip(a, arobos)

AX, AY = 100, -2                                    # acid block offset
def at(ents, x, y, name=None):
    return [e for e in ents if tile_of(e) == (x, y) and (name is None or e['name'] == name)]

# --- acid block into the new cell
acid_out_panels = {(4, 18), (4, 20)}               # its output markers, internal now
for e in a.ents:
    if e['name'] == 'roboport': continue
    if e['name'] == 'display-panel' and tile_of(e) in acid_out_panels: continue
    e = dict(e); e['position'] = {'x': e['position']['x'] + AX, 'y': e['position']['y'] + AY}
    b.ents.append(e)
# --- renumber appended entities (keep acid's internal wires out; rewire below rebuilds copper wires)
for i, e in enumerate(b.ents): e['entity_number'] = i + 1
b.wires = []
for rx, ry in ((150, 0), (150, 50)):
    b.add('roboport', rx - 2, ry - 2, request_filters={'sections': [{'index': 1}]})
assert at(b.ents, 104, 17, 'pipe-to-ground')[0]['direction'] == W
assert at(b.ents, 97, 10, 'pipe-to-ground')[0]['direction'] == E
# --- acid pipe across the grid line
b.pipe(103, 17); b.ptg(103, 16, S); b.ptg(103, 11, N); b.pipe(103, 10)
b.ptg(102, 10, E); b.ptg(99, 10, W); b.pipe(98, 10)
# --- blue's top-cell inputs: extend belts to x=147, move panels
b.ents = [e for e in b.ents if not (e['name'] == 'display-panel' and tile_of(e) in {(97, 11), (97, 19), (97, 27), (97, 29), (97, 37)})]
b.belt_name = 'express-transport-belt'
for row in (18, 20, 28, 36, 38):
    assert at(b.ents, 97, row, 'express-transport-belt'), row
    for x in range(98, 148): b.belt(x, row, W)
for row, item in ((19, 'electronic-circuit'), (27, 'advanced-circuit'), (29, 'advanced-circuit'), (37, 'electronic-circuit')):
    b.panel(147, row, item)
for i, e in enumerate(b.ents): e['entity_number'] = i + 1
robos = sorted(set(robos) | {(100.0, 0.0), (100.0, 50.0), (150.0, 0.0), (150.0, 50.0)})
trees = adapt.rewire(b)
rep, info = adapt.check(b, robos)
bp = adapt.finish(b, 'Blue Circuits 15/s + Acid', [{'signal': {'name': 'processing-unit'}, 'index': 1},
                                                    {'signal': {'type': 'fluid', 'name': 'sulfuric-acid'}, 'index': 2}])
print(f'{trees} pole tree(s)')
for l in rep: print(l)
write_outputs(HERE, bp)
render(HERE, bp, px=4, grid=0)
