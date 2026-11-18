"""Steam power: 150 boilers, 300 steam engines (270 MW at full load). 1 cell wide x 4 cells tall.
All inputs grouped on the right: 12 water pipe-to-ground (two tiles between) + 2 blue coal belts.
Data (2.1.24): boiler 1.8 MW -> 60 steam/s; steam engine 30 steam/s (900 kW) -> 2 per boiler;
offshore pump 1200 water/s; coal 4 MJ -> 0.45 coal/s per boiler.

Cell module (rows r relative to Y = 50k + 2), boilers j at x = 4 + 3j:
  r0 poles | r1..10 engines A | r11..12 boilers A (face N) | r13 fast inserters | r14 coal | r15 fast inserters |
  r16..17 boilers B (face S) | r18..27 engines B | r28 poles | r29..38 engines C | r39..40 boilers C (face N) |
  r41 fast inserters | r42 coal
  Cells 0 and 3: 13 boilers per row (x 4..42, chain inlet tile x=43); cells 1 and 2: 12 (x 4..39, inlet x=40).
Water: inputs at x=47, rows 84 + 3i (i = 0..11), pipe-to-ground facing W (connect from the east with an
  underground pipe). Each input feeds exactly one boiler row (one chain, 780 or 720 water/s, < 1 offshore pump).
  Lines run W, along their own column (x 41..46), W again to the chain inlet - nested so they never meet;
  crossings are pipe-to-ground over pipe-to-ground. Input at row 114 goes straight to cell 2 row A.
Coal: 2 blue belts in at x=50 (rows 96 and 102) -> trunks at x=49 (up / down) -> a splitter per coal row
  (x 48-49) -> underground under the water columns into the row. 33.75/s per trunk.
"""
import sys, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
import lib.bp as LBP
from lib.build import BP, N, E, S, W, VEC, OPP, validate, tile_of, SUPPLY
from lib.cell import check_fixed, finish, corners

RECT = {'boiler': (3, 2), 'steam-engine': (3, 5)}
LBP.SIZES.update({'boiler': (3, 2), 'steam-engine': (3, 5)})
LBP.COLORS.update({'boiler': (170, 90, 60), 'steam-engine': (120, 130, 110)})

class PB(BP):
    def rect(self, name, tx, ty, d):
        w, h = RECT[name]
        if d in (E, W): w, h = h, w
        self.ents.append({'entity_number': len(self.ents) + 1, 'name': name, 'direction': d,
                          'position': {'x': tx + w / 2, 'y': ty + h / 2}})
    def tiles(self, e):
        if e['name'] in RECT:
            w, h = RECT[e['name']]
            if e.get('direction', 0) in (E, W): w, h = h, w
            x0, y0 = e['position']['x'] - w / 2, e['position']['y'] - h / 2
            return [(int(x0) + i, int(y0) + j) for i in range(w) for j in range(h)]
        return super().tiles(e)

NBOIL = {0: 13, 1: 12, 2: 12, 3: 13}
b = PB(); b.belt_name, b.ug_name = 'express-transport-belt', 'express-underground-belt'
CHAINS = {}                                    # (k, row-kind) -> (inlet x, row)
for k in range(4):
    Y = 50 * k + 2; nb = NBOIL[k]
    for j in range(nb):
        x = 4 + 3 * j
        b.rect('steam-engine', x, Y + 1, N); b.rect('steam-engine', x, Y + 6, N)
        b.rect('boiler', x, Y + 11, N)
        b.inserter(x + 1, Y + 13, S); b.inserter(x + 1, Y + 15, N)
        b.rect('boiler', x, Y + 16, S)
        b.rect('steam-engine', x, Y + 18, N); b.rect('steam-engine', x, Y + 23, N)
        b.rect('steam-engine', x, Y + 29, N); b.rect('steam-engine', x, Y + 34, N)
        b.rect('boiler', x, Y + 39, N)
        b.inserter(x + 1, Y + 41, S)
        for r in (13, 15, 41):
            if j % 2 == 0 or j == nb - 1: b.add('medium-electric-pole', x + 2, Y + r)
            elif j in (3, 7, 11): b.add('small-lamp', x + 2, Y + r)
    xe = 4 + 3 * nb                            # chain inlet column (43 or 40)
    for px in range(6, xe, 6):
        b.add('medium-electric-pole', px, Y); b.add('medium-electric-pole', px, Y + 28)
        if px + 3 < xe - 1: b.add('small-lamp', px + 3, Y); b.add('small-lamp', px + 3, Y + 28)
    for r in (6, 22, 35): b.add('medium-electric-pole', xe, Y + r)       # bridges between pole rows
    CHAINS[(k, 'A')] = (xe, Y + 12); CHAINS[(k, 'B')] = (xe, Y + 16); CHAINS[(k, 'C')] = (xe, Y + 40)
    for r in (14, 42):                          # coal rows (fed from the right by the trunk)
        for x in range(4, xe): b.belt(x, Y + r, W)

# ---------------- coal trunks (x=49), splitters (x 48-49), undergrounds into the rows
def drop_belt(x, y):
    b.ents[:] = [e for e in b.ents if not (e['name'] == b.belt_name and tile_of(e) == (x, y))]
COAL_Y = []
def coal_branch(y, k):
    xe = 4 + 3 * NBOIL[k]
    drop_belt(xe - 1, y)
    b.belt(48, y, W); b.ug(47, y, W, 'input'); b.ug(xe - 1, y, W, 'output')
    COAL_Y.append(y)
def run(x, y0, y1, d):
    step = 1 if y1 >= y0 else -1
    for y in range(y0, y1 + step, step): b.belt(x, y, d)
# up trunk: (50,96) -> x=49 north; splitters at rows 95, 67, 45; curve at 16
b.belt(50, 96, W); b.belt(49, 96, N)
b.splitter(48, 95, N); coal_branch(94, 1); b.belt(49, 94, N)
run(49, 93, 68, N)
b.splitter(48, 67, N); coal_branch(66, 1); b.belt(49, 66, N)
run(49, 65, 53, N); b.ug(49, 52, N, 'input'); b.ug(49, 47, N, 'output'); b.belt(49, 46, N)
b.splitter(48, 45, N); coal_branch(44, 0); b.belt(49, 44, N)
run(49, 43, 17, N); b.belt(49, 16, W); coal_branch(16, 0)
# down trunk: (50,102) -> x=49 south; splitters at rows 115, 143, 165; curve at 194
b.belt(50, 102, W); b.belt(49, 102, S)
run(49, 103, 114, S)
b.splitter(48, 115, S); coal_branch(116, 2); b.belt(49, 116, S)
run(49, 117, 142, S)
b.splitter(48, 143, S); coal_branch(144, 2); b.belt(49, 144, S)
run(49, 145, 146, S); b.ug(49, 147, S, 'input'); b.ug(49, 152, S, 'output'); run(49, 153, 164, S)
b.splitter(48, 165, S); coal_branch(166, 3); b.belt(49, 166, S)
run(49, 167, 193, S); b.belt(49, 194, W); coal_branch(194, 3)
COAL_IN = [(50, 96), (50, 102)]
b.panel(51, 95, 'coal') if False else None
b.panel(50, 95, 'coal'); b.panel(50, 103, 'coal')

# ---------------- water lines
occ = {t: e for e in b.ents for t in b.tiles(e)}
def free(t): return t not in occ
def put(e_num_before):
    for e in b.ents[e_num_before:]:
        for t in b.tiles(e):
            assert t not in occ, (t, e['name'], occ[t]['name'])
            occ[t] = e
def segment(tiles, d):
    """tiles in flow order, flow direction d. Pipe-to-ground pairs, surfacing only on free tiles."""
    n = len(tiles)
    if n == 0: return
    if n == 1:
        assert free(tiles[0]), tiles[0]; b.pipe(*tiles[0]); return
    # DP: choose pair (s, e) chains covering 0..n-1, each pair e - s in 1..10, next s = e + 1
    best = {n: []}
    for s in range(n - 1, -1, -1):
        if not free(tiles[s]): continue
        for e in range(min(n - 1, s + 10), s, -1):
            if free(tiles[e]) and (e + 1) in best:
                best[s] = [(s, e)] + best[e + 1]; break
    assert 0 in best, f'no route for segment {tiles[0]}..{tiles[-1]}'
    for s, e in best[0]:
        b.ptg(*tiles[s], OPP[d]); b.ptg(*tiles[e], d)
def hline(y, x0, x1):          # flow W from x0 down to x1
    return [(x, y) for x in range(x0, x1 - 1, -1)]
def vline(x, y0, y1):          # flow from y0 to y1 (exclusive of corners handled by caller)
    st = -1 if y1 < y0 else 1
    return [(x, y) for y in range(y0, y1 + st, st)]
G = [84 + 3 * i for i in range(12)]
# (input row, column or None for direct, chain)
LINES = [(84, 46, (0, 'A')), (87, 45, (0, 'B')), (90, 44, (0, 'C')), (93, 43, (1, 'A')), (96, 42, (1, 'B')),
         (99, 41, (1, 'C')), (102, 42, (2, 'B')), (105, 43, (2, 'C')), (108, 44, (3, 'A')), (111, 45, (3, 'B')),
         (114, None, (2, 'A')), (117, 46, (3, 'C'))]
WATER_IN = []
order = sorted(LINES, key=lambda l: (l[1] is None, -(l[1] or 0)))
for g, c, ch in order:
    n0 = len(b.ents)
    xe, p = CHAINS[ch]
    b.ptg(47, g, W); WATER_IN.append((47, g)); put(n0); n0 = len(b.ents)
    if c is None:
        assert p == g
        segment(hline(g, 46, xe), W); put(n0); continue
    segment(hline(g, 46, c + 1), W); put(n0); n0 = len(b.ents)
    assert free((c, g)); b.pipe(c, g); put(n0); n0 = len(b.ents)
    d = N if p < g else S
    vy0, vy1 = (g - 1, p + 1) if d == N else (g + 1, p - 1)
    segment(vline(c, vy0, vy1), d); put(n0); n0 = len(b.ents)
    assert free((c, p)); b.pipe(c, p); put(n0); n0 = len(b.ents)
    segment(hline(p, c - 1, xe), W); put(n0)
b.panel(47, 83, 'water', 'fluid'); b.panel(47, 118, 'water', 'fluid')
for i, e in enumerate(b.ents): e['entity_number'] = i + 1

# ======================= checks
def rules(ins, src, dst):
    if not src or src['name'] != b.belt_name: return f'picks from {src and src["name"]}'
    if not dst or dst['name'] != 'boiler': return f'drops into {dst and dst["name"]}'
b.wire_poles()
rep, belts = validate(b, rules)
occ = b.occupancy()
poles = [e for e in b.ents if e['name'] in SUPPLY]
for e in b.ents:
    if e['name'] == 'steam-engine':
        assert any(any(abs(tx + .5 - p['position']['x']) < SUPPLY[p['name']] + .5 and abs(ty + .5 - p['position']['y']) < SUPPLY[p['name']] + .5
                       for tx, ty in b.tiles(e)) for p in poles), f'engine at {e["position"]} not on the network'
rep.append('generators: every steam engine inside a pole supply area')

def ports(e):
    n, d = e['name'], e.get('direction', 0)
    cx, cy = e['position']['x'], e['position']['y']
    def P(v, face, kind):
        x, y = v
        for _ in range(d // 4): x, y = -y, x
        return ((math.floor(cx + x), math.floor(cy + y)), (face + d) % 16, kind)
    if n == 'boiler': return [P((-1, .5), W, 'water'), P((1, .5), E, 'water'), P((0, -.5), N, 'steam')]
    if n == 'steam-engine': return [P((0, 2), S, 'steam'), P((0, -2), N, 'steam')]
    if n == 'pipe': t = tile_of(e); return [(t, f, 'any') for f in (N, E, S, W)]
    if n == 'pipe-to-ground': return [(tile_of(e), d, 'any')]
    return []
port_at = {}
for e in b.ents:
    for t, f, kind in ports(e): port_at.setdefault((t, f), []).append((e, kind))
adj = {e['entity_number']: set() for e in b.ents if ports(e)}
for e in b.ents:
    for t, f, kind in ports(e):
        vx, vy = VEC[f]; nt = (t[0] + vx, t[1] + vy)
        for o, k2 in port_at.get((nt, OPP[f]), []):
            assert {kind, k2} != {'water', 'steam'}, (e['position'], o['position'])
            if kind == 'steam' and k2 == 'any': raise AssertionError(f'steam leaks into a pipe at {o["position"]}')
            adj[e['entity_number']].add(o['entity_number'])
    if e['name'] == 'pipe-to-ground':                                  # underground partner
        vx, vy = VEC[OPP[e['direction']]]; t = tile_of(e)
        for s in range(1, 11):
            o = occ.get((t[0] + vx * s, t[1] + vy * s))
            if o and o['name'] == 'pipe-to-ground' and o['direction'] in (e['direction'], OPP[e['direction']]):
                assert o['direction'] == OPP[e['direction']], f'pipe-to-ground at {t}: next one faces the same way'
                adj[e['entity_number']].add(o['entity_number']); break
        else:
            assert t in set(WATER_IN), f'pipe-to-ground at {t} has no partner'
for a, s in list(adj.items()):
    for o in s: adj.setdefault(o, set()).add(a)
byid = {e['entity_number']: e for e in b.ents}
seen, water = set(), []
for e in b.ents:
    if e['entity_number'] in seen or e['name'] not in ('boiler', 'pipe-to-ground', 'pipe'): continue
    grp, st = set(), [e['entity_number']]
    while st:
        u = st.pop()
        if u in grp: continue
        grp.add(u); st += [v for v in adj.get(u, ()) if byid[v]['name'] != 'steam-engine']
    seen |= grp; water.append(grp)
assert len(water) == 12, len(water)
for g in water:
    nb = sum(byid[u]['name'] == 'boiler' for u in g)
    ins = [tile_of(byid[u]) for u in g if tile_of(byid[u]) in set(WATER_IN) and byid[u]['name'] == 'pipe-to-ground']
    assert len(ins) == 1 and nb in (12, 13), (nb, ins)
rep.append('water: 12 separate networks, each = one input + one row of 12 or 13 boilers (720-780/s, < 1 offshore pump)')
for e in b.ents:
    if e['name'] != 'boiler': continue
    e1 = [o for o in adj[e['entity_number']] if byid[o]['name'] == 'steam-engine']
    assert len(e1) == 1, e['position']
    e2 = [o for o in adj[e1[0]] if byid[o]['name'] == 'steam-engine']
    assert len(e2) == 1 and adj[e2[0]] == {e1[0]}, e['position']
rep.append('steam: every boiler feeds exactly 2 engines in a straight column')
rows = sorted(y for _, y in WATER_IN)
assert all(b2 - a == 3 for a, b2 in zip(rows, rows[1:])) and {x for x, _ in WATER_IN} == {47}
rep.append(f'water inputs: 12 pipe-to-ground at x=47, rows {rows[0]}..{rows[-1]}, two tiles between each')
assert sorted(belts['ends']) == sorted((4, y) for y in COAL_Y), sorted(belts['ends'])
assert not belts['sideloads'], belts['sideloads']
from lib.build import reach
for y in COAL_Y:
    assert (4, y) in reach(b, COAL_IN[0]) or (4, y) in reach(b, COAL_IN[1]), y
rep.append(f'coal: 2 blue belts in (x=50, rows 96 and 102), 6 splitters, every coal row fed; no sideloads')
rep += check_fixed(b, 1, 4) if False else []
# grid: no tile on a grid roboport / big pole / lamp (the coal trunk uses the grid line at x 48-50)
from lib import adapt
robos = [(0, 50 * k) for k in range(5)] + [(50, 50 * k) for k in range(5)]
gtiles, gpoles = adapt.world_grid(robos)
tiles = {t for e in b.ents for t in b.tiles(e)}
hit = tiles & gtiles
assert not hit, sorted(hit)[:5]
assert all(4 <= x <= 51 and 2 <= y <= 197 for x, y in tiles), 'outside 1x4 cells + right grid line'
d = min(math.dist((e['position']['x'], e['position']['y']), g) for e in b.ents if e['name'] == 'medium-electric-pole' for g in gpoles)
assert d <= 9
rep.append(f'grid: 1x4 cells (coal trunk on the right grid line x 48-50), no collision with grid roboports/poles/lamps, grid link {d:.1f}')
n = lambda nm: sum(e['name'] == nm for e in b.ents)
rep.append(f'{n("boiler")} boilers, {n("steam-engine")} steam engines -> {n("boiler") * 1.8:.1f} MW; '
           f'coal {n("boiler") * 0.45:.2f}/s; water {n("boiler") * 60}/s')
bp = finish(b, 'Steam Power 270 MW', [('item', 'boiler'), ('item', 'steam-engine')], corner_list=corners(1, 4))
for l in rep: print(l)
write_outputs(HERE, bp)
render(HERE, bp, px=4, grid=0)
