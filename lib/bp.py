"""Blueprint string encode/decode, output writing, simple preview renderer."""
import base64, json, zlib
from pathlib import Path

VERSION = 562954249961473  # from David's 2.1.24 calibration export (same as 2.0)

def decode(s: str) -> dict:
    s = s.strip()
    return json.loads(zlib.decompress(base64.b64decode(s[1:])))

def encode(obj: dict) -> str:
    raw = json.dumps(obj, separators=(',', ':')).encode()
    return '0' + base64.b64encode(zlib.compress(raw, 9)).decode()

def write_outputs(outdir: Path, bp: dict):
    """bp is the inner blueprint dict. Writes blueprint.txt and blueprint.json."""
    obj = {'blueprint': bp}
    (outdir / 'blueprint.json').write_text(json.dumps(obj, indent=1) + '\n')
    (outdir / 'blueprint.txt').write_text(encode(obj) + '\n')

# ---------- preview ----------
SIZES = {'roboport': (4, 4), 'big-electric-pole': (2, 2), 'small-lamp': (1, 1), 'solar-panel': (3, 3),
         'accumulator': (2, 2), 'medium-electric-pole': (1, 1), 'substation': (2, 2), 'chemical-plant': (3, 3),
         'assembling-machine-3': (3, 3), 'oil-refinery': (5, 5), 'storage-tank': (3, 3), 'rocket-silo': (9, 9)}
COLORS = {'roboport': (200, 120, 40), 'big-electric-pole': (90, 90, 110), 'small-lamp': (250, 230, 90),
          'solar-panel': (40, 60, 110), 'accumulator': (120, 120, 130), 'medium-electric-pole': (150, 90, 60),
          'substation': (110, 110, 140), 'transport-belt': (150, 130, 40), 'underground-belt': (110, 95, 30),
          'requester-chest': (60, 110, 200), 'storage-chest': (210, 180, 50), 'fast-inserter': (70, 130, 200),
          'display-panel': (40, 40, 40), 'express-transport-belt': (60, 130, 170),
          'express-underground-belt': (40, 95, 130), 'long-handed-inserter': (190, 60, 60),
          'chemical-plant': (110, 140, 110), 'express-splitter': (30, 80, 120), 'bulk-inserter': (60, 170, 90),
          'assembling-machine-3': (120, 125, 150), 'fast-transport-belt': (170, 50, 50),
          'fast-underground-belt': (130, 40, 40), 'oil-refinery': (150, 110, 70),
          'storage-tank': (90, 110, 130), 'pump': (80, 80, 100), 'pipe': (140, 140, 150), 'pipe-to-ground': (100, 100, 115), 'rocket-silo': (170, 170, 190)}
ABBR = {'landfill': 'LF', 'solar-panel': 'SP', 'accumulator': 'AC', 'medium-electric-pole': 'MP',
        'big-electric-pole': 'BP', 'roboport': 'RP', 'construction-robot': 'CR', 'raw-fish': 'F',
        'plastic-bar': 'PL', 'coal': 'C', 'petroleum-gas': 'PG', 'sulfur': 'S', 'water': 'W',
        'sulfuric-acid': 'SA', 'battery': 'BA', 'explosives': 'EX', 'iron-plate': 'Fe', 'copper-plate': 'Cu',
        'copper-cable': 'cc', 'electronic-circuit': 'GC', 'iron-gear-wheel': 'G',
        'automation-science-pack': 'R', 'logistic-science-pack': 'Gr', 'military-science-pack': 'M',
        'chemical-science-pack': 'B', 'production-science-pack': 'P', 'utility-science-pack': 'Y'}
_V = {0: (0, -1), 4: (1, 0), 8: (0, 1), 12: (-1, 0)}

def render(outdir: Path, bp: dict, px: int = 3, grid: int = 50):
    from PIL import Image, ImageDraw
    ents = bp['entities']
    xs = [e['position']['x'] for e in ents]; ys = [e['position']['y'] for e in ents]
    x0, y0 = int(min(xs)) - 4, int(min(ys)) - 4
    x1, y1 = int(max(xs)) + 5, int(max(ys)) + 5
    img = Image.new('RGB', ((x1 - x0) * px, (y1 - y0) * px), (30, 32, 30))
    dr = ImageDraw.Draw(img)
    T = lambda x, y: ((x - x0) * px, (y - y0) * px)
    if grid:
        for gx in range((x0 // grid) * grid, x1 + 1, grid):
            dr.line([T(gx, y0), T(gx, y1)], fill=(45, 50, 45))
        for gy in range((y0 // grid) * grid, y1 + 1, grid):
            dr.line([T(x0, gy), T(x1, gy)], fill=(45, 50, 45))
    byid = {e['entity_number']: e for e in ents}
    for a, _, b, _ in bp.get('wires', []):
        pa, pb = byid[a]['position'], byid[b]['position']
        dr.line([T(pa['x'], pa['y']), T(pb['x'], pb['y'])], fill=(180, 100, 60), width=1)
    for e in ents:
        w, h = SIZES.get(e['name'], (1, 1)); p = e['position']; cx, cy = p['x'], p['y']
        if 'splitter' in e['name']: w, h = (1, 2) if e.get('direction') in (4, 12) else (2, 1)
        dr.rectangle([T(cx - w / 2, cy - h / 2), T(cx + w / 2, cy + h / 2)],
                     fill=COLORS.get(e['name'], (200, 0, 200)), outline=(0, 0, 0))
        d = e.get('direction')
        if px >= 8 and d in _V:
            vx, vy = _V[d]
            if e['name'] in ('fast-inserter', 'long-handed-inserter', 'bulk-inserter'):   # direction = pickup side; arrow pickup -> drop
                vx, vy = -vx, -vy
            a = (cx - vx * .35, cy - vy * .35); b = (cx + vx * .35, cy + vy * .35)
            dr.line([T(*a), T(*b)], fill=(0, 0, 0), width=max(1, px // 6))
            dr.ellipse([T(b[0] - .12, b[1] - .12), T(b[0] + .12, b[1] + .12)], fill=(0, 0, 0))
            if e['name'] in ('underground-belt', 'fast-underground-belt', 'express-underground-belt'):
                dr.text(T(cx - .3, cy - .45), 'i' if e['type'] == 'input' else 'o', fill=(255, 255, 255))
        if px >= 8:
            item = None
            if 'icon' in e: item = e['icon']['name']
            elif 'recipe' in e: item = e['recipe']
            elif e.get('request_filters', {}).get('sections', [{}])[0].get('filters'):
                item = e['request_filters']['sections'][0]['filters'][0]['name']
            if item:
                dr.text(T(cx - .45, cy - .4), ABBR.get(item, item[:2]), fill=(255, 255, 255))
    img.save(outdir / 'preview.png')
