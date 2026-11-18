"""Flying robot frames: one full YELLOW belt (15/s) out on the left. 4 cells wide x 1 cell tall.

Recipe: 1 electric engine + 2 battery + 1 steel + 3 green, 20 s; AM3 1.25 -> 0.0625/s per asm.
15/s needs 240; built 264 = 3 pairs x 2 rows x 44 (16.5/s).
Inputs (right, top rows 2-5): electric engine 15/s, battery 30/s, green 45/s (1 full blue, the limit), steel 15/s.

Pair p at yb = 8, 21, 34 (rows relative to yb):
  0 out belt -> W (shared with the pair above) | 1 out inserters | 2..4 machines (row A) | 5 fast + long
  6 A belt (engine | battery) -> W | 7 B belt (green | steel) -> W
  8 fast + long | 9..11 machines (row B) | 12 out inserters | 13 out belt (= next pair's 0)
AB side: fast picks the near belt, long-handed the far one (each picks what it needs from both lanes).
Machine j at x = 7 + 3j, +2 from j = 15 and +2 more from j = 31 (gaps for the grid poles at x 52-53 and
102-103, which sit on rows 22-23 = pair 2's out inserters and machines).
East, per pair: A forms at (155, yb+2) facing S (battery from the east on row yb+2, engine from the west,
arriving on row yb+1), curves W into row yb+6; B forms at (157, yb+4) (steel from the east on row yb+4,
green from the west via row yb+3), curves W into row yb+7.
Distribution: each input turns S into its own column D = 160/163/166/169 (engine, battery, green, steel);
a splitter per column at pairs 1 and 2 sends a share W on the pair's feed row (underground under the
columns to its west), pair 3 takes the rest by a curve. Back-pressure gives each pair a third.
Output: out rows 8, 21 -> top collector at x=5 flowing S; 34, 47 -> bottom collector flowing N; both
sideload the yellow output (5,27) from either side (one lane each), leaving W at x=4.
Frame: top-left roboport center = (0,0).
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.build import BP, N, E, S, W, validate, trace, tile_of, reach
from lib.cell import corners, finish, check_fixed

RECIPE = 'flying-robot-frame'
LONG = 'long-handed-inserter'
X0, NJ = 7, 44
PAIRS = (8, 21, 34)
XA, XB = 155, 157
D = (160, 163, 166, 169)
ITEMS = ('electric-engine-unit', 'battery', 'electronic-circuit', 'steel-plate')
FEED = (1, 2, 3, 4)                    # feed row offset per input
XE = 175
COL, YO = 5, 27
GAPS = (15, 31)
ax = lambda j: X0 + 3 * j + 2 * sum(j >= g for g in GAPS)

b = BP(); b.belt_name, b.ug_name = 'express-transport-belt', 'express-underground-belt'
for yb in PAIRS:
    for top, ab, outr, pick_ab, pick_out in ((yb + 2, yb + 5, yb + 1, S, S), (yb + 9, yb + 8, yb + 12, N, N)):
        for j in range(NJ):
            x = ax(j)
            b.asm(x, top, RECIPE)
            b.inserter(x, ab, pick_ab); b.inserter(x + 1, ab, pick_ab, LONG)
            b.inserter(x + 1, outr, pick_out)
            if j % 2 == 0 or j in GAPS:
                b.add('medium-electric-pole', x + 2, ab); b.add('medium-electric-pole', x + 2, outr)
            elif j % 4 == 3:
                b.add('small-lamp', x + 2, ab)
    # formers + A/B rows
    b.belt(XA, yb + 2, S)
    for y in range(yb + 3, yb + 6): b.belt(XA, y, S)
    for x in range(X0, XA + 1): b.belt(x, yb + 6, W)
    b.belt(XB, yb + 4, S); b.belt(XB, yb + 5, S); b.belt(XB, yb + 6, S)
    for x in range(X0, XB + 1): b.belt(x, yb + 7, W)
    # feed rows: engine (west side of A), battery (east of A), green (west of B), steel (east of B)
    for x in range(XA - 1, D[0] - 2): b.belt(x, yb + 1, W)
    b.belt(XA - 1, yb + 2, E)
    # replace the west end tile of the engine row with the turn
    b.ents = [e for e in b.ents if not (e['name'] == b.belt_name and (e['position']['x'], e['position']['y']) == (XA - 1 + .5, yb + 1 + .5))]
    b.belt(XA - 1, yb + 1, S)
    for x in range(XA + 1, D[0] - 2): b.belt(x, yb + 2, W)
    for x in range(XB, D[0] - 2): b.belt(x, yb + 3, W)
    b.ents = [e for e in b.ents if not (e['name'] == b.belt_name and (e['position']['x'], e['position']['y']) == (XB - 1 + .5, yb + 3 + .5))]
    b.belt(XB - 1, yb + 3, S); b.belt(XB - 1, yb + 4, E)
    for x in range(XB + 1, D[0] - 2): b.belt(x, yb + 4, W)
    # column taps
    last = yb == PAIRS[-1]
    for k, f in enumerate(FEED):
        y = yb + f; dk = D[k]
        if not last:
            b.splitter(dk - 1, y - 1, S); b.belt(dk - 1, y, W); b.belt(dk, y, S)
        else:
            b.belt(dk, y, W); b.belt(dk - 1, y, W)
        if k == 0: b.belt(D[0] - 2, y, W)
        else: b.ug(dk - 2, y, W, 'input'); b.ug(D[0] - 2, y, W, 'output')
# renumber after removals
for i, e in enumerate(b.ents): e['entity_number'] = i + 1
# columns between taps, entries on rows 2..5
for k, f in enumerate(FEED):
    dk, r = D[k], 2 + k
    b.belt(dk, r, S)
    stops = [yb + f - 1 for yb in PAIRS[:-1]]
    seg_starts = [r + 1] + [s + 2 for s in stops]
    seg_ends = stops + [PAIRS[-1] + f]
    for s0, s1 in zip(seg_starts, seg_ends):
        for yy in range(s0, s1): b.belt(dk, yy, S)
    for x in range(dk + 1, XE - 2): b.belt(x, r, W)
    b.ug(XE - 2, r, W, 'output'); b.panel(XE - 1, r, ITEMS[k]); b.ug(XE, r, W, 'input')
ENTRIES = [(XE, 2 + k) for k in range(4)]
# output
OUT_ROWS = [PAIRS[0], PAIRS[1], PAIRS[2], PAIRS[2] + 13]
for y in OUT_ROWS:
    for x in range(COL + 1, ax(NJ - 1) + 2): b.belt(x, y, W)
b.belt(COL, OUT_ROWS[0], S)
for y in range(OUT_ROWS[0] + 1, YO): b.belt(COL, y, S)
b.belt(COL, OUT_ROWS[-1], N)
for y in range(YO + 1, OUT_ROWS[-1]): b.belt(COL, y, N)
b.belt_name = 'transport-belt'
b.belt(COL, YO, W); b.belt(COL - 1, YO, W)
b.belt_name = 'express-transport-belt'
b.panel(COL - 1, YO - 1, RECIPE)
OUT = (COL - 1, YO)
for i, e in enumerate(b.ents): e['entity_number'] = i + 1

# ---- checks ----
R = {it: reach(b, t) for it, t in zip(ITEMS, ENTRIES)}
assert not any(OUT in r for r in R.values()), 'an input reaches the output'
def items_at(t): return {it for it, r in R.items() if t in r}
got = {}
def rules(ins, src, dst):
    sn, dn = src and src['name'], dst and dst['name']
    if sn == 'assembling-machine-3':
        if dn != b.belt_name or trace(b, tile_of(dst))[0][-1] != OUT: return 'frame does not reach the output'
        return None
    if dn != 'assembling-machine-3': return f'drops into {dn}'
    its = items_at(tile_of(src))
    want = {ITEMS[0], ITEMS[1]} if its == {ITEMS[0], ITEMS[1]} else {ITEMS[2], ITEMS[3]}
    if its != want: return f'picks from a belt with {its}'
    got.setdefault(dst['entity_number'], set()).update(its)
b.wire_poles()
rep, belts = validate(b, rules)
asms = [e for e in b.ents if e['name'] == 'assembling-machine-3']
assert all(got.get(e['entity_number']) == set(ITEMS) for e in asms), 'a machine misses an ingredient'
rep.append(f'every one of {len(asms)} machines reaches all 4 ingredients (A and B belts)')
formers = [(XA, yb + 2) for yb in PAIRS] + [(XB, yb + 4) for yb in PAIRS]
for (x, y) in formers:
    its = items_at((x, y))
    assert its in ({ITEMS[0], ITEMS[1]}, {ITEMS[2], ITEMS[3]}), its
for k, (it, r) in enumerate(R.items()):
    n = [t for t in formers if t in r]
    assert len(n) == 3, (it, n)
want_side = formers + [(COL, YO), (COL, OUT_ROWS[1]), (COL, OUT_ROWS[2])]
assert sorted(belts['sideloads']) == sorted(want_side), sorted(belts['sideloads'])
want_ends = [OUT] + [(X0, yb + d) for yb in PAIRS for d in (6, 7)]
assert sorted(belts['ends']) == sorted(want_ends), sorted(belts['ends'])
want_curves = [(COL, OUT_ROWS[0]), (COL, OUT_ROWS[-1])]
for yb in PAIRS:
    want_curves += [(XA - 1, yb + 1), (XA - 1, yb + 2), (XA, yb + 6), (XB - 1, yb + 3), (XB - 1, yb + 4), (XB, yb + 7)]
    for k, f in enumerate(FEED):
        want_curves.append((D[k] - 1, yb + f) if yb != PAIRS[-1] else (D[k], yb + f))
want_curves += [(D[k], 2 + k) for k in range(4)]
assert sorted(belts['curves']) == sorted(want_curves), sorted(set(belts['curves']) ^ set(want_curves))
rep.append(f'curves: all {len(want_curves)} intended (formers, feeds, splitter outputs, column entries, collectors)')
rep.append('belts: sideloads = 6 formers (2 ingredients each, opposite sides) + 2 collector joins + output merge; '
           'ends = output + 6 A/B row ends; each input reaches exactly its 3 formers')
rep += check_fixed(b, 4, 1)
rep.append(f'{len(asms)} machines -> {len(asms) * 0.0625:.2f}/s capacity (yellow output caps at 15)')
bp = finish(b, 'Flying Robot Frame', [('item', RECIPE)], corner_list=corners(4, 1))
for l in rep: print(l)
write_outputs(HERE, bp)
render(HERE, bp, px=5, grid=0)
