# Find exactly where in_string is True and shouldn't be
# Track line numbers where in_string=True
with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_string = False
problems = []
for i, line in enumerate(lines, 1):
    count = line.count('"""')
    if count == 0:
        continue
    if count % 2 == 0:
        in_string = not in_string
    else:
        in_string = not in_string
    
    if in_string and i > 960:
        problems.append((i, line.rstrip()))
        if len(problems) > 5:
            break

print('First 5 problems (in_string=True after line 960):')
for lineno, line in problems:
    print(f'Line {lineno}: {repr(line[:80])}')