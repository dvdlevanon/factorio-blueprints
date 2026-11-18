"""Build book.txt + book.json for a library book dir (nested books supported).
Usage: python3 tools/build_book.py library/<book>"""
import json, sys, yaml
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.bp import encode, VERSION

def icons(lst):
    return [{'signal': ({'type': i['type']} if i['type'] != 'item' else {}) | {'name': i['name']}, 'index': k + 1}
            for k, i in enumerate(lst or [])]

def book(d: Path) -> dict:
    meta = yaml.safe_load((d / 'book.yaml').read_text())
    # rows: list of lists; each starts at a multiple of row_width (sparse indices). Else order: then the rest.
    if 'rows' in meta:
        w = meta.get('row_width', 10)
        slots = [(r * w + c, d / n) for r, row in enumerate(meta['rows']) for c, n in enumerate(row)]
        assert all(len(row) <= w for row in meta['rows'])
    else:
        kids = [d / n for n in meta.get('order', [])]
        slots = list(enumerate(kids))
    listed = {k for _, k in slots}
    rest = sorted(p for p in d.iterdir() if p.is_dir() and p not in listed and not p.name.startswith('_'))
    nxt = max((i for i, _ in slots), default=-1) + 1
    slots += [(nxt + i, k) for i, k in enumerate(rest)]
    entries = []
    for i, k in slots:
        if (k / 'book.yaml').exists(): entries.append(dict(index=i, **book(k)))
        elif (k / 'blueprint.json').exists(): entries.append(dict(index=i, **json.loads((k / 'blueprint.json').read_text())))
        else: raise SystemExit(f'missing {k}')
    b = {'item': 'blueprint-book', 'label': meta['label'], 'icons': icons(meta.get('icons')),
         'blueprints': entries,
         'active_index': 0, 'version': VERSION}
    if meta.get('description'): b['description'] = meta['description']
    return {'blueprint_book': b}

d = Path(sys.argv[1])
obj = book(d)
(d / 'book.json').write_text(json.dumps(obj, indent=1) + '\n')
(d / 'book.txt').write_text(encode(obj) + '\n')
print(d / 'book.txt', len(obj['blueprint_book']['blueprints']), 'entries')
