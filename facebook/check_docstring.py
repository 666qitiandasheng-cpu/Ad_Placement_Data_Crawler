with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check lines 720-735 (the function with docstring and f-string triple quotes)
print("Lines 720-735:")
for i in range(719, 736):
    print(f'Line {i+1}: {repr(lines[i][:100])}')