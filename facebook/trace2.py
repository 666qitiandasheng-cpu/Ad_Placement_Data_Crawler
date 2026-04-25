# Find exactly which line opens the unclosed string that closes at line 1406
with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# State machine: open_count=0 means we're in normal code
# When we hit a TSTRING START, increment open_count
# When we hit TSTRING END, decrement open_count
# The one that leaves open_count > 0 at EOF is the culprit
open_count = 0
for i, line in enumerate(lines, 1):
    count = line.count('"""')
    if count == 0:
        continue
    if count % 2 == 0:
        # Even: pairs of triple quotes flip open_count
        open_count += (1 if count > 0 else 0)  # adds count/2 pairs, but this flips open_count
        # Actually: if count=2, that's one pair = closes what was opened
        open_count = 1 - open_count  # simple flip: was open, now closed (or vice versa)
        print(f'Line {i}: flip count={count}, open_count now={open_count}: {repr(line[:60])}')
    else:
        # Odd: opens a new string
        open_count = 1 - open_count
        print(f'Line {i}: odd count={count}, open_count now={open_count} (START string): {repr(line[:60])}')
        start_line = i

print(f'\nopen_count at EOF: {open_count}')
print(f'String that never closed started at line: {start_line}')