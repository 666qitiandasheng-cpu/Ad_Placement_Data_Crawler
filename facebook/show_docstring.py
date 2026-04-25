with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\r\n')
# Check lines 724-730 with exact bytes
for i in range(723, 731):
    print(f'Line {i+1}: {repr(lines[i])}')