with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'rb') as f:
    data = f.read()
import re
for m in re.finditer(rb'"""', data):
    start = m.start()
    prefix = data[:start]
    lineno = prefix.count(b'\r\n') + 1
    print(f'Line {lineno}: pos {start}, context: {repr(data[max(0,start-40):start+60])}')