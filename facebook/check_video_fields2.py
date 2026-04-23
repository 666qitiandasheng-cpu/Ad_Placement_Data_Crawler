import re

PAGE_SOURCE_FILE = r'C:\Users\Ivy\.openclaw\workspace\facebook_ad_scraper\debug\page_source_114846.html'

with open(PAGE_SOURCE_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Find all unique fields that contain video or media
fields = re.findall(r'"(video_[^"]+|media_[^"]+)"', content)
unique_fields = set(fields)
print("视频/媒体相关字段:")
for f in sorted(unique_fields):
    print(f"  {f}")

# Also check for any "url" fields
url_fields = re.findall(r'"(\w*_url)"', content)
unique_url = set(url_fields)
print("\nURL 相关字段:")
for f in sorted(unique_url):
    print(f"  {f}")

# Check for any "permalink" or "permanent" fields
perm_fields = re.findall(r'"(\w*permanent\w*|\w*permalink\w*)"', content, re.IGNORECASE)
if perm_fields:
    print(f"\n永久链接相关字段: {perm_fields}")
else:
    print(f"\n没有找到 permanent/permalink 字段")
