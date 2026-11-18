"""Huge Solar with 4 roboports instead of 16.

Source: David's in-game "Huge Solar" (import/huge-solar.txt): 6x6 modules of 18x18, 108x108 tiles,
standalone (no grid snapping). Each module = 24 panels + 20 accumulators, or 20 panels + 1 roboport.
Here only the 4 KEEP modules have a roboport: roboport modules outside KEEP get the 4 panels of a
normal module, and a normal module inside KEEP swaps those 4 panels for a roboport.
"""
import math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from lib.bp import decode, write_outputs, render, VERSION

M = 18                                   # module size
KEEP = {(0, 1), (2, 3), (3, 1), (4, 5)}  # modules (col, row) with a roboport (exhaustive search, 3-tile margin)
CON, LOG = 55, 25                        # roboport construction / logistic radius (entities.lua 2.1.24)
SIZE = {'solar-panel': 3, 'accumulator': 2, 'medium-electric-pole': 1, 'big-electric-pole': 2, 'roboport': 4}
SUPPLY = {'medium-electric-pole': 3.5, 'big-electric-pole': 2}
REACH = {'medium-electric-pole': 9, 'big-electric-pole': 32}

src = decode((ROOT / 'import/huge-solar.txt').read_text())['blueprint']
E = src['entities']
X0 = min(e['position']['x'] - SIZE[e['name']] / 2 for e in E)
Y0 = min(e['position']['y'] - SIZE[e['name']] / 2 for e in E)
mod = lambda e: (int((e['position']['x'] - X0) // M), int((e['position']['y'] - Y0) // M))
local = lambda e: (e['position']['x'] - X0 - mod(e)[0] * M, e['position']['y'] - Y0 - mod(e)[1] * M)

robo_mods = {mod(e) for e in E if e['name'] == 'roboport'}
normal = next((i, j) for i in range(6) for j in range(6) if (i, j) not in robo_mods)
# the 4 panels that a normal module has where a roboport module has its roboport
robo_local = next(local(e) for e in E if e['name'] == 'roboport')
fill = [local(e) for e in E if mod(e) == normal and e['name'] == 'solar-panel'
        and abs(local(e)[0] - robo_local[0]) < 4 and abs(local(e)[1] - robo_local[1]) < 4]
assert len(fill) == 4, fill

robo_tpl = next(e for e in E if e['name'] == 'roboport')
is_fill = lambda e: e['name'] == 'solar-panel' and local(e) in fill
out, renum = [], {}
for e in E:
    if e['name'] == 'roboport' and mod(e) not in KEEP:
        continue
    if mod(e) in KEEP - robo_mods and is_fill(e):
        continue
    renum[e['entity_number']] = len(out) + 1
    out.append({**e, 'entity_number': len(out) + 1})
for m in sorted(robo_mods - KEEP):
    for lx, ly in fill:
        out.append({'entity_number': len(out) + 1, 'name': 'solar-panel',
                    'position': {'x': X0 + m[0] * M + lx, 'y': Y0 + m[1] * M + ly}})
for m in sorted(KEEP - robo_mods):
    out.append({**robo_tpl, 'entity_number': len(out) + 1,
                'position': {'x': X0 + m[0] * M + robo_local[0], 'y': Y0 + m[1] * M + robo_local[1]}})
wires = [[renum[a], ca, renum[b], cb] for a, ca, b, cb in src['wires']]
bp = {'item': 'blueprint', 'label': 'Huge Solar 4R', 'icons': src['icons'],
      'entities': out, 'wires': wires, 'version': VERSION}

# ---------------- validation ----------------
def box(e):
    s = SIZE[e['name']] / 2; x, y = e['position']['x'], e['position']['y']
    return x - s, y - s, x + s, y + s
occ = {}
for e in out:
    x0, y0, x1, y1 = box(e)
    for tx in range(int(x0), int(x1)):
        for ty in range(int(y0), int(y1)):
            assert (tx, ty) not in occ, f'collision {e}'
            occ[tx, ty] = e['entity_number']
byid = {e['entity_number']: e for e in out}
poles = [e for e in out if e['name'] in SUPPLY]
for e in out:  # every non-pole entity touches a supply area
    if e['name'] in SUPPLY: continue
    x0, y0, x1, y1 = box(e)
    assert any(x0 < p['position']['x'] + SUPPLY[p['name']] and x1 > p['position']['x'] - SUPPLY[p['name']] and
               y0 < p['position']['y'] + SUPPLY[p['name']] and y1 > p['position']['y'] - SUPPLY[p['name']]
               for p in poles), f'unpowered {e}'
adj = {p['entity_number']: set() for p in poles}
for a, _, b, _ in wires:
    pa, pb = byid[a], byid[b]
    d = math.dist((pa['position']['x'], pa['position']['y']), (pb['position']['x'], pb['position']['y']))
    assert d <= min(REACH[pa['name']], REACH[pb['name']]), f'wire too long {a}-{b} {d}'
    adj[a].add(b); adj[b].add(a)
seen, st = set(), [poles[0]['entity_number']]
while st:
    p = st.pop()
    if p not in seen: seen.add(p); st += adj[p]
assert len(seen) == len(poles), f'{len(poles) - len(seen)} poles not wired'
robos = [(e['position']['x'], e['position']['y']) for e in out if e['name'] == 'roboport']
margin = min(max(CON - max(abs(tx + .5 - x), abs(ty + .5 - y)) for x, y in robos)
             for tx in range(int(X0), int(X0) + 6 * M) for ty in range(int(Y0), int(Y0) + 6 * M))
assert margin >= 0, 'field not fully inside construction area'
P = 6 * M
nodes = [(x + i * P, y + j * P) for i in range(3) for j in range(3) for x, y in robos]
seen, st = {nodes[0]}, [nodes[0]]
while st:
    a = st.pop()
    for b in nodes:
        if b not in seen and max(abs(a[0] - b[0]), abs(a[1] - b[1])) <= 2 * LOG: seen.add(b); st.append(b)
assert len(seen) == len(nodes), 'tiled fields do not form one network'
links = max(min(max(abs(a[0] - b[0]), abs(a[1] - b[1])) for b in nodes if b != a) for a in nodes)

cnt = {k: sum(e['name'] == k for e in out) for k in SIZE}
print(cnt)
print(f'construction margin {margin} tiles; logistic links OK (longest needed {links} <= {2 * LOG}); '
      f'collisions, power, wires OK')
write_outputs(HERE, bp)
render(HERE, bp, px=4, grid=0)
