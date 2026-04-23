@echo off
cd /d C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper
del /f run_output2.txt 2>nul
python -u run.py > run_output2.txt 2>&1
echo DONE >> run_output2.txt
