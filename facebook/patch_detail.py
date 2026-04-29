"""
Patch scrape_detail.py: add debug print and fix extract_block
"""
import re

path = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\scrape_detail.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add debug print after "Dialog text length"
old = '        print(f"  [CDP] Dialog text length: {len(full_text)}")\n'
if old in content:
    content = content.replace(old, old + '        if full_text:\n            print(f"  [CDP] Text preview: {repr(full_text[:300])}")\n')
    print("Added debug print")
else:
    print("Could not find target string")

# Fix extract_block: remove the [:1500] slice limit
old_block = "        return block[:1500] if block else None\n"
new_block = "        return block if block else None\n"
if old_block in content:
    content = content.replace(old_block, new_block)
    print("Fixed extract_block")
else:
    print("extract_block already fixed or not found")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done patching")