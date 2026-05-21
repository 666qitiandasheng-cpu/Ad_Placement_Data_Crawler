"""
从 ads_2026-05-07.json 读取所有有 video_url 的广告，下载视频到 videos/ 目录。
视频以 library_id.mp4 命名。
"""
import json
import urllib.request
import urllib.error
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).parent
JSON_FILE = BASE_DIR / "output" / "ads_2026-05-07.json"
VIDEO_DIR = BASE_DIR / "output" / "videos"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'video/mp4,video/*;q=0.9,*/*;q=0.1',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.facebook.com/',
}

def download_one(ad):
    video_url = ad.get('video_url', '')
    if not video_url or not video_url.startswith('http'):
        return False, ad['library_id'], 'no_url'

    fname = VIDEO_DIR / (ad['library_id'] + ".mp4")
    if fname.exists():
        return True, ad['library_id'], 'already_exists'

    try:
        req = urllib.request.Request(video_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(fname, 'wb') as f:
                shutil.copyfileobj(resp, f, length=1024*1024)
        size_mb = fname.stat().st_size / 1024 / 1024
        return True, ad['library_id'], f'downloaded ({size_mb:.1f}MB)'
    except Exception as e:
        return False, ad['library_id'], str(e)[:80]

def main():
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    ads = data.get('ads', [])
    print(f"共 {len(ads)} 条广告")

    # 统计有视频URL的广告
    with_video = [a for a in ads if str(a.get('video_url', '')).startswith('http')]
    print(f"有 video_url 的广告: {len(with_video)}")

    # 检查已下载
    existing = {f.stem for f in VIDEO_DIR.glob("*.mp4")}
    print(f"已下载视频: {len(existing)}")

    to_download = [a for a in with_video if a['library_id'] not in existing]
    print(f"待下载: {len(to_download)}")

    if not to_download:
        print("没有新视频要下载")
        return

    print(f"\n开始下载 {len(to_download)} 个视频...")
    success = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(download_one, ad): ad for ad in to_download}
        for future in as_completed(futures):
            ok, lid, msg = future.result()
            if ok:
                print(f"  [OK] {lid}: {msg}")
                success += 1
            else:
                print(f"  [FAIL] {lid}: {msg}")
                failed += 1

    print(f"\n完成！成功 {success}，失败 {failed}")

if __name__ == '__main__':
    main()
