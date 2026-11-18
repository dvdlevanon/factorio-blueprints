"""Steam power: 150 boilers, 300 steam engines (270 MW at full load). 4 cells wide x 1 cell tall.
Water enters on the WEST edge (11 pipe-to-ground, two tiles between), coal on the EAST edge (2 blue belts).
Everything sits inside the cell interiors; only underground pipes/belts and the 2 coal rows cross grid lines.
Data (2.1.24): boiler 1.8 MW -> 60 steam/s; steam engine 30 steam/s (900 kW) -> 2 per boiler;
offshore pump 1200 water/s; coal 4 MJ -> 0.45 coal/s per boiler.

Rows (same in every cell, y absolute): 2 poles | 3..12 engines A | 13..14 boilers A (face N, water row 14) |
  15 fast inserters A | 16 coal A|B | 17 fast inserters B | 18..19 boilers B (face S, water row 18) |
  20..29 engines B | 30 poles | 31..40 engines C | 41..42 boilers C (water row 42) | 43 fast inserters C |
  44 coal C | 45 lamps | 46..47 free
Cells 1..3: 14 boilers per row (x = 50k+6+3j), chain inlet tile x = 50k+5, band x 50k+4..5 for the water.
Cell 0: rows A and C only, 12 boilers (x = 8+3j), inlet x = 7; rows 17..29 free for the water fan-out.
Water: each input feeds exactly one boiler row (one chain of 12 or 14 boilers = 720 / 840 water/s, under one
  offshore pump). Lines are routed by a small maze router (pipe-to-ground pairs, pipes only at turns), along the
  free rows and the inserter rows (between inserters), never touching another line, a foreign boiler or steam.
Coal: row 16 feeds rows A+B = 96 boilers (43.2/s, 96% of a blue belt), row 44 feeds rows C = 54 (24.3/s).
"""
import sys, math, heapq, itertools, random
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
import lib.bp as LBP
from lib.build import BP, N, E, S, W, VEC, OPP, validate, tile_of, SUPPLY, reach
from lib.cell import finish, corners
from lib import adapt

RECT = {'boiler': (3, 2), 'steam-engine': (3, 5)}
LBP.SIZES.update({'boiler': (3, 2), 'steam-engine': (3, 5)})
LBP.COLORS.update({'boiler': (170, 90, 60), 'steam-engine': (120, 130, 110)})
DIRS = (N, E, S, W)


class PB(BP):
    def rect(self, name, tx, ty, d):
        w, h = RECT[name]
        if d in (E, W): w, h = h, w
        self.ents.append({'entity_number': len(self.ents) + 1, 'name': name, 'direction': d,
                          'position': {'x': tx + w / 2, 'y': ty + h / 2}})
        return self.ents[-1]
    def tiles(self, e):
        if e['name'] in RECT:
            w, h = RECT[e['name']]
            if e.get('direction', 0) in (E, W): w, h = h, w
            x0, y0 = e['position']['x'] - w / 2, e['position']['y'] - h / 2
            return [(int(x0) + i, int(y0) + j) for i in range(w) for j in range(h)]
        return super().tiles(e)


def ports(e):
    """(tile, facing, kind) of every fluid connection of e."""
    n, d = e['name'], e.get('direction', 0)
    cx, cy = e['position']['x'], e['position']['y']
    def P(v, face, kind):
        x, y = v
        for _ in range(d // 4): x, y = -y, x
        return ((math.floor(cx + x), math.floor(cy + y)), (face + d) % 16, kind)
    if n == 'boiler': return [P((-1, .5), W, 'water'), P((1, .5), E, 'water'), P((0, -.5), N, 'steam')]
    if n == 'steam-engine': return [P((0, 2), S, 'steam'), P((0, -2), N, 'steam')]
    if n == 'pipe': t = tile_of(e); return [(t, f, 'any') for f in DIRS]
    if n == 'pipe-to-ground': return [(tile_of(e), d, 'any')]
    return []


def step(t, d, k=1): return (t[0] + VEC[d][0] * k, t[1] + VEC[d][1] * k)


# ======================= machines
b = PB(); b.belt_name, b.ug_name = 'express-transport-belt', 'express-underground-belt'
CHAINS = {}            # name -> (inlet tile, [boilers])
POLE = 'medium-electric-pole'
def row_pair_x(k):     # boiler x positions in cell k
    return [8 + 3 * j for j in range(12)] if k == 0 else [50 * k + 6 + 3 * j for j in range(14)]

for k in range(4):
    xs = row_pair_x(k); X0 = 50 * k
    kinds = ('A', 'C') if k == 0 else ('A', 'B', 'C')
    for kind in kinds:
        CHAINS[(k, kind)] = ((xs[0] - 1, {'A': 14, 'B': 18, 'C': 42}[kind]), [])
    for j, x in enumerate(xs):
        if 'A' in kinds:
            b.rect('steam-engine', x, 3, N); b.rect('steam-engine', x, 8, N)
            CHAINS[(k, 'A')][1].append(b.rect('boiler', x, 13, N)); b.inserter(x + 1, 15, S)
        if 'B' in kinds:
            b.inserter(x + 1, 17, N); CHAINS[(k, 'B')][1].append(b.rect('boiler', x, 18, S))
            b.rect('steam-engine', x, 20, N); b.rect('steam-engine', x, 25, N)
        b.rect('steam-engine', x, 31, N); b.rect('steam-engine', x, 36, N)
        CHAINS[(k, 'C')][1].append(b.rect('boiler', x, 41, N)); b.inserter(x + 1, 43, S)
    # inserter-row poles: first boiler's left tile, then right of every odd boiler (free pairs between the others)
    for y in ((15, 43) if k == 0 else (15, 17, 43)):
        pxs = [xs[0]] + [xs[j] + 2 for j in range(1, len(xs), 2)]
        if k == 3 and y == 15: pxs[-1] = xs[-1]          # make room for the coal panel at (197, 15)
        if k == 0: pxs.append(47)                         # link to cell 1 (47 -> 56 = 9)
        for px in pxs: b.add(POLE, px, y)
    for y in ((2, 30)):
        for px in range(xs[0] + 2, xs[-1] + 3, 6): b.add(POLE, px, y)
    if k == 0:
        b.add(POLE, 44, 8); b.add(POLE, 44, 37)           # bridges 2<->15, 30<->43
    else:
        for y in (8, 24, 37): b.add(POLE, X0 + 4, y)      # bridges 2<->15, 17<->30, 30<->43
    for lx in (12, 24, 36): b.add('small-lamp', X0 + lx, 45)

# coal: row 16 (A|B) and row 44 (C), from the east edge (x=197) west to x=8; underground under each grid line
COAL_IN = [(197, 16), (197, 44)]
for y in (16, 44):
    x = 197
    while x >= 8:
        if x % 50 == 5 and x > 50:                         # band tile 50k+5 -> underground to 50(k-1)+47
            b.ug(x, y, W, 'input'); b.ug(x - 8, y, W, 'output'); x -= 9; continue
        b.belt(x, y, W); x -= 1
b.panel(197, 15, 'coal'); b.panel(197, 45, 'coal')

# ======================= water router
GRID_COLS = {x for x in range(0, 205) if x % 50 in (48, 49, 0, 1, 2, 3)}
def inside(t): return 4 <= t[0] <= 197 and 2 <= t[1] <= 47 and t[0] not in GRID_COLS


class Router:
    def __init__(self, b, lines):
        self.b = b
        self.occ = {t: e for e in b.ents for t in b.tiles(e)}
        self.port = {}                                   # (tile, facing) -> owner (line name or 'steam')
        for name, (inlet, boilers) in CHAINS.items():
            for e in boilers:
                for t, f, kind in ports(e): self.port[(t, f)] = name if kind == 'water' else 'steam'
        for e in b.ents:
            if e['name'] == 'steam-engine':
                for t, f, kind in ports(e): self.port[(t, f)] = 'steam'
        self.reserved = {inlet: name for name, (inlet, _) in CHAINS.items()}
        self.span = {0: set(), 1: set()}                 # axis -> tiles strictly inside an underground pair
        self.lines = lines

    def free(self, t, line):
        return inside(t) and t not in self.occ and self.reserved.get(t, line) == line

    def ports_ok(self, t, faces, line):
        for f in faces:
            o = self.port.get((step(t, f), OPP[f]))
            if o is not None and o != line: return False
        return True

    def ptg_between(self, t, d, k):
        ax = d in (E, W)
        e = self.occ.get(step(t, d, k))
        return e is not None and e['name'] == 'pipe-to-ground' and (e['direction'] in (E, W)) == ax

    def route(self, line, start, goal):
        """start = tile of the input ptg (faces E). Dijkstra over (tile, dir, kind):
        kind P = pipe, I = ptg entering underground, O = ptg leaving underground."""
        ax = lambda d: int(d in (E, W))
        h = lambda t: (abs(t[0] - goal[0]) + abs(t[1] - goal[1])) / 11
        st0 = (start, E, 'O'); dist = {st0: 0}; par = {st0: None}
        pq = [(h(start), 0, st0)]; cnt = itertools.count()
        while pq:
            _, c, s = heapq.heappop(pq)
            if c > dist[s]: continue
            t, d, kind = s
            if t == goal and (kind == 'P' or (kind == 'O' and d == E)):
                path = []
                while s: path.append(s); s = par[s]
                return path[::-1][1:]
            nxt = []
            if kind in ('P', 'O'):
                for d2 in ([d] if kind == 'O' else [x for x in DIRS if x != OPP[d]]):
                    t2 = step(t, d2)
                    if not self.free(t2, line): continue
                    turn = TURN if d2 != d else 0
                    if self.ports_ok(t2, DIRS, line): nxt.append(((t2, d2, 'P'), 1 + turn + 0.3))
                    if t2 != goal and t2 not in self.span[ax(d2)] and self.ports_ok(t2, [OPP[d2]], line):
                        nxt.append(((t2, d2, 'I'), 1 + turn))
            else:
                for k in range(1, 11):
                    t2 = step(t, d, k)
                    if self.ptg_between(t, d, k): break
                    if self.free(t2, line) and t2 not in self.span[ax(d)] and self.ports_ok(t2, [d], line):
                        nxt.append(((t2, d, 'O'), 1))
            for s2, w in nxt:
                c2 = c + w
                if c2 < dist.get(s2, 1e9):
                    dist[s2] = c2; par[s2] = s; heapq.heappush(pq, (c2 + h(s2[0]), c2, s2))
        return None

    def place(self, line, path):
        tiles = [t for t, _, _ in path]
        if len(set(tiles)) != len(tiles): return False
        prev = None
        for t, d, kind in path:
            if kind == 'P': n = self.b.pipe(*t); faces = DIRS
            elif kind == 'I': n = self.b.ptg(*t, OPP[d]); faces = (OPP[d],)
            else:
                n = self.b.ptg(*t, d); faces = (d,)
                a = prev[0]; k = abs(t[0] - a[0]) + abs(t[1] - a[1])
                for i in range(1, k): self.span[int(d in (E, W))].add(step(a, d, i))
            e = self.b.ents[n - 1]; e['_line'] = line
            self.occ[t] = e
            for f in faces: self.port[(t, f)] = line
            prev = (t, d, kind)
        return True


FAIL = {}
TURN = 3
def solve(g0, order, assign):
    """assign: chain per input i (rows g0 + 3i). Returns (entities, ...) or None."""
    keep = len(b.ents)
    R = Router(b, None)
    inputs = {}
    for i, ch in enumerate(assign):
        t = (4, g0 + 3 * i)
        if not R.free(t, ch): b.ents[keep:] = []; return None
        n = b.ptg(*t, E); e = b.ents[n - 1]; e['_line'] = ch
        R.occ[t] = e; R.port[(t, E)] = ch; inputs[ch] = t
    for ch in order:
        p = R.route(ch, inputs[ch], CHAINS[ch][0])
        if p is None or not R.place(ch, p):
            FAIL[ch] = FAIL.get(ch, 0) + 1; b.ents[keep:] = []; return None
    return inputs


def chains_sorted():
    return sorted(CHAINS, key=lambda c: ({'A': 14, 'B': 18, 'C': 42}[c[1]], c[0]))

# search: inputs top -> bottom mapped to chains sorted by row; route far cells first
best = None
base = len(b.ents)
for g0 in range(2, 18):
    assign = chains_sorted()
    for order in (sorted(CHAINS, key=lambda c: (-c[0], c[1])), sorted(CHAINS, key=lambda c: (c[0], c[1]))):
        inp = solve(g0, order, assign)
        if inp:
            n = len(b.ents) - base
            if best is None or n < best[0]: best = (n, g0, order, assign)
            b.ents[base:] = []
    print('g0', g0, 'best', best and best[:2])
assert best, f'no routing found {FAIL}'
_, g0, order, assign = best
INPUTS = solve(g0, order, assign)
WATER_IN = set(INPUTS.values())
gs = sorted(t[1] for t in WATER_IN)
for y in (gs[0] - 1, gs[-1] + 1):
    if 2 <= y <= 47 and (4, y) not in b.occupancy(): b.panel(4, y, 'water', 'fluid')
for i, e in enumerate(b.ents):
    e['entity_number'] = i + 1; e.pop('_line', None)

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

port_at = {}
for e in b.ents:
    for t, f, kind in ports(e): port_at.setdefault((t, f), []).append((e, kind))
adj = {e['entity_number']: set() for e in b.ents if ports(e)}
for e in b.ents:
    for t, f, kind in ports(e):
        nt = step(t, f)
        for o, k2 in port_at.get((nt, OPP[f]), []):
            assert {kind, k2} != {'water', 'steam'}, (e['position'], o['position'])
            if kind == 'steam' and k2 == 'any': raise AssertionError(f'steam leaks into a pipe at {o["position"]}')
            adj[e['entity_number']].add(o['entity_number'])
    if e['name'] == 'pipe-to-ground':                                  # underground partner
        d = OPP[e['direction']]; t = tile_of(e)
        for s in range(1, 11):
            o = occ.get(step(t, d, s))
            if o and o['name'] == 'pipe-to-ground' and o['direction'] in (e['direction'], OPP[e['direction']]):
                assert o['direction'] == OPP[e['direction']], f'pipe-to-ground at {t}: next one faces the same way'
                adj[e['entity_number']].add(o['entity_number']); break
        else:
            assert t in WATER_IN, f'pipe-to-ground at {t} has no partner'
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
assert len(water) == len(CHAINS), len(water)
sizes = []
for g in water:
    nb = sum(byid[u]['name'] == 'boiler' for u in g)
    ins = [tile_of(byid[u]) for u in g if byid[u]['name'] == 'pipe-to-ground' and tile_of(byid[u]) in WATER_IN]
    assert len(ins) == 1 and nb in (12, 14), (nb, ins)
    sizes.append(nb)
rep.append(f'water: {len(water)} separate networks, each = one input + one boiler row '
           f'({sizes.count(12)} x 12, {sizes.count(14)} x 14 boilers = 720 / 840 water/s, < 1 offshore pump)')
for e in b.ents:
    if e['name'] != 'boiler': continue
    e1 = [o for o in adj[e['entity_number']] if byid[o]['name'] == 'steam-engine']
    assert len(e1) == 1, e['position']
    e2 = [o for o in adj[e1[0]] if byid[o]['name'] == 'steam-engine']
    assert len(e2) == 1 and adj[e2[0]] == {e1[0]}, e['position']
rep.append('steam: every boiler feeds exactly 2 engines in a straight column')
assert all(b2 - a == 3 for a, b2 in zip(gs, gs[1:])) and {x for x, _ in WATER_IN} == {4}
rep.append(f'water inputs: {len(gs)} pipe-to-ground at x=4 (west edge), rows {gs[0]}..{gs[-1]}, two tiles between each')
COAL_ENDS = [(8, 16), (8, 44)]
assert sorted(belts['ends']) == sorted(COAL_ENDS), sorted(belts['ends'])
assert not belts['sideloads'] and not belts['curves'], (belts['sideloads'], belts['curves'])
for s, t in zip(COAL_IN, COAL_ENDS): assert t in reach(b, s)
rep.append('coal: 2 straight blue belts from the east edge (rows 16 and 44), no curves, no sideloads')
robos = [(50 * i, 50 * j) for i in range(5) for j in range(2)]
gtiles, gpoles = adapt.world_grid(robos)
tiles = {t for e in b.ents for t in b.tiles(e)}
assert not tiles & gtiles, sorted(tiles & gtiles)[:5]
assert all(inside(t) for t in tiles), [t for t in tiles if not inside(t)][:5]
d = min(math.dist((e['position']['x'], e['position']['y']), g) for e in b.ents if e['name'] == POLE for g in gpoles)
assert d <= 9
rep.append(f'grid: 4x1 cells, every entity inside a cell interior (only undergrounds and 2 coal belts cross the '
           f'grid lines), no collision with grid roboports/poles/lamps, grid link {d:.1f}')
n = lambda nm: sum(e['name'] == nm for e in b.ents)
nb = n('boiler')
ab = sum(len(CHAINS[c][1]) for c in CHAINS if c[1] in 'AB')
rep.append(f'{nb} boilers, {n("steam-engine")} steam engines -> {nb * 1.8:.1f} MW; coal {nb * 0.45:.2f}/s '
           f'(row 16: {ab * .45:.1f}/s, row 44: {(nb - ab) * .45:.1f}/s); water {nb * 60}/s')
bp = finish(b, 'Steam Power 270 MW', [('item', 'boiler'), ('item', 'steam-engine')], corner_list=corners(4, 1))
for l in rep: print(l)
write_outputs(HERE, bp)
render(HERE, bp, px=4, grid=0)
