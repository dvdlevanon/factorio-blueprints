"""Green circuits: 2 full blue belts (90/s), 2 cells side by side, leaving WEST.
Inputs from the EAST: iron 2 blue belts (90/s), copper 3 blue belts (135/s). All exactly full.

Unit (19 wide) = C G C G C, cable (C) -> circuit (G) by direct insertion, 3:2 (5 circuits/s per unit):
  C0 | 2 bulk | G0 | 1 bulk | C1 | 1 bulk | G1 | 2 bulk | C2
Row = 3 units (copper on one lane of the row's mixed belt caps a row at 3 units = 22.5/s copper).
Units at x 14, 33, 54 (2-column gap at x 52-53 for the grid's big pole at (53,23)).
3 mirrored pairs (6 rows, 18 units = 90/s): pair p at yb = 5, 19, 33:
  yb mixed (row A) | A machines yb+1..yb+5 | yb+6 out (A south lane, B north lane) | B | yb+12 mixed (row B)
  spacer rows 18 and 32 (iron feeders), 4 and 46 (iron feeders).
East, row formers at E = 77 / 75 / 73 (pair 1/2/3): copper from inside the pair (one copper belt per pair,
  entering on the out row yb+6 -> splitter -> up to row A, down to row B), iron from outside (spacer rows).
  Iron 1 (row 18) -> splitter -> row 4 (pair 1 A) + splitter -> row 18 (pair 2 A) / row 20 (pair 1 B).
  Iron 2 (row 33) -> splitter -> row 46 (pair 3 B) + splitter -> row 32 (pair 3 A) / row 34 (pair 2 B).
West: pair 2's out belt splits in two; each half merges with pair 1 / pair 3 in a splitter used as a
  lane-preserving merger (one output) -> output belts on rows 20 and 28 (22.5 + 22.5 each).
Coordinates: 2-cell frame, top-left roboport center = (0,0).
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.build import BP, N, E, S, W, validate, trace, tile_of, reach
from lib.cell import check_fixed, finish, corners

UX = (14, 33, 54)            # unit x positions (gap 52-53)
X0 = UX[0]
b = BP(); b.belt_name, b.ug_name = 'express-transport-belt', 'express-underground-belt'
BULK = 'bulk-inserter'
toward = {1: N, -1: S}       # pickup direction for side inserters of a row with sign s

def row(y_in, s):
    """Machines + inserters of one row. y_in = mixed belt row, s = +1 (machines below) or -1 (above)."""
    top = min(y_in + 2 * s, y_in + 4 * s)
    a, m, bb = y_in + 2 * s, y_in + 3 * s, y_in + 4 * s
    for u, ux in enumerate(UX):
        for i, (dx, rec) in enumerate(((0, 'copper-cable'), (4, 'electronic-circuit'), (8, 'copper-cable'),
                                        (12, 'electronic-circuit'), (16, 'copper-cable'))):
            b.asm(ux + dx, top, rec)
            b.inserter(ux + dx + 1, y_in + s, toward[s], BULK)              # copper -> C / iron -> G
            if rec == 'electronic-circuit':
                b.inserter(ux + dx + 1, y_in + 5 * s, toward[s], BULK)      # G -> output belt
        b.inserter(ux + 3, a, W, BULK); b.add('medium-electric-pole', ux + 3, m); b.inserter(ux + 3, bb, W, BULK)
        b.inserter(ux + 7, a, E, BULK); b.add('medium-electric-pole', ux + 7, m)
        if u % 2 == 0: b.add('small-lamp', ux + 7, bb)
        b.inserter(ux + 11, a, W, BULK); b.add('medium-electric-pole', ux + 11, m)
        b.inserter(ux + 15, a, E, BULK); b.add('medium-electric-pole', ux + 15, m); b.inserter(ux + 15, bb, E, BULK)


G_LAST = UX[-1] + 13                                                     # east-most G output inserter
PAIRS = (5, 19, 33)
EP = {5: 77, 19: 75, 33: 73}                                             # former column per pair
ROWS = []
for yb in PAIRS:
    e = EP[yb]
    row(yb, 1); row(yb + 12, -1)
    ROWS += [(yb, e), (yb + 12, e)]
    for y in (yb, yb + 12):
        for x in range(X0, e + 1): b.belt(x, y, W)                       # mixed belt, former at e
    for x in range(X0 - 1, G_LAST + 1): b.belt(x, yb + 6, W)             # out belt
    # copper: entry on row yb+6 -> splitter at e+1 -> up to row A, down to row B
    b.splitter(e + 1, yb + 5, W)
    for y in range(yb + 1, yb + 6): b.belt(e, y, N)
    for y in range(yb + 6, yb + 12): b.belt(e, y, S)
XE = 87
CU = [(XE, yb + 6) for yb in PAIRS]
for (x, y), yb in zip(CU, PAIRS):
    for xx in range(EP[yb] + 2, XE + 1):
        if not (xx == 83 and y == 11) and not (xx == 83 and y == 39): b.belt(xx, y, W)
    b.panel(XE, y - 1, 'copper-plate')
# column-83 iron undergrounds cross copper rows 11 and 39; the copper belt continues over them
b.belt(83, 11, W); b.belt(83, 39, W)
# ---- iron 1: rows 4 (-> 77,5), 18 (-> 75,19), 20 (-> 77,17)
FE1 = (XE, 18)
for x in (85, 86, 87): b.belt(x, 18, W)
b.splitter(84, 17, W)
b.belt(83, 17, N)
for y in range(13, 17): b.belt(83, y, N)
b.ug(83, 12, N, 'input'); b.ug(83, 10, N, 'output')
for y in range(5, 10): b.belt(83, y, N)
b.belt(83, 4, W)
for x in range(78, 83): b.belt(x, 4, W)
b.belt(77, 4, S)
b.belt(83, 18, W); b.splitter(82, 18, W)
for x in (81, 80, 79): b.belt(x, 18, W)
b.ug(78, 18, W, 'input'); b.ug(76, 18, W, 'output'); b.belt(75, 18, S)
b.belt(81, 19, S); b.belt(81, 20, W)
for x in (80, 79, 78): b.belt(x, 20, W)
b.belt(77, 20, N); b.belt(77, 19, N); b.belt(77, 18, N)
b.panel(XE, 17, 'iron-plate')
# ---- iron 2: rows 46 (-> 73,45), 32 (-> 73,33), 34 (-> 75,31)
FE2 = (XE, 33)
for x in (85, 86, 87): b.belt(x, 33, W)
b.splitter(84, 33, W)
b.belt(83, 34, S)
for y in range(35, 38): b.belt(83, y, S)
b.ug(83, 38, S, 'input'); b.ug(83, 40, S, 'output')
for y in range(41, 46): b.belt(83, y, S)
b.belt(83, 46, W)
for x in range(74, 83): b.belt(x, 46, W)
b.belt(73, 46, N)
b.belt(83, 33, W); b.splitter(82, 32, W)
for x in range(77, 82): b.belt(x, 32, W)
b.ug(76, 32, W, 'input'); b.ug(74, 32, W, 'output'); b.belt(73, 32, S)
b.belt(81, 33, S); b.belt(81, 34, W)
for x in range(76, 81): b.belt(x, 34, W)
b.belt(75, 34, N); b.belt(75, 33, N); b.belt(75, 32, N)
b.panel(XE, 32, 'iron-plate')
# ---- west: outputs
for x in (12, 11): b.belt(x, 11, W); b.belt(x, 39, W)
b.belt(10, 11, S)
for y in range(12, 20): b.belt(10, y, S)
b.belt(10, 20, W)
b.belt(10, 39, N)
for y in range(29, 39): b.belt(10, y, N)
b.belt(10, 28, W)
b.splitter(12, 24, W)                                                    # pair 2 split
b.belt(11, 24, N); b.belt(11, 23, N); b.belt(11, 22, N); b.belt(11, 21, W); b.belt(10, 21, W)
b.belt(11, 25, S); b.belt(11, 26, S); b.belt(11, 27, W); b.belt(10, 27, W)
b.splitter(9, 20, W); b.splitter(9, 27, W)                               # mergers (one output each)
for x in range(4, 9): b.belt(x, 20, W); b.belt(x, 28, W)
OUTS = [(4, 20), (4, 28)]
b.panel(4, 19, 'electronic-circuit'); b.panel(4, 29, 'electronic-circuit')

# ---- checks ----
R_CU = set().union(*(reach(b, t) for t in CU)); R_FE = reach(b, FE1) | reach(b, FE2)
assert not set(OUTS) & (R_CU | R_FE), 'an input reaches an output'
reach_cache = {}
def rch(t):
    if t not in reach_cache: reach_cache[t] = reach(b, t)
    return reach_cache[t]
def rules(ins, src, dst):
    sn, dn = src and src['name'], dst and dst['name']
    if sn == b.belt_name and dn == 'assembling-machine-3':
        t = tile_of(src)
        need = R_CU if dst['recipe'] == 'copper-cable' else R_FE
        if t not in need: return f'{dst["recipe"]} picks from a belt without its ingredient'
        if set(OUTS) & rch(t): return 'input belt reaches an output'
    elif sn == 'assembling-machine-3' and dn == 'assembling-machine-3':
        if (src['recipe'], dst['recipe']) != ('copper-cable', 'electronic-circuit'): return 'asm -> asm not cable -> circuit'
    elif sn == 'assembling-machine-3' and dn == b.belt_name:
        if src['recipe'] != 'electronic-circuit': return 'cable onto a belt'
        if not set(OUTS) & rch(tile_of(dst)) or tile_of(dst) in R_CU | R_FE: return 'circuits not on an output belt'
    else:
        return f'{sn} -> {dn}'
b.wire_poles()
rep, belts = validate(b, rules)
formers = [(e, y) for y, e in ROWS]
for t in formers:
    assert t in R_CU and t in R_FE, f'row former {t} misses copper or iron'
    for cu in CU:
        pass
# each copper belt feeds exactly its own pair; each iron belt feeds 3 rows
for (x, y), yb in zip(CU, PAIRS):
    got = [t for t in formers if t in reach(b, (x, y))]
    assert got == [(EP[yb], yb), (EP[yb], yb + 12)], (y, got)
fe1 = [t for t in formers if t in reach(b, FE1)]; fe2 = [t for t in formers if t in reach(b, FE2)]
assert len(fe1) == 3 and len(fe2) == 3 and not set(fe1) & set(fe2), (fe1, fe2)
assert sorted(belts['sideloads']) == sorted(formers), sorted(belts['sideloads'])
merger_dead = [(9, 21), (9, 27)]                                         # mergers' unused outputs
assert sorted(belts['ends']) == sorted(OUTS + [(X0, y) for y, _ in ROWS] + merger_dead), sorted(belts['ends'])
# each output gets one outer pair + one half of pair 2
for o, outer in zip(OUTS, (11, 39)):
    assert o in reach(b, (G_LAST, outer)) and o in reach(b, (G_LAST, 25))
    other = 39 if outer == 11 else 11
    assert o not in reach(b, (G_LAST, other))
rep.append('belts: sideloads = 6 row formers only (copper one side, iron the other); ends = 2 outputs + 6 row '
           'ends + 2 merger splitters\' unused outputs; each copper belt feeds its pair, each iron belt 3 rows; '
           'output 1 = pair 1 + half pair 2, output 2 = pair 3 + half pair 2; inputs never reach an output')
asms = [e for e in b.ents if e['name'] == 'assembling-machine-3']
nc = sum(e['recipe'] == 'copper-cable' for e in asms); ng = len(asms) - nc
rep.append(f'ratios: {nc} cable + {ng} circuit assemblers -> {ng * 2.5:.0f}/s circuits; copper lane per row '
           f'{3 * 7.5}/s (exactly full)')
want_curves = [(10, 11), (10, 20), (10, 28), (10, 39), (11, 21), (11, 24), (11, 25), (11, 27),   # west routing
               (73, 32), (73, 46), (75, 18), (75, 34), (77, 4), (77, 20),                  # iron feeders into formers
               (73, 38), (73, 39), (75, 24), (75, 25), (77, 10), (77, 11),                 # copper splitter outputs
               (81, 19), (81, 20), (81, 33), (81, 34), (83, 4), (83, 17), (83, 34), (83, 46)]  # iron distribution
assert sorted(belts['curves']) == sorted(want_curves), sorted(belts['curves'])
rep.append(f'curves: all {len(want_curves)} intended (west routing, feeders, splitter outputs)')
rep += check_fixed(b, 2, 1)
bp = finish(b, 'Green Circuit', [('item', 'electronic-circuit')], corner_list=corners(2, 1))
for l in rep: print(l)
write_outputs(HERE, bp)
render(HERE, bp, px=8, grid=0)
