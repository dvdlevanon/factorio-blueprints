"""Small blueprint builder + validators (tile-based, vanilla 2.1 data, verified numbers noted)."""
import math

N, E, S, W = 0, 4, 8, 12
VEC = {N: (0, -1), E: (1, 0), S: (0, 1), W: (-1, 0)}
OPP = {N: S, S: N, E: W, W: E}

# footprint in tiles (data/base entities.lua 2.1.24)
SIZE = {'roboport': 4, 'big-electric-pole': 2, 'medium-electric-pole': 1, 'small-lamp': 1,
        'solar-panel': 3, 'accumulator': 2, 'requester-chest': 1, 'storage-chest': 1,
        'fast-inserter': 1, 'transport-belt': 1, 'underground-belt': 1, 'display-panel': 1,
        'long-handed-inserter': 1, 'express-transport-belt': 1, 'express-underground-belt': 1,
        'chemical-plant': 3, 'pipe': 1, 'pipe-to-ground': 1, 'express-splitter': 1,
        'bulk-inserter': 1, 'assembling-machine-3': 3,
        'fast-transport-belt': 1, 'fast-underground-belt': 1, 'fast-splitter': 1, 'splitter': 1,
        'rocket-silo': 9}
BELTS = {'transport-belt', 'fast-transport-belt', 'express-transport-belt'}
UGS = {'underground-belt', 'fast-underground-belt', 'express-underground-belt'}
SPLITTERS = {'splitter', 'fast-splitter', 'express-splitter'}            # 1 tile along the flow, 2 across
INSERTER_REACH = {'fast-inserter': 1, 'long-handed-inserter': 2, 'bulk-inserter': 1}       # pickup_position (0,-1) / (0,-2)
PTG_MAX = 10                                                          # pipe-to-ground max_underground_distance
# chemical plant (direction N): inputs at (-1,-1),(1,-1) facing N, outputs at (-1,1),(1,1) facing S
SUPPLY = {'medium-electric-pole': 3.5, 'big-electric-pole': 2}       # supply_area_distance
REACH = {'medium-electric-pole': 9, 'big-electric-pole': 32}          # maximum_wire_distance
POWERED = {'roboport', 'fast-inserter', 'small-lamp', 'display-panel', 'long-handed-inserter', 'chemical-plant',
           'bulk-inserter', 'assembling-machine-3', 'rocket-silo'}  # display panel: no power needed? see note
POWERED.discard('display-panel')
UG_MAX = {'underground-belt': 5, 'fast-underground-belt': 7, 'express-underground-belt': 9}   # transport-belts.lua       # max_distance
LAMP_COLOR = {'r': 1, 'g': 1, 'b': 0.75, 'a': 1}


class BP:
    def __init__(self):
        self.ents, self.wires = [], []

    def add(self, name, tx, ty, **kw):
        """tx, ty = top-left tile."""
        s = SIZE[name]
        e = {'entity_number': len(self.ents) + 1, 'name': name,
             'position': {'x': tx + s / 2, 'y': ty + s / 2}, **kw}
        if name == 'small-lamp': e.setdefault('color', LAMP_COLOR)
        self.ents.append(e)
        return e['entity_number']

    belt_name, ug_name = 'transport-belt', 'underground-belt'          # set to express-* for blue

    def belt(self, tx, ty, d): return self.add(self.belt_name, tx, ty, direction=d)
    def ug(self, tx, ty, d, io): return self.add(self.ug_name, tx, ty, direction=d, type=io)
    def inserter(self, tx, ty, pickup, name='fast-inserter'): return self.add(name, tx, ty, direction=pickup)
    def panel(self, tx, ty, item, kind='item'): return self.add('display-panel', tx, ty, icon={'type': kind, 'name': item})
    def splitter(self, tx, ty, d, name='express-splitter'):
        """tx, ty = top-left of its 2 tiles (stacked in y when flowing E/W, side by side when N/S)."""
        n = self.add(name, tx, ty, direction=d)
        e = self.ents[-1]
        e['position'] = {'x': tx + .5, 'y': ty + 1} if d in (E, W) else {'x': tx + 1, 'y': ty + .5}
        return n
    def asm(self, tx, ty, recipe): return self.add('assembling-machine-3', tx, ty, recipe=recipe)
    def pipe(self, tx, ty): return self.add('pipe', tx, ty)
    def ptg(self, tx, ty, d): return self.add('pipe-to-ground', tx, ty, direction=d)   # d = above-ground side
    def plant(self, tx, ty, d, recipe): return self.add('chemical-plant', tx, ty, direction=d, recipe=recipe)
    def requester(self, tx, ty, item, count, active=True, bar=None):
        sec = {'index': 1, 'filters': [{'index': 1, 'name': item, 'quality': 'normal', 'comparator': '=', 'count': count}]}
        if not active: sec['active'] = False                    # section switched off (draftsman format)
        kw = {'bar': bar} if bar else {}                          # bar = usable slots (draftsman format)
        return self.add('requester-chest', tx, ty, request_filters={'sections': [sec]}, **kw)
    def storage(self, tx, ty, item=None, bar=None):
        kw = {'bar': bar} if bar else {}
        if item:
            kw['request_filters'] = {'sections': [{'index': 1, 'filters': [
                {'index': 1, 'name': item, 'quality': 'normal', 'comparator': '='}]}]}
        return self.add('storage-chest', tx, ty, **kw)

    def wire_poles(self):
        """Minimum spanning tree over poles (reach = min of both ends)."""
        poles = [e for e in self.ents if e['name'] in REACH]
        if not poles: return
        inside, rest = {poles[0]['entity_number']}, poles[1:]
        P = {e['entity_number']: e for e in poles}
        while rest:
            best = None
            for e in rest:
                for i in inside:
                    d = dist(e, P[i])
                    if d <= min(REACH[e['name']], REACH[P[i]['name']]) and (best is None or d < best[0]):
                        best = (d, i, e)
            assert best, 'poles cannot be wired into one network'
            _, i, e = best
            self.wires.append([i, 5, e['entity_number'], 5]); inside.add(e['entity_number']); rest.remove(e)

    def tiles(self, e):
        if e['name'] in SPLITTERS:
            x, y = e['position']['x'], e['position']['y']
            if e.get('direction', 0) in (E, W): return [(int(math.floor(x)), int(y) - 1), (int(math.floor(x)), int(y))]
            return [(int(x) - 1, int(math.floor(y))), (int(x), int(math.floor(y)))]
        s = SIZE[e['name']]; x0, y0 = e['position']['x'] - s / 2, e['position']['y'] - s / 2
        return [(int(x0) + i, int(y0) + j) for i in range(s) for j in range(s)]

    def occupancy(self):
        occ = {}
        for e in self.ents:
            for t in self.tiles(e):
                assert t not in occ, f'collision at {t}: {e["name"]} vs {occ[t]["name"]}'
                occ[t] = e
        return occ

    def bbox(self):
        ts = [t for e in self.ents for t in self.tiles(e)]
        return min(x for x, _ in ts), min(y for _, y in ts), max(x for x, _ in ts), max(y for _, y in ts)

    def shift(self, dx, dy):
        for e in self.ents:
            e['position']['x'] += dx; e['position']['y'] += dy


def dist(a, b):
    return math.dist((a['position']['x'], a['position']['y']), (b['position']['x'], b['position']['y']))


def tile_of(e):
    return int(math.floor(e['position']['x'])), int(math.floor(e['position']['y']))


def validate(bp: BP, inserter_rules, grid_poles=None):
    """Returns report lines; raises AssertionError on failure.
    inserter_rules(ins, src, dst) -> None or error string.
    grid_poles: list of (x, y) centers of grid big poles the block must reach with a medium pole (<= 9)."""
    rep = []
    occ = bp.occupancy(); rep.append(f'collisions: none ({len(bp.ents)} entities)')
    poles = [e for e in bp.ents if e['name'] in SUPPLY]
    for e in bp.ents:
        if e['name'] not in POWERED: continue
        ts = bp.tiles(e)
        ok = any(any(abs(tx + .5 - p['position']['x']) < SUPPLY[p['name']] + .5 and
                     abs(ty + .5 - p['position']['y']) < SUPPLY[p['name']] + .5 for tx, ty in ts) for p in poles)
        assert ok, f'unpowered {e["name"]} at {e["position"]}'
    byid = {e['entity_number']: e for e in bp.ents}
    adj = {p['entity_number']: set() for p in poles}
    for a, _, b, _ in bp.wires:
        assert dist(byid[a], byid[b]) <= min(REACH[byid[a]['name']], REACH[byid[b]['name']])
        adj[a].add(b); adj[b].add(a)
    seen, st = set(), [poles[0]['entity_number']]
    while st:
        p = st.pop()
        if p not in seen: seen.add(p); st += adj[p]
    assert len(seen) == len(poles), 'poles not in one network'
    rep.append(f'power: all powered, {len(poles)} poles in one network')
    if grid_poles:
        d = min(math.dist((p['position']['x'], p['position']['y']), g) for p in poles
                if p['name'] == 'medium-electric-pole' for g in grid_poles)
        assert d <= 9, f'no medium pole within 9 of a grid big pole (closest {d:.1f})'
        rep.append(f'grid link: medium pole {d:.1f} tiles from a grid big pole (<= 9)')
    # inserters
    for e in bp.ents:
        if e['name'] not in INSERTER_REACH: continue
        k = INSERTER_REACH[e['name']]
        x, y = tile_of(e); vx, vy = VEC[e.get('direction', 0)]
        src, dst = occ.get((x + vx * k, y + vy * k)), occ.get((x - vx * k, y - vy * k))
        err = inserter_rules(e, src, dst)
        assert not err, f'inserter at {(x, y)}: {err}'
    rep.append('inserters: every pickup/drop target as expected')
    r2, info = belt_check(bp)
    return rep + r2, info


def belt_check(bp: BP):
    """Undergrounds paired; list curves, sideloads, dead ends. Returns (report lines, info)."""
    rep = []
    belts = belt_tiles(bp)
    ug_pair = {}
    for t, e in belts.items():
        if e['name'] in UGS and e.get('type', 'input') == 'input':
            vx, vy = VEC[e.get('direction', 0)]
            for k in range(1, UG_MAX[e['name']] + 1):
                o = belts.get((t[0] + vx * k, t[1] + vy * k))
                if o and o['name'] == e['name'] and o.get('direction', 0) == e.get('direction', 0):
                    assert o.get('type', 'input') == 'output', f'underground at {t}: next one is not an exit'
                    ug_pair[t] = (t[0] + vx * k, t[1] + vy * k); break
            assert t in ug_pair, f'underground entrance at {t} has no exit within range'
    outs = [t for t, e in belts.items() if e['name'] in UGS and e.get('type', 'input') == 'output']
    assert len(outs) == len(ug_pair), 'unpaired underground exit'
    feeders = {t: [] for t in belts}
    ends, curves, sides = [], [], []
    for t, e in belts.items():
        if e['name'] in UGS and e.get('type', 'input') == 'input':
            continue  # goes underground
        vx, vy = VEC[e.get('direction', 0)]; n = (t[0] + vx, t[1] + vy)
        if n in belts:
            assert belts[n].get('direction', 0) != OPP[e.get('direction', 0)], f'belt at {t} faces into opposite belt'
            feeders[n].append((t, e.get('direction', 0)))
        else:
            ends.append(t)
    for t, fs in feeders.items():
        d = belts[t].get('direction', 0)
        behind = [f for f in fs if f[1] == d]
        side = [f for f in fs if f[1] != d]
        if side and not behind and len(side) == 1 and belts[t]['name'] in BELTS:
            curves.append(t)
        elif side:
            sides.append(t)
    rep.append(f'belts: {len(curves)} curves, {len(sides)} sideloads, {len(ends)} dead ends, '
               f'{len(ug_pair)} underground pairs')
    return rep, dict(curves=curves, sideloads=sides, ends=ends)


def belt_tiles(bp: BP):
    """tile -> belt-like entity (belts, undergrounds, each tile of a splitter)."""
    return {t: e for e in bp.ents if e['name'] in BELTS | UGS | SPLITTERS for t in bp.tiles(e)}


def trace(bp: BP, start):
    """Follow belts from tile `start`. Returns (path tiles, tiles jumped by undergrounds)."""
    belts = belt_tiles(bp)
    path, jumped, t = [], [], start
    while t in belts and t not in path:
        path.append(t); e = belts[t]; vx, vy = VEC[e.get('direction', 0)]
        if e['name'] in UGS and e.get('type', 'input') == 'input':
            for k in range(1, UG_MAX[e['name']] + 1):
                o = (t[0] + vx * k, t[1] + vy * k)
                if o in belts and belts[o]['name'] in UGS and belts[o].get('type', 'input') == 'output':
                    t = o; break
                jumped.append(o)
            continue
        t = (t[0] + vx, t[1] + vy)
    return path, jumped


def panels_on(bp: BP, tiles):
    occ = {tile_of(e): e for e in bp.ents if e['name'] == 'display-panel'}
    return [occ[t]['icon']['name'] for t in tiles if t in occ]


def rot(v, d):
    """Rotate tile vector v (given for direction N) to direction d (N/E/S/W)."""
    x, y = v
    for _ in range(d // 4): x, y = -y, x
    return x, y


PORTS = {'chemical-plant': (('input', (-1, -1), N), ('input', (1, -1), N), ('output', (-1, 1), S), ('output', (1, 1), S)),
         'assembling-machine-3': (('input', (0, -1), N), ('output', (0, 1), S))}   # entities.lua 2.1.24


def plant_ports(e):
    """Fluid machine -> {'input': [(own tile, target tile)], 'output': [...]}, rotated by direction."""
    cx, cy = e['position']['x'], e['position']['y']; d = e.get('direction', N)
    out = {}
    for kind, pos, face in PORTS[e['name']]:
        px, py = rot(pos, d); fx, fy = VEC[(face + d) % 16]
        own = (int(math.floor(cx + px)), int(math.floor(cy + py)))
        out.setdefault(kind, []).append((own, (own[0] + fx, own[1] + fy)))
    return out


def fluid_networks(bp: BP):
    """Flood-fill pipe networks. Returns (list of sets of pipe tiles, {plant entity_number: ports})."""
    occ = bp.occupancy()
    pipes = {tile_of(e): e for e in bp.ents if e['name'] in ('pipe', 'pipe-to-ground')}
    plants = [e for e in bp.ents if e['name'] in PORTS]
    ports = {e['entity_number']: plant_ports(e) for e in plants}
    port_at = {}                                  # pipe tile -> list of (plant, kind) connecting into it
    for e in plants:
        for kind, lst in ports[e['entity_number']].items():
            for own, tgt in lst: port_at.setdefault(tgt, []).append((e, kind, own))
    def sides(t):
        e = pipes[t]
        if e['name'] == 'pipe': return [VEC[d] for d in (N, E, S, W)]
        return [VEC[e.get('direction', 0)]]
    def nbrs(t):
        res = []
        for vx, vy in sides(t):
            n = (t[0] + vx, t[1] + vy)
            if n in pipes and (-vx, -vy) in sides(n): res.append(n)
        e = pipes[t]
        if e['name'] == 'pipe-to-ground':          # underground: nearest ptg behind, facing back
            vx, vy = VEC[OPP[e.get('direction', 0)]]
            for k in range(1, PTG_MAX + 1):
                n = (t[0] + vx * k, t[1] + vy * k)
                if n in pipes and pipes[n]['name'] == 'pipe-to-ground' and pipes[n].get('direction', 0) in (e.get('direction', 0), OPP[e.get('direction', 0)]):
                    assert pipes[n].get('direction', 0) == OPP[e.get('direction', 0)], f'pipe-to-ground at {t}: next one faces the same way'
                    res.append(n); break
            else:
                raise AssertionError(f'pipe-to-ground at {t} has no partner within {PTG_MAX}')
        return res
    seen, nets = set(), []
    for t in pipes:
        if t in seen: continue
        net, st = set(), [t]
        while st:
            u = st.pop()
            if u in net: continue
            net.add(u); st += nbrs(u)
        seen |= net; nets.append(net)
    # which plant ports touch which pipe: a pipe tile at the port target, with a side facing the plant
    touch = {}
    for tgt, lst in port_at.items():
        if tgt not in pipes: continue
        for e, kind, own in lst:
            v = (own[0] - tgt[0], own[1] - tgt[1])
            if v in sides(tgt): touch.setdefault(e['entity_number'], []).append((kind, tgt))
    return nets, touch


def reach(bp: BP, start):
    """All belt tiles reachable from tile `start` following flow (splitters feed both outputs,
    sideloads continue on the target belt, undergrounds jump)."""
    belts = belt_tiles(bp)
    seen, st = set(), [start]
    while st:
        t = st.pop()
        if t in seen or t not in belts: continue
        seen.add(t); e = belts[t]; vx, vy = VEC[e.get('direction', 0)]
        if e['name'] in UGS and e.get('type', 'input') == 'input':
            for k in range(1, UG_MAX[e['name']] + 1):
                o = (t[0] + vx * k, t[1] + vy * k)
                if o in belts and belts[o]['name'] in UGS and belts[o].get('type', 'input') == 'output':
                    st.append(o); break
        elif e['name'] in SPLITTERS:
            st += [(u[0] + vx, u[1] + vy) for u in bp.tiles(e)] + [u for u in bp.tiles(e)]
        else:
            st.append((t[0] + vx, t[1] + vy))
    return seen
