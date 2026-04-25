import ast
with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'r', encoding='utf-8') as f:
    source = f.read()

# Try to find where the triple-quote issue is
# First let's see what the parser complains about specifically
try:
    ast.parse(source)
    print('Parse OK')
except SyntaxError as e:
    print(f'Error at line {e.lineno}: {e.msg}')
    lines = source.split('\n')
    # Show lines around error
    start = max(0, e.lineno - 5)
    for i in range(start, min(len(lines), e.lineno + 3)):
        marker = ' >>> ' if i == e.lineno - 1 else '     '
        print(f'{marker}Line {i+1}: {repr(lines[i][:120])}')