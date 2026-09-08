"""
把 render_previews.py 生成的 6 张行走帧拼成一张序列图。

用法（必须在 render_previews.py 之后执行）：
    C:/Users/liuqi/.workbuddy/binaries/python/versions/3.13.12/python.exe tools/blender/compose_walk_sheet.py
"""

import os
import glob
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "assets", "_previews")

tiles = sorted(glob.glob(os.path.join(OUT, "_sheet_*.png")))
if not tiles:
    print("No _sheet_*.png tiles found. Run render_previews.py first.")
    raise SystemExit(1)

tiles = tiles[:6]
im0 = Image.open(tiles[0]).convert("RGB")
w, h = im0.size

canvas = Image.new("RGB", (w * len(tiles), h), (40, 40, 44))
for i, p in enumerate(tiles):
    img = Image.open(p).convert("RGB").resize((w, h), Image.LANCZOS)
    canvas.paste(img, (i * w, 0))

out_path = os.path.join(OUT, "zombie_walk_sheet.png")
canvas.save(out_path, "PNG")
print("COMPOSE ->", out_path)

# 清理中间帧
for p in tiles:
    os.remove(p)
print("CLEANED_TILES")
