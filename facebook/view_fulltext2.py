import json

with open(r"C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\output\block_blast\detail_fulltext.json", "r", encoding="utf-8") as f:
    data = json.load(f)

text = data["4284029755143955"]["full_text"]
lines = text.split('\n')
for i, line in enumerate(lines, 1):
    if line.strip():
        print(f"{i:4d}: {line}")
