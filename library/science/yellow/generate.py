"""Utility (yellow) science: 1 full blue belt (45/s) out on the left. 2 cells wide x 2 tall.
Layout and numbers: see spec.yaml. Engine: lib/factory.py."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.cell import corners, finish
from lib.factory import Plant, Band, auto_gaps, write_spec

PACK = 'utility-science-pack'
ING = ['low-density-structure', 'processing-unit', 'flying-robot-frame']
RATES = [22.5, 15, 7.5]                               # per band (half the block)
F = Plant(2, 2)
B1 = F.band(Band(PACK, ING, nj=22, npairs=3, y0=6, gaps=auto_gaps(7, 22), panel=False))
B2 = F.band(Band(PACK, ING, nj=22, npairs=3, y0=6, gaps=auto_gaps(7, 22), panel=False), dy=50)
F.merge_exit(B1, B2, (4, 47), PACK)
for bd in (B1, B2):
    for k, (it, r) in enumerate(zip(ING, RATES)):
        t, _, _ = bd.stub(k); F.feed(it, r, t[1], bd.stub(k))
rep = F.check()
for r in rep: print(r)
DESC = ('2x2 cells. Two identical halves (one per cell row), each 132 machines in 3 mirrored row pairs with '
        'LDS | processing unit and frame belts. Outputs meet on the west edge. Inputs on the east edge, marked '
        'by panels, per half: LDS red belt, processing units yellow, frames yellow.')
write_spec(HERE / 'spec.yaml', F, 'Utility Science', DESC, [PACK], PACK, ratios='''\\
pack: 3 LDS + 2 processing units + 1 frame -> 3 packs, 21 s; AM3 -> 0.179/s. 45/s needs 252; 264 built (47.1/s).
inputs (whole block): LDS 45/s, processing units 30/s, frames 15/s. Per half: LDS 22.5 (red belt),
  processing units 15 (yellow), frames 7.5 (yellow).
per pair: LDS 7.5, processing units 5, frames 2.5 /s.''',
           bottleneck='inputs: used exactly (output = 45/s); machines 5% spare', rep=rep,
           check_in_game=["don't rotate it; align the 9 corner roboports"], log=['2026-11-19: built'])
bp = finish(F.b, 'Utility Science', [('item', PACK)], description=DESC, corner_list=corners(2, 2))
write_outputs(HERE, bp)
render(HERE, bp, px=5, grid=0)
