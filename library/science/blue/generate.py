"""Chemical (blue) science: 1 full blue belt (45/s) out on the left. 3 cells wide x 2 tall.
Layout and numbers: see spec.yaml. Engine: lib/factory.py."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.cell import corners, finish
from lib.factory import Plant, Band, auto_gaps, write_spec

PACK = 'chemical-science-pack'
ING = ['engine-unit', 'advanced-circuit', 'advanced-circuit', 'sulfur']
RATES = [22.5, 16.875, 16.875, 11.25]                 # per band (half the block)
F = Plant(3, 2)
B1 = F.band(Band(PACK, ING, nj=37, npairs=3, y0=6, gaps=auto_gaps(7, 37), panel=False))
B2 = F.band(Band(PACK, ING, nj=37, npairs=3, y0=6, gaps=auto_gaps(7, 37), panel=False), dy=50)
F.merge_exit(B1, B2, (4, 47), PACK)
for bd in (B1, B2):
    for k, (it, r) in enumerate(zip(ING, RATES)):
        t, _, _ = bd.stub(k); F.feed(it, r, t[1], bd.stub(k))
rep = F.check()
for r in rep: print(r)
DESC = ('3x2 cells. Two identical halves (one per cell row), each 222 machines in 3 mirrored row pairs with '
        'engine | red circuit and red circuit | sulfur belts. Outputs meet on the west edge. Inputs on the east '
        'edge, marked by panels, per half: engines red belt, red circuits 2 red belts, sulfur yellow.')
write_spec(HERE / 'spec.yaml', F, 'Chemical Science', DESC, [PACK], PACK, ratios='''\\
pack: 2 engines + 3 red circuits + 1 sulfur -> 2 packs, 24 s; AM3 -> 0.104/s. 45/s needs 432; 444 built (46.3/s).
inputs (whole block): engines 45/s, red circuits 67.5/s, sulfur 22.5/s. Per half: engines 22.5 (red belt),
  red circuits 2 x 16.9 (red belts, one per lane), sulfur 11.25 (yellow).
per pair: engines 7.5, red 11.25 (two lanes), sulfur 3.75 /s - every lane under half full.''',
           bottleneck='inputs: used exactly (output = 45/s); machines 3% spare', rep=rep,
           check_in_game=["don't rotate it; align the 12 corner roboports"], log=['2026-11-19: built'])
bp = finish(F.b, 'Chemical Science', [('item', PACK)], description=DESC, corner_list=corners(3, 2))
write_outputs(HERE, bp)
render(HERE, bp, px=5, grid=0)
