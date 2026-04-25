with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'rb') as f:
    data = f.read()

lines = data.split(b'\r\n')
# Show lines 945-955
for i in range(944, 956):
    print(f'Line {i+1}: {repr(lines[i])}')