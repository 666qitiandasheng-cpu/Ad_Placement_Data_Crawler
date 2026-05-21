import json
import pathlib

base = pathlib.Path(__file__).parent  # output directory
videos_dir = base / "videos"
videos = sorted(videos_dir.glob("*.mp4"))

manifest = {
    "total": len(videos),
    "videos": [
        {
            "library_id": v.stem,
            "filename": v.name,
            "size_mb": round(v.stat().st_size / 1024 / 1024, 1),
            "local_path": str(v.resolve())
        }
        for v in videos
    ]
}

out = base / "videos_manifest.json"
with open(out, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print(f"Manifest saved: {out}")
print(f"Total videos: {len(videos)}")
