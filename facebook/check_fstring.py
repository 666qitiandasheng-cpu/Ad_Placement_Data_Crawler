with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
# Check line 692 (index 691)
for i in range(690, 702):
    print(f'Line {i+1}: {repr(lines[i])}')