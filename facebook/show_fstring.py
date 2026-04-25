with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\r\n')
# Show lines 690-700 with exact bytes
for i in range(689, 702):
    print(f'Line {i+1} ({len(lines[i])} bytes): {repr(lines[i])}')