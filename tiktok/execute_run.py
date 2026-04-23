import sys
import os

os.chdir(r'C:\Users\Ivy\.openclaw\workspace\tiktok')

log_file = open(r'C:\Users\Ivy\.openclaw\workspace\tiktok\output\run_log.txt', 'w', encoding='utf-8')
sys.stdout = log_file
sys.stderr = log_file

print('Starting tiktok run.py (test 5 records)...', flush=True)

try:
    import run
    run.main()
    print('Done!', flush=True)
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}', flush=True)
    import traceback
    traceback.print_exc()

log_file.close()