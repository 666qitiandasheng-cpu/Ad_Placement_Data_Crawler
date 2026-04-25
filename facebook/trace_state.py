with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Manually simulate the state
in_string = False
state_log = []
for i, line in enumerate(lines, 1):
    count = line.count('"""')
    if count == 0:
        continue
    if count % 2 == 0:
        in_string = not in_string
        state_log.append(f'Line {i}: flip({count}), in_string={in_string}: {repr(line[:60])}')
    else:
        in_string = not in_string
        state_log.append(f'Line {i}: odd({count}), in_string={in_string}: {repr(line[:60])}')

# Show transitions around lines 913, 948, 1403
print('Around line 913:')
for e in state_log:
    lineno = int(e.split(':')[0].replace('Line ', ''))
    if 910 <= lineno <= 950:
        print(e)

print('\nAround line 1403:')
for e in state_log:
    lineno = int(e.split(':')[0].replace('Line ', ''))
    if 1400 <= lineno <= 1410:
        print(e)