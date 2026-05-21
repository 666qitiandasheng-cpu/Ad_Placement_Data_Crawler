import json
import pathlib

output_dir = pathlib.Path(__file__).parent
videos_dir = output_dir / "videos"

# 加载视频清单
with open(output_dir / "videos_manifest.json", encoding='utf-8') as f:
    manifest = json.load(f)

# 构建 library_id -> 本地路径 的字典
video_paths = {v['library_id']: v['local_path'] for v in manifest['videos']}

# 读取原始广告数据
with open(output_dir / "ads_2026-05-07.json", encoding='utf-8') as f:
    ads_data = json.load(f)

# 为每个广告添加本地视频路径（如果有）
for ad in ads_data.get('ads', []):
    lid = ad.get('library_id', '')
    if lid in video_paths:
        ad['local_video_path'] = video_paths[lid]

# 保存合并后的文件
merged_out = output_dir / "ads_2026-05-07_with_video_paths.json"
with open(merged_out, 'w', encoding='utf-8') as f:
    json.dump(ads_data, f, ensure_ascii=False, indent=2)

print(f"合并完成: {merged_out}")
print(f"共 {len(ads_data.get('ads',[]))} 条广告")
print(f"其中有本地视频: {sum(1 for a in ads_data.get('ads',[]) if 'local_video_path' in a)} 条")
