"""Oil megapack: David's own design, added AS IS (no adaptation, no re-validation).
Source: import/oil-megapack.txt. Copies the string and writes the decoded JSON + a preview."""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from lib.bp import decode, render

s = (ROOT / 'import' / 'oil-megapack.txt').read_text().strip()
obj = decode(s)
(HERE / 'blueprint.txt').write_text(s + '\n')
(HERE / 'blueprint.json').write_text(json.dumps(obj, indent=1) + '\n')
render(HERE, obj['blueprint'], px=3, grid=50)
