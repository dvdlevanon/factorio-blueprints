"""Mall - Artillery shells, 60/min (1/s), output on a belt to the left. 2 cells side by side.
Replaces David's 30/min design (import/mall-artillery.txt). Frame: top-left roboport center = (0,0);
left cell x 4..47, right cell x 54..97, rows 2..47. Rows that cross the line between the cells avoid
rows 22-23 (grid pole at x 52-53).

Recipes (2.1): artillery shell = 4 explosive cannon shells + 1 radar + 8 explosives, 15 s;
cannon shell = 2 steel + 2 plastic + 2 explosives, 8 s; radar = 5 green + 5 gear + 10 iron, 0.5 s;
explosives = 1 sulfur + 1 coal + 10 water -> 2, 4 s; sulfur = 30 water + 30 petroleum -> 2, 1 s.

RIGHT CELL (block origin (62,25)): 5 sulfur plants (rows -10..-2) -> sulfur belt -> explosives block
  lib/chem_rows (2 modules x 18 plants, sulfur | coal trunk); explosives leave at (59,36) W, a splitter
  at (56,36-37) sends one half up column x=55 to the cannon rows, the other W along row 37 to the
  artillery rows.
LEFT CELL
  Cannon pair (13 + 13 machines, x 8..46), rows: out 3 | out ins 4 | machines 5..7 | fast + long 8 |
    B1 9 (steel | explosives, forms at (55,9)) | B2 10 (plastic, dives under (55,10)) | fast + long 11 |
    machines 12..14 | out ins 15 | out 16. Out rows merge at x=6 and run via x=5, row 20, x=29 down.
  Radar: 2 units [gear -> bulk -> radar] at x 31..44, rows 26..32; top belt row 26 = iron | green
    (forms at (46,26)); radars drop on row 32 -> artillery B2.
  Artillery pair (7 + 7 machines, x 8..28), rows: out 26 | out ins 27 | machines 28..30 | fast + long 31 |
    B1 32 (cannon | explosives, forms at (29,32)) | B2 33 (radar, dives under (29,33)) | fast + long 34 |
    machines 35..37 | out ins 38 | out 39. Out rows merge at x=6, output leaves W at (4,39).
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from lib.bp import write_outputs, render
from lib.build import BP, N, E, S, W, validate, trace, tile_of, reach, fluid_networks, plant_ports
from lib.cell import check_fixed, finish, corners
from lib.sp_rows import tier
from lib import chem_rows

XE = 97                                                             # right edge (input entries)
def tiered(b, rate, fn):
    keep = b.belt_name, b.ug_name
    b.belt_name, b.ug_name = tier(rate); fn(); b.belt_name, b.ug_name = keep

def entry(b, row, x_to, item, rate):
    def go():
        for x in range(x_to, XE - 2): b.belt(x, row, W)
        b.ug(XE - 2, row, W, 'output'); b.ug(XE, row, W, 'input')
    tiered(b, rate, go); b.panel(XE - 1, row, item)
    return (XE, row)

# ======================= right cell: sulfur + explosives (local coords)
c, _, g = chem_rows.build(2, 9, 'explosives', 'coal', 'sulfur', 'water')
T, H, XP = g['T'], g['H'], g['XP']
c.ents = [e for e in c.ents if not (
    (e['name'] == 'pipe' and tile_of(e)[1] == H and tile_of(e)[0] > XP) or
    (e['name'] == 'display-panel' and e['icon']['name'] in ('water', 'sulfur')))]
for e in c.ents:                                                    # coal entry: yellow
    x, y = tile_of(e)
    if e['name'] == 'express-transport-belt' and y == 2 and x > T: e['name'] = 'transport-belt'
def _coal():
    for x in range(T + 3, 36): c.belt(x, 2, W)
tiered(c, 8, _coal)
NS = 5
for j in range(NS):
    x = 3 * j
    c.plant(x, -6, N, 'sulfur'); c.inserter(x + 1, -3, N)
    if j % 2 == 0: c.add('medium-electric-pole', x + 2, -3)
    else: c.add('small-lamp', x + 2, -3)
    c.pipe(x, -7); c.ptg(x + 2, -7, S); c.ptg(x + 2, -9, N)
for x in range(0, 36): c.pipe(x, -10); c.pipe(x, -8)                # petroleum, water (inlets at x=35)
c.panel(35, -9, 'petroleum-gas', 'fluid'); c.panel(35, -7, 'water', 'fluid')
c.ptg(1, -7, N); c.ptg(1, -1, S)                                    # water down to the explosives pipe row 0
for x in range(0, T + 2): c.belt(x, -2, E)                          # sulfur belt
c.belt(T + 2, -2, S); c.belt(T + 2, -1, S); c.belt(T + 2, 0, S)     # into the sulfur entry (T+2,1)
c.add('medium-electric-pole', 4, -1)
c.shift(62, 25)
b = BP(); b.belt_name, b.ug_name = 'express-transport-belt', 'express-underground-belt'
b.ents = c.ents
L = lambda x, y: (x + 62, y + 25)
EXPL_OUT = L(-3, 11)                                                # (59, 36)
# explosives split
b.belt(58, 36, W); b.belt(57, 36, W); b.splitter(56, 36, W)
b.belt(55, 36, N)
for y in range(11, 36): b.belt(55, y, N)
b.belt(55, 10, N)
for x in range(30, 56): b.belt(x, 37, W)                            # to the artillery rows
b.belt(29, 37, N); b.belt(29, 36, N); b.belt(29, 35, N); b.belt(29, 34, N); b.belt(29, 33, N)

# ======================= cannon pair
CX = [8 + 3 * j for j in range(13)]
AXA = [8 + 3 * j for j in range(7)]
def pair(recipe, xs, r, lamps=(3, 7, 11)):
    """r = (outA, outinsA, asmA, inA, b1, b2, inB, asmB, outinsB, outB)."""
    outA, oiA, aA, inA, b1, b2, inB, aB, oiB, outB = r
    for j, x in enumerate(xs):
        b.asm(x, aA, recipe); b.asm(x, aB, recipe)
        b.inserter(x, inA, S); b.inserter(x + 1, inA, S, 'long-handed-inserter')
        b.inserter(x, inB, N); b.inserter(x + 1, inB, N, 'long-handed-inserter')
        b.inserter(x + 1, oiA, S); b.inserter(x + 1, oiB, N)
        for row in (inA, inB, oiA, oiB):
            if j % 2 == 0 or j == len(xs) - 1: b.add('medium-electric-pole', x + 2, row)
            elif row in (inA, inB) and j in lamps: b.add('small-lamp', x + 2, row)
    for row in (outA, outB):
        for x in range(7, xs[-1] + 3): b.belt(x, row, W)
    b.belt(6, outA, S)                                               # merge column x=6 (input rows end at x=8)
    for y in range(outA + 1, outB): b.belt(6, y, S)
pair('explosive-cannon-shell', CX, (3, 4, 5, 8, 9, 10, 11, 12, 15, 16))
for x in range(8, 56): b.belt(x, 9, W)                              # B1 (former at 55)
b.ug(56, 10, W, 'input'); b.ug(54, 10, W, 'output')
for x in range(8, 54): b.belt(x, 10, W)                             # B2 plastic
b.belt(55, 8, S)
STEEL = entry(b, 8, 56, 'steel-plate', 8)
PLASTIC = entry(b, 10, 57, 'plastic-bar', 8)
# cannon out -> artillery B1 (north side)
b.belt(6, 16, W); b.belt(5, 16, S); b.belt(5, 17, S); b.belt(5, 18, S); b.belt(5, 19, S); b.belt(5, 20, E)
for x in range(6, 29): b.belt(x, 20, E)
b.belt(29, 20, S)
for y in range(21, 32): b.belt(29, y, S)

# ======================= artillery pair
pair('artillery-shell', AXA, (26, 27, 28, 31, 32, 33, 34, 35, 38, 39), lamps=(1, 5))
for x in range(8, 30): b.belt(x, 32, W)                             # B1 (former at 29)
b.ug(30, 33, W, 'input'); b.ug(28, 33, W, 'output')
for x in range(8, 28): b.belt(x, 33, W)                             # B2 radar
for x in (6, 5, 4): b.belt(x, 39, W)
b.panel(4, 38, 'artillery-shell')
OUT = (4, 39)

# ======================= radar units
for k, gx in enumerate((31, 38)):
    rx = gx + 4
    b.asm(gx, 28, 'iron-gear-wheel'); b.asm(rx, 28, 'radar')
    b.inserter(gx, 27, N, 'bulk-inserter'); b.inserter(gx + 1, 27, N, 'bulk-inserter')
    b.inserter(rx, 27, N, 'bulk-inserter'); b.inserter(rx + 1, 27, N, 'bulk-inserter')
    b.inserter(gx + 3, 29, W, 'bulk-inserter')                      # gear -> radar
    b.inserter(rx + 1, 31, N)                                       # radar -> row 32
    b.add('medium-electric-pole', gx + 2, 27); b.add('medium-electric-pole', gx + 3, 31)
    b.add('small-lamp', rx + 2, 27)
for x in range(31, 47): b.belt(x, 26, W)                            # top belt (former at 46)
for x in range(32, 45): b.belt(x, 32, W)
b.belt(31, 32, S); b.belt(31, 33, W)
b.belt(46, 25, S); b.belt(46, 27, N)
for x in (47, 48, 49): b.belt(x, 25, W)
b.belt(50, 25, W)
for y in range(13, 25): b.belt(50, y, S)
b.belt(50, 12, S)
for x in (51, 52, 53): b.belt(x, 12, W)
b.ug(54, 12, W, 'output'); b.ug(56, 12, W, 'input')
IRON = entry(b, 12, 57, 'iron-plate', 20)
for x in (47, 48, 49, 50): b.belt(x, 27, W)
b.belt(51, 27, W)
for y in range(14, 27): b.belt(51, y, S)
b.belt(51, 13, S)
for x in (52, 53): b.belt(x, 13, W)
b.ug(54, 13, W, 'output'); b.ug(56, 13, W, 'input')
GREEN = entry(b, 13, 57, 'electronic-circuit', 5)
# bridges
for p in ((10, 21), (47, 18), (47, 30), (53, 30), (58, 24)): b.add('medium-electric-pole', *p)
for i, e in enumerate(b.ents): e['entity_number'] = i + 1
b.wires = []

# ======================= checks
SRC = {'steel': STEEL, 'plastic': PLASTIC, 'iron': IRON, 'green': GREEN, 'coal': L(35, 2),
       'sulfur': L(0, -2), 'explosives': EXPL_OUT, 'cannon': (8, 3), 'radar': (44, 32)}
R = {k: reach(b, t) for k, t in SRC.items()}
assert reach(b, (8, 16)) <= R['cannon'] | reach(b, (8, 16))
R['cannon'] |= reach(b, (8, 16))
NEED = {'explosive-cannon-shell': [{'explosives', 'steel'}, {'plastic'}],
        'artillery-shell': [{'cannon', 'explosives'}, {'radar'}],
        'explosives': [{'sulfur', 'coal'}],
        'iron-gear-wheel': [{'iron', 'green'}], 'radar': [{'iron', 'green'}]}
WANT = {'explosive-cannon-shell': {'explosives', 'steel', 'plastic'}, 'artillery-shell': {'cannon', 'explosives', 'radar'},
        'explosives': {'sulfur', 'coal'}, 'iron-gear-wheel': {'iron', 'green'}, 'radar': {'iron', 'green', 'gears'}}
DEST = {'explosive-cannon-shell': (29, 32), 'radar': (28, 33), 'artillery-shell': OUT, 'explosives': (29, 32),
        'sulfur': L(T, 2)}
got = {}
def rules(ins, src, dst):
    sn, dn = src and src['name'], dst and dst['name']
    if sn in ('assembling-machine-3', 'chemical-plant') and dn in ('assembling-machine-3',):
        if (src['recipe'], dst['recipe']) != ('iron-gear-wheel', 'radar'): return 'bad machine link'
        got.setdefault(dst['entity_number'], set()).add('gears'); return None
    if sn in ('assembling-machine-3', 'chemical-plant'):
        r = src['recipe']
        if not dst or DEST[r] not in reach(b, tile_of(dst)): return f'{r} does not reach {DEST[r]}'
        if r == 'explosives' and (55, 9) not in reach(b, tile_of(dst)): return 'explosives miss the cannon rows'
        return None
    if dn not in ('assembling-machine-3', 'chemical-plant'): return f'{sn} -> {dn}'
    its = {k for k, r in R.items() if tile_of(src) in r}
    if its not in NEED[dst['recipe']]: return f'{dst["recipe"]} picks from {its}'
    got.setdefault(dst['entity_number'], set()).update(its)
b.wire_poles()
rep, belts = validate(b, rules)
for e in b.ents:
    if e.get('recipe') in WANT:
        assert got.get(e['entity_number']) == WANT[e['recipe']], (e['recipe'], e['position'], got.get(e['entity_number']))
rep.append('every machine reaches all its ingredients; products reach their consumers; artillery reaches the output')
nets, touch = fluid_networks(b)
assert len(nets) == 2, len(nets)
net_of = lambda t: next(i for i, n in enumerate(nets) if t in n)
NW, NP = net_of(L(35, -8)), net_of(L(35, -10))
for e in b.ents:
    if e['name'] != 'chemical-plant': continue
    ins_t = [t for _, t in plant_ports(e)['input']]
    if e['recipe'] == 'sulfur': assert net_of(ins_t[0]) == NW and net_of(ins_t[1]) == NP, e['position']
    else: assert all(net_of(t) == NW for t in ins_t), e['position']
rep.append('fluids: 2 networks (petroleum, water); sulfur box1 water / box2 petroleum; every explosives plant on water')
assert sorted(belts['curves']) == [(5, 16), (5, 20), (6, 3), (6, 26), (29, 20), (29, 37), (31, 32), (31, 33), (46, 25), (46, 27),
    (50, 12), (50, 25), (51, 13), (51, 27), (55, 8), (55, 36), (60, 30), (60, 41), (90, 26), (90, 27), (90, 31), (91, 42),
    (93, 23), (93, 26)], belts['curves']
assert sorted(belts['sideloads']) == [(6, 16), (6, 39), (29, 32), (46, 26), (55, 9), (60, 36), (91, 27)], belts['sideloads']
assert sorted(belts['ends']) == [(4, 39), (8, 9), (8, 10), (8, 32), (8, 33), (31, 26), (62, 31), (62, 42)], belts['ends']
rep.append('belts: 24 intended curves; sideloads = 2 output merges, 4 formers, explosives collector + trunk; '
           'ends = output + 7 row ends')
rep += check_fixed(b, 2, 1)
bp = finish(b, 'Mall - Artillery Shells', [('item', 'artillery-shell')], corner_list=corners(2, 1))
for l in rep: print(l)
write_outputs(HERE, bp)
render(HERE, bp, px=7, grid=0)
