"""Automation (red) science: 1 full blue belt (45/s) out on the left. 3 cells wide x 1 tall.

Recipe: 1 copper + 1 gear -> 1 pack in 5 s; AM3 1.25 -> 0.25/s per machine. 45/s needs 180; built 192
(3 pairs x 2 rows x 32, lib/sp_rows.py, one mixed belt per pair: copper | gear).
Gears made here: gear 2 iron -> 1 in 0.5 s -> 2.5/s per machine (5 iron/s). 20 gear machines in a vertical
mirrored block (x 118..130, rows 5..34): iron 1 column (x 118) | 2 bulk in | gear machines | 1 bulk out |
gear belt (x 124, flows N) | 1 bulk out | gear machines | 2 bulk in | iron 2 column (x 130).
Each iron belt (45/s) feeds 9 machines' worth -> 22.5 gears/s on one lane of the gear belt; the gear belt
leaves the block at the top (row 3) and turns down the gear column of the rows.
Inputs (right): copper 45/s (blue, row 2), iron 2 x 45/s (blue, rows 35-36).
Frame: top-left roboport center = (0,0). Grid poles at x 52-53 / 102-103 rows 22-23: gaps at j = 15, 31.
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.build import BP, N, E, S, W, validate, trace, tile_of, reach
from lib.cell import corners, finish, check_fixed
from lib.sp_rows import Rows, tier

PACK = 'automation-science-pack'
b = BP(); b.belt_name, b.ug_name = 'express-transport-belt', 'express-underground-belt'
rows = Rows(b, PACK, ['copper-plate', 'iron-gear-wheel'], nj=32, pairs=(8, 20, 32), gaps=(15, 31),
            rates={'copper-plate': 45})
rows.build()
XE = 134
CU = rows.entry(0, XE)

# ---- gear block
FE1, GL, GR, GB, FE2 = 118, 120, 126, 124, 130
NG = 10
for i in range(NG):
    y = 5 + 3 * i
    b.asm(GL, y, 'iron-gear-wheel'); b.asm(GR, y, 'iron-gear-wheel')
    for dy in (0, 1):
        b.inserter(FE1 + 1, y + dy, W, 'bulk-inserter'); b.inserter(FE2 - 1, y + dy, E, 'bulk-inserter')
    b.add('medium-electric-pole', FE1 + 1, y + 2); b.add('medium-electric-pole', FE2 - 1, y + 2)
    b.inserter(GB - 1, y + 1, W, 'bulk-inserter'); b.inserter(GB + 1, y + 1, E, 'bulk-inserter')
    if i % 2 == 0:
        b.add('medium-electric-pole', GB - 1, y + 2); b.add('medium-electric-pole', GB + 1, y + 2)
    else:
        b.add('small-lamp', GB - 1, y + 2)
for y in range(4, 5 + 3 * NG): b.belt(GB, y, N)
b.belt(GB, 3, W)
for x in range(rows.d[1] + 1, GB): b.belt(x, 3, W)
# iron columns
for y in range(5, 35): b.belt(FE1, y, N)
for y in range(5, 35): b.belt(FE2, y, N)
b.belt(FE2, 35, N); b.belt(FE1, 36, N); b.belt(FE1, 35, N)
b.ents = [e for e in b.ents if not (e['name'] == b.belt_name and e['position'] == {'x': FE2 + .5, 'y': 35.5})]
b.belt(FE2, 35, N)
belt, ug = tier(45)
for r, xend in ((35, FE2 + 1), (36, FE1 + 1)):
    for x in range(xend, XE - 2): b.belt(x, r, W)
    b.ug(XE - 2, r, W, 'output'); b.panel(XE - 1, r, 'iron-plate'); b.ug(XE, r, W, 'input')
b.add('medium-electric-pole', 114, 6)                                    # bridge rows <-> gear block
for i, e in enumerate(b.ents): e['entity_number'] = i + 1
IRON = [(XE, 35), (XE, 36)]

# ---- checks
sp_rule = rows.rules()
R_FE = reach(b, IRON[0]) | reach(b, IRON[1])
def rules(ins, src, dst):
    if dst and dst.get('recipe') == 'iron-gear-wheel':
        return None if src and tile_of(src) in R_FE else 'gear machine does not pick iron'
    if src and src.get('recipe') == 'iron-gear-wheel':
        if not dst or (rows.d[1], 3) not in reach(b, tile_of(dst)): return 'gears do not reach the gear column'
        return None
    return sp_rule(ins, src, dst)
b.wire_poles()
rep, belts = validate(b, rules)
rep += rows.check(belts)
assert rows.R['iron-gear-wheel'] <= reach(b, (GB, 34)), 'gear column not fed by the gear belt'
want_curves = rows.curves + [(GB, 3), (FE1, 36), (FE2, 35)]
assert sorted(belts['curves']) == sorted(want_curves), sorted(set(belts['curves']) ^ set(want_curves))
assert sorted(belts['sideloads']) == sorted(rows.sideloads), sorted(set(belts['sideloads']) ^ set(rows.sideloads))
want_ends = rows.ends + [(FE1, 5), (FE2, 5)]
assert sorted(belts['ends']) == sorted(want_ends), sorted(set(belts['ends']) ^ set(want_ends))
rep.append(f'belts: {len(want_curves)} curves, {len(rows.sideloads)} sideloads, {len(want_ends)} ends - all intended '
           '(formers, taps, collectors, gear belt exit, iron turns; iron column tops)')
rep += check_fixed(b, 3, 1)
n = lambda r: sum(e.get('recipe') == r for e in b.ents)
rep.append(f'{n(PACK)} pack machines ({n(PACK) * 0.25:.0f}/s), {n("iron-gear-wheel")} gear machines '
           f'(iron-limited 2 x 22.5 = 45 gears/s)')
bp = finish(b, 'Automation Science', [('item', PACK)], corner_list=corners(3, 1))
for l in rep: print(l)
write_outputs(HERE, bp)
render(HERE, bp, px=5, grid=0)
