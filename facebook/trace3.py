with open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\run.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# State machine: each line's triple-quotes change the state
# in_string=True means we're INSIDE a triple-quoted string
in_string = False
for i, line in enumerate(lines, 1):
    count = line.count('"""')
    if count == 0:
        continue
    
    if count % 2 == 1:
        # ODD number: starts a string if we weren't in one, or ends one if we were
        in_string = not in_string
        print(f'Line {i}: ODD({count}), in_string={in_string} (string {"STARTS" if in_string else "ENDS"}): {repr(line[:80])}')
        if in_string:
            start_line = i
    else:
        # EVEN number: if count>0, it's a pair of """, so close one string and open another
        # In this context, with 2 """, first one closes, second one opens
        # So: close + open = net: opens a new string
        print(f'Line {i}: EVEN({count}), in_string={in_string} (string continues): {repr(line[:80])}')
        # Actually with count=2: we go from in_string to NOT in_string (close) then to in_string (open)
        # So net effect: close then immediately open = state doesn't change... but we ARE in a string
        # Wait - if we were in_string=True, then close means in_string=False, then open means in_string=True again
        # So even count flips twice: stays same
        # But the "continues" message says it doesn't close
        # Let me reconsider: if count=2 and we're at line 948, we close js_script (entering normal code)
        # then immediately open a new string. After both operations, we're in a string again.
        # So state at start of line: in_string
        # After first """: NOT in_string
        # After second """: in_string
        # Net: same as start, but we ARE in a string
        if in_string:
            # We were in a string, it was closed, now reopened
            print(f'  -> (was in_string=True, closed, now reopened at same line)')

print(f'\nFinal in_string: {in_string}')