"""Space science, one rocket silo (~2.9/s): place as many as you need (about 15 for a full belt).
2 cells wide x 1 tall. Hand layout (coordinates: top-left roboport centre = (0,0)); checks from lib/factory.py.

  silo (10..18, 16..24) | west: 3 fast inserters -> output belt x=8 -> exit (4,22)
  south: inserter row 25, B1 row 26 = processing unit | LDS (former at x=28), B2 row 27 = rocket fuel
  satellite assembler (20..22, 22..24) -> inserter (19,23) -> silo; its north side picks row 20 (solar | radar)
    and row 19 (accumulators); its south side picks B1 / B2
  rocket fuel: 2 rows x 20 assemblers (30..89, rows 32..34 and 39..41), solid fuel belt row 36, fuel belt row 37
    (flows W, up x=26 into B2), light oil pipes rows 31 and 42 (pipe at every port, underground pairs between)
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.build import N, E, S, W, VEC, validate, fluid_networks
from lib.cell import corners, finish, check_fixed
from lib.factory import Plant, entry_gate, check_flow, bridge_poles, tier, write_spec, RATE
from lib import adapt

PACK = 'space-science-pack'
F = Plant(2, 1); b = F.b; XE = F.XE
curves, sides, ends = [], [], []

def run(pts, rate=45):
    """Belts along a polyline of corner tiles (last tile included). Corners become curves."""
    belt, _ = tier(rate); keep = b.belt_name; b.belt_name = belt
    tiles = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d = E if x1 > x0 else W if x1 < x0 else S if y1 > y0 else N
        n = max(abs(x1 - x0), abs(y1 - y0))
        for i in range(n): tiles.append(((x0 + VEC[d][0] * i, y0 + VEC[d][1] * i), d))
    tiles.append((pts[-1], tiles[-1][1]))
    for i, (t, d) in enumerate(tiles):
        b.belt(t[0], t[1], d)
        if i and d != tiles[i - 1][1]: curves.append(t)
    b.belt_name = keep
    return tiles

def gate(item, rate, y):
    start, inp = entry_gate(b, XE, y, item, rate)
    F.sources.append((inp, item)); F.inputs.append((item, rate, y))
    return start

# ---- silo, output
b.add('rocket-silo', 10, 16)
for y in (19, 20, 21): b.inserter(9, y, E)
b.add('medium-electric-pole', 9, 18); b.add('small-lamp', 9, 22)
run([(8, 19), (8, 22), (4, 22)]); b.panel(4, 21, PACK)
F.exits[(4, 22)] = (PACK, 'one lane'); ends.append((4, 22))
# ---- south: inserters into the silo
for x, kind in zip(range(10, 19), 'FLPFLFLPF'):
    if kind == 'F': b.inserter(x, 25, S)
    elif kind == 'L': b.inserter(x, 25, S, 'long-handed-inserter')
    else: b.add('medium-electric-pole', x, 25)
# B1 = processing unit | LDS, formed at (28, 26) by side-loads from north (PU) and south (LDS)
run([(28, 26), (10, 26)]); sides.append((28, 26)); ends.append((10, 26))
run([gate('processing-unit', 3.3, 24), (28, 24), (28, 25)], 3.3)
run([gate('low-density-structure', 3.3, 28), (28, 28), (28, 27)], 3.3)
# ---- satellite assembler
b.asm(20, 22, 'satellite')
b.inserter(19, 23, E)                                            # satellite -> silo
b.inserter(21, 25, S); b.inserter(20, 25, S, 'long-handed-inserter'); b.add('medium-electric-pole', 22, 25)
b.inserter(21, 21, N); b.inserter(20, 21, N, 'long-handed-inserter'); b.add('medium-electric-pole', 22, 21)
run([(26, 20), (20, 20)]); sides.append((26, 20)); ends.append((20, 20))       # solar (N) | radar (S)
run([gate('solar-panel', 0.3, 18), (26, 18), (26, 19)], 0.3)
run([gate('radar', 0.015, 21), (27, 21)], 0.015)
kb = b.belt_name; b.belt_name = tier(0.015)[0]; b.belt(26, 21, N); b.belt_name = kb; curves.append((26, 21))
run([gate('accumulator', 0.3, 17), (24, 17), (24, 19), (20, 19)], 0.3); ends.append((20, 19))
# ---- rocket fuel: 2 rows x 20 assemblers
X0, NJ = 30, 20
SF, RF, TOP, BOT = 36, 37, 32, 39
for j in range(NJ):
    x = X0 + 3 * j
    b.add('assembling-machine-3', x, TOP, recipe='rocket-fuel', direction=N)
    b.add('assembling-machine-3', x, BOT, recipe='rocket-fuel', direction=S)
    b.inserter(x, 35, S); b.inserter(x + 1, 35, N, 'long-handed-inserter')        # solid fuel in, fuel out
    b.inserter(x, 38, N, 'long-handed-inserter'); b.inserter(x + 1, 38, S)
    if j % 2 == 0 or j == NJ - 1:
        b.add('medium-electric-pole', x + 2, 35); b.add('medium-electric-pole', x + 2, 38)
    elif j % 4 == 3: b.add('small-lamp', x + 2, 35)
    for py in (31, 42):                                                       # oil pipes: pipe at each port
        b.pipe(x + 1, py); b.ptg(x + 2, py, W); b.ptg(x + 3, py, E)
xe = X0 + 3 * NJ + 1                                                        # 91: junction of the two pipe rows
for py in (31, 42): b.pipe(xe, py)
b.ptg(xe, 32, N); b.ptg(xe, 41, S)
b.ptg(xe + 1, 31, W); b.ptg(XE - 1, 31, E); b.pipe(XE, 31); b.panel(XE, 30, 'light-oil', 'fluid')
run([gate('solid-fuel', 30.4, SF), (X0, SF)], 30.4); ends.append((X0, SF))
run([(X0 + 3 * NJ - 1, RF), (26, RF), (26, 27), (10, 27)]); ends.append((10, 27))
for i, e in enumerate(b.ents): e['entity_number'] = i + 1
# ---- checks
nb = bridge_poles(b, 2, 1)
for i, e in enumerate(b.ents): e['entity_number'] = i + 1
adapt.rewire(b)
rep, info = validate(b, lambda ins, s_, d: None)
rep = [r for r in rep if not r.startswith('inserters')] + [f'power: {nb} bridge poles']
for want, got, what in ((curves, info['curves'], 'curves'), (sides, info['sideloads'], 'sideloads'),
                        (ends, info['ends'], 'dead ends')):
    assert sorted(want) == sorted(got), f'{what}: unexpected {sorted(set(got) - set(want))}, missing {sorted(set(want) - set(got))}'
rep.append(f'belts: {len(curves)} curves, {len(sides)} sideloads, {len(ends)} dead ends - all intended')
nets, touch = fluid_networks(b)
fm = [e for e in b.ents if e.get('recipe') == 'rocket-fuel']
assert len(nets) == 1 and all('input' in [k for k, _ in touch.get(e['entity_number'], [])] for e in fm)
rep.append(f'fluids: one light-oil network, all {len(fm)} rocket fuel machines on it')
silo = next(e for e in b.ents if e['name'] == 'rocket-silo')
silo['recipe'] = 'rocket-part'                                            # for the flow check only
rep += check_flow(b, F.sources, F.exits)
del silo['recipe']
rep += check_fixed(b, 2, 1)
for r in rep: print(r)
DESC = ('One rocket silo, ~2.9 space science/s (1000 per launch); place ~15 for a full belt. 2x1 cells. Makes its '
        'own rocket fuel (40 assemblers, light oil by pipe) and satellites. Inputs on the east edge, marked by '
        'panels: processing units, LDS, solar panels, accumulators, radars (yellow), solid fuel (blue), light oil (pipe).')
write_spec(HERE / 'spec.yaml', F, 'Space Science (1 silo)', DESC, [PACK, 'rocket-silo'], PACK, ratios='''\\
Rate: one silo (David: "do what makes sense"; 45/s would be 15 silos and ~570 rocket fuel assemblers).
rocket: 100 parts x 3 s (silo speed 1) = 300 s + launch (~30-45 s, not verified offline) -> ~2.9 packs/s.
per rocket: 1000 PU, 1000 LDS, 1000 rocket fuel (+ satellite: 100 LDS, 100 PU, 50 fuel, 100 solar, 100 accumulators,
  5 radars). Averaged: PU and LDS ~3.2/s, fuel ~3.05/s, solar and accumulators ~0.3/s.
while building parts the silo takes 3.33/s of each: 4 fast (PU | LDS) + 3 long-handed (fuel, 3.6/s).
rocket fuel: 10 solid fuel + 10 light oil, 15 s -> 0.083/s per AM3; 40 built = 3.33/s. Solid fuel 30.4/s, oil 30.4/s.''',
           bottleneck='the silo (crafting + launch time)', rep=rep,
           check_in_game=["don't rotate it; align the 6 corner roboports",
                          'satellites launch by themselves (send_to_orbit_mode = automated in 2.1 data)',
                          'the 1000 packs land in the silo output and the 3 west inserters take them out',
                          'inserters work on the silo south side and on its west side',
                          'output belt carries one lane (~2.9/s average, bursts of 1000)'],
           makes_itself=['rocket-part', 'rocket-fuel', 'satellite'], log=['2026-11-19: built (one silo)'])
bp = finish(b, 'Space Science (1 silo)', [('item', PACK), ('item', 'rocket-silo')], description=DESC,
            corner_list=corners(2, 1))
write_outputs(HERE, bp)
render(HERE, bp, px=8, grid=0)
