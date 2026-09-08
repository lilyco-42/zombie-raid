"""太空基地压暗变体网格预览。"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_vendor_lc import SPACE_PICKS, ROOT
from render_vendor_batch2 import grid_preview

DARK_DIR = os.path.join(ROOT, "assets", "static", "vendor", "space_dark")
NAMES = [n.replace(".gltf", "") for n in SPACE_PICKS]

if __name__ == "__main__":
    grid_preview(DARK_DIR, NAMES, "vendor_space_dark.png", 4, 6.5,
                 (22.0, -24.0, 16.0), (9.75, -6.5, 0.5), lens=30.0)
