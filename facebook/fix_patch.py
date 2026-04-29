# -*- coding: utf-8 -*-
"""Fix scrape_detail.py: replace parse_detail_text using raw byte search"""
import re, sys, ast

DEST = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py'
NEW_SRC = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\_new_parse_func.py'

with open(DEST, 'rb') as f:
    raw = f.read()
print(f"File size: {len(raw)}")

with open(NEW_SRC, 'r', encoding='utf-8') as f:
    new_func_src = f.read()

# Verify new function is valid Python
try:
    ast.parse(new_func_src)
    print("New function syntax OK")
except SyntaxError as e:
    print(f"New function syntax error: {e}")
    sys.exit(1)

# Convert to bytes (utf-8) for replacement
new_func_bytes = new_func_src.encode('utf-8')

# Find parse_detail_text start - scan for "def parse_detail_text(" 
func_pattern = b'def parse_detail_text('
func_start = raw.find(func_pattern)
if func_start == -1:
    print("ERROR: parse_detail_text def not found")
    sys.exit(1)
print(f"parse_detail_text starts at byte {func_start}")

# Find parse_region_block start
region_pattern = b'def parse_region_block('
region_start = raw.find(region_pattern, func_start + len(func_pattern))
if region_start == -1:
    print("ERROR: parse_region_block not found")
    sys.exit(1)
print(f"parse_region_block starts at byte {region_start}")

# Check what's between func_start and func_start+200
print(f"Before func: {raw[func_start-30:func_start]!r}")
print(f"After func start: {raw[func_start:func_start+60]!r}")
print(f"Before region: {raw[region_start-30:region_start]!r}")

# Build new content
new_raw = raw[:func_start] + b'\n' + new_func_bytes + b'\n' + raw[region_start:]
print(f"New file size: {len(new_raw)}")

# Verify syntax
try:
    ast.parse(new_raw.decode('utf-8'))
    print("Combined syntax OK")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}: {e.msg}")
    lines = new_raw.decode('utf-8').split('\n')
    for i in range(max(0, e.lineno-3), min(len(lines), e.lineno+3)):
        print(f"  {i+1}: {repr(lines[i][:100])}")
    sys.exit(1)

with open(DEST, 'wb') as f:
    f.write(new_raw)

print("Done - patched successfully!")