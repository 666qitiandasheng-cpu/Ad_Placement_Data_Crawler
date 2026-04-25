with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Track bracket/string state - simplified approach
# Look for unclosed triple-quoted strings
in_triple = False
triple_start_line = 0
for i, line in enumerate(lines, 1):
    # Count triple quotes in line
    count = line.count('"""')
    if count % 2 == 1:
        if not in_triple:
            in_triple = True
            triple_start_line = i
            print(f'Unclosed triple quote opens at line {i}: {repr(line[:60])}')
        else:
            in_triple = False
            print(f'  Closed at line {i}: {repr(line[:60])}')
            triple_start_line = 0
    # Check for f-string triple quotes too
    fcount = line.count('f"""')
    if fcount % 2 == 1:
        if not in_triple:
            print(f'f""" unclosed at line {i}: {repr(line[:60])}')
        else:
            print(f'f""" closes something at line {i}: {repr(line[:60])}')

# Also check for single-quoted strings that might be open
# Simple bracket matching
brackets = {'(': 0, '[': 0, '{': 0}
for i, line in enumerate(lines, 1):
    for c in line:
        if c == '(':
            brackets['('] += 1
        elif c == ')':
            brackets['('] -= 1
        elif c == '[':
            brackets['['] += 1
        elif c == ']':
            brackets['['] -= 1
        elif c == '{':
            brackets['{'] += 1
        elif c == '}':
            brackets['{'] -= 1

for k, v in brackets.items():
    if v != 0:
        print(f'Unclosed bracket {k}: count={v}')