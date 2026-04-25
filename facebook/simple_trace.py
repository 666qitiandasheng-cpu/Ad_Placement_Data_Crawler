with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Simple state: each line's """" toggles in_string
in_string = False
for i, line in enumerate(lines, 1):
    count = line.count('"""')
    if count == 0:
        continue
    
    if count % 2 == 1:
        in_string = not in_string
        print(f'Line {i}: ODD({count}), in_string={in_string}: {repr(line[:80])}')
        if in_string:
            start_line = i
    else:
        # Even count - flip twice = same state but we're still "in a string" context
        # after the line. Simple simulation: flip once for even (like odd)
        in_string = not in_string
        print(f'Line {i}: EVEN({count}), in_string={in_string}: {repr(line[:80])}')
        if in_string:
            start_line = i

print(f'\nFinal in_string: {in_string}')
# Find string that never closed
if in_string:
    print(f'String starting at line {start_line} never closed')