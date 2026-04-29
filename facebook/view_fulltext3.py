import json, sys

with open(r"C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\output\block_blast\detail_fulltext.json", "r", encoding="utf-8") as f:
    data = json.load(f)

text = data["4284029755143955"]["full_text"]
lines = text.split('\n')

with open(r"C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\fulltext_4284029755143955.txt", "w", encoding="utf-8") as out:
    for i, line in enumerate(lines, 1):
        if line.strip():
            out.write(f"{i:4d}: {line}\n")

print("Done", len(lines), "lines")
