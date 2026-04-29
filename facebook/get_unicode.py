import sys
sys.stdout.reconfigure(encoding='utf-8')

# 用实际字符查 Unicode 编码
markers = [
    "广告信息公示（按地区）",
    "关于广告赞助方",
    "关于广告主",
    "广告主和付费方",
    "欧盟",
    "英国",
    "广告主\n",
    "付费方\n",
]

for m in markers:
    print(f"{m!r} -> {m.encode('unicode_escape').decode('ascii')}")
