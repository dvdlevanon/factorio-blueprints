"""Place a block in one roboport-grid cell: center it, check all 4 rotations against the grid, and
finish the blueprint with the cell's 4 corner roboports (no snapping; David aligns it on the existing
roboports). Cell coordinates are relative to the cell's top-left roboport center R=(0,0).
With the 4 corner roboports the blueprint's bbox is centered on (25,25), so an in-game rotation maps the
roboports onto roboports and the block onto the same cell.

Grid per roboport R' (see CLAUDE.md): roboport tiles -2..1, big poles (2x2) centered at R'+(3,0),
R'+(27,0), R'+(3,23), lamps at R'+(2.5,-1.5), R'+(26.5,1.5).
Rotation-safe square: tiles 4..45 in x and y (42x42, symmetric about (25,25), inside the interior).
"""
import math
from .build import SIZE

SQ = (4, 4, 46, 46)                 # x0, y0, x1, y1 (exclusive) of the rotation-safe square
INTERIOR = (4, 2, 48, 48)


def grid():
    """(occupied tiles, big pole centers) of the grid around cell (0,0)."""
    tiles, poles = set(), []
    for gx in (-50, 0, 50, 100):
        for gy in (-50, 0, 50, 100):
            tiles |= {(gx + i, gy + j) for i in range(-2, 2) for j in range(-2, 2)}
            for px, py in ((3, 0), (27, 0), (3, 23)):
                c = (gx + px, gy + py); poles.append(c)
                tiles |= {(c[0] + i, c[1] + j) for i in (-1, 0) for j in (-1, 0)}
            for lx, ly in ((2.5, -1.5), (26.5, 1.5)):
                tiles.add((int(math.floor(gx + lx)), int(math.floor(gy + ly))))
    return tiles, poles


def center(b):
    """Shift block b (lib.build.BP) so its bbox is centered in the rotation-safe square."""
    x0, y0, x1, y1 = b.bbox()
    w, h = x1 - x0 + 1, y1 - y0 + 1
    assert w <= SQ[2] - SQ[0] and h <= SQ[3] - SQ[1], f'block {w}x{h} does not fit the 42x42 square'
    b.shift(SQ[0] + (SQ[2] - SQ[0] - w) // 2 - x0, SQ[1] + (SQ[3] - SQ[1] - h) // 2 - y0)


def check_rotations(b):
    """For each rotation about the square center: inside the interior, no grid collision,
    a medium pole within 9 of a grid big pole. Returns report lines."""
    gtiles, gpoles = grid()
    cx, cy = 25, 25                 # center of the 4-roboport blueprint
    rep = []
    for r in range(4):
        def R(x, y):
            for _ in range(r): x, y = cx - (y - cy), cy + (x - cx)
            return x, y
        tiles = set()
        for e in b.ents:
            for tx, ty in b.tiles(e):
                x, y = R(tx + .5, ty + .5); tiles.add((int(math.floor(x)), int(math.floor(y))))
        assert all(INTERIOR[0] <= x < INTERIOR[2] and INTERIOR[1] <= y < INTERIOR[3] for x, y in tiles), \
            f'rotation {r * 90}: outside the cell interior'
        hit = tiles & gtiles
        assert not hit, f'rotation {r * 90}: collides with grid at {sorted(hit)[:3]}'
        d = min(math.dist(R(e['position']['x'], e['position']['y']), g)
                for e in b.ents if e['name'] == 'medium-electric-pole' for g in gpoles)
        assert d <= 9, f'rotation {r * 90}: nearest medium pole {d:.1f} from a grid big pole (> 9)'
        rep.append(f'rotation {r * 90:3}: inside cell, no grid collision, grid link {d:.1f} (<= 9)')
    return rep


CORNERS = ((0, 0), (50, 0), (0, 50), (50, 50))


def corners(cw, ch):
    return tuple((50 * i, 50 * j) for j in range(ch + 1) for i in range(cw + 1))


def check_fixed(b, cw, ch):
    """Multi-cell block, no rotation: inside the cells' area (grid lines may be crossed), no grid
    collision, a medium pole within 9 of a grid big pole."""
    gtiles, gpoles = grid()
    tiles = {t for e in b.ents for t in b.tiles(e)}
    assert all(4 <= x <= 50 * cw - 3 and 2 <= y <= 50 * ch - 3 for x, y in tiles), 'outside the cells'
    hit = tiles & gtiles
    assert not hit, f'collides with grid at {sorted(hit)[:3]}'
    d = min(math.dist((e['position']['x'], e['position']['y']), g)
            for e in b.ents if e['name'] == 'medium-electric-pole' for g in gpoles)
    assert d <= 9, f'nearest medium pole {d:.1f} from a grid big pole (> 9)'
    return [f'{cw}x{ch} cells: inside, no grid collision, grid link {d:.1f} (<= 9); not rotation-safe']


def finish(b, label, icons, description=None, corner_list=CORNERS):
    """Add the corner roboports, normalise (bbox top-left (0,0)), return the blueprint dict."""
    from .bp import VERSION
    for rx, ry in corner_list:
        b.add('roboport', rx - 2, ry - 2, request_filters={'sections': [{'index': 1}]})
    x0, y0, _, _ = b.bbox()
    b.shift(-x0, -y0)
    bp = {'item': 'blueprint', 'label': label,
          'icons': [{'signal': ({'type': t} if t != 'item' else {}) | {'name': n}, 'index': i + 1}
                    for i, (t, n) in enumerate(icons)],
          'entities': b.ents, 'wires': b.wires}
    if description: bp['description'] = description
    bp['version'] = VERSION
    return bp
