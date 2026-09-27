"""Show how product names shorten, shortest first, to spot bad cuts.

    uv run --project ~/Projects/amazon-gnucash ~/Projects/amazon-gnucash/scripts/names.py FOLDER
"""

import sys
from pathlib import Path

from amazon_gnucash.cli import find_inputs
from amazon_gnucash.emit import shorten
from amazon_gnucash.parse.export import load_digital_items, load_retail_items

_, retail, digital = find_inputs(Path(sys.argv[1]))
names = {item.name for export in retail for item in load_retail_items(export)} | {
    item.name for export in digital for item in load_digital_items(export)
}
changed = sorted({(shorten(name), name) for name in names if shorten(name) != name},
                 key=lambda pair: (len(pair[0]), pair))
for short, full in changed:
    print(f'"{short}" <- "{full}"')
print(f"{len(changed)} of {len(names)} names shortened", file=sys.stderr)
