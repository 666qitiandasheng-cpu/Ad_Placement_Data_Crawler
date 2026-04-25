# CORRECT: each triple-quote toggles the state
with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_string = False
flips = 0
for i, line in enumerate(lines, 1):
    count = line.count('"""')
    if count == 0:
        continue
    
    for k in range(count):
        in_string = not in_string
        flips += 1
    
    if count == 1:
        print(f'Line {i}: 1x """ -> in_string={in_string}: {repr(line[:80])}')
    else:
        print(f'Line {i}: {count}x """ -> in_string={in_string}: {repr(line[:80])}')
        if in_string and i > 910:
            start_line = i

print(f'\nFinal in_string: {in_string}')