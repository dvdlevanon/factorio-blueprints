"""Military science: 1 full blue belt (45/s) out on the left. 4 cells wide x 3 tall.
Layout and numbers: see spec.yaml. Engine: lib/factory.py."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render
from lib.cell import corners, finish
from lib.factory import Plant, Band, auto_gaps, right_aligned, write_spec

PACK = 'military-science-pack'
BULK = dict(near='bulk-inserter', out='bulk-inserter')
F = Plant(4, 3)
XS = F.XE - 4                                    # direct bands end next to the input gates
P = F.band(Band(PACK, ['stone-wall', 'grenade', 'piercing-rounds-magazine'], nj=32, npairs=3, y0=6,
                gaps=auto_gaps(7, 32)))
wb, wdx = right_aligned(lambda g: Band('stone-wall', spec=[('stone-brick',)] * 2, nj=7, npairs=3, y0=3,
                                       direct=True, gaps=g, **BULK), XS)
WALL = F.band(wb, dx=wdx)
gb, gdx = right_aligned(lambda g: Band('grenade', spec=[('coal',), ('iron-plate',), ('coal',)], nj=25, npairs=3,
                                       y0=55, direct=True, gaps=g), XS)
GREN = F.band(gb, dx=gdx)
PIER = F.band(Band('piercing-rounds-magazine', spec=[('firearm-magazine',), ('copper-plate', 'steel-plate')], nj=15,
                   npairs=2, y0=6), dy=50)
mb, mdx = right_aligned(lambda g: Band('firearm-magazine', spec=[('iron-plate',), ('iron-plate',)], nj=10, npairs=1,
                                       y0=104, direct=True, gaps=g, **BULK), XS)
MAG = F.band(mb, dx=mdx)
F.exit(P, PACK)
F.link(PIER, P.stub(2), name='piercing')
F.link(GREN, P.stub(1), rate=22.5, name='grenades')
F.link(WALL, P.stub(0), name='walls', bias=lambda t: t[0] > 125 and t[1] < 20)
F.link(MAG, PIER.stub(0), rate=22.5, name='magazines', bias=lambda t: 20 * (t[0] < 72 and t[1] > 52))
F.feed('copper-plate', 22.5, 119, PIER.stub(1), bias=lambda t: 20 * (t[0] < 71 and t[1] > 53))
F.feed('steel-plate', 11.25, 120, PIER.stub(2))
for k in range(2):
    t, _, _ = MAG.stub(k, 0); F.feed('iron-plate', 45, t[1], MAG.stub(k, 0))
for i in range(3):
    for k, it in enumerate(['coal', 'iron-plate', 'coal']):
        t, _, _ = GREN.stub(k, i); F.feed(it, 37.5, t[1], GREN.stub(k, i))
    for k in range(2):
        t, _, _ = WALL.stub(k, i); F.feed('stone-brick', 37.5, t[1], WALL.stub(k, i))
rep = F.check()
for r in rep: print(r)
DESC = ('4x3 cells. Top: 192 pack machines (wall | grenade, piercing belts). Walls (42, bulk) top right, grenades '
        '(150) middle right, magazines (20, bulk) bottom right, piercing rounds (60) middle left. Inputs on the east '
        'edge, marked by panels: bricks 6, coal 6, iron 5 blue belts; copper red, steel yellow.')
write_spec(HERE / 'spec.yaml', F, 'Military Science', DESC, [PACK], PACK, ratios='''\
pack: 1 piercing + 1 grenade + 2 walls -> 2 packs, 10 s; AM3 -> 0.25/s. 45/s needs 180; 192 built (48/s).
  Per 45 packs/s: 22.5 piercing, 22.5 grenades, 45 walls.
walls: 5 bricks, 0.5 s. Bulk (hand 2) near + long-handed far -> 5.8 bricks/s = 1.16 walls/s per machine.
  3 pairs x 14 = 42 machines (49/s). Each pair: two brick belts of 37.5/s (middle belts, both lanes) -> 15 walls/s.
grenades: 5 iron + 10 coal, 8 s -> 0.156/s. Three middle belts per pair (coal | iron | coal), 50 machines per
  pair -> 7.8/s for 7.5 needed (coal 2 x 37.5, iron 37.5 per pair). 150 machines, 22.5/s.
magazines: 4 iron, 1 s -> 1.25/s (crafting-limited). 20 machines (25/s) for 22.5; 2 iron belts of 45/s.
piercing: 2 magazines + 1 steel + 2 copper -> 2, 6 s -> 0.42/s. 60 machines (25/s) for 22.5.
inputs: bricks 225/s (6 x 37.5), coal 225/s (6 x 37.5), iron 112.5 (3 x 37.5) + 90 (2 x 45), copper 22.5, steel 11.25.''',
           bottleneck='inputs: every input is used exactly (output = 45/s)', rep=rep,
           check_in_game=["don't rotate it; align the 20 corner roboports",
                          'bulk inserters carry 2 (bulk inserter research): walls and magazines',
                          'walls: 15 walls/s per pair needs 75 bricks/s; machines cap 81/s (8% spare)'],
           makes_itself=['piercing-rounds-magazine', 'firearm-magazine', 'grenade', 'stone-wall'],
           log=['2026-11-19: built'])
bp = finish(F.b, 'Military Science', [('item', PACK)], description=DESC, corner_list=corners(4, 3))
write_outputs(HERE, bp)
render(HERE, bp, px=4, grid=0)
