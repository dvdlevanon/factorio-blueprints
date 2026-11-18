"""Mall - Solar panels + Accumulators (one blueprint), ~105/min each, outputs on belts to the left.
Replaces David's two designs (import/mall-solar.txt, import/mall-accumulator.txt). 1 cell wide x 2 tall.
Frame: top-left roboport center = (0,0); top cell y 2..47, bottom cell y 52..97.

TOP CELL (machines j = 0..6 at x = 10 + 3j)
  Solar pair, rows 5..18: out A 5 | out ins 6 | machines 7..9 | bulk (near) + long (far) 10 |
    belt1 11 (steel | green) | belt2 12 (copper | green) | bulk + long 13 | machines 14..16 | out ins 17 | out B 18
    belt1 forms at (33,11): steel from N (row 10), green from S (column 33); belt2 forms at (35,12): copper
    from N (row 11), green from S (column 35), and dives under (33,12). Green (one red belt) is split by a
    splitter at x=38 rows 14-15.
  Accumulator pair, rows 30..42: out A 30 | out ins 31 | machines 32..34 | fast 35 | M 36 (iron | battery) |
    fast 37 | machines 38..40 | out ins 41 | out B 42. M forms at (33,36): iron from N (row 35), batteries
    from S (column 33, fed by row 46 from the battery riser at x=5).
  Out A rows turn S at x=7 and sideload onto out B -> output belt leaves W at x=4 (solar row 18, accu row 42).
BOTTOM CELL (block origin (9,54))
  rows 0..8: 9 sulfur plants (water box 1 / petroleum box 2 on separate pipes, as Intermediates/sulfur);
    sulfur belt row 8 -> E -> down x=27 -> feed row 12 (W): sulfur on the north lane, iron sideloaded
    onto the south lane at (26,12).
  rows 10..17: 6 acid plants (face N): water via pipe-to-ground diving under the feed belt, one bulk
    inserter each from the feed belt, acid out on pipe row 17 -> (0,18) -> battery pipe rows.
  rows 19..41: batteries, lib/chem_rows (2 modules x 18 plants, iron | copper trunk); battery output at
    (-3,30) rises at x=-4 (cell x=5) to the top cell.
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

def tiered(b, rate, fn):
    keep = b.belt_name, b.ug_name
    b.belt_name, b.ug_name = tier(rate)
    fn()
    b.belt_name, b.ug_name = keep

def entry(b, row, x_from, item, rate, xe=46):
    """Input belt on `row` from the right edge (UG pair with the panel between) W down to x_from."""
    def go():
        for x in range(x_from, xe - 2): b.belt(x, row, W)
        b.ug(xe - 2, row, W, 'output'); b.ug(xe, row, W, 'input')
    tiered(b, rate, go)
    b.panel(xe - 1, row, item)
    return (xe, row)

# ======================= bottom cell: chem block (built in local coords, then shifted)
bb, rules_bat, g = chem_rows.build(2, 9, 'battery', 'iron-plate', 'copper-plate', 'sulfuric-acid')
# drop chem_rows' own acid inlet (bottom row, east) - acid comes from the acid plants above
H = g['H']
bb.ents = [e for e in bb.ents if not ((e['name'] == 'pipe' and tile_of(e)[1] == H and tile_of(e)[0] > g['XP'])
                                      or (e['name'] == 'display-panel' and e['icon']['name'] == 'sulfuric-acid'))]
for e in bb.ents:                                                   # battery entries: yellow (9/s each)
    x, y = tile_of(e)
    if e['name'] == 'express-transport-belt' and y in (1, 2) and x > g['T']: e['name'] = 'transport-belt'
bb.shift(0, 19)
c = BP(); c.belt_name, c.ug_name = 'express-transport-belt', 'express-underground-belt'
c.ents = bb.ents
# sulfur row (j = 0..8)
for j in range(9):
    x = 3 * j
    c.plant(x, 4, N, 'sulfur'); c.inserter(x + 1, 7, N)
    if j % 2 == 0: c.add('medium-electric-pole', x + 2, 7)
    elif j in (1, 5): c.add('small-lamp', x + 2, 7)
    c.pipe(x, 3); c.ptg(x + 2, 3, S); c.ptg(x + 2, 1, N)
c.add('medium-electric-pole', 26, 7) if False else None
for x in range(0, 32): c.pipe(x, 0)                                 # petroleum (inlet at x=31)
for x in range(0, 32): c.pipe(x, 2)                                 # water (inlet at x=31)
c.panel(31, 1, 'petroleum-gas', 'fluid'); c.panel(31, 3, 'water', 'fluid')
c.ptg(19, 3, N); c.ptg(19, 9, S)                                    # water down to the acid water row
for x in range(0, 27): c.belt(x, 8, E)                              # sulfur belt
for y in range(8, 12): c.belt(27, y, S)
for x in range(0, 28): c.belt(x, 12, W)                             # feed row (curve at 27)
c.belt(26, 13, N)                                                   # iron sideload (south lane)
IRON_ACID = None
def _iron():
    for x in range(27, 31): c.belt(x, 13, W)
tiered(c, 3.5, _iron); c.panel(31, 14, 'iron-plate')
c.belt_name = 'transport-belt'; c.belt(31, 13, W); c.belt_name = 'express-transport-belt'
# acid row (j = 0..5)
for x in range(0, 20): c.pipe(x, 10)                                # acid-plant water
for j in range(6):
    x = 3 * j
    c.plant(x, 14, N, 'sulfuric-acid')
    c.ptg(x, 11, N); c.ptg(x + 2, 11, N); c.ptg(x, 13, S); c.ptg(x + 2, 13, S)
    c.inserter(x + 1, 13, N, 'bulk-inserter')
    if j % 2 == 0: c.add('medium-electric-pole', x + 1, 11)
    elif j == 3: c.add('small-lamp', x + 1, 11)
for x in range(0, 18): c.pipe(x, 17)                                # acid out
c.pipe(0, 18)                                                       # -> battery pipe row (local 19)
c.add('medium-electric-pole', 4, 18)
# battery riser: (-3,30) W -> (-4,30) N
c.belt(-4, 30, N)
c.shift(9, 54)
# ======================= top cell
b = BP(); b.belt_name, b.ug_name = 'express-transport-belt', 'express-underground-belt'
b.ents = c.ents
for y in range(47, 84): b.belt(5, y, N)
b.belt(5, 46, E)
for x in range(6, 33): b.belt(x, 46, E)
b.belt(33, 46, N)
for y in range(37, 46): b.belt(33, y, N)
AX = [10 + 3 * j for j in range(7)]
def pair(top, rows, ins_kind):
    """rows: dict with outA, outinsA, asmA, inA, inB, asmB, outinsB, outB."""
    for j, x in enumerate(AX):
        b.asm(x, rows['asmA'], top); b.asm(x, rows['asmB'], top)
        b.inserter(x + 1, rows['outinsA'], S); b.inserter(x + 1, rows['outinsB'], N)
        if ins_kind == 'solar':
            b.inserter(x, rows['inA'], S, 'bulk-inserter'); b.inserter(x + 1, rows['inA'], S, 'long-handed-inserter')
            b.inserter(x, rows['inB'], N, 'bulk-inserter'); b.inserter(x + 1, rows['inB'], N, 'long-handed-inserter')
        else:
            b.inserter(x + 1, rows['inA'], S); b.inserter(x + 1, rows['inB'], N)
        for r in (rows['outinsA'], rows['outinsB'], rows['inA'], rows['inB']):
            if j % 2 == 0: b.add('medium-electric-pole', x + 2, r)
            elif r in (rows['inA'], rows['inB']) and j in (1, 5): b.add('small-lamp', x + 2, r)
    for r in (rows['outA'], rows['outB']):
        for x in range(8, 32): b.belt(x, r, W)
    b.belt(7, rows['outA'], S)
    for y in range(rows['outA'] + 1, rows['outB']): b.belt(7, y, S)
    for x in (7, 6, 5, 4): b.belt(x, rows['outB'], W)
    b.panel(4, rows['outB'] - 1, top)
    return (4, rows['outB'])
OUT_SOLAR = pair('solar-panel', dict(outA=5, outinsA=6, asmA=7, inA=10, inB=13, asmB=14, outinsB=17, outB=18), 'solar')
OUT_ACC = pair('accumulator', dict(outA=30, outinsA=31, asmA=32, inA=35, inB=37, asmB=38, outinsB=41, outB=42), 'acc')
# solar belts + formers
for x in range(10, 34): b.belt(x, 11, W)                            # belt1 (former at 33)
b.belt(35, 12, W); b.ug(34, 12, W, 'input'); b.ug(32, 12, W, 'output')
for x in range(10, 32): b.belt(x, 12, W)                            # belt2
b.belt(33, 10, S); STEEL = entry(b, 10, 34, 'steel-plate', 8.75)
b.belt(35, 11, S); COPPER = entry(b, 11, 36, 'copper-plate', 8.75)
b.splitter(38, 14, W)
GREEN = entry(b, 15, 39, 'electronic-circuit', 26.25)
b.belt(37, 14, W); b.belt(36, 14, W); b.belt(35, 14, N); b.belt(35, 13, N)
for x in (37, 36, 35, 34): b.belt(x, 15, W)
b.belt(33, 15, N); b.belt(33, 14, N); b.belt(33, 13, N); b.belt(33, 12, N)
# accumulator M + iron
for x in range(10, 34): b.belt(x, 36, W)                            # M (former at 33)
b.belt(33, 35, S); IRON_ACC = entry(b, 35, 34, 'iron-plate', 3.5)
# bridges / grid
for p in ((8, 24), (9, 48), (8, 56)): b.add('medium-electric-pole', *p)
for i, e in enumerate(b.ents): e['entity_number'] = i + 1
b.wires = []

# ======================= checks
B0 = (9, 54)
L = lambda x, y: (x + B0[0], y + B0[1])
ent = {'petroleum': L(31, 0), 'water': L(31, 2)}
IRON_BAT, COPPER_BAT = L(g['T'] + 2, 21), L(g['T'] + 2, 20)
R = {k: reach(b, t) for k, t in (('steel-plate', STEEL), ('copper-solar', COPPER), ('green', GREEN), ('iron-acc', IRON_ACC),
                                ('iron-acid', L(31, 13)), ('iron-bat', IRON_BAT), ('copper-bat', COPPER_BAT))}
R['sulfur'] = reach(b, L(0, 8))
R['battery'] = reach(b, L(-3, 30))
OUTS = {'solar-panel': OUT_SOLAR, 'accumulator': OUT_ACC, 'battery': L(-3, 30)}
NEED = {'solar-panel': [{'steel-plate', 'green'}, {'copper-solar', 'green'}],
        'accumulator': [{'iron-acc', 'battery'}],
        'battery': [{'iron-bat', 'copper-bat'}],
        'sulfuric-acid': [{'sulfur', 'iron-acid'}]}
got = {}
def rules(ins, src, dst):
    sn, dn = src and src['name'], dst and dst['name']
    if sn in ('assembling-machine-3', 'chemical-plant'):
        r = src['recipe']
        if r == 'sulfur':
            return None if dst and tile_of(dst) in reach(b, L(0, 8)) and L(26, 12) in reach(b, tile_of(dst)) else 'sulfur not onto the feed'
        if not dst or trace(b, tile_of(dst))[0][-1] != OUTS[r] and OUTS[r] not in reach(b, tile_of(dst)):
            return f'{r} does not reach its output'
        return None
    if dn not in ('assembling-machine-3', 'chemical-plant'): return f'{sn} -> {dn}'
    its = {k for k, r in R.items() if tile_of(src) in r}
    if its not in NEED[dst['recipe']]: return f'{dst["recipe"]} picks from a belt with {its}'
    got.setdefault(dst['entity_number'], set()).update(its)
b.wire_poles()
rep, belts = validate(b, rules)
for e in b.ents:
    if e['name'] in ('assembling-machine-3', 'chemical-plant') and e['recipe'] in NEED:
        want = set().union(*NEED[e['recipe']])
        assert got.get(e['entity_number']) == want or (e['recipe'] == 'battery' and got.get(e['entity_number']) == {'iron-bat', 'copper-bat'}), \
            (e['recipe'], e['position'], got.get(e['entity_number']))
rep.append('every machine reaches all its ingredients (solar: steel, copper, green; accumulator: iron, battery; '
           'battery: iron, copper; acid: sulfur, iron)')
nets, touch = fluid_networks(b)
assert len(nets) == 3, f'{len(nets)} pipe networks'
net_of = lambda t: next(i for i, n in enumerate(nets) if t in n)
NW, NP = net_of(L(31, 2)), net_of(L(31, 0)); NA = net_of(L(0, 17))
assert len({NW, NP, NA}) == 3
for e in b.ents:
    if e['name'] != 'chemical-plant': continue
    pp = plant_ports(e); ins_t = [t for _, t in pp['input']]; out_t = [t for _, t in pp['output']]
    r = e['recipe']
    if r == 'sulfur': assert net_of(ins_t[0]) == NW and net_of(ins_t[1]) == NP, e['position']
    elif r == 'sulfuric-acid':
        assert all(net_of(t) == NW for t in ins_t) and all(net_of(t) == NA for t in out_t), e['position']
    elif r == 'battery': assert all(net_of(t) == NA for t in ins_t), e['position']
rep.append('fluids: 3 networks (petroleum, water, acid); sulfur box1 water / box2 petroleum; acid plants water in, '
           'acid out; every battery plant on acid')
want_curves = [(5, 46), (5, 84), (7, 5), (7, 30), (7, 78), (7, 89), (33, 10), (33, 15), (33, 35), (33, 46), (35, 11),
               (35, 14), (35, 67), (36, 62), (36, 66), (37, 74), (37, 75), (37, 79), (38, 90)]
assert sorted(belts['curves']) == want_curves, sorted(belts['curves'])
assert sorted(belts['sideloads']) == [(7, 18), (7, 42), (7, 84), (33, 11), (33, 36), (35, 12), (35, 66), (38, 75)], belts['sideloads']
assert sorted(belts['ends']) == [(4, 18), (4, 42), (9, 66), (9, 79), (9, 90), (10, 11), (10, 12), (10, 36)], belts['ends']
rep.append('belts: 19 intended curves; sideloads = 3 output merges, 5 formers (belt1, belt2, M, acid feed, battery trunk); '
           'ends = 2 outputs + 6 row ends')
rep += check_fixed(b, 1, 2)
bp = finish(b, 'Mall - Solar + Accumulators', [('item', 'solar-panel'), ('item', 'accumulator')], corner_list=corners(1, 2))
for l in rep: print(l)
write_outputs(HERE, bp)
render(HERE, bp, px=8, grid=0)
