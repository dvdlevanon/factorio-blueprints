"""Chemical-plant block with two item ingredients + one fluid: stacked modules of 2 mirrored rows.

Module k (oy = 11k), plants j = 0..P-1 at x = 3j..3j+2:
  oy        fluid pipe (row A ports; shared with the module above)
  oy+1..3   plants A (face N)
  oy+4      fast out (3j: plant -> out belt), long-handed in (3j+1: in belt -> plant), slot 3j+2
  oy+5      out belt -> W  (A drops on the south lane, B on the north lane)
  oy+6      in belt  -> W  (mixed: ingredient 1 | ingredient 2, one per lane)
  oy+7      fast in (3j+1: in belt -> plant), long-handed out (3j: plant -> out belt), slot 3j+2
  oy+8..10  plants B (face S)
  oy+11     fluid pipe (row B ports)
Slot 3j+2: medium pole for even j and the last plant, lamp for j = 1, 5, 9.
x = P*3 (XP): pipe-to-ground pairs link all pipe rows (under the in belts).
Trunk (mixed belt) at x = XP+2 flowing S; per module a south-facing splitter at (XP+1..XP+2, oy+5):
left output curves W into the module's in belt, right output continues; the last module takes a curve.
Trunk start (XP+2, 2): ingredient 1 sideloads from the east (row 2), ingredient 2 from the west
(arrives on row 1 from the east, turns S at XP+1, then E).
West: out belts go to x = -2. Top half: first module curves S, the others sideload; bottom half the
same flowing N. Both collectors sideload into the output tile (-2, ym) (ym = pipe row in the middle)
-> one lane each.
"""
from .build import BP, N, E, S, W, trace, tile_of, reach, fluid_networks

def build(modules, P, recipe, ing1, ing2, fluid, dual=False, gap=None):
    """dual: two trunks (modules 0-1 fed by trunk A flowing N, 2-3 by trunk B flowing S), each
    ingredient split in two by a splitter (for > one lane of each ingredient). gap = (j, w): leave w
    empty columns before plant j (e.g. for a grid pole)."""
    assert modules % 2 == 0 and (not dual or modules == 4)
    b = BP(); b.belt_name, b.ug_name = 'express-transport-belt', 'express-underground-belt'
    px = lambda j: 3 * j + (gap[1] if gap and j >= gap[0] else 0)
    XP = px(P - 1) + 3; T = XP + 2; H = 11 * modules
    exp_curves, exp_side = [], []
    for k in range(modules):
        oy = 11 * k
        for j in range(P):
            x = px(j)
            b.plant(x, oy + 1, N, recipe); b.plant(x, oy + 8, S, recipe)
            b.inserter(x, oy + 4, N); b.inserter(x + 1, oy + 4, S, 'long-handed-inserter')
            b.inserter(x + 1, oy + 7, N); b.inserter(x, oy + 7, S, 'long-handed-inserter')
            for y in (oy + 4, oy + 7):
                if j % 2 == 0 or j == P - 1 or (gap and j == gap[0]): b.add('medium-electric-pole', x + 2, y)
                elif j in (1, 5, 9): b.add('small-lamp', x + 2, y)
        for x in range(-1 if False else 0, XP): b.belt(x, oy + 5, W)          # out belt
        for x in range(0, T - 1): b.belt(x, oy + 6, W)                         # in belt up to XP
        # pipe link to the next pipe row
        b.ptg(XP, oy + 1, N); b.ptg(XP, oy + 10, S)
        if dual: continue
        # single trunk flowing S
        if k < modules - 1:
            b.splitter(T - 1, oy + 5, S); b.belt(T - 1, oy + 6, W); b.belt(T, oy + 6, S)
            for y in range(oy + 7, oy + 11 + 5): b.belt(T, y, S)
            exp_curves.append((T - 1, oy + 6))
        else:
            b.belt(T, oy + 5, S); b.belt(T, oy + 6, W); b.belt(T - 1, oy + 6, W)
            exp_curves.append((T, oy + 6))
    for k in range(modules + 1):
        for x in range(0, XP + 1): b.pipe(x, 11 * k)
    if not dual:
        # trunk start + inputs
        for y in range(2, 5): b.belt(T, y, S)
        b.belt(T + 1, 2, W); b.belt(T + 2, 2, W)                            # ingredient 1 (east lane)
        b.belt(T + 2, 1, W); b.belt(T + 1, 1, W); b.belt(T, 1, W); b.belt(T - 1, 1, S); b.belt(T - 1, 2, E)
        b.panel(T + 2, 3, ing1); b.panel(T + 2, 0, ing2)
        exp_curves += [(T - 1, 1), (T - 1, 2)]; exp_side.append((T, 2))
        starts = [(T + 2, 2), (T + 2, 1)]; XE = T + 2
    else:
        c1, c2 = T - 1, T; c = lambda i: XP + i; XE = c(9)
        # trunk A (N): modules 1 (splitter) and 0 (curve)
        b.belt(c2, 20, N); b.belt(c2, 19, N); b.splitter(c1, 18, N)
        b.belt(c1, 17, W); b.belt(c2, 17, N)
        for y in range(7, 17): b.belt(c2, y, N)
        b.belt(c2, 6, W); b.belt(c1, 6, W)
        # trunk B (S): modules 2 (splitter) and 3 (curve)
        for y in (24, 25, 26): b.belt(c2, y, S)
        b.splitter(c1, 27, S); b.belt(c1, 28, W); b.belt(c2, 28, S)
        for y in range(29, 39): b.belt(c2, y, S)
        b.belt(c2, 39, W); b.belt(c1, 39, W)
        # ingredient 1 (east lanes): enters row 20, splitter -> row 20 (A) and down column c4 to row 24 (B)
        for x in range(c(6), XE + 1): b.belt(x, 20, W)
        b.splitter(c(5), 20, W); b.belt(c(4), 20, W); b.belt(c(3), 20, W)
        for y in (21, 22, 23): b.belt(c(4), y, S)
        b.belt(c(4), 24, W); b.belt(c(3), 24, W)
        # ingredient 2 (west lanes): enters row 22, splitter -> row 21 (A) and row 23 (B), under column c4
        for x in range(c(8), XE + 1): b.belt(x, 22, W)
        b.splitter(c(7), 21, W)
        b.ug(c(6), 21, W, 'input'); b.ug(c(3), 21, W, 'output'); b.belt(c2, 21, W); b.belt(c1, 21, N); b.belt(c1, 20, E)
        b.belt(c(6), 22, S); b.belt(c(6), 23, W); b.ug(c(5), 23, W, 'input'); b.ug(c(3), 23, W, 'output')
        b.belt(c2, 23, W); b.belt(c1, 23, S); b.belt(c1, 24, E)
        b.panel(XE, 19, ing1); b.panel(XE, 23, ing2)
        exp_curves += [(c1, 17), (c2, 6), (c1, 28), (c2, 39), (c(4), 21), (c(4), 24), (c1, 21), (c1, 20),
                       (c(6), 22), (c(6), 23), (c1, 23), (c1, 24)]
        exp_side += [(c2, 20), (c2, 24)]
        starts = [(XE, 20), (XE, 22)]
    # fluid inlet (bottom pipe row)
    yi = H
    for x in range(XP + 1, XE + 1): b.pipe(x, yi)
    b.panel(XE, yi - 1, fluid, 'fluid')
    # west collectors
    ym = 11 * (modules // 2)
    outs = [11 * k + 5 for k in range(modules)]
    for k, y in enumerate(outs):
        b.belt(-1, y, W)
        top = y < ym
        if k == 0: b.belt(-2, y, S)
        elif k == modules - 1: b.belt(-2, y, N)
        else: b.belt(-2, y, S if top else N)
    for y in range(outs[0] + 1, ym):
        if y not in outs: b.belt(-2, y, S)
    for y in range(ym + 1, outs[-1]):
        if y not in outs: b.belt(-2, y, N)
    b.belt(-2, ym, W); b.belt(-3, ym, W)
    b.panel(-3, ym - 1, recipe)
    OUT = (-3, ym)
    exp_side += [(-2, ym)] + [(-2, y) for y in outs[1:-1]]
    exp_curves += [(-2, outs[0]), (-2, outs[-1])]

    def rules(ins, src, dst):
        if ins['name'] == 'fast-inserter' and src and src['name'] == 'chemical-plant' or \
           ins['name'] == 'long-handed-inserter' and src and src['name'] == 'chemical-plant':
            if not dst or dst['name'] != b.belt_name: return f'drops on {dst and dst["name"]}'
            if trace(b, tile_of(dst))[0][-1] != OUT: return 'output belt does not reach the output'
        else:
            if not src or src['name'] != b.belt_name: return f'picks from {src and src["name"]}'
            if all(tile_of(src) in reach(b, st) for st in starts) and trace(b, tile_of(src))[0][-1] != OUT:
                if not dst or dst['name'] != 'chemical-plant': return f'drops into {dst and dst["name"]}'
                return None
            return 'in inserter does not pick from the trunk-fed belt'
    return b, rules, dict(OUT=OUT, T=T, XP=XP, ym=ym, outs=outs, H=H, yi=yi, starts=starts,
                          curves=exp_curves, sideloads=exp_side, px=px)


def check_fluids(b):
    nets, touch = fluid_networks(b)
    assert len(nets) == 1, f'{len(nets)} pipe networks'
    plants = [e for e in b.ents if e['name'] == 'chemical-plant']
    for e in plants:
        t = touch.get(e['entity_number'], [])
        assert sorted(k for k, _ in t) == ['input', 'input'], f'plant at {e["position"]}: ports {t}'
    return f'fluids: 1 network, all {len(plants)} plants on both inputs, no outputs touching pipes'


def check_belts(b, belts, g, modules):
    want_ends = [g['OUT']] + [(0, 11 * k + 6) for k in range(modules)]
    assert sorted(belts['ends']) == sorted(want_ends), belts['ends']
    assert sorted(belts['sideloads']) == sorted(g['sideloads']), (sorted(belts['sideloads']), sorted(g['sideloads']))
    assert sorted(belts['curves']) == sorted(g['curves']), (sorted(belts['curves']), sorted(g['curves']))
    for k in range(modules):
        for st in g['starts']:
            assert (0, 11 * k + 6) in reach(b, st), f'module {k} in belt not fed from {st}'
    return (f'belts: ends = output + {modules} in-belt ends; sideloads = trunk start(s) (2 ingredients), '
            f'output merge, {modules - 2} collector joins; curves = all intended turns; every in belt fed by both inputs')
