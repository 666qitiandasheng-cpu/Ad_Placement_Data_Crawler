# Read the file
with open(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\run.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace ad_id patterns with ad_archive_id
# The key change: ad_archive_id is the correct field name
content = content.replace(r'ad_id[":\s]+(\d+)', r'ad_archive_id[":\s]+(\d+)')
content = content.replace(r'ad_archive_id[":\s]+(\d+)', r'ad_archive_id[":\s]+(\d+)', 1)

# Write back
with open(r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\run.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")
