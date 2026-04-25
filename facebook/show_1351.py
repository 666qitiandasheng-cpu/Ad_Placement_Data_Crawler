with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\r\n')

# Show lines 1349-1356 with exact bytes
for i in range(1348, 1357):
    print(f'Line {i+1}: {repr(lines[i])}')