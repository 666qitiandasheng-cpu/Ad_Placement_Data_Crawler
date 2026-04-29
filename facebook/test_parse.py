import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

import json
from pathlib import Path

# Import from the actual module
sys.path.insert(0, r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook')
from scrape_detail import parse_detail_text

# Load raw full_text
with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\output\block_blast\detail_fulltext.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Available IDs: {list(data.keys())}", flush=True)

for lid, entry in data.items():
    full_text = entry['full_text']
    print(f"\n{'='*50}\nParsing: {lid} ({len(full_text)} chars)\n{'='*50}", flush=True)
    result = parse_detail_text(full_text, lid)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
