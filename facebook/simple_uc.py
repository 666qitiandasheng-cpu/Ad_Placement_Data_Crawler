import sys
out_file = open(r'C:\Users\Ivy\.openclaw\workspace\Ad_Placement_Data_Crawler\facebook\simple_test.txt', 'w', encoding='utf-8')
out_file.write('Starting test\n')
out_file.flush()

try:
    import undetected_chromedriver as uc
    out_file.write('imported uc\n')
    out_file.flush()
    
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless=new')
    
    out_file.write('starting chrome\n')
    out_file.flush()
    driver = uc.Chrome(options=options, version_main=147)
    out_file.write('chrome started\n')
    out_file.flush()
    
    driver.get('https://google.com')
    out_file.write('got google\n')
    out_file.flush()
    
    title = driver.title
    out_file.write(f'title: {title}\n')
    out_file.flush()
    
    driver.quit()
    out_file.write('done\n')
    out_file.flush()
except Exception as e:
    out_file.write(f'Error: {e}\n')
    import traceback
    traceback.print_exc(file=out_file)
    out_file.flush()
finally:
    out_file.close()
