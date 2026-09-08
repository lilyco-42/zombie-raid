"""后室 (Backrooms) 风格变体: 灰石烘成芥末黄壁纸/潮湿地毯。

输出 static/vendor/backrooms/ — 与 SCP 灰色区、LC 暗区形成分区识别。
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_vendor_lc import SPACE_DIR
from build_vendor_batch2 import curate_batch
from build_vendor_lc import ROOT

VENDOR = os.path.join(ROOT, "assets", "vendor", "kaykit")
DGN = os.path.join(VENDOR, "KayKit-Dungeon-Remastered-1.0",
                   "addons", "kaykit_dungeon_remastered", "Assets", "gltf")

# 芥末黄: 去饱和后整体乘黄 (壁纸感); 地毯用更土的黄褐
WALL_SAT, WALL_TINT = 0.55, (0.82, 0.70, 0.40)
CARPET_SAT, CARPET_TINT = 0.60, (0.62, 0.55, 0.38)

PIECES_WALL = [
    "wall.gltf.glb", "wall_arched.gltf.glb", "wall_doorway.glb",
    "pillar.gltf.glb", "column.gltf.glb",
]

if __name__ == "__main__":
    out_dir = os.path.join(ROOT, "assets", "static", "vendor", "backrooms")
    n1, m1 = curate_batch(DGN, PIECES_WALL, "backrooms", WALL_SAT, WALL_TINT)
    n2, m2 = curate_batch(DGN, ["floor_dirt_large.gltf.glb"], "backrooms",
                          CARPET_SAT, CARPET_TINT)
    print(f"BACKROOMS_DONE walls={n1} carpet={n2}")
    if m1 or m2:
        print("MISSING:", m1 + m2)
