with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'rb') as f:
    data = f.read()

# Count triple-quote occurrences per line (byte-based)
lines = data.split(b'\r\n')
for i, line in enumerate(lines, 1):
    count = line.count(b'"""')
    if count > 0:
        print(f'Line {i}: {count}x """ : {repr(line[:80])}')