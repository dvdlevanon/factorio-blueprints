"""Adapt David's existing grid-embedded designs (import/*.txt) to the current constraints:
- keep the corner roboports (alignment), drop the grid's big poles and lamps (they exist in the world),
  drop wires to them;
- yellow belts -> blue (constraint 9);
- re-validate: collisions (also against the real grid), power (blueprint medium poles + the grid's big
  poles), every pole group within 9 of a grid big pole (auto-connect, check in game), inserters have a
  pickup and a drop target, undergrounds paired, fluid machines' inputs on a pipe, panels icons only.
Frame: R0 = top-left roboport center = (0,0) (same as lib/cell.py).
"""
import json, math
from .bp import decode, VERSION
from .build import BP, SIZE, SUPPLY, REACH, POWERED, INSERTER_REACH, VEC, PORTS, tile_of, belt_check, fluid_networks

UPGRADE = {'transport-belt': 'express-transport-belt', 'underground-belt': 'express-underground-belt',
           'splitter': 'express-splitter'}
GRID_POLES = ((3, 0), (27, 0), (3, 23))
GRID_LAMPS = ((2.5, -1.5), (26.5, 1.5))
FLUID_RECIPES = {'processing-unit', 'electric-engine-unit', 'sulfuric-acid', 'sulfur', 'plastic-bar',
                 'lubricant', 'battery'}


def load(path):
    obj = decode(open(path).read().strip())
    return obj['blueprint']


def to_frame(bp):
    """BP in the R0 frame (top-left roboport center at (0,0)); returns (BP, roboport centers)."""
    rp = [e for e in bp['entities'] if e['name'] == 'roboport']
    x0 = min(e['position']['x'] for e in rp); y0 = min(e['position']['y'] for e in rp)
    b = BP()
    for e in bp['entities']:
        e = json.loads(json.dumps(e))
        e['position'] = {'x': e['position']['x'] - x0, 'y': e['position']['y'] - y0}
        b.ents.append(e)
    b.wires = [list(w) for w in bp.get('wires', [])]
    return b, sorted((e['position']['x'], e['position']['y']) for e in b.ents if e['name'] == 'roboport')


def grid_of(robos):
    """Grid entities implied by the roboport lattice: pole centers and lamp positions."""
    poles = {(rx + dx, ry + dy) for rx, ry in robos for dx, dy in GRID_POLES}
    lamps = {(rx + dx, ry + dy) for rx, ry in robos for dx, dy in GRID_LAMPS}
    return poles, lamps


def world_grid(robos, margin=1):
    """Tiles + big pole centers of the full grid around the lattice (incl. one ring outside)."""
    xs = sorted({x for x, _ in robos}); ys = sorted({y for _, y in robos})
    allx = [xs[0] - 50 * margin] + xs + [xs[-1] + 50 * margin]
    ally = [ys[0] - 50 * margin] + ys + [ys[-1] + 50 * margin]
    tiles, poles = set(), []
    for gx in allx:
        for gy in ally:
            gx, gy = int(gx), int(gy)
            tiles |= {(gx + i, gy + j) for i in range(-2, 2) for j in range(-2, 2)}
            for px, py in GRID_POLES:
                c = (gx + px, gy + py); poles.append(c)
                tiles |= {(c[0] + i, c[1] + j) for i in (-1, 0) for j in (-1, 0)}
            for lx, ly in GRID_LAMPS:
                tiles.add((int(math.floor(gx + lx)), int(math.floor(gy + ly))))
    return tiles, poles


def strip(b, robos):
    """Remove the grid's big poles and lamps (and wires to them); upgrade yellow belts. Renumber."""
    gp, gl = grid_of(robos)
    keep, gone = [], set()
    for e in b.ents:
        p = (e['position']['x'], e['position']['y'])
        if (e['name'] == 'big-electric-pole' and p in gp) or (e['name'] == 'small-lamp' and p in gl):
            gone.add(e['entity_number']); continue
        if e['name'] in UPGRADE: e['name'] = UPGRADE[e['name']]
        keep.append(e)
    remap = {e['entity_number']: i + 1 for i, e in enumerate(keep)}
    for e in keep: e['entity_number'] = remap[e['entity_number']]
    wires = []
    for w in b.wires:
        if w[0] in gone or w[2] in gone: continue
        wires.append([remap[w[0]], w[1], remap[w[2]], w[3]] + list(w[4:]))
    b.ents, b.wires = keep, wires
    return len(gone)


def rewire(b):
    """Replace copper pole wires with a minimum spanning forest over the blueprint's poles
    (reach = min of both ends); keep circuit wires. Returns the number of trees."""
    byid = {e['entity_number']: e for e in b.ents}
    poles = [e for e in b.ents if e['name'] in REACH]
    keep = [w for w in b.wires if not (w[1] == 5 and w[3] == 5)]
    import heapq
    pos = {e['entity_number']: (e['position']['x'], e['position']['y']) for e in poles}
    # grid bucket for neighbour search
    cell = {}
    for n, (x, y) in pos.items(): cell.setdefault((int(x // 9), int(y // 9)), []).append(n)
    def near(n):
        x, y = pos[n]
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for m in cell.get((int(x // 9) + i, int(y // 9) + j), []):
                    if m != n:
                        d = math.dist(pos[n], pos[m])
                        if d <= min(REACH[byid[n]['name']], REACH[byid[m]['name']]): yield d, m
    done, trees, wires = set(), 0, []
    for start in pos:
        if start in done: continue
        trees += 1; done.add(start); h = [(d, start, m) for d, m in near(start)]; heapq.heapify(h)
        while h:
            d, a, m = heapq.heappop(h)
            if m in done: continue
            done.add(m); wires.append([a, 5, m, 5])
            for d2, k in near(m):
                if k not in done: heapq.heappush(h, (d2, m, k))
    b.wires = keep + wires
    return trees


def check(b, robos):
    rep = []
    unknown = {e['name'] for e in b.ents} - set(SIZE)
    assert not unknown, f'unknown entity sizes {unknown}'
    occ = b.occupancy()
    rep.append(f'collisions: none ({len(b.ents)} entities)')
    gtiles, gpoles = world_grid(robos)
    rp_tiles = {t for e in b.ents if e['name'] == 'roboport' for t in b.tiles(e)}
    hit = (set(occ) - rp_tiles) & gtiles
    assert not hit, f'collides with the grid at {sorted(hit)[:5]}'
    rep.append('grid: no collision with the grid roboports / big poles / lamps')
    # power: blueprint poles + grid big poles (supply 2)
    sup = [(e['position']['x'], e['position']['y'], SUPPLY[e['name']]) for e in b.ents if e['name'] in SUPPLY]
    sup += [(x, y, SUPPLY['big-electric-pole']) for x, y in gpoles]
    for e in b.ents:
        if e['name'] not in POWERED: continue
        ok = any(any(abs(tx + .5 - x) < s + .5 and abs(ty + .5 - y) < s + .5 for tx, ty in b.tiles(e)) for x, y, s in sup)
        assert ok, f'unpowered {e["name"]} at {e["position"]}'
    rep.append('power: every powered entity in a pole supply area (grid big poles included)')
    # wired groups -> each needs a pole within reach of a grid big pole
    poles = [e for e in b.ents if e['name'] in REACH]
    adj = {e['entity_number']: set() for e in poles}
    for w in b.wires:
        if w[1] == 5 and w[3] == 5 and w[0] in adj and w[2] in adj: adj[w[0]].add(w[2]); adj[w[2]].add(w[0])
    byid = {e['entity_number']: e for e in b.ents}
    seen, worst, groups = set(), 0, 0
    for p in adj:
        if p in seen: continue
        grp, st = set(), [p]
        while st:
            u = st.pop()
            if u not in grp: grp.add(u); st += adj[u]
        seen |= grp; groups += 1
        d = min(math.dist((byid[u]['position']['x'], byid[u]['position']['y']), g) for u in grp for g in gpoles
                if True) if grp else 99
        reach = max(REACH[byid[u]['name']] for u in grp)
        assert d <= reach, f'pole group of {len(grp)} has no pole within reach of a grid big pole ({d:.1f})'
        worst = max(worst, d)
    rep.append(f'pole network: {groups} wired group(s), each within reach of a grid big pole (max {worst:.1f}); '
               f'links to the grid rely on in-game auto-connect')
    # inserters
    bad = []
    for e in b.ents:
        if e['name'] not in INSERTER_REACH: continue
        k = INSERTER_REACH[e['name']]; x, y = tile_of(e); vx, vy = VEC[e.get('direction', 0)]
        if not occ.get((x + vx * k, y + vy * k)) or not occ.get((x - vx * k, y - vy * k)): bad.append((x, y))
    assert not bad, f'inserters without pickup/drop target at {bad[:5]}'
    rep.append(f'inserters: all {sum(e["name"] in INSERTER_REACH for e in b.ents)} have a pickup and a drop target')
    r2, info = belt_check(b); rep += r2
    # fluids
    nets, touch = fluid_networks(b)
    for e in b.ents:
        if e['name'] in PORTS and e.get('recipe') in FLUID_RECIPES:
            kinds = [k for k, _ in touch.get(e['entity_number'], [])]
            assert 'input' in kinds, f'{e["recipe"]} at {e["position"]} has no pipe on a fluid input'
    rep.append(f'fluids: {len(nets)} pipe network(s); every fluid machine has a pipe on an input')
    assert not any(e['name'] == 'display-panel' and e.get('text') for e in b.ents), 'panel with text'
    assert not any('items' in e for e in b.ents), 'modules present'
    assert not any(e['name'] == 'beacon' for e in b.ents), 'beacons present'
    rep.append('panels icons only; no modules, no beacons')
    return rep, info


def finish(b, label, icons, description=None):
    x0, y0, _, _ = b.bbox()
    b.shift(-x0, -y0)
    bp = {'item': 'blueprint', 'label': label, 'icons': icons, 'entities': b.ents, 'wires': b.wires}
    if description: bp['description'] = description
    bp['version'] = VERSION
    return bp
