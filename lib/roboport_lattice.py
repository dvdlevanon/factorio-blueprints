"""NX x NY roboport lattice, same layout as David's 'Roboport Huge' (calibration.txt).

Per roboport R (relative to its center, +x east, +y south):
  big pole (3,0), lamp (2.5,-1.5)           every roboport
  big pole (27,0), lamp (26.5,1.5)          between columns (not after the last one)
  big pole (3,23)                            between rows (not after the last one)
Wires: horizontal chain along each roboport row, vertical chain down each column.
Snapping copied from the calibration export.
"""
import math
from .bp import VERSION

PITCH = 50
ORIGIN = (2, 2)            # first roboport center, as in the calibration export
SNAP = {'snap-to-grid': {'x': 50, 'y': 50}, 'absolute-snapping': True,
        'position-relative-to-grid': {'x': 192, 'y': 185}}
LAMP_COLOR = {'r': 1, 'g': 1, 'b': 0.75, 'a': 1}
POLE_REACH = 32            # big-electric-pole maximum_wire_distance (data/base entities.lua, 2.1.24)

def build(n: int, label: str, ny: int = None) -> dict:
    nx, ny = n, (n if ny is None else ny)
    ents, wires = [], []
    def add(name, x, y, **kw):
        e = {'entity_number': len(ents) + 1, 'name': name, 'position': {'x': x, 'y': y}, **kw}
        ents.append(e); return e['entity_number']
    pole = {}  # (i, j, kind) -> entity number; kind: 'r' (3,0), 'h' (27,0), 'v' (3,23)
    for j in range(ny):
        for i in range(nx):
            rx, ry = ORIGIN[0] + PITCH * i, ORIGIN[1] + PITCH * j
            add('roboport', rx, ry, request_filters={'sections': [{'index': 1}]})
            add('small-lamp', rx + 2.5, ry - 1.5, color=LAMP_COLOR)
            pole[i, j, 'r'] = add('big-electric-pole', rx + 3, ry)
            if i < nx - 1:
                pole[i, j, 'h'] = add('big-electric-pole', rx + 27, ry)
                add('small-lamp', rx + 26.5, ry + 1.5, color=LAMP_COLOR)
            if j < ny - 1:
                pole[i, j, 'v'] = add('big-electric-pole', rx + 3, ry + 23)
    for j in range(ny):
        for i in range(nx - 1):
            wires.append([pole[i, j, 'r'], 5, pole[i, j, 'h'], 5])
            wires.append([pole[i, j, 'h'], 5, pole[i + 1, j, 'r'], 5])
    for i in range(nx):
        for j in range(ny - 1):
            wires.append([pole[i, j, 'r'], 5, pole[i, j, 'v'], 5])
            wires.append([pole[i, j, 'v'], 5, pole[i, j + 1, 'r'], 5])
    return {'item': 'blueprint', 'label': label,
            'icons': [{'signal': {'name': 'roboport'}, 'index': 1}],
            **SNAP, 'entities': ents, 'wires': wires, 'version': VERSION}

def validate(bp: dict, n: int, ny: int = None):
    nx, ny = n, (n if ny is None else ny)
    """Raise on failure. Returns list of check lines."""
    ents = bp['entities']; byid = {e['entity_number']: e for e in ents}
    size = {'roboport': 4, 'big-electric-pole': 2, 'small-lamp': 1}
    # collisions on tile occupancy
    occ = {}
    for e in ents:
        s = size[e['name']]; x, y = e['position']['x'] - s / 2, e['position']['y'] - s / 2
        assert x == int(x) and y == int(y), f'off-grid {e}'
        for tx in range(int(x), int(x) + s):
            for ty in range(int(y), int(y) + s):
                assert (tx, ty) not in occ, f'collision at {(tx, ty)}'
                occ[tx, ty] = e['entity_number']
    # wire reach
    for a, _, b, _ in bp['wires']:
        pa, pb = byid[a]['position'], byid[b]['position']
        d = math.dist((pa['x'], pa['y']), (pb['x'], pb['y']))
        assert d <= POLE_REACH, f'wire {a}-{b} length {d}'
    # one connected network
    poles = [e['entity_number'] for e in ents if e['name'] == 'big-electric-pole']
    adj = {p: set() for p in poles}
    for a, _, b, _ in bp['wires']: adj[a].add(b); adj[b].add(a)
    seen, st = set(), [poles[0]]
    while st:
        p = st.pop()
        if p in seen: continue
        seen.add(p); st += adj[p]
    assert len(seen) == len(poles), 'pole network not connected'
    # power: every roboport and lamp overlaps some big pole supply area (2 tiles each side)
    for e in ents:
        if e['name'] == 'big-electric-pole': continue
        s = size[e['name']] / 2; ex, ey = e['position']['x'], e['position']['y']
        ok = any(abs(ex - byid[p]['position']['x']) < s + 2 and abs(ey - byid[p]['position']['y']) < s + 2
                 for p in poles)
        assert ok, f'unpowered {e}'
    counts = {k: sum(e['name'] == k for e in ents) for k in size}
    assert counts['roboport'] == nx * ny
    return [f'{nx}x{ny} roboports, {counts["big-electric-pole"]} big poles, {counts["small-lamp"]} lamps, '
            f'{len(bp["wires"])} wires (max {POLE_REACH}): collisions/reach/network/power OK']
