import os
p = r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\debug_html.html'
print('size:', os.path.getsize(p))
with open(p, 'rb') as f:
    data = f.read(1000)
print(data[:500])
