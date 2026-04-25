with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Track triple-quote state manually
in_string = False
for i, line in enumerate(lines, 1):
    count = line.count('"""')
    if count == 0:
        continue
    if count % 2 == 0:
        # Even - flips state
        in_string = not in_string
        print(f'Line {i}: flip (count={count}), in_string={in_string}: {repr(line[:80])}')
    else:
        # Odd - new state
        print(f'Line {i}: odd={count}, START in_string={in_string}: {repr(line[:80])}')
        in_string = not in_string
    if i > 960 or (in_string and i < 950 and i > 910):
        pass  # skip for brevity

# Show around lines 945-955
print('\n\nLines 945-955:')
for i in range(944, 956):
    print(f'Line {i+1}: {repr(lines[i][:100])}')