"""Horizontal rows of assemblers fed by mixed belts (the flying-robot-frame layout, generalised).

2 ingredients -> one mixed belt M per pair of rows (pitch 12):
  0 out belt | 1 out inserters | 2..4 machines A | 5 fast (picks M) | 6 M | 7 fast | 8..10 machines B
  11 out inserters | 12 = next pair's out belt
4 ingredients -> two mixed belts A, B per pair (pitch 13):
  0 out | 1 out ins | 2..4 machines A | 5 fast (near A) + long (far B) | 6 A | 7 B | 8 fast (B) + long (A)
  9..11 machines B | 12 out ins | 13 = next out
Lanes: A/M = ings[0] | ings[1], B = ings[2] | ings[3]. Each belt forms at a tile facing S at the east end
(ings[0]/[2] sideloaded from the west, ings[1]/[3] from the east), then curves W into its row.
Distribution: ingredient k turns S into column D[k] on entry row 2+k; a splitter per column at every pair but
the last sends a share W on the pair's feed row (underground under the columns to its west); the last pair
takes the rest by a curve.
Output: the out rows run W into two collectors at x=col (top half flows S, bottom half N) that sideload the
output tile (col, yo) from both sides; the output leaves W at col-1.
"""
import math
from .build import BP, N, E, S, W, trace, tile_of, reach

TIERS = ((15, 'transport-belt', 'underground-belt'), (30, 'fast-transport-belt', 'fast-underground-belt'),
         (45, 'express-transport-belt', 'express-underground-belt'))


def tier(rate):
    """Belt + underground names for a belt that must carry `rate` items/s (yellow / red / blue)."""
    for cap, belt, ug in TIERS:
        if rate <= cap + 1e-9: return belt, ug
    raise ValueError(f'{rate}/s needs more than one blue belt')


class Rows:
    def __init__(self, b, recipe, ings, nj, pairs, x0=7, gaps=(), xa=None, d0=None, col=5, rates=None):
        assert len(ings) in (2, 4)
        self.b, self.recipe, self.ings, self.nj, self.pairs = b, recipe, ings, nj, pairs
        self.nb = len(ings) // 2
        self.pitch = 12 if self.nb == 1 else 13
        self.x0, self.gaps, self.col = x0, gaps, col
        self.xa = xa if xa is not None else self.ax(nj - 1) + 5
        self.xb = self.xa + 2
        east = self.xb if self.nb == 2 else self.xa
        self.d = [(d0 if d0 is not None else east + 3) + 3 * k for k in range(len(ings))]
        self.feeds = (1, 2) if self.nb == 1 else (1, 2, 3, 4)
        self.curves, self.sideloads, self.ends = [], [], []
        self.rates = rates or {}

    def ax(self, j):
        return self.x0 + 3 * j + 2 * sum(j >= g for g in self.gaps)

    def out_rows(self):
        return [yb for yb in self.pairs] + [self.pairs[-1] + self.pitch]

    def belt_rows(self, yb):
        return [yb + 6] if self.nb == 1 else [yb + 6, yb + 7]

    # ------------------------------------------------------------------ build
    def build(self):
        b, L = self.b, 'long-handed-inserter'
        for yb in self.pairs:
            if self.nb == 1:
                rows = ((yb + 2, yb + 5, yb + 1, S, S), (yb + 8, yb + 7, yb + 11, N, N))
            else:
                rows = ((yb + 2, yb + 5, yb + 1, S, S), (yb + 9, yb + 8, yb + 12, N, N))
            for top, ab, outr, pick_ab, pick_out in rows:
                for j in range(self.nj):
                    x = self.ax(j)
                    b.asm(x, top, self.recipe)
                    if self.nb == 1:
                        b.inserter(x + 1, ab, pick_ab)
                    else:
                        b.inserter(x, ab, pick_ab); b.inserter(x + 1, ab, pick_ab, L)
                    b.inserter(x + 1, outr, pick_out)
                    if j % 2 == 0 or j in self.gaps or j == self.nj - 1:
                        b.add('medium-electric-pole', x + 2, ab); b.add('medium-electric-pole', x + 2, outr)
                    elif j % 4 == 3:
                        b.add('small-lamp', x + 2, ab)
            self._formers(yb)
        self._columns()
        self._output()

    def _formers(self, yb):
        b, xa, xb, f0 = self.b, self.xa, self.xb, self.d[0] - 3
        # A / M: former (xa, yb+2) facing S -> curve W into row yb+6
        for y in range(yb + 2, yb + 6): b.belt(xa, y, S)
        for x in range(self.x0, xa + 1): b.belt(x, yb + 6, W)
        self.curves.append((xa, yb + 6)); self.sideloads.append((xa, yb + 2)); self.ends.append((self.x0, yb + 6))
        for x in range(xa, f0 + 1): b.belt(x, yb + 1, W)                 # ings[0] (west side)
        b.belt(xa - 1, yb + 1, S); b.belt(xa - 1, yb + 2, E)
        for x in range(xa + 1, f0 + 1): b.belt(x, yb + 2, W)             # ings[1] (east side)
        self.curves += [(xa - 1, yb + 1), (xa - 1, yb + 2)]
        if self.nb == 2:
            for y in range(yb + 4, yb + 7): b.belt(xb, y, S)
            for x in range(self.x0, xb + 1): b.belt(x, yb + 7, W)
            self.curves.append((xb, yb + 7)); self.sideloads.append((xb, yb + 4)); self.ends.append((self.x0, yb + 7))
            for x in range(xb, f0 + 1): b.belt(x, yb + 3, W)             # ings[2]
            b.belt(xb - 1, yb + 3, S); b.belt(xb - 1, yb + 4, E)
            for x in range(xb + 1, f0 + 1): b.belt(x, yb + 4, W)         # ings[3]
            self.curves += [(xb - 1, yb + 3), (xb - 1, yb + 4)]
        # taps
        last = yb == self.pairs[-1]
        for k, f in enumerate(self.feeds):
            y, dk = yb + f, self.d[k]
            if not last:
                b.splitter(dk - 1, y - 1, S); b.belt(dk - 1, y, W); b.belt(dk, y, S)
                self.curves.append((dk - 1, y))
            else:
                b.belt(dk, y, W); b.belt(dk - 1, y, W)
                self.curves.append((dk, y))
            if k == 0: b.belt(self.d[0] - 2, y, W)
            else: b.ug(dk - 2, y, W, 'input'); b.ug(self.d[0] - 2, y, W, 'output')

    def _columns(self):
        b = self.b
        for k, f in enumerate(self.feeds):
            dk, r = self.d[k], 2 + k
            b.belt(dk, r, S); self.curves.append((dk, r))
            stops = [yb + f - 1 for yb in self.pairs[:-1]]
            for s0, s1 in zip([r + 1] + [s + 2 for s in stops], stops + [self.pairs[-1] + f]):
                for y in range(s0, s1): b.belt(dk, y, S)

    def entry(self, k, xe):
        """External input k entering on row 2+k at x = xe (marked by a panel between an underground pair),
        belt tier sized to rates[ings[k]]."""
        b, r, dk = self.b, 2 + k, self.d[k]
        belt, ug = tier(self.rates[self.ings[k]])
        keep = b.belt_name, b.ug_name
        b.belt_name, b.ug_name = belt, ug
        for x in range(dk + 1, xe - 2): b.belt(x, r, W)
        b.ug(xe - 2, r, W, 'output'); b.panel(xe - 1, r, self.ings[k]); b.ug(xe, r, W, 'input')
        b.belt_name, b.ug_name = keep
        return (xe, r)

    def _output(self):
        b, col = self.b, self.col
        outs = self.out_rows(); h = math.ceil(len(outs) / 2)
        self.yo = yo = (outs[h - 1] + outs[h]) // 2
        for y in outs:
            for x in range(col + 1, self.ax(self.nj - 1) + 3): b.belt(x, y, W)
        b.belt(col, outs[0], S)
        for y in range(outs[0] + 1, yo): b.belt(col, y, S)
        b.belt(col, outs[-1], N)
        for y in range(yo + 1, outs[-1]): b.belt(col, y, N)
        b.belt(col, yo, W); b.belt(col - 1, yo, W)
        b.panel(col - 1, yo - 1, self.recipe)
        self.OUT = (col - 1, yo)
        self.curves += [(col, outs[0]), (col, outs[-1])]
        self.sideloads += [(col, yo)] + [(col, y) for y in outs[1:-1]]
        self.ends.append(self.OUT)

    # ------------------------------------------------------------------ checks
    def rules(self):
        """Inserter rules: out inserters reach the output; input inserters pick a belt that carries exactly
        one lane pair. Records what each machine can reach in self.got."""
        b, ings = self.b, self.ings
        R = {it: reach(b, (self.d[k], 2 + k)) for k, it in enumerate(ings)}
        assert not any(self.OUT in r for r in R.values()), 'an input reaches the output'
        pairs = [set(ings[0:2])] + ([set(ings[2:4])] if self.nb == 2 else [])
        self.got = {}
        def rule(ins, src, dst):
            sn, dn = src and src['name'], dst and dst['name']
            if sn == 'assembling-machine-3' and src.get('recipe') == self.recipe:
                if not dst or trace(b, tile_of(dst))[0][-1] != self.OUT: return 'product does not reach the output'
                return None
            if dn != 'assembling-machine-3' or dst.get('recipe') != self.recipe: return None   # not ours
            its = {it for it, r in R.items() if tile_of(src) in r}
            if its not in pairs: return f'picks from a belt with {its}'
            self.got.setdefault(dst['entity_number'], set()).update(its)
        self.R = R
        return rule

    def check(self, belts):
        """After validate(): every machine reaches all ingredients; each ingredient reaches one former per pair."""
        b = self.b
        asms = [e for e in b.ents if e['name'] == 'assembling-machine-3' and e.get('recipe') == self.recipe]
        assert all(self.got.get(e['entity_number']) == set(self.ings) for e in asms), 'a machine misses an ingredient'
        formers = [(self.xa, yb + 2) for yb in self.pairs] + ([(self.xb, yb + 4) for yb in self.pairs] if self.nb == 2 else [])
        for it, r in self.R.items():
            assert len([t for t in formers if t in r]) == len(self.pairs), f'{it} does not reach one former per pair'
        return [f'every one of {len(asms)} {self.recipe} machines reaches all {len(self.ings)} ingredients; '
                f'each input reaches one former per pair']
