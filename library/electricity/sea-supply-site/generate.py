"""Sea supply, site side: 7 belts arrive from the EAST, each product into its own filtered
storage chest (landfill: 8 chests), robots straight into the roboport; return lane from one open storage chest back EAST.
Standalone (no snapping): it sits at the sea next to the solar fields."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from lib.bp import write_outputs, render, VERSION
from lib.build import validate
from lib.sea_supply import site_block, make_site_rules

b = site_block()
b.wire_poles()
rep, belts = validate(b, make_site_rules(b))
x0, y0, _, _ = b.bbox(); b.shift(-x0, -y0)
bp = {'item': 'blueprint', 'label': 'Sea Supply - Site',
      'icons': [{'signal': {'name': 'storage-chest'}, 'index': 1}, {'signal': {'name': 'roboport'}, 'index': 2}],
      'entities': b.ents, 'wires': b.wires, 'version': VERSION}
for l in rep: print(l)
print('belt ends (7 column tops + return exit):', sorted(belts['ends']))
write_outputs(HERE, bp)
render(HERE, bp, px=12, grid=0)
