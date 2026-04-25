# CORRECTED: each triple-quote in the line toggles the state
with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_string = False
for i, line in enumerate(lines, 1):
    count = line.count('"""')
    if count == 0:
        continue
    
    if count % 2 == 1:
        # ODD: one triple-quote → toggles state
        in_string = not in_string
        print(f'Line {i}: ODD({count}), in_string={in_string}: {repr(line[:80])}')
        if in_string:
            start_line = i
    else:
        # EVEN: TWO triple-quotes on same line, each toggles → net effect: same state as before
        in_string = not in_string  # first """
        in_string = not in_string  # second """
        # But we need to show intermediate states
        print(f'Line {i}: EVEN({count}), in_string same as before: {repr(line[:80])}')

print(f'\nFinal in_string: {in_string}')