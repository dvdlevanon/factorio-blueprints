"""Low density structure: 184 assembling machine 3 -> 1 yellow belt (15/s), leaving WEST. 2x2 cells.
Frame: cell coordinates of the 2x2 block (top-left roboport center = (0,0)).

Two blocks (top cell row at y=18, bottom at y=54), each = 2 pairs of rows, 23 machines per row:
  r+0   out belt -> W (shared with the pair above/below)
  r+1   out inserters (row A, pick S)                       r+13 out inserters (row B, pick N)
  r+2..4  machines A                                        r+10..12 machines B
  r+5   fast (copper, x0) + long-handed (plastic/steel, x0+1), pick S;  r+9 the same, pick N
  r+6   copper A -> W     r+7 plastic|steel -> W     r+8 copper B -> W
Machine j at x0 = 7 + 3j (+2 from j = 15: gap for the grid pole at x 52..53).
East (x 78..81), per pair: plastic in on row r+4, curves S at x=78 and sideloads onto the PS belt's
north lane; steel in on row r+10, curves N, south lane; copper A/B in on rows r+6/r+8, underground
under x=78. Each pair: 2 copper belts, 1 plastic, 1 steel.
West: out belts sideload onto collectors at x=5 (top flows S, bottom flows N); both sideload into the
yellow output at (5,49) on the horizontal grid line (one lane each), leaving W at x=4.
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.build import BP, N, E, S, W, validate, trace, tile_of, reach
from lib.cell import check_fixed, finish, corners

J = 23
RECIPE = 'low-density-structure'
X0, GAPJ, GAPW = 7, 15, 2
XS = 78                      # plastic/steel merge column
XI = 81                      # input entry column (and panels)
COL = 5                      # collectors
OUTY = 49                    # output row (grid line band)
BLOCKS = (18, 54)
ax = lambda j: X0 + 3 * j + (GAPW if j >= GAPJ else 0)
assert ax(J - 1) + 2 == XS - 1

b = BP(); b.belt_name, b.ug_name = 'express-transport-belt', 'express-underground-belt'
out_rows, pairs = [], []
for by in BLOCKS:
    for p in range(2):
        r = by + 14 * p; pairs.append(r)
        for j in range(J):
            x = ax(j)
            b.asm(x, r + 2, RECIPE); b.asm(x, r + 10, RECIPE)
            b.inserter(x + 1, r + 1, S); b.inserter(x + 1, r + 13, N)                       # out
            b.inserter(x, r + 5, S); b.inserter(x + 1, r + 5, S, 'long-handed-inserter')     # in A
            b.inserter(x, r + 9, N); b.inserter(x + 1, r + 9, N, 'long-handed-inserter')     # in B
            for y in (r + 1, r + 5, r + 9, r + 13):
                if j % 2 == 0 or j == J - 1 or j == GAPJ: b.add('medium-electric-pole', x + 2, y)
            for y in (r + 1, r + 13):
                if j in (1, 7, 13, 19): b.add('small-lamp', x, y)
        # belts
        for y in (r + 6, r + 8):
            for x in range(X0, XS - 1): b.belt(x, y, W)
            b.ug(XS - 1, y, W, 'output'); b.ug(XS + 1, y, W, 'input')
            for x in range(XS + 2, XI + 1): b.belt(x, y, W)
        for x in range(X0, XS + 1): b.belt(x, r + 7, W)                                     # PS start at XS
        for x in range(XS + 1, XI + 1): b.belt(x, r + 4, W); b.belt(x, r + 10, W)
        b.belt(XS, r + 4, S); b.belt(XS, r + 5, S); b.belt(XS, r + 6, S)                     # plastic
        b.belt(XS, r + 10, N); b.belt(XS, r + 9, N); b.belt(XS, r + 8, N)                    # steel
        b.panel(XI, r + 3, 'plastic-bar'); b.panel(XI, r + 5, 'copper-plate')
        b.panel(XI, r + 9, 'copper-plate'); b.panel(XI, r + 11, 'steel-plate')
    for k in range(3):
        y = by + 14 * k; out_rows.append(y)
        for x in range(COL + 1, ax(J - 1) + 3): b.belt(x, y, W)
# collectors
top, bot = out_rows[:3], out_rows[3:]
for y in range(top[0], OUTY): b.belt(COL, y, S)
for y in range(OUTY + 1, bot[-1] + 1): b.belt(COL, y, N)
b.belt_name = 'transport-belt'
b.belt(COL, OUTY, W); b.belt(COL - 1, OUTY, W)
b.belt_name = 'express-transport-belt'
b.panel(COL - 1, OUTY - 1, RECIPE)
OUT = (COL - 1, OUTY)
b.add('medium-electric-pole', 9, 50)                                                        # links the two blocks

# ---- checks ----
def rules(ins, src, dst):
    y = tile_of(ins)[1]; rel = [(y - r) for r in pairs if 0 <= y - r <= 14]
    if src and src['name'] == 'assembling-machine-3':
        if ins['name'] != 'fast-inserter': return 'out inserter must be fast'
        if not dst or dst['name'] != b.belt_name: return f'drops on {dst and dst["name"]}'
        if trace(b, tile_of(dst))[0][-1] != OUT: return 'out belt does not reach the output'
        return None
    if not dst or dst['name'] != 'assembling-machine-3': return f'drops into {dst and dst["name"]}'
    if not src or src['name'] not in (b.belt_name, b.ug_name): return f'picks from {src and src["name"]}'
    st = tile_of(src)
    want = 'copper' if ins['name'] == 'fast-inserter' else 'ps'
    r = next(r for r in pairs if r + 5 <= st[1] <= r + 9)
    if want == 'copper':
        if st[1] not in (r + 6, r + 8) or st not in reach(b, (XI, st[1])): return 'fast does not pick copper'
    else:
        if st[1] != r + 7 or st not in reach(b, (XI, r + 4)) or st not in reach(b, (XI, r + 10)):
            return 'long-handed does not pick the plastic|steel belt'
b.wire_poles()
rep, belts = validate(b, rules)
want_side = [(COL, OUTY)] + [(COL, y) for y in top[1:] + bot[:-1]] + [(XS, r + 7) for r in pairs]
assert sorted(belts['sideloads']) == sorted(want_side), sorted(belts['sideloads'])
want_curves = [(COL, top[0]), (COL, bot[-1])] + [(XS, r + d) for r in pairs for d in (4, 10)]
assert sorted(belts['curves']) == sorted(want_curves), sorted(belts['curves'])
want_ends = [OUT] + [(X0, r + d) for r in pairs for d in (6, 7, 8)]
assert sorted(belts['ends']) == sorted(want_ends), sorted(belts['ends'])
rep.append('belts: sideloads = 4 plastic|steel merges, 4 collector joins, output merge; curves = collector tops/'
           'bottoms + plastic/steel turns; ends = output + row belt ends')
# lanes: plastic sideloads from the north, steel from the south
for r in pairs:
    assert belts and (XS, r + 6) in reach(b, (XI, r + 4)) and (XS, r + 8) in reach(b, (XI, r + 10))
rep += check_fixed(b, 2, 2)
asms = sum(e['name'] == 'assembling-machine-3' for e in b.ents)
rep.append(f'{asms} assemblers -> {asms * 1.25 / 15:.2f} LDS/s capacity')
bp = finish(b, 'Low Density Structure', [('item', RECIPE)], corner_list=corners(2, 2))
for l in rep: print(l)
write_outputs(HERE, bp)
render(HERE, bp, px=5, grid=0)
