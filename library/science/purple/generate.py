"""Production (purple) science: 1/3 blue belt (15/s, yellow belt) out on the left - place 3 for a full belt.
4 cells wide x 2 tall. Layout and numbers: see spec.yaml. Engine: lib/factory.py."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.cell import corners, finish
from lib.factory import Plant, Band, auto_gaps, write_spec

PACK = 'production-science-pack'
BULK = dict(near='bulk-inserter', out='bulk-inserter')
F = Plant(4, 2)
UG = 12
P = F.band(Band(PACK, spec=[('rail', 'rail'), ('electric-furnace', 'productivity-module'), ('rail', 'rail')],
                direct={0, 2}, nj=22, npairs=2, y0=5, gaps=auto_gaps(7, 22)))
def R(g): return Band('rail', spec=[('stone', 'steel-plate'), ('iron-stick',), ('stone', 'steel-plate')],
                      groups={0: 'stone', 3: 'stone', 1: 'steel', 4: 'steel'}, nj=8, npairs=2, split_out=True,
                      unshare=True, near='bulk-inserter', out='bulk-inserter', gaps=g)
def S(g): return Band('iron-stick', ['iron-plate'], nj=5, npairs=1, gaps=g, **BULK)
def Fu(g): return Band('electric-furnace', spec=[('steel-plate', 'stone-brick'), ('advanced-circuit',),
                                                 ('steel-plate', 'stone-brick')],
                       groups={0: 'steel', 3: 'steel', 1: 'brick', 4: 'brick'}, nj=6, npairs=1,
                       near='bulk-inserter', gaps=g)
def Mo(g): return Band('productivity-module', spec=[('advanced-circuit', 'electronic-circuit')] * 2,
                       groups={0: 'red', 2: 'red', 1: 'green', 3: 'green'}, nj=16, npairs=2, y0=6, gaps=g)
RA = F.fit(R, 0, 99, name='RA'); RB = F.fit(R, 50, 99, name='RB')
SA = F.fit(S, 4, 150, name='SA'); FA = F.fit(Fu, 22, 150, name='FA')
SB = F.fit(S, 54, 150, name='SB'); FB = F.fit(Fu, 72, 150, name='FB')
M = F.fit(Mo, 50, 4, name='M')
F.exit(P, PACK)
# rails: 4 one-lane belts per pair, routed bottom-most first so each turns west of the next
lanes = [(RA, 0, 0, 0), (RA, 1, 0, 1), (RA, 2, 0, 4), (RA, 3, 0, 5),
         (RB, 0, 1, 0), (RB, 1, 1, 1), (RB, 2, 1, 4), (RB, 3, 1, 5)]
XT = 97                                               # innermost turn column (west of the grid line at 98..103)
for n, (r, o, i, k) in enumerate(lanes):
    (st, _), (g, _, cap) = r.out(o), P.stub(k, i)
    assert cap >= 18.75
    F.lshape(st, XT - max(n - 1, 0) if n else XT, g, name=f'rails {i}.{k}')
F.link(SA, RA.stub(2), rate=37.5, name='sticks A', ugc=UG); F.link(SB, RB.stub(2), rate=37.5, name='sticks B', ugc=UG)
for r in (RA, RB):
    F.feed('stone', 37.5, r.stub(0)[0][1], r.stub(0), ugc=UG); F.feed('steel-plate', 37.5, r.stub(1)[0][1], r.stub(1), ugc=UG)
for s_ in (SA, SB): F.feed('iron-plate', 18.75, s_.stub(0)[0][1], s_.stub(0), ugc=UG)
fp = F.link(FA, P.stub(0), rate=5, name='furnaces', ugc=UG); F.join(FB, fp, name='furnaces 2', ugc=UG)
F.link(M, P.stub(1), rate=5, name='modules', ugc=UG)
for f in (FA, FB):
    for k, (it, rt) in enumerate((('steel-plate', 25), ('stone-brick', 25), ('advanced-circuit', 12.5))):
        F.feed(it, rt, f.stub(k)[0][1], f.stub(k), ugc=UG)
for k, (it, rt) in enumerate((('advanced-circuit', 25), ('electronic-circuit', 25))):
    F.feed(it, rt, 96 + k, M.stub(k), ugc=UG, bias=lambda t, k=k: 20 * (k == 0 and t[0] < 76 and t[1] > 53))
rep = F.check()
for r in rep: print(r)
DESC = ('15/s (1/3 belt) - place 3 for a full belt. 4x2 cells. Top left: 88 pack machines in 2 row pairs (rails on '
        'the outer belts, furnace | module in the middle). Middle: two rail blocks (32 machines each, 4 one-lane rail '
        'belts each, laid as nested L-shapes). Right: stick blocks (10, bulk) and furnace blocks (12). Bottom left: '
        'module block (64). Inputs on the east edge, marked by panels.')
write_spec(HERE / 'spec.yaml', F, 'Production Science 15/s', DESC, [PACK], PACK, ratios='''\
Rate: 15/s, not a full belt (David: "do what makes sense" - 45/s would be ~770 machines and ~30 inputs). 3 copies = 45/s.
pack: 1 furnace + 1 module + 30 rails -> 3 packs, 21 s; AM3 -> 0.0595 crafts/s. 5 crafts/s needs 84; 88 built.
  Per pair: 75 rails/s on four one-lane feeds (18.75 each), furnace 2.5/s, module 2.5/s.
rails: stone + stick + steel -> 2, 0.5 s. Bulk picks stone | steel, long-handed picks sticks (1.2/s) -> 1.2 crafts/s
  per machine. Each rail block: 2 pairs x 2 rows x 8 = 32 machines; rows need 9.4 crafts/s, 8 machines give 9.6 (2% spare).
  Each block: stone 37.5, steel 37.5, sticks 37.5 -> 75 rails/s on 4 one-lane belts (own output rows per pair).
sticks: iron -> 2, 0.5 s; bulk in/out -> 4.6/s per machine; 10 per block = 46 for 37.5 (iron 18.75).
furnaces: 10 steel + 5 red + 10 bricks, 5 s. Bulk picks steel | bricks (20/craft) -> 0.23/s per machine; 12 per block
  (2.8/s) for 2.5/s. Two blocks join onto one belt (5/s).
modules: 5 red + 5 green, 15 s -> 0.083/s; 64 machines (5.3/s) for 5/s.
inputs: stone 2 x 37.5, steel 2 x 37.5 + 2 x 25, iron 2 x 18.75, bricks 2 x 25, red circuits 2 x 12.5 + 25, green 25.''',
           bottleneck='rail machines (2% spare, long-handed stick inserters)', rep=rep,
           check_in_game=["don't rotate it; align the 15 corner roboports",
                          'rail machines: long-handed inserters must keep up (1.2 sticks/s each); 2% spare',
                          'bulk inserters carry 2 (bulk inserter research)',
                          'output belt carries 15/s (blue belt, one third full)'],
           makes_itself=['rail', 'iron-stick', 'electric-furnace', 'productivity-module'], log=['2026-11-19: built at 15/s'])
bp = finish(F.b, 'Production Science 15/s', [('item', PACK)], description=DESC, corner_list=corners(4, 2))
write_outputs(HERE, bp)
render(HERE, bp, px=4, grid=0)
