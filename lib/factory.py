"""Science-pack factory engine: production bands, a belt router, a lane-level item-flow checker.

Band = the sp_rows layout generalised (1..4 ingredients, any inserter types), built in its own local frame
  and placed into the blueprint with a rotation (quarter turns clockwise) + offset:
  entry rows top..top+n-1 come in from the EAST and turn down into one column per ingredient; splitter taps
  give each pair of machine rows its share; formers build the pair's middle belt(s) by side-loading
  (1 ingredient -> a curve, both lanes the same item). Output rows run WEST into two collectors that meet on
  the band's OUT tile (west, middle).
  nb = 1 (1-2 ingredients, pitch 12): 0 out | 1 out ins | 2..4 machines | 5 pick | 6 A | 7 pick | 8..10 machines
       | 11 out ins | 12 next out.
  nb = 2 (3-4 ingredients, pitch 13): A on row 6, B on row 7; near inserter picks the adjacent belt, a
       long-handed one the far belt. Lanes: A = ings[0] | ings[1], B = ings[2] | ings[3] (3 ingredients ->
       B carries ings[2] on both lanes).
Router: Dijkstra over (tile, direction) with underground hops; never feeds or touches other belts or
  inserter targets, crosses grid lines only straight, never runs along them.
Flow check: items per belt lane from the inputs and every machine's output inserters; every machine gets
  all its ingredients, every inserter moves something its target uses, no item rides a belt that has no
  consumer or exit downstream, the exits carry exactly what they should on both lanes.
Recipes: data/base/prototypes/recipe.lua (2.1.24), default energy_required 0.5.
"""
import heapq, math
from .build import (BP, N, E, S, W, VEC, OPP, SIZE, BELTS, UGS, SPLITTERS, INSERTER_REACH, UG_MAX, REACH,
                    tile_of, belt_tiles)
from . import adapt
from .cell import corners

EXPRESS = ('express-transport-belt', 'express-underground-belt')
TIERS = ((15, 'transport-belt', 'underground-belt'), (30, 'fast-transport-belt', 'fast-underground-belt'),
         (45, 'express-transport-belt', 'express-underground-belt'))


def tier(rate):
    for cap, belt, ug in TIERS:
        if rate <= cap + 1e-9: return belt, ug
    raise ValueError(f'{rate}/s needs more than one blue belt')


RECIPES = {   # name: (seconds, {ingredient: amount}, results)
    'iron-gear-wheel': (0.5, {'iron-plate': 2}, 1),
    'inserter': (0.5, {'electronic-circuit': 1, 'iron-gear-wheel': 1, 'iron-plate': 1}, 1),
    'transport-belt': (0.5, {'iron-plate': 1, 'iron-gear-wheel': 1}, 2),
    'automation-science-pack': (5, {'copper-plate': 1, 'iron-gear-wheel': 1}, 1),
    'logistic-science-pack': (6, {'inserter': 1, 'transport-belt': 1}, 1),
    'firearm-magazine': (1, {'iron-plate': 4}, 1),
    'piercing-rounds-magazine': (6, {'firearm-magazine': 2, 'steel-plate': 1, 'copper-plate': 2}, 2),
    'grenade': (8, {'iron-plate': 5, 'coal': 10}, 1),
    'stone-wall': (0.5, {'stone-brick': 5}, 1),
    'military-science-pack': (10, {'piercing-rounds-magazine': 1, 'grenade': 1, 'stone-wall': 2}, 2),
    'chemical-science-pack': (24, {'engine-unit': 2, 'advanced-circuit': 3, 'sulfur': 1}, 2),
    'iron-stick': (0.5, {'iron-plate': 1}, 2),
    'rail': (0.5, {'stone': 1, 'iron-stick': 1, 'steel-plate': 1}, 2),
    'electric-furnace': (5, {'steel-plate': 10, 'advanced-circuit': 5, 'stone-brick': 10}, 1),
    'productivity-module': (15, {'advanced-circuit': 5, 'electronic-circuit': 5}, 1),
    'production-science-pack': (21, {'electric-furnace': 1, 'productivity-module': 1, 'rail': 30}, 3),
    'utility-science-pack': (21, {'low-density-structure': 3, 'processing-unit': 2, 'flying-robot-frame': 1}, 3),
    'solar-panel': (10, {'steel-plate': 5, 'electronic-circuit': 15, 'copper-plate': 5}, 1),
    'accumulator': (10, {'iron-plate': 2, 'battery': 5}, 1),
    'radar': (0.5, {'electronic-circuit': 5, 'iron-gear-wheel': 5, 'iron-plate': 10}, 1),
    'satellite': (5, {'low-density-structure': 100, 'solar-panel': 100, 'accumulator': 100, 'radar': 5,
                      'processing-unit': 100, 'rocket-fuel': 50}, 1),
    'rocket-fuel': (15, {'solid-fuel': 10, 'light-oil': 10}, 1),
    'rocket-part': (3, {'processing-unit': 10, 'low-density-structure': 10, 'rocket-fuel': 10}, 1),
}
AM3 = 1.25
PRODUCT = {'rocket-part': 'space-science-pack'}       # a silo's output is what the launched satellite returns
EXTRA_IN = {'rocket-part': {'satellite'}}
RATE = {'fast-inserter': 2.31, 'long-handed-inserter': 1.2, 'bulk-inserter': 4.62}   # items/s, hand 1 / bulk 2

LEFT = {N: W, W: S, S: E, E: N}        # left of the travel direction
RIGHT = {v: k for k, v in LEFT.items()}


def add(a, b, k=1): return a[0] + b[0] * k, a[1] + b[1] * k


# ====================================================================== band
class Band:
    def __init__(self, recipe, ings=None, nj=1, npairs=1, top=2, x0=7, col=5, gaps=(), near='fast-inserter',
                 far='long-handed-inserter', out='fast-inserter', near2=False, out2=False, y0=None, panel=True,
                 stub=None, direct=False, spec=None, groups=None, split_out=False, unshare=False):
        """spec: the middle belts as item tuples, e.g. [('coal',), ('iron-plate',)] = A all coal, B all iron;
        [('a', 'b')] = A with a | b. Default from ings (1..4 items).
        direct: True / set of belt indices whose feed rows run straight to the east edge of the band, one input
        per pair (no column). The other items come down columns with splitter taps (one input each).
        groups: {flat index: key} - flat items with the same key share one column (e.g. stone for A and C).
        split_out: one pair only; the top and bottom output rows leave separately (two outputs)."""
        if spec is None:
            i = list(ings)
            spec = [tuple(i[:2])] + ([tuple(i[2:])] if len(i) > 2 else [])
        self.spec = [tuple(t) for t in spec]
        assert 1 <= len(self.spec) <= 3 and all(1 <= len(t) <= 2 for t in self.spec)
        self.ings = [it for t in self.spec for it in t]
        n = len(self.ings)
        self.recipe, self.nj, self.n = recipe, nj, n
        self.nb = len(self.spec)
        self.pitch0 = (12, 13, 14)[self.nb - 1]
        self.unshare = unshare                  # each pair has its own two output rows (4 one-lane outputs / 2 pairs)
        self.pitch = self.pitch0 + (1 if unshare else 0)
        self.top, self.x0, self.col, self.gaps = top, x0, col, gaps
        self.near, self.far, self.out, self.near2, self.out2, self.panel = near, far, out, near2, out2, panel
        dset = set(range(self.nb)) if direct is True else set(direct or ())
        self.belt_of = [bi for bi, t in enumerate(self.spec) for _ in t]
        self.feeds = tuple(o for bi, t in enumerate(self.spec) for o in ((1, 2), (3, 4), (5, 6))[bi][:len(t)])
        self.lane = [len(t) == 2 for t in self.spec for _ in t]        # True: side-loaded onto one lane
        self.isdirect = [self.belt_of[k] in dset for k in range(n)]
        keys = groups or {}
        self.groups = []                                              # [(key, [flat indices])]
        for k in range(n):
            if self.isdirect[k]: continue
            key = keys.get(k, ('k', k))
            for g in self.groups:
                if g[0] == key: g[1].append(k); break
            else: self.groups.append((key, [k]))
        G = len(self.groups)
        self.direct = G == 0
        self.split_out = split_out
        y0 = (top + G + 1 if G else top) if y0 is None else y0
        self.pairs = [y0 + i * self.pitch for i in range(npairs)]
        self.xa = self.ax(nj - 1) + 5; self.xb = self.xa + 2; self.xc = self.xa + 4
        east = (self.xa, self.xb, self.xc)[self.nb - 1]
        self.d = [east + 3 + 3 * g for g in range(G)]
        anyd = any(self.isdirect)
        self.xs = (self.d[-1] + (2 if anyd else 1)) if G else east + 2
        if stub is not None: self.xs = stub
        self.y_top = top if G else self.pairs[0]
        self.kx0 = col + 1 if split_out else col
        self.curves, self.sideloads, self.ends = [], [], []
        self.b = BP(); self.b.belt_name, self.b.ug_name = EXPRESS
        self.build()

    def feed_cap(self, k, direct=False):
        """Max items/s into column group k (or direct flat item k, one pair)."""
        if direct: return 22.5 if self.lane[k] else 45
        return sum(22.5 if self.lane[f] else 45 for f in self.groups[k][1]) * len(self.pairs)

    def ax(self, j): return self.x0 + 3 * j + 2 * sum(j >= g for g in self.gaps)

    def out_rows(self):
        if self.unshare: return sorted([yb for yb in self.pairs] + [yb + self.pitch0 for yb in self.pairs])
        return list(self.pairs) + [self.pairs[-1] + self.pitch]

    def machines(self): return 2 * self.nj * len(self.pairs)

    def build(self):
        b = self.b
        for yb in self.pairs:
            rows = {1: ((yb + 2, yb + 5, yb + 1, S), (yb + 8, yb + 7, yb + 11, N)),
                    2: ((yb + 2, yb + 5, yb + 1, S), (yb + 9, yb + 8, yb + 12, N)),
                    3: ((yb + 2, yb + 5, yb + 1, S), (yb + 10, yb + 9, yb + 13, N))}[self.nb]
            for top, ab, outr, pick in rows:
                for j in range(self.nj):
                    x = self.ax(j)
                    b.asm(x, top, self.recipe)
                    if self.nb == 1:
                        b.inserter(x + 1, ab, pick, self.near)
                        if self.near2: b.inserter(x, ab, pick, self.near)
                    else:
                        b.inserter(x, ab, pick, self.near); b.inserter(x + 1, ab, pick, self.far)
                    b.inserter(x + 1, outr, pick, self.out)
                    if self.out2: b.inserter(x, outr, pick, self.out)
                    if j % 2 == 0 or j in self.gaps or j == self.nj - 1:
                        b.add('medium-electric-pole', x + 2, ab); b.add('medium-electric-pole', x + 2, outr)
                    elif j % 4 == 3:
                        b.add('small-lamp', x + 2, ab)
            self._formers(yb)
        self.stubd = {}
        for i, yb in enumerate(self.pairs):
            for k, f in enumerate(self.feeds):
                if self.isdirect[k]: self.stubd[(i, k)] = (self.xs, yb + f)
        if self.groups: self._columns(); self._stubs()
        self._output()

    def _formers(self, yb):
        b = self.b
        G = len(self.groups)
        f0 = self.d[0] - 3 if G else self.xs
        k = 0
        for bi, items in enumerate(self.spec):
            x = (self.xa, self.xb, self.xc)[bi]; r = yb + 1 + 2 * bi  # first feed row; former tile (x, r + 1)
            for y in range(r + 1, yb + 6 + bi): b.belt(x, y, S)
            for xx in range(self.x0, x + 1): b.belt(xx, yb + 6 + bi, W)
            self.curves.append((x, yb + 6 + bi)); self.ends.append((self.x0, yb + 6 + bi))
            (self.sideloads if len(items) == 2 else self.curves).append((x, r + 1))
            for xx in range(x, f0 + 1): b.belt(xx, r, W)
            b.belt(x - 1, r, S); b.belt(x - 1, r + 1, E)
            self.curves += [(x - 1, r), (x - 1, r + 1)]
            if len(items) == 2:
                for xx in range(x + 1, f0 + 1): b.belt(xx, r + 1, W)
        if not G: return
        last_tap = {}
        for g, (_, ks) in enumerate(self.groups):
            taps = [(y2, k2) for y2 in self.pairs for k2 in ks]
            last_tap[g] = max(y2 + self.feeds[k2] for y2, k2 in taps)
        for k, f in enumerate(self.feeds):
            y = yb + f
            if self.isdirect[k]:                        # straight to the east edge, under the columns
                b.ug(self.d[0] - 2, y, W, 'output'); b.ug(self.d[-1] + 1, y, W, 'input')
                for xx in range(self.d[-1] + 2, self.xs + 1): b.belt(xx, y, W)
                continue
            g = next(i for i, (_, ks) in enumerate(self.groups) if k in ks)
            dk = self.d[g]
            if y != last_tap[g]:
                b.splitter(dk - 1, y - 1, S); b.belt(dk - 1, y, W); b.belt(dk, y, S)
                self.curves.append((dk - 1, y))
            else:
                b.belt(dk, y, W); b.belt(dk - 1, y, W)
                self.curves.append((dk, y))
            if g == 0: b.belt(self.d[0] - 2, y, W)
            else: b.ug(dk - 2, y, W, 'input'); b.ug(self.d[0] - 2, y, W, 'output')

    def _columns(self):
        b = self.b
        for g, (_, ks) in enumerate(self.groups):
            dk, r = self.d[g], self.top + g
            b.belt(dk, r, S); self.curves.append((dk, r))
            taps = sorted(yb + self.feeds[k] for yb in self.pairs for k in ks)
            stops = [t - 1 for t in taps[:-1]]                        # splitter rows
            for s0, s1 in zip([r + 1] + [s + 2 for s in stops], stops + [taps[-1]]):
                for y in range(s0, s1): b.belt(dk, y, S)

    def _stubs(self):
        self.stub = []
        for g in range(len(self.groups)):
            r = self.top + g
            for x in range(self.d[g] + 1, self.xs + 1): self.b.belt(x, r, W)
            self.stub.append((self.xs, r))

    def _output(self):
        b, col = self.b, self.col
        outs = self.out_rows()
        last = self.ax(self.nj - 1) + 3
        if self.split_out:
            for y in outs:
                for x in range(col + 1, last): b.belt(x, y, W)
            self.OUTS = [(col, y) for y in outs]
            self.OUT = self.OUTS[0]
            return
        h = math.ceil(len(outs) / 2)
        self.yo = yo = (outs[h - 1] + outs[h]) // 2
        for y in outs:
            for x in range(col + 1, last): b.belt(x, y, W)
        b.belt(col, outs[0], S)
        for y in range(outs[0] + 1, yo): b.belt(col, y, S)
        b.belt(col, outs[-1], N)
        for y in range(yo + 1, outs[-1]): b.belt(col, y, N)
        b.belt(col, yo, W)
        self.curves += [(col, outs[0]), (col, outs[-1])]
        self.sideloads += [(col, yo)] + [(col, y) for y in outs[1:-1]]
        self.OUT = (col - 1, yo)            # first tile after the collectors (the router starts here)
        self.OUTS = [self.OUT]

    def lane_expect(self):
        """(tile, (lane items, lane items)) on each pair's middle belts, just west of the formers."""
        res = []
        for yb in self.pairs:
            for bi, t in enumerate(self.spec):
                res.append((((self.xa, self.xb, self.xc)[bi] - 1, yb + 6 + bi), ({t[0]}, {t[-1]})))
        return res


# ====================================================================== placement
class Placed:
    """A band copied into the blueprint with rotation rot (quarter turns clockwise) then offset (dx, dy)."""
    def __init__(self, main, band, rot=0, dx=0, dy=0):
        self.band, self.rot, self.dx, self.dy = band, rot, dx, dy
        for e in band.b.ents:
            e = dict(e); e['position'] = dict(e['position'])
            x, y = self.P(e['position']['x'], e['position']['y'])
            e['position'] = {'x': x, 'y': y}
            if 'direction' in e or e['name'] in BELTS | UGS | SPLITTERS | set(INSERTER_REACH):
                e['direction'] = self.D(e.get('direction', 0))
            e['entity_number'] = len(main.ents) + 1
            main.ents.append(e)

    def P(self, x, y):
        for _ in range(self.rot): x, y = -y, x
        return x + self.dx, y + self.dy

    def T(self, t):
        x, y = self.P(t[0] + .5, t[1] + .5)
        return int(math.floor(x)), int(math.floor(y))

    def D(self, d): return (d + 4 * self.rot) % 16

    @property
    def OUT(self): return self.T(self.band.OUT), self.D(W)

    def out(self, i): return self.T(self.band.OUTS[i]), self.D(W)

    def stub(self, k, i=None):
        if i is None: return self.T(self.band.stub[k]), self.D(W), self.band.feed_cap(k)
        return self.T(self.band.stubd[(i, k)]), self.D(W), self.band.feed_cap(k, direct=True)

    def junctions(self):
        bd = self.band
        return ([self.T(t) for t in bd.curves], [self.T(t) for t in bd.sideloads], [self.T(t) for t in bd.ends])

    def lane_expect(self):
        return [(self.T(t), l) for t, l in self.band.lane_expect()]


# ====================================================================== router
class Router:
    def __init__(self, b, cw, ch):
        self.b, self.cw, self.ch = b, cw, ch
        self.gtiles, self.gpoles = adapt.world_grid(corners(cw, ch))
        self.keepout, self.curves, self.joined = set(), [], []

    def keep_out(self, placed, margin=0):
        """Routes never enter a placed band's bounding box (its stubs and OUT stay reachable)."""
        bd = placed.band
        x0, x1, y0, y1 = bd.kx0, bd.xs, bd.y_top, bd.out_rows()[-1]      # OUT column stays free
        for x in range(x0 - margin, x1 + 1 + margin):
            for y in range(y0 - margin, y1 + 1 + margin): self.keepout.add(placed.T((x, y)))

    def keep_rect(self, x0, y0, x1, y1):
        self.keepout |= {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}

    def _state(self):
        b = self.b
        self.occ = b.occupancy()
        self.belts = belt_tiles(b)
        self.avoid = set(self.gtiles)
        for e in b.ents:
            if e['name'] in INSERTER_REACH:
                k = INSERTER_REACH[e['name']]; x, y = tile_of(e); v = VEC[e.get('direction', 0)]
                self.avoid |= {(x + v[0] * k, y + v[1] * k), (x - v[0] * k, y - v[1] * k)}
        self.pointed = set()
        for t, e in self.belts.items():
            if e['name'] in UGS and e.get('type') == 'input': continue
            f = add(t, VEC[e.get('direction', 0)])
            if f not in self.belts: self.pointed.add(f)
        self.ugs = {t: e for t, e in self.belts.items() if e['name'] in UGS}
        self.upair = _ug_pairs(self.belts)

    def band_dirs(self, t):
        """Allowed directions on tile t (None = any)."""
        x, y = t
        vl, hl = (x % 50) in (48, 49, 0, 1, 2, 3), (y % 50) in (48, 49, 0, 1)
        if vl and hl: return ()
        if vl: return (E, W)
        if hl: return (N, S)
        return None

    def inside(self, t):
        return 4 <= t[0] <= 50 * self.cw - 3 and 2 <= t[1] <= 50 * self.ch - 3

    def free(self, t, ok=()):
        return self.inside(t) and t not in self.occ and t not in self.avoid and (t not in self.pointed or t in ok) \
            and (t not in self.keepout or t in ok)

    def route(self, start, df, goal, gd, rate=45, turn=2, ugc=1000, start_dirs=None, name='', bias=None, merge=False,
              joins=None):
        """Place belts from tile `start` (fed by a belt moving in direction df) into the existing belt tile
        `goal` (direction gd), entering it from behind or from a side. Returns the placed path."""
        self._state()
        belt, ug = tier(rate); umax = UG_MAX[ug]
        joins = joins or {}                    # tile -> direction: may side-load onto any of these belts
        assert goal is None or goal in self.belts, f'{name}: goal {goal} is not a belt'
        def okdir(t, d):
            a = self.band_dirs(t)
            return a is None or d in a
        def front_ok(t, d):
            f = add(t, VEC[d])
            return f not in self.belts or (f == goal and d != OPP[gd]) or (f in joins and d not in (joins[f], OPP[joins[f]]))
        def ug_clear(p, q, d):
            """No same-name underground strictly between p and q, and neither inside another pair's span."""
            ax = 0 if d in (E, W) else 1
            lo, hi = sorted((p[ax], q[ax]))
            for t, e in self.ugs.items():
                if e['name'] != ug or t[1 - ax] != p[1 - ax] or e.get('direction', 0) not in (d, OPP[d]): continue
                if lo < t[ax] < hi: return False
            for a, o in self.upair.items():
                if self.ugs[a]['name'] != ug or a[1 - ax] != p[1 - ax] or self.ugs[a].get('direction', 0) not in (d, OPP[d]): continue
                l2, h2 = sorted((a[ax], o[ax]))
                if l2 < p[ax] < h2 or l2 < q[ax] < h2: return False
            return True
        h, best, prev = [], {}, {}
        sd = start_dirs or [d for d in (N, E, S, W) if d != OPP[df]]
        if not self.free(start, ok={start}): raise AssertionError(f'{name}: start {start} not free')
        self.keepout.discard(start)
        for d in sd:
            if okdir(start, d) and front_ok(start, d):
                c = 0 if d == df else turn
                best[(start, d)] = c; prev[(start, d)] = None; heapq.heappush(h, (c, start, d))
        end = None
        while h:
            c, t, d = heapq.heappop(h)
            if best.get((t, d), 1e9) < c: continue
            n = add(t, VEC[d])
            if n == goal and d != OPP[gd] and not (merge and d == gd): end = (t, d); break
            if n in joins and d not in (joins[n], OPP[joins[n]]): end = (t, d); goal, gd = n, joins[n]; merge = True; break
            if not self.free(n) or not okdir(n, d): continue
            inband = self.band_dirs(n) is not None
            for d2 in ((d,) if inband else (d, LEFT[d], RIGHT[d])):
                if not front_ok(n, d2): continue
                c2 = c + 1 + (turn if d2 != d else 0) + (bias(n) if bias else 0)
                if c2 < best.get((n, d2), 1e9):
                    best[(n, d2)] = c2; prev[(n, d2)] = ((t, d), 'belt'); heapq.heappush(h, (c2, n, d2))
            if inband: continue
            for k in range(2, umax + 1):                     # underground: input at n, output at n + k*d
                q = add(n, VEC[d], k)
                if not self.inside(q): break
                if not self.free(q) or self.band_dirs(q) is not None or not front_ok(q, d): continue
                if not ug_clear(n, q, d): continue
                if any(add(n, VEC[d], i) in self.keepout for i in range(1, k)): continue
                c2 = c + ugc + k
                if c2 < best.get((q, d), 1e9):
                    best[(q, d)] = c2; prev[(q, d)] = ((t, d), ('ug', n)); heapq.heappush(h, (c2, q, d))
        assert end, f'{name}: no route from {start} to {goal}'
        steps, s = [], end
        while s is not None:
            p = prev[s]
            steps.append((s, p[1] if p else 'belt'))
            s = p[0] if p else None
        steps.reverse()
        b = self.b; keep = b.belt_name, b.ug_name
        b.belt_name, b.ug_name = belt, ug
        path = []
        for (t, d), kind in steps:
            if kind == 'belt': b.belt(t[0], t[1], d)
            else:
                n = kind[1]; b.ug(n[0], n[1], d, 'input'); b.ug(t[0], t[1], d, 'output'); path.append(n)
            path.append(t)
        b.belt_name, b.ug_name = keep
        assert len(set(path)) == len(path), f'{name}: path crosses itself'
        dirs = [d for (t, d), _ in steps]
        if dirs[0] != df: self.curves.append(steps[0][0][0])
        for i in range(1, len(steps)):
            if dirs[i] != dirs[i - 1]: self.curves.append(steps[i][0][0])
        if dirs[-1] != gd and not merge: self.curves.append(goal)
        if merge: self.joined.append(goal)
        self.last = [(t, d) for (t, d), _ in steps]
        return path


def entry_gate(b, xe, y, item, rate):
    """External input at the east edge: underground in at xe, panel, underground out; returns (start, input)."""
    belt, ug = tier(rate)
    keep = b.belt_name, b.ug_name
    b.belt_name, b.ug_name = belt, ug
    b.ug(xe, y, W, 'input'); b.panel(xe - 1, y, item); b.ug(xe - 2, y, W, 'output')
    b.belt_name, b.ug_name = keep
    return (xe - 3, y), (xe, y)


def auto_gaps(x0, nj, gx=(2, 3)):
    """Machine gaps (Band.gaps) so no machine of an unrotated band covers the grid's vertical-line big pole
    columns (x mod 50 in gx)."""
    gaps = []
    for j in range(nj):
        while any((x0 + 3 * j + 2 * len(gaps) + i) % 50 in gx for i in range(3)): gaps.append(j)
    return tuple(gaps)


# ====================================================================== poles
def bridge_poles(b, cw, ch):
    """Join pole groups with extra medium poles on free tiles (spacing <= 9). Returns poles added."""
    gt, _ = adapt.world_grid(corners(cw, ch))
    added = 0
    while True:
        trees = adapt.rewire(b)
        if trees == 1: return added
        poles = [e for e in b.ents if e['name'] in REACH]
        byid = {e['entity_number']: e for e in poles}
        adj = {p['entity_number']: set() for p in poles}
        for w in b.wires:
            if w[0] in adj and w[2] in adj: adj[w[0]].add(w[2]); adj[w[2]].add(w[0])
        comp, cid = {}, 0
        for p in adj:
            if p in comp: continue
            st = [p]
            while st:
                u = st.pop()
                if u in comp: continue
                comp[u] = cid; st += adj[u]
            cid += 1
        pos = {n: (e['position']['x'], e['position']['y']) for n, e in byid.items()}
        best = None
        main = [n for n in pos if comp[n] == 0]; rest = [n for n in pos if comp[n] != 0]
        for a in main:
            for c in rest:
                d = math.dist(pos[a], pos[c])
                if best is None or d < best[0]: best = (d, a, c)
        _, a, c = best
        occ = b.occupancy()
        (x0, y0), (x1, y1) = pos[a], pos[c]
        k = math.ceil(math.dist(pos[a], pos[c]) / 8.5)
        last = pos[a]
        for i in range(1, k):
            tx, ty = x0 + (x1 - x0) * i / k - .5, y0 + (y1 - y0) * i / k - .5
            cand = sorted(((round(tx) + i2, round(ty) + j2) for i2 in range(-3, 4) for j2 in range(-3, 4)),
                          key=lambda t: math.dist((t[0] + .5, t[1] + .5), (tx + .5, ty + .5)))
            for t in cand:
                if t in occ or t in gt or not (4 <= t[0] <= 50 * cw - 3 and 2 <= t[1] <= 50 * ch - 3): continue
                if math.dist((t[0] + .5, t[1] + .5), last) > 9: continue
                b.add('medium-electric-pole', t[0], t[1]); occ[t] = b.ents[-1]; last = (t[0] + .5, t[1] + .5)
                added += 1; break
            else:
                raise AssertionError(f'cannot bridge poles near {(tx, ty)}')


# ====================================================================== flow check
def _feeders(belts, b):
    fd = {t: [] for t in belts}
    for t, e in belts.items():
        if e['name'] in UGS and e.get('type') == 'input': continue
        n = add(t, VEC[e.get('direction', 0)])
        if n in belts: fd[n].append((t, e.get('direction', 0)))
    return fd


def _ug_pairs(belts):
    pair = {}
    for t, e in belts.items():
        if e['name'] in UGS and e.get('type') == 'input':
            v = VEC[e.get('direction', 0)]
            for k in range(1, UG_MAX[e['name']] + 1):
                o = add(t, v, k)
                if o in belts and belts[o]['name'] == e['name'] and belts[o].get('type') == 'output' \
                        and belts[o].get('direction', 0) == e.get('direction', 0):
                    pair[t] = o; break
    return pair


def check_flow(b, sources, exits, lane_expect=()):
    """sources: [(tile, item)] external inputs (both lanes). exits: {tile: item} (must carry exactly that item,
    both lanes). Returns report lines."""
    belts = belt_tiles(b)
    occ = b.occupancy()
    fd = _feeders(belts, b)
    upair = _ug_pairs(belts)
    machines = {e['entity_number']: e for e in b.ents if e.get('recipe')}
    def succ(t):
        """[(next tile, lane map)] lane map: function lane -> lane, or a fixed lane."""
        e = belts[t]; d = e.get('direction', 0)
        if e['name'] in UGS and e.get('type') == 'input':
            return [(upair[t], None)]
        outs = [t]
        if e['name'] in SPLITTERS: outs = b.tiles(e)
        res = []
        for u in outs:
            n = add(u, VEC[d])
            if n not in belts: continue
            ne = belts[n]; dn = ne.get('direction', 0)
            if ne['name'] in UGS:
                assert ne.get('type') == 'input' and dn == d, f'belt {u} feeds an underground {n} from the side/back'
                res.append((n, None)); continue
            if ne['name'] in SPLITTERS:
                assert dn == d, f'belt {u} side-loads a splitter at {n}'
                res.append((n, None)); continue
            if dn == d: res.append((n, None)); continue
            behind = [f for f in fd[n] if f[1] == dn]
            side = [f for f in fd[n] if f[1] != dn]
            if not behind and len(side) == 1: res.append((n, None)); continue
            v = (u[0] - n[0], u[1] - n[1])
            res.append((n, 0 if v == VEC[LEFT[dn]] else 1))
        return res
    lanes = {t: (set(), set()) for t in belts}
    work = []
    def put(t, lane, item):
        if item not in lanes[t][lane]:
            lanes[t][lane].add(item); work.append((t, lane, item))
    for t, item in sources:
        put(t, 0, item); put(t, 1, item)
    # inserters
    ins = []
    for e in b.ents:
        if e['name'] not in INSERTER_REACH: continue
        k = INSERTER_REACH[e['name']]; x, y = tile_of(e); v = VEC[e.get('direction', 0)]
        pt, dt = (x + v[0] * k, y + v[1] * k), (x - v[0] * k, y - v[1] * k)
        ins.append((e, (x, y), pt, dt, occ.get(pt), occ.get(dt)))
    def drop_lane(itile, t):
        d = belts[t].get('direction', 0)
        s = tuple((v > 0) - (v < 0) for v in (itile[0] - t[0], itile[1] - t[1]))
        assert s in (VEC[LEFT[d]], VEC[RIGHT[d]]), f'inserter {itile} drops onto belt {t} along its axis'
        return 1 if s == VEC[LEFT[d]] else 0
    for e, it, pt, dt, src, dst in ins:
        if src and src.get('recipe') and dst and dt in belts:
            prod = PRODUCT.get(src['recipe'], src['recipe'])
            assert belts[dt]['name'] in BELTS, f'inserter {it} drops onto a non-belt {belts[dt]["name"]}'
            put(dt, drop_lane(it, dt), prod)
    while work:
        t, lane, item = work.pop()
        e = belts[t]
        if e['name'] in SPLITTERS:
            for u in b.tiles(e):
                if u != t: put(u, lane, item)
        for n, m in succ(t):
            put(n, lane if m is None else m, item)
    # machines and inserters
    got = {n: set() for n in machines}
    consumers = {}                      # item -> belt tiles where an inserter picks it for a machine that uses it
    for e, it, pt, dt, src, dst in ins:
        if dst and dst.get('recipe'):
            need = set(RECIPES[dst['recipe']][1]) | EXTRA_IN.get(dst['recipe'], set())
            if src and src.get('recipe'):
                p_ = PRODUCT.get(src['recipe'], src['recipe'])
                assert p_ in need, f'inserter {it}: {p_} into a {dst["recipe"]} machine'
                got[dst['entity_number']].add(p_)
            else:
                assert pt in belts, f'inserter {it} picks from nothing'
                have = lanes[pt][0] | lanes[pt][1]
                use = have & need
                assert use, f'inserter {it} at {dst["recipe"]}: belt {pt} carries {sorted(have)}, nothing it needs'
                got[dst['entity_number']] |= use
                for i in use: consumers.setdefault(i, set()).add(pt)
        elif src and src.get('recipe'):
            assert dst is not None, f'inserter {it} drops onto nothing'
        else:
            raise AssertionError(f'inserter {it} not between a machine and a belt/machine')
    for n, m in machines.items():
        need = (set(RECIPES[m['recipe']][1]) | EXTRA_IN.get(m['recipe'], set())) - {'light-oil'}
        assert need <= got[n], f'{m["recipe"]} machine at {m["position"]} misses {sorted(need - got[n])}'
    # every item on every belt has a consumer or an exit downstream
    pred = {t: set() for t in belts}
    for t in belts:
        for n, _ in succ(t): pred[n].add(t)
        if belts[t]['name'] in SPLITTERS:
            for u in b.tiles(belts[t]): pred[u].add(t)
    for item in {i for l in lanes.values() for s in l for i in s}:
        ok = set(); st = list(consumers.get(item, ())) + [t for t, i in exits.items() if item in (i, i[0] if isinstance(i, tuple) else i)]
        while st:
            u = st.pop()
            if u in ok: continue
            ok.add(u); st += pred[u]
        carry = {t for t, l in lanes.items() if item in l[0] | l[1]}
        for t in carry - ok:             # a tail past the last consumer is fine if the line has a consumer
            seen, st, tail = set(), [t], False
            while st and not tail:
                u = st.pop()
                if u in seen: continue
                seen.add(u); tail = u in ok; st += [v for v in pred[u] if v in carry]
            assert tail, f'{item} rides belts with no consumer or exit, e.g. at {t}'
    for t, item in exits.items():
        if isinstance(item, tuple):                    # (item, 'one lane') - a low-rate exit
            assert lanes[t][0] | lanes[t][1] == {item[0]}, f'exit {t} carries {lanes[t]}, want {item[0]}'
            continue
        assert lanes[t][0] == {item} and lanes[t][1] == {item}, f'exit {t} carries {lanes[t]}, want {item} on both lanes'
    for t, (l0, l1) in lane_expect:
        assert (lanes[t][0], lanes[t][1]) in ((l0, l1), (l1, l0)), f'lanes at {t}: {lanes[t]}, want {l0}|{l1}'
    return [f'flow: {len(machines)} machines each get all ingredients; {len(ins)} inserters move items their '
            f'target uses; no item rides a belt without a consumer or exit; exits carry only their product on '
            f'both lanes; {len(lane_expect)} mixed belts have the intended lanes']


# ====================================================================== helpers
def machine_rate(recipe, n_in_fast=0, n_in_long=0, n_in_bulk=0, out='fast-inserter', n_out=1, belt_items=None):
    """Crafts/s of one AM3, limited by crafting speed and by its inserters (nominal rates, hand size 1,
    bulk 2). Input items per craft = all ingredients (an inserter picks one item per swing)."""
    t, ing, res = RECIPES[recipe]
    full = AM3 / t
    per_craft = sum(ing.values()) if belt_items is None else belt_items
    cap_in = n_in_fast * RATE['fast-inserter'] + n_in_long * RATE['long-handed-inserter'] + n_in_bulk * RATE['bulk-inserter']
    cap_out = n_out * RATE[out] / res
    return min(full, cap_in / per_craft if per_craft else full, cap_out)


# ====================================================================== plant
class Plant:
    """One science block: bands placed in a cw x ch cell area (top-left roboport at (0,0)), external inputs
    gated at the east edge, links routed, final output on the west edge."""
    def __init__(self, cw, ch):
        self.b = BP(); self.b.belt_name, self.b.ug_name = EXPRESS
        self.cw, self.ch = cw, ch
        self.R = Router(self.b, cw, ch)
        self.placed, self.sources, self.exits, self.inputs = [], [], {}, []
        self.XE = 50 * cw - 3

    def band(self, band, rot=0, dx=0, dy=0):
        p = Placed(self.b, band, rot, dx, dy)
        self.placed.append(p); self.R.keep_out(p)
        return p

    def feed(self, item, rate, y, to, name=None, **kw):
        """External input entering at the east edge on row y, routed to `to` = (tile, dir)."""
        g, gd, cap = to
        assert rate <= cap + 1e-9, f'{item} {rate}/s into a feed that carries {cap}/s'
        start, inp = entry_gate(self.b, self.XE, y, item, rate)
        self.R.keepout |= {(self.XE - i, y) for i in range(3)}
        self.sources.append((inp, item)); self.inputs.append((item, rate, y))
        self.R.route(start, W, g, gd, rate=rate, name=name or item, **kw)

    def link_out(self, frm, i, to, rate=45, name='', **kw):
        """Output i of a split-output band -> stub."""
        g, gd, cap = to
        assert rate <= cap + 1e-9, f'{name}: {rate}/s into a feed that carries {cap}/s'
        self.R.route(*frm.out(i), g, gd, rate=45, name=name, **kw)
        return dict(self.R.last)

    def lshape(self, start, xt, goal, name=''):
        """Hand route: from start go W to column xt, N/S to the goal's row, W into the goal (a W-facing stub)."""
        (sx, sy), (gx, gy) = start, goal
        assert gx < xt <= sx
        b = self.b; occ = b.occupancy(); tiles = []
        for x in range(sx, xt, -1): tiles.append(((x, sy), W))
        v = S if gy > sy else N
        if gy != sy:
            tiles.append(((xt, sy), v))
            for y in range(sy + (1 if v == S else -1), gy, 1 if v == S else -1): tiles.append(((xt, y), v))
            tiles.append(((xt, gy), W))
            self.R.curves += [(xt, sy), (xt, gy)]
        else: tiles.append(((xt, sy), W))
        for x in range(xt - 1, gx, -1): tiles.append(((x, gy), W))
        for t, d in tiles:
            assert t not in occ and t not in self.R.gtiles, f'{name}: {t} taken'
            b.belt(t[0], t[1], d)

    def join(self, frm, path, name='', **kw):
        """Band output side-loaded onto an earlier route (path = {tile: dir})."""
        self.R.route(*frm.OUT, None, None, name=name, joins=path, **kw)
        return dict(self.R.last)

    def link(self, frm, to, rate=45, name='', **kw):
        """Band output -> another band's stub."""
        g, gd, cap = to
        assert rate <= cap + 1e-9, f'{name}: {rate}/s into a feed that carries {cap}/s'
        self.R.route(*frm.OUT, g, gd, rate=45, name=name, **kw)          # internal belts are blue
        return dict(self.R.last)

    def exit(self, p, item):
        t, d = p.OUT
        assert d == W and t[0] == 4, 'final output must leave west at x = 4'
        self.b.belt(t[0], t[1], W); self.b.panel(t[0], t[1] - 1, item)
        self.exits[t] = item
        return t

    def merge_exit(self, a, b, m, item, panel=None):
        """Final output: bands a and b side-load onto tile m (facing W, on the west edge), one lane each."""
        assert m[0] == 4
        self.b.belt(m[0], m[1], W); self.b.panel(*(panel or (m[0] + 1, m[1])), item)
        self.R.route(*a.OUT, m, W, name='output a', merge=True)
        self.R.route(*b.OUT, m, W, name='output b', merge=True)
        self.exits[m] = item
        self.R.joined.remove(m); self.R.joined.append(m)            # one sideload tile (two feeders)
        self.R.joined = list(dict.fromkeys(self.R.joined))

    def check(self, extra_curves=(), extra_sideloads=(), extra_ends=()):
        from .build import validate, belt_check
        from .cell import check_fixed
        b = self.b
        for i, e in enumerate(b.ents): e['entity_number'] = i + 1
        nb = bridge_poles(b, self.cw, self.ch)
        for i, e in enumerate(b.ents): e['entity_number'] = i + 1
        adapt.rewire(b)
        rep, info = validate(b, lambda ins, s, d: None)
        rep = [r for r in rep if not r.startswith('inserters')]
        if nb: rep.append(f'power: {nb} bridge poles join the bands')
        cur, side, ends = [], [], []
        for p in self.placed:
            c, s_, e_ = p.junctions(); cur += c; side += s_; ends += e_
        cur += self.R.curves + list(extra_curves); side += list(extra_sideloads) + self.R.joined
        ends += list(self.exits) + list(extra_ends)
        for want, got, what in ((cur, info['curves'], 'curves'), (side, info['sideloads'], 'sideloads'),
                                (ends, info['ends'], 'dead ends')):
            assert sorted(want) == sorted(got), f'{what}: unexpected {sorted(set(got) - set(want))[:5]}, ' \
                                                f'missing {sorted(set(want) - set(got))[:5]}'
        rep.append(f'belts: {len(cur)} curves, {len(side)} sideloads, {len(ends)} dead ends - all intended '
                   f'(formers, taps, collectors, route turns; row ends; outputs)')
        lanes = [l for p in self.placed for l in p.lane_expect()]
        rep += check_flow(b, self.sources, self.exits, lanes)
        xs = [t[0] for e in b.ents for t in b.tiles(e)]
        assert all(t[0] == max(xs) for t, _ in self.sources), 'inputs not on the east edge'
        assert all(t[0] == min(xs) for t in self.exits), 'output not on the west edge'
        rep.append('inputs all on the east edge, output on the west edge')
        rep += check_fixed(b, self.cw, self.ch)
        return rep

    def count(self, recipe): return sum(e.get('recipe') == recipe for e in self.b.ents)

    def fit(self, make, dy, xmin, xmax=None, step=1, name=''):
        """Place band make(gaps) (unrotated) at the first dx >= xmin where it hits neither the grid nor anything
        placed, stays inside the cells and keeps its stubs/outputs off the grid-line columns."""
        occ = self.b.occupancy()
        xmax = xmax if xmax is not None else 50 * self.cw
        bd0 = make(())
        cache = {}
        for dx in range(xmin, xmax, step):
            g = auto_gaps(bd0.x0 + dx, bd0.nj)
            if g not in cache: cache[g] = make(g)
            bd = cache[g]
            tiles = {(t[0] + dx, t[1] + dy) for e in bd.b.ents for t in bd.b.tiles(e)}
            if any(not (4 <= x <= 50 * self.cw - 3 and 2 <= y <= 50 * self.ch - 3) for x, y in tiles): continue
            if bd.xs + dx > self.XE - 4: continue                       # leave room for the input gates
            if tiles & self.R.gtiles or any(t in occ for t in tiles): continue
            edge = [bd.xs + dx] + [o[0] + dx - (0 if bd.split_out else 0) for o in bd.OUTS]
            if any((x % 50) in (48, 49, 0, 1, 2, 3) for x in edge): continue
            return self.band(bd, dx=dx, dy=dy)
        raise AssertionError(f'{name}: no fit in x {xmin}..{xmax}')


def belts_text(rate):
    belt, _ = tier(rate)
    col = {'transport-belt': 'yellow', 'fast-transport-belt': 'red', 'express-transport-belt': 'blue'}[belt]
    return f'{col} ({rate:g}/s)'


def write_spec(path, F, label, description, icons, product, ratios, bottleneck, rep, check_in_game,
               makes_itself=(), log=()):
    """spec.yaml from the built plant (entity counts, inputs as gated)."""
    import yaml
    from collections import Counter
    ents = F.b.ents
    names = Counter(e['name'] for e in ents)
    recipes = Counter(e['recipe'] for e in ents if e.get('recipe'))
    inputs = [{'item': it, 'belt': belts_text(r), 'row': y} for it, r, y in F.inputs]
    spec = {
        'label': label, 'description': description,
        'icons': [{'type': 'item', 'name': i} for i in icons],
        'status': 'built',
        'request': {'product': product, 'rate': '1 full blue belt',
                    'inputs': 'belt colour sized to need: yellow <= 15/s, red <= 30/s, blue <= 45/s',
                    'makes_itself': list(makes_itself)},
        'result': {
            'footprint': {'cells': f'{F.cw}x{F.ch}', 'placement': 'not rotation-safe'},
            'inputs': inputs,
            'outputs': [{'item': product, 'belts': '1 full blue (45/s), west edge, both lanes'}],
            'machines': [{'entity': 'assembling-machine-3', 'recipe': r, 'count': n} for r, n in recipes.items()] +
                        [{'entity': n, 'count': c} for n, c in sorted(names.items()) if n != 'assembling-machine-3'],
            'ratios': ratios, 'bottleneck': bottleneck,
            'validators': rep},
        'check_in_game': list(check_in_game),
        'log': list(log)}
    path.write_text(yaml.safe_dump(spec, sort_keys=False, width=110, allow_unicode=True))


def right_aligned(make, x_end, x0=7):
    """Build band make(gaps) so that its stub column lands on world x_end with machine gaps for the grid
    poles. Returns (band, dx)."""
    gaps = ()
    for _ in range(10):
        bd = make(gaps); dx = x_end - bd.xs
        g2 = auto_gaps(x0 + dx, bd.nj)
        if g2 == gaps: return bd, dx
        gaps = g2
    raise AssertionError('gaps do not settle')
