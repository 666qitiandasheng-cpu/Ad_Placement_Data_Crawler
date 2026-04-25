with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'rb') as f:
    data = f.read()

# Find Strategy 1 js_script
idx = data.find(b'js_script = ')
print(f'js_script = at byte {idx}')

# Find the string concatenation
idx2 = data.find(b'% (region_labels,) + ')
print(f'concatenation at byte {idx2}')
print(repr(data[idx2:idx2+100]))

# Look at the raw bytes around the concatenation
chunk = data[idx2:idx2+200]
print('\nHex around concatenation:')
for i, b in enumerate(chunk[:50]):
    print(f'{b:3d} 0x{b:02x} {chr(b) if 32 <= b < 127 else "?"}', end=' ')
    if (i+1) % 10 == 0:
        print()
