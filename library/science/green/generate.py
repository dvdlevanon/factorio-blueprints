"""Logistic (green) science: 1 full blue belt (45/s) out on the left. 3 cells wide x 2 tall.
Layout and numbers: see spec.yaml. Engine: lib/factory.py."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.cell import corners, finish
from lib.factory import Plant, Band, auto_gaps, write_spec

PACK = 'logistic-science-pack'
BULK = dict(near='bulk-inserter', out='bulk-inserter')
F = Plant(3, 2)
P = F.band(Band(PACK, ['transport-belt', 'inserter'], nj=37, npairs=3, y0=8, gaps=auto_gaps(7, 37)))
I = F.band(Band('inserter', ['iron-gear-wheel', 'electronic-circuit', 'iron-plate'], nj=7, npairs=3, y0=6),
           rot=1, dx=50, dy=51)                                               # in S, out N
B = F.band(Band('transport-belt', ['iron-gear-wheel', 'iron-plate'], nj=6, npairs=1, near2=True, out2=True),
           rot=1, dx=123, dy=51)
G1 = F.band(Band('iron-gear-wheel', ['iron-plate', 'iron-plate'], nj=4, npairs=3, **BULK), rot=3, dx=54, dy=84)
G2 = F.band(Band('iron-gear-wheel', ['iron-plate'], nj=6, npairs=1, **BULK), rot=3, dx=124, dy=87)   # in N, out S
F.exit(P, PACK)
F.link(I, P.stub(1), name='inserters', bias=lambda t: 3 * (t[1] in (53, 54)))
F.link(B, P.stub(0), name='belts')
F.feed('iron-plate', 45, 54, G2.stub(0))
F.link(G2, B.stub(0), rate=22.5, name='gears for belts')
F.feed('iron-plate', 22.5, 88, B.stub(1))
F.link(G1, I.stub(0), name='gears for inserters')
F.feed('electronic-circuit', 45, 95, I.stub(1))
F.feed('iron-plate', 45, 96, I.stub(2))
F.feed('iron-plate', 45, 89, G1.stub(0), bias=lambda t: 5 * (t[1] == 54 or t[0] == 96))
F.feed('iron-plate', 45, 90, G1.stub(1))
rep = F.check()
for r in rep: print(r)
DESC = ('3x2 cells. Top: 222 pack machines in 3 mirrored row pairs (inserter | belt mixed belts). '
        'Bottom, turned on their side: inserters (42), transport belts (12) and two gear blocks (24 + 12, bulk '
        'inserters) feeding them. Inputs on the east edge, marked by panels: circuits 1 blue, iron 4 blue + 1 red.')
write_spec(HERE / 'spec.yaml', F, 'Logistic Science', DESC, [PACK], PACK, ratios='''\
pack: 1 inserter + 1 belt, 6 s; AM3 1.25 -> 0.208/s. 45/s needs 216; 222 built (46.3/s).
inserter: circuit + gear + iron, 0.5 s. Limited by its inserters: fast picks circuit+gear (2 per craft) ->
  1.15 crafts/s per machine; 42 built = 48.5/s for 45 needed. Lanes per pair 15/s.
belt: gear + iron -> 2, 0.5 s. 2 fast in + 2 fast out -> 2.31 crafts = 4.6 belts/s; 12 built = 55/s for 45.
  One pair: gear and iron one lane each, exactly 22.5/s (= the need).
gears: 2 iron -> 1, 0.5 s; bulk in/out (hand 2) -> 2.31/s per machine. 24 machines for the inserters (45/s from
  2 iron belts), 12 for the belts (22.5/s from 1 iron belt).
iron: 90 + 45 (gears) + 45 (inserters) + 22.5 (belts) = 202.5/s = 4 blue + 1 red. Circuits 45/s = 1 blue.''',
           bottleneck='inputs: every input belt is used exactly (output = 45/s)', rep=rep,
           check_in_game=["don't rotate it; align the 12 corner roboports",
                          'bulk inserters carry 2 (bulk inserter research) - gear blocks need it',
                          'belt-recipe pair: gear and iron lanes are exactly full (22.5/s each)'],
           makes_itself=['inserter', 'transport-belt', 'iron-gear-wheel'], log=['2026-11-19: built'])
bp = finish(F.b, 'Logistic Science', [('item', PACK)], description=DESC, corner_list=corners(3, 2))
write_outputs(HERE, bp)
render(HERE, bp, px=5, grid=0)
