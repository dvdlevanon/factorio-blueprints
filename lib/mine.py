"""Ore mines on the roboport grid: n x n cells (50n x 50n tiles), outputs on the WEST edge.

Covers the WHOLE square (David 2026-11-19: no holes; drills may sit on the grid lines as long as the
roboports are in the blueprint). The blueprint carries every roboport of the lattice; the grid's big
poles/lamps inside the square are replaced by the mine's own poles.
Frame: top-left roboport center = (0,0). Mined area x, y 2..50n-3.

Per cell 7 pairs of drill columns (pitch 7) at x0 = 50i + 2 + 7p: L drills x0..x0+2 (face E) | belt x0+3 |
  R drills x0+4..x0+6 (face W). The last cell's pair 6 has no R column. Column 50i+51 stays free (reached by the
  drills on both sides). Pair 6's R column skips the 4 roboport rows.
Drills per column: a small dynamic programme picks the drill rows: first no row out of reach (a drill reaches
  1 tile around itself), then as many drills as possible.
Poles: one lattice, medium pole at x0+1 of every L column on local rows 2, 11, 20, 29, 38, 47 (steps 9; 47 -> 52
  is 5), lamp beside it. One wired network.
Collectors: K horizontal belts (2 or 4) cross the mine, >= 4 rows from a pole row. At the west edge they turn into
  verticals at x 4 and 5 and meet on K adjacent output rows (x = 2); one splitter (K=2) or a real 4-4 balancer
  (K=4, one underground). Drills at x 1..3 along the verticals drop straight onto them.
Unmined: a few tiles at x 2..4 under the output splitters and beside the west-edge roboports.
"""
import math
from .build import BP, N, E, S, W, VEC, SIZE, POWERED, SUPPLY, BELTS, SPLITTERS, UGS, belt_check, belt_tiles
from . import bp as LBP, adapt
from .cell import corners

SIZE['electric-mining-drill'] = 3
POWERED.add('electric-mining-drill')
LBP.SIZES['electric-mining-drill'] = (3, 3)
LBP.COLORS['electric-mining-drill'] = (95, 105, 120)

DRILL = 'electric-mining-drill'
RATE = 0.5                       # ore/s per drill: mining_speed 0.5, iron/copper/coal/stone mining_time 1
BELT = 45.0                      # express belt items/s
PX = (4, 12, 20, 29, 37, 45)     # pole columns (local) for pairs 0..5; also the pole rows
PY = (2, 11, 20, 29, 38, 47)   # pole rows per cell: steps of 9, edge rows used so no 2-row leftovers
LX = (5, 13, 19, 30, 36, 44)     # lamp next to each pole, inside the same drill column slot
FORBID = {22, 23, 26, 27}        # local rows/cols where a line crossing hits a grid pole/lamp (some rotation)
COLLECTORS = {1: (16, 33), 2: (25, 74), 3: (16, 57, 92, 133), 4: (25, 74, 125, 174), 5: (33, 92, 157, 216)}
# collector rows sit >= 4 rows from a pole row (or right next to one): no 1-2 row strip no drill can reach
OUTS = {1: 2, 2: 2, 3: 4, 4: 4, 5: 4}


ROBO = (48, 49, 0, 1)            # roboport rows/cols around every lattice point (mod 50)


def field(y): return y % 50 not in ROBO


def place_run(lo, hi):
    """Drill top rows in rows lo..hi (inclusive): floor(len/3) drills, spare rows in the middle."""
    L = hi - lo + 1; k = L // 3; r = L - 3 * k
    if k == 0: return []
    top = k // 2
    return [lo + 3 * i for i in range(top)] + [lo + 3 * top + r + 3 * i for i in range(k - top)]


def cover(free, need, lo, hi, ok=lambda t: True):
    """Drill top rows in one column: drills on free rows only, no overlap. Minimise needed rows (lo..hi) out of
    reach (a drill at t reaches t-1..t+3), then maximise the number of drills. Dynamic programme over tops."""
    free = set(free)
    tops = [t for t in range(lo - 1, hi + 1) if {t, t + 1, t + 2} <= free and ok(t)]
    nd = [0] * (hi + 3 - lo + 3)
    def holes(a, b):                       # needed rows in a..b
        return sum(1 for y in range(a, b + 1) if y in need) if b >= a else 0
    best = {}
    for t in tops:
        cand = (holes(lo, t - 2), -1, None)
        for u in tops:
            if u + 3 > t: break
            if u not in best: continue
            h, c, _ = best[u]
            gap = holes(u + 4, t - 2)
            v = (h + gap, c - 1, u)
            if v[:2] < cand[:2]: cand = v
            if u + 9 < t and gap > 0 and h + gap > cand[0]: pass
        best[t] = cand
    end = (holes(lo, hi), 0, None)
    last = None
    for t in tops:
        h, c, _ = best[t]
        v = (h + holes(t + 4, hi), c)
        if v < end[:2]: end = (v[0], v[1], t); last = t
    res = []
    t = end[2]
    while t is not None: res.append(t); t = best[t][2]
    return sorted(res)


def runs(rows):
    """Maximal runs of consecutive rows from a sorted list."""
    out, st = [], None
    for y in rows:
        if st is None: st = pv = y
        elif y == pv + 1: pv = y
        else: out.append((st, pv)); st = pv = y
    if st is not None: out.append((st, pv))
    return out


def split_row(c0, c1):
    """Row s between collectors: rows c0+1..s flow N, s+1..c1-1 flow S; equal field rows on both sides."""
    best = None
    for s in range(c0, c1):
        a = sum(field(y) for y in range(c0 + 1, s + 1)); b = sum(field(y) for y in range(s + 1, c1))
        if best is None or abs(a - b) < best[0]: best = (abs(a - b), s)
    return best[1]


def out_window(n, K, C):
    H = 50 * n; up, lo = C[:K // 2], C[K // 2:]
    best = None
    for r in range(max(up) + 3, min(lo) - K - 2):
        rows = range(r, r + K)
        if len({y // 50 for y in rows}) > 1: continue
        if not all(field(y) and y % 50 not in set(PY) for y in rows): continue
        d = abs(r + (K - 1) / 2 - (H - 1) / 2)
        if best is None or d < best[0]: best = (d, r)
    return list(range(best[1], best[1] + K))


def build(n):
    K, C = OUTS[n], list(COLLECTORS[n]); H = 50 * n
    m = out_window(n, K, C)
    b = BP(); b.belt_name = 'express-transport-belt'
    top, bot = 2, H - 3                          # the whole square between the roboport rows of the edges
    pole_rows = {50 * j + p for j in range(n) for p in PY}
    xe = 50 * (n - 1) + 47                       # belt column of the east-most pair
    # ---- collectors, verticals, output (the merge) ----
    if K == 2: turn = {0: (4, S), 1: (4, N)}
    else: turn = {0: (4, S), 1: (5, S), 2: (5, N), 3: (4, N)}
    special = {}                                  # tile -> direction for merge belts
    land = {0: m[0], 1: m[-1]} if K == 2 else {0: m[0], 1: m[2], 3: m[3]}   # K=4: C lands on m[1] via a jog
    for k, c in enumerate(C):
        xt, d = turn[k]
        for x in range(xt + 1, xe + 1): special[(x, c)] = W
        special[(xt, c)] = d
        if k in land:
            rng = range(c + 1, land[k]) if d == S else range(land[k] + 1, c)
            for y in rng: special[(xt, y)] = d
            special[(xt, land[k])] = W
    vsplit = []
    if K == 4:
        # C: up x=5 to m3, jog east to x=7, up to m1, west under B's vertical (underground 6 -> 4), lands on m1
        for y in range(m[3] + 1, C[2]): special[(5, y)] = N
        special[(5, m[3])] = E; special[(6, m[3])] = E
        special[(7, m[3])] = N; special[(7, m[2])] = N; special[(7, m[1])] = W
        special[(4, m[2])] = W
        vsplit = [(C[1] + 1, m[0] - 1, S), (m[3] + 2, C[2] - 1, N)]
    # ---- drills ----
    drills = []                                   # (x, ytop, dir)
    strip_L = (C[0], C[-1])
    for i in range(n):
        for p in range(7):
            x0 = 50 * i + 2 + 7 * p
            sides = (('L', x0, E), ('R', x0 + 4, W)) if (i, p) != (n - 1, 6) else (('L', x0, E),)
            for side, xd, d in sides:
                rows = [y for y in range(top, bot + 1) if y not in C]
                if side == 'L': rows = [y for y in rows if y not in pole_rows]
                need = set(range(top, bot + 1))
                if p == 6 and side == 'R':                                   # roboport
                    rows = [y for y in rows if y % 50 not in ROBO]; need = {y for y in need if y % 50 not in ROBO}
                if (i, p, side) == (0, 0, 'L'):
                    rows = [y for y in rows if not strip_L[0] <= y <= strip_L[1]]
                    need = {y for y in need if not strip_L[0] <= y <= strip_L[1]}
                if (i, p, side) == (0, 0, 'R') and K == 4: rows = [y for y in rows if not m[1] <= y <= m[3]]
                drills += [(xd, y, d) for y in cover(rows, need, top, bot)]
    # splitter rows on the verticals: not where a pair-0 R drill drops
    r0_drops = {y + 1 for x, y, d in drills if x == 6}
    vs = []
    for y0, y1, d in vsplit:
        order = range(y1, y0 - 1, -1) if d == S else range(y0, y1 + 1)     # as close to the output as possible
        ys = next(y for y in order if y not in r0_drops)
        vs.append((ys, d))
    if K == 4:                                    # pair 0 R column: only drops upstream of the layer-1 splitters
        (y1, _), (y2, _) = vs
        def good(r): return (not C[1] < r < C[2]) or (r < y1 if r < m[0] else r > y2 + 1)
        drills = [t for t in drills if t[0] != 6]
        rows = [y for y in range(top, bot + 1) if y not in C and not m[1] <= y <= m[3]]
        drills += [(6, y, W) for y in cover(rows, set(range(top, bot + 1)), top, bot, ok=lambda t: good(t + 1))]
    # ---- column belts ----
    for i in range(n):
        for p in range(7):
            bx = 50 * i + 5 + 7 * p
            for y in range(top, bot + 1):
                if y in C: continue
                if (i, p) == (0, 0) and K == 4:
                    if C[1] <= y <= C[2]: continue
                    if C[0] < y < C[1]: special.setdefault((bx, y), N); continue
                    if C[2] < y < C[3]: special.setdefault((bx, y), S); continue
                if y < C[0]: d = S
                elif y > C[-1]: d = N
                else:
                    k = max(k for k in range(len(C)) if C[k] < y)
                    d = N if y <= split_row(C[k], C[k + 1]) else S
                special.setdefault((bx, y), d)
    split_tiles = set()
    for ys, d in vs: split_tiles |= {(4, ys), (5, ys)}
    if K == 2: split_tiles |= {(3, m[0]), (3, m[1])}
    else: split_tiles |= {(3, y) for y in m}
    for t, d in special.items():
        if t not in split_tiles: b.belt(t[0], t[1], d)
    for ys, d in vs: b.splitter(4, ys, d)
    if K == 2:
        b.splitter(3, m[0], W); b.belt(2, m[0], W); b.belt(2, m[1], W)
    else:
        b.ug_name = 'express-underground-belt'
        b.ug(6, m[1], W, 'input'); b.ug(4, m[1], W, 'output')
        b.splitter(3, m[0], W); b.splitter(3, m[2], W)
        for y in m: b.belt(2, y, W)
    # west strip: the collector verticals take pair 0's L column; drills at x 1..3 drop onto the vertical at x=4
    bt = {(t[0], t[1]): d for t, d in special.items() if t not in split_tiles}
    used = set()
    for x, y, d in drills: used |= {(x + i, y + j) for i in range(3) for j in range(3)}
    keep = set(bt) | {(3, y) for y in m} | {(4, ys) for ys, _ in vs} | {(5, ys) for ys, _ in vs} \
        | {(x, y) for x in (2, 3) for y in pole_rows} | {(1, y) for y in range(strip_L[0], strip_L[1] + 3) if y % 50 in ROBO}
    okrow = [y for y in range(strip_L[0] - 1, strip_L[1] + 3) if not {(1, y), (2, y), (3, y)} & (keep | used)]
    sneed = set(range(strip_L[0], strip_L[1] + 1))
    def upstream(r):                              # K=4: drop before the layer-1 splitters, so the ore is balanced
        if K == 2: return True
        (y1, _), (y2, _) = vs
        return r < y1 if r < m[0] else r > y2 + 1
    drills += [(1, y, E) for y in cover(okrow, sneed, strip_L[0], strip_L[1],
                                        ok=lambda t: bt.get((4, t + 1)) in (N, S) and upstream(t + 1))]
    for x, y, d in drills: b.add(DRILL, x, y, direction=d)
    # ---- poles and lamps ----
    for i in range(n):
        for p in range(7):
            x0 = 50 * i + 2 + 7 * p
            for j in range(n):
                for py in PY:
                    b.add('medium-electric-pole', x0 + 1, 50 * j + py)
                    b.add('small-lamp', x0, 50 * j + py)
    for i in range(n + 1):                        # the roboport lattice, edges included
        for j in range(n + 1):
            b.add('roboport', 50 * i - 2, 50 * j - 2, request_filters={'sections': [{'index': 1}]})
    occ = b.occupancy()
    def free0(y): return y % 50 not in ROBO and (0, y) not in occ
    out_lamps = [(0, y) for y in (m[0] - 1, m[-1] + 1) if free0(y)]
    for x, y in out_lamps: b.add('small-lamp', x, y)
    for y in (next(y for y in range(m[0] - 2, m[0] - 9, -1) if free0(y)),
              next(y for y in range(m[-1] + 2, m[-1] + 9) if free0(y))):
        b.add('medium-electric-pole', 0, y)                                    # powers the output lamps
    info = dict(n=n, K=K, C=C, m=m, drills=drills, vs=vs, turn=turn, xe=xe)
    return b, info


# ------------------------------------------------------------------ checks
def rot_tile(t, r, c):
    x, y = t[0] + .5, t[1] + .5
    for _ in range(r): x, y = c - (y - c), c + (x - c)
    return int(math.floor(x)), int(math.floor(y))


def check(b, info):
    n, K, C, m = info['n'], info['K'], info['C'], info['m']
    rep = []
    occ = b.occupancy(); rep.append(f'collisions: none ({len(b.ents)} entities)')
    # power: coverage + one wired network
    cov = set()
    for e in b.ents:
        if e['name'] in SUPPLY:
            px, py = e['position']['x'], e['position']['y']; s = SUPPLY[e['name']]
            cov |= {(int(px - s + .5) + i, int(py - s + .5) + j) for i in range(int(2 * s)) for j in range(int(2 * s))}
    bad = [e for e in b.ents if e['name'] in POWERED and not any(t in cov for t in b.tiles(e))]
    assert not bad, f'unpowered {bad[0]["name"]} at {bad[0]["position"]}'
    trees = adapt.rewire(b)
    assert trees == 1, f'poles form {trees} networks'
    np_ = sum(e['name'] == 'medium-electric-pole' for e in b.ents)
    rep.append(f'power: every drill, lamp and roboport covered; {np_} poles wired as ONE network (spanning tree, reach 9)')
    # belts
    r2, bi = belt_check(b); rep += r2
    belts = belt_tiles(b)
    exits = {(2, y) for y in m}
    assert set(bi['ends']) == exits, f'dead ends {sorted(set(bi["ends"]) ^ exits)[:6]}'
    exp_curves = {(info['turn'][k][0], C[k]) for k in range(K)}
    if K == 2: exp_curves |= {(4, m[0]), (4, m[1])}
    else: exp_curves |= {(4, m[0]), (5, m[2]), (4, m[3]), (5, m[3]), (7, m[3]), (7, m[1])}
    assert set(bi['curves']) == exp_curves, f'curves {sorted(set(bi["curves"]) ^ exp_curves)[:6]}'
    col_x = {50 * i + 5 + 7 * p for i in range(n) for p in range(7)}
    assert all(t[0] in col_x and t[1] in C for t in bi['sideloads']), 'unexpected sideload'
    rep.append(f'belts: curves = the {len(exp_curves)} merge turns; sideloads = pair belts onto collectors only; '
               f'dead ends = the {K} output tiles'
               + ('; one underground pair (balancer crossing)' if K == 4 else ''))
    # flow: every belt tile reaches an exit
    memo = {}
    def ok(t):
        st = [t]
        while st:
            u = st[-1]
            if u in memo: st.pop(); continue
            e = belts[u]; vx, vy = VEC[e['direction']]
            nx = [(u[0] + vx, u[1] + vy)]
            if e['name'] in SPLITTERS: nx = [(w[0] + vx, w[1] + vy) for w in b.tiles(e)]
            if e['name'] in UGS and e['type'] == 'input':
                nx = [next((u[0] + vx * k, u[1] + vy * k) for k in range(1, 10)
                           if belts.get((u[0] + vx * k, u[1] + vy * k), {}).get('type') == 'output')]
            nx = [w for w in nx if w in belts]
            if u in exits: memo[u] = True; st.pop(); continue
            todo = [w for w in nx if w not in memo]
            if todo:
                for w in todo:
                    if w in st: raise AssertionError(f'belt loop at {w}')
                st += todo; continue
            memo[u] = any(memo[w] for w in nx); st.pop()
        return memo[t]
    assert all(ok(t) for t in belts), 'a belt does not reach an output'
    # balance: share of each collector reaching each output (a splitter halves into both outputs)
    def share(t, f=1.0, acc=None):
        acc = {} if acc is None else acc
        while True:
            if t in exits: acc[t] = acc.get(t, 0) + f; return acc
            e = belts[t]; vx, vy = VEC[e['direction']]
            if e['name'] in SPLITTERS:
                for w in b.tiles(e): share((w[0] + vx, w[1] + vy), f / 2, acc)
                return acc
            if e['name'] in UGS and e['type'] == 'input':
                t = next((t[0] + vx * k, t[1] + vy * k) for k in range(1, 10)
                         if belts.get((t[0] + vx * k, t[1] + vy * k), {}).get('type') == 'output'); continue
            t = (t[0] + vx, t[1] + vy)
    for c in C:
        sh = share((info['xe'], c))
        assert len(sh) == K and all(abs(v - 1 / K) < 1e-9 for v in sh.values()), f'collector {c}: {sh}'
    rep.append(f'balancer: each of the {K} collectors sends exactly 1/{K} to every output (splitter graph traced)')
    # drills: drop on a plain belt that reaches an output
    nd = 0
    for e in b.ents:
        if e['name'] != DRILL: continue
        vx, vy = VEC[e['direction']]
        t = (int(math.floor(e['position']['x'] + 1.85 * vx)), int(math.floor(e['position']['y'] + 1.85 * vy)))
        assert t in belts and belts[t]['name'] in BELTS, f'drill at {e["position"]} drops on {t}'
        assert ok(t); nd += 1
        sh = share(t)
        assert len(sh) == K and all(abs(v - 1 / K) < 1e-9 for v in sh.values()), f'drill at {e["position"]}: {sh}'
    rep.append(f'drills: all {nd} drop on a belt that reaches an output, and every drill sends exactly 1/{K} of its ore '
               f'to each output (no drill drops after the balancer)')
    # grid: the blueprint carries the whole roboport lattice; nothing else may sit on a roboport
    H = 50 * n
    robo = {(e['position']['x'], e['position']['y']) for e in b.ents if e['name'] == 'roboport'}
    assert robo == {(50 * i, 50 * j) for i in range(n + 1) for j in range(n + 1)}, 'roboport lattice incomplete'
    assert all(-2 <= t[0] <= H + 1 and -2 <= t[1] <= H + 1 for e in b.ents for t in b.tiles(e)), 'outside the square'
    rep.append(f'grid: all {len(robo)} roboports of the lattice included (edges and inside); drills, belts, poles '
               f'fill everything else, grid lines included (the grid big poles/lamps inside are replaced)')
    # coverage: every tile of the square except roboports is in reach of a drill
    mined = set()
    for x, y, d in info['drills']:
        mined |= {(x - 1 + i, y - 1 + j) for i in range(5) for j in range(5)}
    rtiles = {t for e in b.ents if e['name'] == 'roboport' for t in b.tiles(e)}
    area = {(x, y) for x in range(2, H - 2) for y in range(2, H - 2)} - rtiles
    holes = area - mined
    win = {(x, y) for x in range(2, 8 if K == 4 else 5) for y in range(m[0] - 2, m[-1] + 3)} \
        | {(x, y) for x in range(2, 5) for y in range(H) if y % 50 in ROBO}       # beside the west-edge roboports
    assert holes <= win, f'{len(holes - win)} unmined tiles, e.g. {sorted(holes - win)[:5]}'
    raw = nd * RATE
    rep.append(f'coverage: every tile from the edge roboports inward is in reach of a drill (x, y 2..{H - 3}, '
               f'{len(area)} tiles) except {len(holes)} tiles at the west edge (under the output splitters / beside the edge '
               f'roboports where the collector verticals run)')
    info['holes'] = len(holes)
    rep.append(f'ratio: {nd} drills x 0.5/s = {raw:.0f} ore/s = {raw / BELT:.1f} blue belts (base, no mining '
               f'productivity) -> {K} output belts ({K * BELT:.0f}/s)')
    stats = dict(drills=nd, poles=np_, lamps=sum(e['name'] == 'small-lamp' for e in b.ents),
                 belts=sum(e['name'] in BELTS for e in b.ents), splitters=sum(e['name'] in SPLITTERS for e in b.ents),
                 raw=raw, mined=1.0)
    return rep, stats


def main(n, outdir):
    from .cell import finish
    from .bp import write_outputs, render
    b, info = build(n)
    rep, st = check(b, info)
    for r in rep: print(' ', r)
    K = info['K']
    bp = finish(b, f'Mine {50 * n}x{50 * n}', [('item', DRILL), ('item', 'express-transport-belt')],
                description=f'{st["drills"]} electric drills covering the whole square (grid lines too), {K} blue belts '
                            f'out on the WEST edge (adjacent rows), balanced by splitters. One pole lattice: power any '
                            f'pole. Carries all {(n + 1) ** 2} roboports of the grid; replaces the grid poles/lamps inside.',
                corner_list=())
    write_outputs(outdir, bp)
    render(outdir, bp, px=6 if n == 1 else 3, grid=0)
    return rep, st, info
