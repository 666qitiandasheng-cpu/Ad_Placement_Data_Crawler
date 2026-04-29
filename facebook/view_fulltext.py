import json

with open(r"C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\output\block_blast\detail_ads_Block_Blast_2026-04-29.json", "r", encoding="utf-8") as f:
    data = json.load(f)

text = data["4284029755143955"]["full_text"]
print(f"Total length: {len(text)}")
print("=" * 60)

# Print with line numbers for analysis
for i, line in enumerate(text.split('\n'), 1):
    if line.strip():
        print(f"{i:4d}: {line}")
