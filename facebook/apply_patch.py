# -*- coding: utf-8 -*-
import re

DEST = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py'
FUNC_FILE = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\_new_parse_func.py'

# Read the new function source
with open(FUNC_FILE, 'r', encoding='utf-8') as f:
    new_func_src = f.read()

# Read destination
with open(DEST, 'r', encoding='utf-8') as f:
    dest = f.read()

# Find boundaries (text mode)
func_start = dest.find('\ndef parse_detail_text(')
region_start = dest.find('\ndef parse_region_block(', func_start)
print(f"func_start={func_start}, region_start={region_start}")

# Replace
new_dest = dest[:func_start] + '\n' + new_func_src + '\n' + dest[region_start:]

# Verify syntax
import ast
try:
    ast.parse(new_dest)
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.msg}")
    # Show the problematic lines
    lines = new_dest.split('\n')
    for i in range(max(0, e.lineno-3), min(len(lines), e.lineno+2)):
        print(f"  {i+1}: {repr(lines[i][:100])}")
    import sys; sys.exit(1)

with open(DEST, 'w', encoding='utf-8') as f:
    f.write(new_dest)

print("Done!")