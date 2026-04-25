with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The js_script block spans lines 913-948
# Let's extract and print it cleanly
lines = content.split('\n')
for i in range(912, 952):
    print(f'{i+1:4d}: {lines[i]}')