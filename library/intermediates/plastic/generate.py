"""Plastic: 3 stacked modules x 24 chemical plants -> 3 full blue belts of plastic (135/s), leaving WEST.
Inputs from the EAST: coal on 2 blue belts (uses 67.5/s = 1.5 belts), petroleum in 2 pipes (1350/s total).

Module k (oy = 12k), plants j = 0..11 at x = 3j..3j+2:
  oy+0     petroleum pipe (row A intakes, plants face N); shared with the module above
  oy+1..3  plants row A
  oy+4     per plant: fast out (x=3j, plant -> oy+5), long-handed in (3j+1, oy+6 -> plant), slot 3j+2
  oy+5     plastic belt A -> W        (one lane, 22.5/s)
  oy+6     coal belt      <- from E   (shared by both rows)
  oy+7     plastic belt B -> W
  oy+8     same as oy+4, mirrored
  oy+9..11 plants row B (face S)
  oy+12    petroleum pipe (row B intakes); shared with the module below
West end: A turns S and B turns N into the output tile (-2, oy+6) (sideload -> both lanes).
x=36: per module, a pipe-to-ground pair links pipe rows oy and oy+12 (under the belts).
East (x 37..39): petroleum enters on rows 0 and 36. Coal belt 1 enters on row 6, belt 2 on row 30;
each hits a splitter at x=38: one output feeds its own module (rows 6 / 30), the other runs along x=37
(rows 7..17 S / 29..19 N) and sideloads into module 1's coal row 18 from both sides.
Slot 3j+2: medium pole for even j and j=11, lamp for j=1,5,9.
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.build import BP, N, E, S, W, validate, trace, tile_of, fluid_networks
from lib.cell import center, check_rotations, finish

MODULES = 3
PLANTS = 12                     # per row
RECIPE = 'plastic-bar'
b = BP(); b.belt_name, b.ug_name = 'express-transport-belt', 'express-underground-belt'
XE = 3 * PLANTS - 1             # last plant column (35)
OUTS = []                       # output end tiles

for k in range(MODULES):
    oy = 12 * k
    for j in range(PLANTS):
        x = 3 * j
        b.plant(x, oy + 1, N, RECIPE); b.plant(x, oy + 9, S, RECIPE)
        b.inserter(x, oy + 4, N); b.inserter(x + 1, oy + 4, S, 'long-handed-inserter')
        b.inserter(x, oy + 8, S); b.inserter(x + 1, oy + 8, N, 'long-handed-inserter')
        for y in (oy + 4, oy + 8):
            if j % 2 == 0 or j == PLANTS - 1: b.add('medium-electric-pole', x + 2, y)
            elif j in (1, 5, 9): b.add('small-lamp', x + 2, y)
    # petroleum rows (row oy shared with the module above) and the link between them at x=36
    if k == 0:
        for x in range(0, XE + 2): b.pipe(x, oy)
    for x in range(0, XE + 2): b.pipe(x, oy + 12)
    b.pipe(XE + 1, oy + 1); b.ptg(XE + 1, oy + 2, N); b.ptg(XE + 1, oy + 10, S); b.pipe(XE + 1, oy + 11)
    # coal row (fed from the east section below)
    for x in range(1, XE + 3): b.belt(x, oy + 6, W)
    # plastic out
    for y, turn in ((oy + 5, S), (oy + 7, N)):
        for x in range(-1, 3 * (PLANTS - 1) + 1): b.belt(x, y, W)
        b.belt(-2, y, turn)
    b.belt(-2, oy + 6, W)
    b.panel(-2, oy + 4, RECIPE)
    OUTS.append((-2, oy + 6))

# ---- east: inputs ----
YB = 12 * MODULES                                              # bottom pipe row (36)
for y in (0, YB):
    for x in (XE + 2, XE + 3, XE + 4): b.pipe(x, y)            # petroleum entrances
b.panel(XE + 4, 1, 'petroleum-gas', 'fluid'); b.panel(XE + 4, YB - 1, 'petroleum-gas', 'fluid')
c0, c2 = 6, 12 * (MODULES - 1) + 6                             # coal rows of the top and bottom module
cm = 12 + 6                                                    # middle module coal row
b.belt(XE + 4, c0, W); b.splitter(XE + 3, c0, W)               # belt 1: splitter rows 6-7
b.belt(XE + 4, c2, W); b.splitter(XE + 3, c2 - 1, W)           # belt 2: splitter rows 29-30
for y in range(c0 + 1, cm): b.belt(XE + 2, y, S)               # x=37 rows 7..17 down
for y in range(cm + 1, c2): b.belt(XE + 2, y, N)               # x=37 rows 19..29 up
b.panel(XE + 4, c0 - 1, 'coal'); b.panel(XE + 4, c2 + 1, 'coal')

# ---- checks ----
def rules(ins, src, dst):
    if ins['name'] == 'fast-inserter':
        if not src or src['name'] != 'chemical-plant': return f'picks from {src and src["name"]}'
        if not dst or dst['name'] != b.belt_name: return f'drops on {dst and dst["name"]}'
        path, _ = trace(b, tile_of(dst))
        if path[-1] not in OUTS: return f'plastic belt ends at {path[-1]}, not an output'
    else:
        if not src or src['name'] != b.belt_name: return 'long-handed must pick from a belt'
        path, _ = trace(b, tile_of(src))
        if path[-1] in OUTS: return 'picks from a plastic belt'
        if not dst or dst['name'] != 'chemical-plant': return f'drops into {dst and dst["name"]}'
b.wire_poles()
rep, belts = validate(b, rules)
nets, touch = fluid_networks(b)
assert len(nets) == 1, f'{len(nets)} pipe networks'
plants = [e for e in b.ents if e['name'] == 'chemical-plant']
for e in plants:
    t = touch.get(e['entity_number'], [])
    assert sorted(k for k, _ in t) == ['input', 'input'], f'plant at {e["position"]}: ports {t}'
rep.append(f'fluids: 1 petroleum network, all {len(plants)} plants on both inputs, no outputs touching pipes')
coal_ends = [(1, 12 * k + 6) for k in range(MODULES)]
assert sorted(belts['ends']) == sorted(OUTS + coal_ends), belts['ends']
want_side = [(-2, 12 * k + 6) for k in range(MODULES)] + [(XE + 2, cm)]
assert sorted(belts['sideloads']) == sorted(want_side), belts['sideloads']
assert sorted(belts['curves']) == sorted([(-2, 12 * k + d) for k in range(MODULES) for d in (5, 7)]
                                         + [(XE + 2, c0 + 1), (XE + 2, c2 - 1)]), belts['curves']
rep.append(f'belt ends: {MODULES} outputs (west) + {MODULES} coal ends; sideloads = {MODULES} output merges '
           f'+ middle coal row fed from both splitters; curves = output turns + splitter side outputs')
center(b)
rep += check_rotations(b)
bp = finish(b, 'Plastic', [('item', 'plastic-bar')])
for l in rep: print(l)
x0, y0, x1, y1 = b.bbox()
print('size with roboports', x1 - x0 + 1, 'x', y1 - y0 + 1)
write_outputs(HERE, bp)
render(HERE, bp, px=8, grid=0)
