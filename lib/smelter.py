"""Straight horizontal smelters: ore belt in from the EAST edge, plate belt out on the WEST edge, no turns.
Electric furnaces (no fuel). One furnace picks its recipe from the ore: iron, copper (stone -> half the bricks).

Module (10 rows, y0 = top):
  y0..y0+2 furnaces F1 | y0+3 inserters I1 | y0+4 ORE belt (W) | y0+5 PLATE belt (W) | y0+6 inserters I2 |
  y0+7..y0+9 furnaces F2
  I1: fast ORE -> F1, long-handed F1 -> PLATE.  I2: long-handed ORE -> F2, fast F2 -> PLATE.
  F1 drops on PLATE's south lane, F2 on its north lane -> both lanes full.
Per cell: 14 furnaces per row at local x 4+3k. Each furnace has 3 inserter-row tiles: 2 inserters + 1 slot.
  The slot is on the left for k 0..6 and on the right for k 7..13 (mirror). Slots hold a medium pole at
  k = 0,2,4,6,7,9,11,13 (x 4,10,16,22,27,33,39,45; next cell's 54 is 9 away), else a lamp. Same in I1 and I2.
Data (2.1.24): electric furnace 3x3, speed 2, 180 kW; iron/copper plate 3.2 s -> 0.625/s per furnace;
  long-handed ~1.2/s, fast ~2.3/s (hand size 1). Belts 15 / 30 / 45 per s.
Module per cell = 28 furnaces = 17.5 plates/s. Cells wide: yellow 1, red 2, blue 3 (117% of the belt).
"""
import math
from .build import BP, N, E, S, W, SIZE, POWERED, VEC, validate, tile_of, trace
from . import bp as LBP, adapt
from .cell import check_fixed, finish, corners

SIZE['electric-furnace'] = 3
POWERED.add('electric-furnace')
LBP.SIZES['electric-furnace'] = (3, 3)
LBP.COLORS['electric-furnace'] = (150, 110, 90)

TIER = {'yellow': ('transport-belt', 15, 1), 'red': ('fast-transport-belt', 30, 2),
        'blue': ('express-transport-belt', 45, 3)}
RATE = 0.625
Y0 = {1: (20,), 2: (15, 25), 3: (10, 20, 30)}          # module tops, centered in the cell (interior y 2..47)
POLE_K = {0, 2, 4, 6, 7, 9, 11, 13}


def build(color, nmod):
    belt, cap, cw = TIER[color]
    b = BP(); b.belt_name = belt
    xe = 50 * (cw - 1) + 47
    mods = []
    for y0 in Y0[nmod]:
        ore, plate, i1, i2 = y0 + 4, y0 + 5, y0 + 3, y0 + 6
        assert not ({ore % 50, plate % 50} & {22, 23}), 'belt row hits the grid pole on the vertical lines'
        for x in range(4, xe + 1):
            b.belt(x, ore, W); b.belt(x, plate, W)
        for i in range(cw):
            for k in range(14):
                x = 50 * i + 4 + 3 * k
                b.add('electric-furnace', x, y0); b.add('electric-furnace', x, y0 + 7)
                left = k <= 6
                slot, a, c = (x, x + 1, x + 2) if left else (x + 2, x, x + 1)
                b.inserter(a, i1, S); b.inserter(c, i1, N, 'long-handed-inserter')
                b.inserter(a, i2, N, 'long-handed-inserter'); b.inserter(c, i2, S)
                for y in (i1, i2):
                    if k in POLE_K: b.add('medium-electric-pole', slot, y)
                    else: b.add('small-lamp', slot, y)
        mods.append(dict(ore=ore, plate=plate))
    return b, dict(color=color, nmod=nmod, cw=cw, cap=cap, xe=xe, mods=mods)


def check(b, info):
    xe = info['xe']
    ore_in = {(xe, m['ore']) for m in info['mods']}
    exits = {(4, m['plate']) for m in info['mods']}
    ore_rows = {m['ore'] for m in info['mods']}; plate_rows = {m['plate'] for m in info['mods']}
    def rule(ins, src, dst):
        sn, dn = src and src['name'], dst and dst['name']
        if sn == 'electric-furnace':
            t = tile_of(dst) if dst else None
            if not t or t[1] not in plate_rows: return 'furnace output not on a plate belt'
            if trace(b, t)[0][-1] not in exits: return 'plate belt does not reach the output'
            return None
        if dn == 'electric-furnace':
            t = tile_of(src) if src else None
            if not t or t[1] not in ore_rows: return 'furnace input not from an ore belt'
            return None
        return 'inserter without a furnace'
    trees = adapt.rewire(b); assert trees == 1, f'{trees} pole networks'
    rep, bi = validate(b, rule)
    assert not bi['curves'] and not bi['sideloads'], 'belts must be straight'
    ends = {(4, m['ore']) for m in info['mods']} | exits
    assert set(bi['ends']) == ends, f'dead ends {sorted(set(bi["ends"]) ^ ends)}'
    rep.append('belts: straight rows only; dead ends = ore row ends + plate outputs (west edge)')
    rep += check_fixed(b, info['cw'], 1)
    nf = sum(e['name'] == 'electric-furnace' for e in b.ents)
    per = nf // info['nmod']
    rep.append(f'ratio: {per} furnaces per belt x 0.625/s = {per * RATE:.1f} plates/s for a {info["color"]} '
               f'belt ({info["cap"]}/s, {100 * per * RATE / info["cap"]:.0f}%); ore in = plates out (iron, copper)')
    return rep, dict(furnaces=nf, per=per)


def main(color, nmod, outdir):
    b, info = build(color, nmod)
    rep, st = check(b, info)
    for r in rep: print(' ', r)
    belt = TIER[color][0]
    bp = finish(b, f'Smelter {color} x{nmod}', [('item', 'electric-furnace'), ('item', belt)],
                description=f'{nmod} {color} belt(s) of ore in from the EAST, {nmod} {color} belt(s) of plates out '
                            f'WEST, straight rows. {st["per"]} electric furnaces per belt. Iron or copper '
                            f'(stone gives half the bricks).',
                corner_list=corners(info['cw'], 1))
    LBP.write_outputs(outdir, bp)
    LBP.render(outdir, bp, px=6 if info['cw'] == 1 else 4)
    return rep, st, info
