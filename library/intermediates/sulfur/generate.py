"""Sulfur: 24 chemical plants (2 mirrored rows of 12) -> 1 full blue belt (45/s), leaving WEST.
Inputs from the EAST: water and petroleum, each in its own pipe (one inlet each).

Rows (plants j = 0..11 at x = 3j..3j+2):
  0      petroleum line (row A)              16  petroleum line (row B)
  1      ptg N at 3j+2                       15  ptg S at 3j
  2      water line                          14  water line
  3      ports: pipe 3j (water), ptg S 3j+2  13  ports: pipe 3j+2 (water), ptg N 3j
  4..6   plants A (face N)                   10..12 plants B (face S)
  7      fast inserters (plant -> belt)      9   fast inserters
  8      sulfur belt -> W (A on the south lane, B on the north lane)
Fluid box 1 (left port when facing N) = water, box 2 = petroleum (recipe ingredient order; check in game).
The petroleum port tile is a pipe-to-ground that dives under the water line, so the fluids never touch.
East: x=36 links the water lines (ptg 3 -> 13), x=37 the petroleum lines (ptg 1 -> 10, 12 -> 15).
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.build import BP, N, E, S, W, validate, trace, tile_of, fluid_networks, plant_ports
from lib.cell import center, check_rotations, finish

P = 12
RECIPE = 'sulfur'
b = BP(); b.belt_name, b.ug_name = 'express-transport-belt', 'express-underground-belt'
XE = 3 * P            # 36: first column east of the plants

for j in range(P):
    x = 3 * j
    b.plant(x, 4, N, RECIPE); b.plant(x, 10, S, RECIPE)
    b.inserter(x + 1, 7, N); b.inserter(x + 1, 9, S)
    for y in (7, 9):
        if j % 2 == 0 or j == P - 1: b.add('medium-electric-pole', x + 2, y)
        elif j in (1, 5, 9): b.add('small-lamp', x + 2, y)
    # row A ports (row 3): water pipe at x, petroleum ptg at x+2 diving to row 1
    b.pipe(x, 3); b.ptg(x + 2, 3, S); b.ptg(x + 2, 1, N)
    # row B ports (row 13): water pipe at x+2, petroleum ptg at x diving to row 15
    b.pipe(x + 2, 13); b.ptg(x, 13, N); b.ptg(x, 15, S)
for x in range(0, XE):
    b.pipe(x, 2); b.pipe(x, 14)        # water lines
for x in range(0, XE + 2):
    b.pipe(x, 0); b.pipe(x, 16)        # petroleum lines (to x=37)
# east links
b.pipe(XE, 2); b.ptg(XE, 3, N); b.ptg(XE, 13, S); b.pipe(XE, 14)
b.ptg(XE + 1, 1, N); b.ptg(XE + 1, 10, S); b.pipe(XE + 1, 11); b.ptg(XE + 1, 12, N); b.ptg(XE + 1, 15, S)
# inlets: petroleum row 0, water row 2
for x in (XE + 2, XE + 3): b.pipe(x, 0)
for x in (XE + 1, XE + 2, XE + 3): b.pipe(x, 2)
b.panel(XE + 3, 1, 'petroleum-gas', 'fluid'); b.panel(XE + 3, 3, 'water', 'fluid')
# output belt
for x in range(-1, XE): b.belt(x, 8, W)
b.panel(-1, 7, RECIPE)
OUT = (-1, 8)

# ---- checks ----
def rules(ins, src, dst):
    if not src or src['name'] != 'chemical-plant': return f'picks from {src and src["name"]}'
    if not dst or dst['name'] != b.belt_name: return f'drops on {dst and dst["name"]}'
    path, _ = trace(b, tile_of(dst))
    if path[-1] != OUT: return f'belt ends at {path[-1]}'
b.wire_poles()
rep, belts = validate(b, rules)
nets, touch = fluid_networks(b)
assert len(nets) == 2, f'{len(nets)} pipe networks'
net_of = lambda t: next(i for i, n in enumerate(nets) if t in n)
water, petro = net_of((XE + 3, 2)), net_of((XE + 3, 0))
assert water != petro
plants = [e for e in b.ents if e['name'] == 'chemical-plant']
for e in plants:
    t = touch.get(e['entity_number'], [])
    assert sorted(k for k, _ in t) == ['input', 'input'], f'plant at {e["position"]}: ports {t}'
    ports = [tg for _, tg in plant_ports(e)['input']]          # [box 1 (left when N), box 2]
    assert net_of(ports[0]) == water and net_of(ports[1]) == petro, f'plant at {e["position"]}: fluids swapped'
rep.append(f'fluids: 2 networks (water, petroleum) never touching; all {len(plants)} plants: box 1 water, box 2 petroleum')
assert belts['ends'] == [OUT] and not belts['curves'] and not belts['sideloads'], belts
rep.append('belt: one straight output belt, west end only')
center(b)
rep += check_rotations(b)
bp = finish(b, 'Sulfur', [('item', 'sulfur')])
for l in rep: print(l)
x0, y0, x1, y1 = b.bbox()
print('size with roboports', x1 - x0 + 1, 'x', y1 - y0 + 1)
write_outputs(HERE, bp)
render(HERE, bp, px=8, grid=0)
